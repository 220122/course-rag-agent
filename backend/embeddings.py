"""
向量化（Embedding）模块
封装豆包（火山方舟）Embedding 接口，并实现 ChromaDB 的 EmbeddingFunction 接口，
使 Chroma 在写入 / 检索时自动调用豆包模型生成向量。

火山方舟有**两套**向量化接口，入参与返回结构都不同：

1. 标准文本向量化  POST {base}/embeddings
   入参 input=["文本1", "文本2"]   一次请求返回多条向量（支持批量）
   适用于 doubao-embedding-text-* 等纯文本向量化模型。

2. 多模态向量化    POST {base}/embeddings/multimodal
   入参 input=[{"type":"text","text":"..."}, ...]
   ⚠️ 整个 input 数组会被**融合成一条向量**返回（data.embedding，而不是 data[i].embedding），
      因此每个文本块都必须单独发一次请求。
   适用于 doubao-embedding-vision-* 等多模态模型——这类模型调用 /embeddings 会直接
   报 400 "does not support this api"。

OpenAI SDK 的 client.embeddings.create 只能打标准接口，所以多模态模式用 httpx 直接请求。
"""
import httpx
import chromadb
from openai import OpenAI

from config import settings

# OpenAI 兼容客户端，指向火山方舟地址
# 未配置 Key 时使用占位符，保证服务可启动；真正调用时由业务层检查并给出友好提示
client = OpenAI(
    api_key=settings.ark_api_key or "MISSING_API_KEY",
    base_url=settings.ark_base_url,
)

# 多模态接口用的原生 HTTP 客户端（连接复用）
_http = httpx.Client(
    base_url=settings.ark_base_url.rstrip("/"),
    headers={
        "Authorization": f"Bearer {settings.ark_api_key or 'MISSING_API_KEY'}",
        "Content-Type": "application/json",
    },
    timeout=60.0,
)

# 多模态模型不支持标准接口时，接口返回的错误特征
_UNSUPPORTED_HINT = "does not support this api"

# 累计向量化用量（便于观察 token 消耗 / 额度占用）
_usage = {"requests": 0, "prompt_tokens": 0}


def get_usage() -> dict:
    """返回本次进程内累计的向量化请求数与 token 消耗。"""
    return dict(_usage)


def reset_usage() -> None:
    """重置用量统计。"""
    _usage["requests"] = 0
    _usage["prompt_tokens"] = 0


def _embed_text_batch(texts: list[str]) -> list[list[float]]:
    """标准文本向量化接口：一次请求批量返回多条向量。"""
    resp = client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
    )
    _usage["requests"] += 1
    _usage["prompt_tokens"] += int(getattr(resp.usage, "prompt_tokens", 0) or 0)
    # data 按输入顺序返回，排序保险
    resp.data.sort(key=lambda x: x.index)
    return [item.embedding for item in resp.data]


def _embed_multimodal_one(text: str) -> list[float]:
    """
    多模态向量化接口：对**单个**文本发一次请求，取回一条融合向量。
    遇到 429 / 5xx 做有限次重试。
    """
    payload = {
        "model": settings.embedding_model,
        "input": [{"type": "text", "text": text}],
    }
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = _http.post("/embeddings/multimodal", json=payload)
            # 限流与服务端错误重试
            if resp.status_code == 429 or resp.status_code >= 500:
                last_err = RuntimeError(
                    f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
                continue
            resp.raise_for_status()
            payload_json = resp.json()
            _usage["requests"] += 1
            _usage["prompt_tokens"] += int(
                (payload_json.get("usage") or {}).get("prompt_tokens", 0) or 0
            )
            data = payload_json.get("data")
            # 正常形态：data 是单个对象 {"embedding": [...], "object": "embedding"}
            if isinstance(data, dict):
                return data["embedding"]
            # 兼容万一返回数组的情况
            if isinstance(data, list) and data:
                return data[0]["embedding"]
            raise RuntimeError(f"多模态向量化返回结构异常：{str(data)[:200]}")
        except httpx.HTTPError as e:
            last_err = e
    raise RuntimeError(f"多模态向量化请求失败：{last_err}")


def _embed_multimodal(texts: list[str]) -> list[list[float]]:
    """多模态模式：每个文本块单独请求（接口会把整批融合成一条，故不能批量）。"""
    concurrency = max(1, settings.embedding_concurrency)
    if concurrency == 1 or len(texts) == 1:
        return [_embed_multimodal_one(t) for t in texts]

    # 并发请求，executor.map 保持输入顺序
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=min(concurrency, len(texts))) as pool:
        return list(pool.map(_embed_multimodal_one, texts))


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    将一批文本转为向量，自动适配「标准」与「多模态」两套接口。

    embedding_mode:
      text       仅用标准接口
      multimodal 仅用多模态接口
      auto       先试标准接口；若模型不支持（400 does not support this api）则回退多模态
    """
    if not texts:
        return []

    mode = (settings.embedding_mode or "auto").strip().lower()

    if mode == "text":
        return _embed_text_batch(texts)
    if mode == "multimodal":
        return _embed_multimodal(texts)

    # auto：先试标准接口，按错误特征回退
    try:
        return _embed_text_batch(texts)
    except Exception as e:
        if _UNSUPPORTED_HINT in str(e):
            return _embed_multimodal(texts)
        raise


class DoubaoEmbeddingFunction(chromadb.EmbeddingFunction):
    """ChromaDB 自定义嵌入函数：文档 -> 豆包向量。"""

    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        return embed_texts(list(input))
