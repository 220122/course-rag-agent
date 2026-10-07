"""
文本语义切块模块

切块策略：按段落（换行）切开后，把**连续段落累积合并**成接近 chunk_size 的文本块，
而不是让每个段落各自成块。这样做的原因：

1. 电子书 / 课件往往「一行即一段」，逐段成块会产生大量一二百字符的碎块，
   每块上下文太少，检索命中率差；碎块数量多还会放大向量化接口的每请求固定开销。
2. 过短的段落（章节标题）若单独成块，会因关键词高度匹配而挤占检索 Top-K 名额，
   导致真正含答案的段落被排除，表现为「检索到了却答不出来」。

处理要点：
- 章节标题处另起一块，使块边界尽量与小节对齐；连续标题会合并，不会各自单独成块。
- 标题识别只认**多级编号**（1.1 / 1.2.3）、第X章/节、中文数字顿号（一、），
  以免把「1.试说明…」这类编号习题误判成标题（那样会让整份习题粘连成一个超大块）。
- 过滤页眉页脚噪声：纯数字页码、在文中重复出现多次的短行（如书名页眉）。
- 段落本身超过 chunk_size 时才滑窗切分，并保留 chunk_overlap 的重叠。
"""
import re
from collections import Counter

from config import settings

# 章节标题特征：只认多级编号 / 第X章节 / 中文数字顿号
_HEADING_RE = re.compile(
    r'^\s*(?:'
    r'\d+\.\d+(?:\.\d+)*[\s、.．]'                     # 1.1 / 1.2.3
    r'|第[一二三四五六七八九十百零\d]+[章节讲编部]'       # 第二章 / 第3节
    r'|[一二三四五六七八九十]+[、.．]'                  # 一、
    r')'
)

_HEADING_MAX_CHARS = 40        # 标题一般较短
_PURE_DIGIT_RE = re.compile(r'^\d{1,4}$')   # 纯数字 = 页码
_REPEAT_MAX_CHARS = 15         # 短于此长度且反复出现 => 页眉页脚
_REPEAT_MIN_COUNT = 8
_SENTENCE_END = '。！？；：，,.!?'   # 以这些结尾的不是标题
_MIN_SECTION_CHARS = 80        # 缓冲小于此长度时，不与下一个标题断开，避免碎块


def _is_heading(para: str) -> bool:
    """判断某段落是否像章节标题。"""
    if not para or len(para) > _HEADING_MAX_CHARS:
        return False
    if para[-1] in _SENTENCE_END:      # 句子结尾 => 是正文，不是标题
        return False
    return bool(_HEADING_RE.match(para))


def _drop_noise(paragraphs: list[str]) -> tuple[list[str], dict]:
    """过滤页码与重复出现的页眉页脚短行。返回 (保留的段落, 统计)。"""
    counts = Counter(p for p in paragraphs if len(p) <= _REPEAT_MAX_CHARS)

    kept, dropped_digit, dropped_repeat = [], 0, 0
    for p in paragraphs:
        if _PURE_DIGIT_RE.match(p):
            dropped_digit += 1
            continue
        if len(p) <= _REPEAT_MAX_CHARS and counts[p] >= _REPEAT_MIN_COUNT:
            dropped_repeat += 1
            continue
        kept.append(p)

    return kept, {"dropped_page_numbers": dropped_digit,
                  "dropped_repeated_headers": dropped_repeat}


def split_text(text: str) -> list[str]:
    """
    将长文本切分为带重叠的文本块。
    1. 按换行拆成段落，过滤空行与页眉页脚噪声；
    2. 连续段落合并累积，直到接近 chunk_size；
    3. 章节标题处另起新块（连续标题会合并）；
    4. 超长段落滑窗切分并保留 overlap。
    """
    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap

    raw = [p.strip() for p in text.split("\n") if p.strip()]
    paragraphs, _ = _drop_noise(raw)

    chunks: list[str] = []
    buf: list[str] = []
    buf_has_body = False   # 缓冲区里是否已有正文（非标题）

    def buf_len() -> int:
        return sum(len(p) for p in buf) + max(0, len(buf) - 1)

    def flush() -> None:
        nonlocal buf, buf_has_body
        if buf:
            chunks.append("\n".join(buf))
            buf = []
            buf_has_body = False

    for para in paragraphs:
        # --- 章节标题：另起一块；连续标题累积，但不让其无限增长 ---
        if _is_heading(para):
            too_big = bool(buf) and buf_len() + 1 + len(para) > chunk_size
            # 缓冲里已有足够正文才断开；正文太少则并入本节，避免产生碎块
            worth_break = buf_has_body and buf_len() >= _MIN_SECTION_CHARS
            if too_big or worth_break:
                flush()
            buf.append(para)
            continue

        # --- 超长段落：并入缓冲后滑窗切分，避免标题单独成块 ---
        if len(para) > chunk_size:
            merged = "\n".join(buf + [para]) if buf else para
            buf, buf_has_body = [], False
            start = 0
            while start < len(merged):
                end = start + chunk_size
                chunks.append(merged[start:end])
                if end >= len(merged):
                    break
                start = end - overlap  # 回退 overlap 个字符形成重叠
            continue

        # --- 普通段落：累积合并到接近 chunk_size ---
        if not buf:
            buf.append(para)
            buf_has_body = True
        elif buf_len() + 1 + len(para) <= chunk_size:
            buf.append(para)
            buf_has_body = True
        else:
            flush()
            buf.append(para)
            buf_has_body = True

    flush()
    return [c.strip() for c in chunks if c.strip()]
