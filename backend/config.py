"""
全局配置模块
使用 pydantic-settings 从 backend 目录下的 .env 文件读取配置，
避免在代码中硬编码 API Key 等敏感信息。
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置项，字段名自动与 .env 中的大写变量对应（不区分大小写）。"""

    # 火山方舟（豆包）API 配置
    ark_api_key: str = ""
    ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    chat_model: str = "doubao-pro-32k"
    embedding_model: str = "doubao-embedding-text-240715"

    # 向量化接口形态：
    #   text       => 标准 /embeddings 接口，一次请求可批量向量化（文本向量化模型）
    #   multimodal => /embeddings/multimodal 接口，一次请求只出一个融合向量
    #                 （doubao-embedding-vision 等多模态模型必须用这个）
    #   auto       => 先试 text，若模型不支持标准接口则自动回退到 multimodal
    embedding_mode: str = "auto"

    # multimodal 模式下并发请求数（每个文本块一次请求，并发可显著提速）
    embedding_concurrency: int = 8

    # 本地存储路径
    chroma_dir: str = "./data/chroma"
    upload_dir: str = "./data/uploads"
    eval_file: str = "./data/evaluations.jsonl"

    # RAG 参数
    chunk_size: int = 500       # 每个文本块的最大字符数
    chunk_overlap: int = 80     # 相邻文本块的重叠字符数（保证语义连贯）
    top_k: int = 3              # 检索返回的片段数量
    relevance_threshold: float = 0.45  # 余弦距离阈值，超过则判定不相关

    # 指定从 .env 读取，忽略多余变量
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# 全局唯一配置实例
settings = Settings()
