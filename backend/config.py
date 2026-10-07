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
