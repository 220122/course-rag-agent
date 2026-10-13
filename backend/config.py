"""
全局配置模块
使用 pydantic-settings 从 backend 目录下的 .env 文件读取配置，
避免在代码中硬编码 API Key 等敏感信息。

「对话模型」与「向量化模型」是**两个独立可切换的部件**：

- chat_provider      deepseek | ark      决定用谁答题
- embedding_provider local    | ark      决定用谁把文本转成向量

之所以要分开，是因为 DeepSeek 官方只提供对话接口，**没有 embedding 接口**，
而 RAG 必须有向量化，所以向量化只能另选（本地离线模型或火山方舟）。
"""
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置项，字段名自动与 .env 中的大写变量对应（不区分大小写）。"""

    # ===================== 对话模型（答题） =====================
    # deepseek => 调用 DeepSeek 官方接口
    # ark      => 调用火山方舟（豆包）
    chat_provider: str = "deepseek"
    chat_model: str = "deepseek-flash"
    # 是否开启思考模式。RAG 问答的答案已被检索资料约束，思考模式只会增加延迟，
    # 默认关闭；需要更强推理时可置为 true
    chat_thinking: bool = False

    # DeepSeek 配置
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    # ===================== 向量化（检索） =====================
    # local => 本地离线模型，不消耗任何 API 额度
    # ark   => 火山方舟向量化接口
    embedding_provider: str = "local"

    # 本地模型（HuggingFace 模型 ID 或本地路径）。默认用 BGE 中文检索模型
    local_embedding_model: str = "BAAI/bge-small-zh-v1.5"
    local_embedding_cache_dir: str = "./data/models"
    # HuggingFace 镜像地址。中国大陆直连 huggingface.co 常常超时，
    # 默认走 hf-mirror 镜像；模型下载完成后即使留空也能离线运行
    hf_endpoint: str = "https://hf-mirror.com"

    # 火山方舟配置（仅当 chat_provider=ark 或 embedding_provider=ark 时需要）
    ark_api_key: str = ""
    ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    ark_embedding_model: str = ""      # 向量化推理接入点 ID 或模型名

    # 方舟向量化接口形态：
    #   text       => 标准 /embeddings 接口，一次请求可批量向量化
    #   multimodal => /embeddings/multimodal 接口，一次请求只出一个融合向量
    #                 （doubao-embedding-vision 等多模态模型必须用这个）
    #   auto       => 先试 text，若模型不支持标准接口则自动回退到 multimodal
    embedding_mode: str = "auto"
    # multimodal 模式下并发请求数（每个文本块一次请求，并发可显著提速）
    embedding_concurrency: int = 8

    # ===================== 本地存储路径 =====================
    chroma_dir: str = "./data/chroma"
    upload_dir: str = "./data/uploads"
    eval_file: str = "./data/evaluations.jsonl"

    # ===================== RAG 参数 =====================
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

# 让 huggingface_hub / fastembed 走镜像下载模型。
# 必须在加载本地向量化模型之前设置，因此放在 config 模块的导入期执行。
# 模型下载完成后本地已有缓存，即使镜像不可达也能离线运行。
if settings.hf_endpoint:
    os.environ.setdefault("HF_ENDPOINT", settings.hf_endpoint)
