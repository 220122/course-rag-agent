"""
向量化（Embedding）模块

按 .env 的 EMBEDDING_PROVIDER 选择实现：

1. local（默认）—— 本地离线模型，**不消耗任何 API 额度**，无需 Key。
   使用 fastembed（ONNX Runtime，不依赖 torch），默认模型 BAAI/bge-small-zh-v1.5，
   是面向中文检索的模型，比 Chroma 自带的英文 MiniLM 更适合中文教材。
   模型首次使用时会自动下载到 LOCAL_EMBEDDING_CACHE_DIR，之后完全离线。

2. ark —— 火山方舟（豆包）向量化接口。它本身又分两套接口：
   - 标准   POST {base}/embeddings              入参字符串数组，一次返回多条向量
   - 多模态 POST {base}/embeddings/multimodal   入参 [{"type":"text","text":"..."}]，
     整个 input 会被**融合成一条向量**返回，故每个文本块必须单独发一次请求。
   doubao-embedding-vision 等多模态模型调用标准接口会报
   400 does not support this api，而 OpenAI SDK 无法访问多模态路径，故用 httpx 直连。

⚠️ 两套实现的向量维度不同（BGE-small-zh 为 512 维，豆包多模态为 2048 维）。
   切换 provider 后**必须重建知识库**，否则 Chroma 会因维度不一致而报错。
"""
import chromadb
import httpx
from openai import OpenAI

from config import settings

# ===================== 用量统计 =====================
# 本地模型不计费，这里只统计调用次数；Ark 模式才累计 token
_usage = {"requests": 0, "prompt_tokens": 0}


def get_usage() -> dict:
    """返回本次进程内累计的向量化请求数与 token 消耗。"""
    return dict(_usage)


def reset_usage() -> None:
    """重置用量统计。"""
    _usage["requests"] = 0
    _usage["prompt_tokens"] = 0


def _provider() -> str:
    """当前向量化 provider：local 或 ark。"""
    return (settings.embedding_provider or "local").strip().lower()


# ===================== 一、本地离线向量化 =====================

_local_model = None


def _get_local_model():
    """惰性加载本地 ONNX 向量化模型（首次调用会下载模型文件）。"""
    global _local_model
    if _local_model is None:
        try:
            from fastembed import TextEmbedding
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "本地向量化需要 fastembed，请先执行 pip install fastembed；"
                "或把 .env 的 EMBEDDING_PROVIDER 改回 ark 使用火山方舟接口。"
            ) from e
        _local_model = TextEmbedding(
            model_name=settings.local_embedding_model,
            cache_dir=settings.local_embedding_cache_dir,
        )
    return _local_model


def _embed_local(texts: list[str]) -> list[list[float]]:
    """本地模型批量向量化（fastembed 内部已做批处理）。"""
    model = _get_local_model()
    vectors = list(model.embed(texts))
    _usage["requests"] += 1
    # fastembed 返回 numpy 数组，转成 Chroma 需要的 list[float]
    return [v.tolist() for v in vectors]


# ===================== 二、火山方舟向量化 =====================

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


def _embed_text_batch(texts: list[str]) -> list[list[float]]:
    """标准文本向量化接口：一次请求批量返回多条向量。"""
    resp = client.embeddings.create(
        model=settings.ark_embedding_model,
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
        "model": settings.ark_embedding_model,
        "input": [{"type": "text", "text": text}],
    }
    last_err: Exception | None = None
    for _ in range(3):
        try:
            resp = _http.post("/embeddings/multimodal", json=payload)
            # 限流与服务端错误重试
            if resp.status_code == 429 or resp.status_code >= 500:
                last_err = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
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


def _embed_ark(texts: list[str]) -> list[list[float]]:
    """
    火山方舟向量化，自动适配「标准」与「多模态」两套接口。

    embedding_mode:
      text       仅用标准接口
      multimodal 仅用多模态接口
      auto       先试标准接口；若模型不支持（400 does not support this api）则回退多模态
    """
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


# ===================== 统一入口 =====================


def embed_texts(texts: list[str]) -> list[list[float]]:
    """将一批文本转为向量，按配置选择本地模型或火山方舟。"""
    if not texts:
        return []
    if _provider() == "ark":
        return _embed_ark(texts)
    return _embed_local(texts)


class LocalEmbeddingFunction(chromadb.EmbeddingFunction):
    """ChromaDB 嵌入函数：本地离线模型。"""

    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        return embed_texts(list(input))


class DoubaoEmbeddingFunction(chromadb.EmbeddingFunction):
    """ChromaDB 自定义嵌入函数：文档 -> 豆包向量。"""

    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        return embed_texts(list(input))


def get_embedding_function() -> chromadb.EmbeddingFunction:
    """按当前 provider 返回对应的 Chroma 嵌入函数。"""
    if _provider() == "ark":
        return DoubaoEmbeddingFunction()
    return LocalEmbeddingFunction()
