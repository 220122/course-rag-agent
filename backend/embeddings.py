"""
向量化（Embedding）模块
封装豆包（火山方舟）Embedding 接口，并实现 ChromaDB 的 EmbeddingFunction 接口，
使 Chroma 在写入 / 检索时自动调用豆包模型生成向量。
"""
import chromadb
from openai import OpenAI

from config import settings

# OpenAI 兼容客户端，指向火山方舟地址
# 未配置 Key 时使用占位符，保证服务可启动；真正调用时由业务层检查并给出友好提示
client = OpenAI(
    api_key=settings.ark_api_key or "MISSING_API_KEY",
    base_url=settings.ark_base_url,
)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """调用豆包 Embedding 接口，将一批文本转为向量。"""
    resp = client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
    )
    # data 按输入顺序返回，排序保险
    resp.data.sort(key=lambda x: x.index)
    return [item.embedding for item in resp.data]


class DoubaoEmbeddingFunction(chromadb.EmbeddingFunction):
    """ChromaDB 自定义嵌入函数：文档 -> 豆包向量。"""

    def __call__(self, input: chromadb.Documents) -> chromadb.Embeddings:
        return embed_texts(list(input))
