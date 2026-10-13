"""
大语言模型模块

对话模型支持两个 provider（由 .env 的 CHAT_PROVIDER 决定）：
- deepseek => DeepSeek 官方接口（默认）
- ark      => 火山方舟（豆包）

无论用哪家，系统提示词都会强制模型只能依据检索到的课程资料作答。
"""
from openai import OpenAI

from config import settings


def _build_client() -> OpenAI:
    """按配置的 provider 构造 OpenAI 兼容客户端。"""
    provider = (settings.chat_provider or "deepseek").strip().lower()
    if provider == "ark":
        return OpenAI(
            api_key=settings.ark_api_key or "MISSING_API_KEY",
            base_url=settings.ark_base_url,
        )
    # 默认 DeepSeek
    return OpenAI(
        api_key=settings.deepseek_api_key or "MISSING_API_KEY",
        base_url=settings.deepseek_base_url,
    )


client = _build_client()

# 系统提示词：限定角色与回答边界，禁止编造
SYSTEM_PROMPT = (
    "你是一名严谨的课程知识问答助手。"
    "你必须且只能依据下方提供的【课程参考资料】回答用户问题，"
    "回答要条理清晰、准确忠实于资料，不得使用资料以外的知识，不得编造内容。"
    "如果参考资料不足以回答问题，请直接回复：当前课程知识库中没有该知识点，无法作答。"
)


def build_user_prompt(question: str, contexts: list[str]) -> str:
    """将检索到的资料片段与用户问题拼接成提示词。"""
    context_block = "\n\n".join(
        f"【资料片段{i + 1}】\n{ctx}" for i, ctx in enumerate(contexts)
    )
    return (
        f"课程参考资料如下：\n{context_block}\n\n"
        f"请严格根据以上资料回答用户问题。\n"
        f"用户问题：{question}"
    )


def generate_answer(question: str, contexts: list[str]) -> str:
    """
    调用对话接口生成回答。

    RAG 场景下答案已被检索资料约束，思考模式（thinking）只会显著增加首字延迟，
    因此默认传 thinking.type=disabled；如需更强推理可把 CHAT_THINKING 设为 true。
    DeepSeek 与火山方舟都接受该参数，写法一致。
    """
    kwargs: dict = {}
    if not settings.chat_thinking:
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

    resp = client.chat.completions.create(
        model=settings.chat_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(question, contexts)},
        ],
        temperature=0.3,  # 低温度，降低自由发挥
        **kwargs,
    )
    return (resp.choices[0].message.content or "").strip()
