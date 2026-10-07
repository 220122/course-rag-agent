"""
文本语义切块模块
先按段落（换行）切分，再将过长的段落按 chunk_size 滑窗切分，
相邻块之间保留 chunk_overlap 的重叠，避免语义被截断。
"""
from config import settings


def split_text(text: str) -> list[str]:
    """
    将长文本切分为带重叠的文本块。
    1. 按换行拆成段落，过滤空行；
    2. 短段落直接保留，长段落按固定窗口+重叠切分；
    3. 去除切分后仍为空的块。
    """
    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap

    chunks: list[str] = []
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    for para in paragraphs:
        if len(para) <= chunk_size:
            chunks.append(para)
            continue
        # 滑窗切分长段落
        start = 0
        while start < len(para):
            end = start + chunk_size
            chunks.append(para[start:end])
            if end >= len(para):
                break
            start = end - overlap  # 回退 overlap 个字符形成重叠

    return [c.strip() for c in chunks if c.strip()]
