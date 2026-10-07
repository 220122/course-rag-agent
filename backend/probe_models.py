# -*- coding: utf-8 -*-
"""探测当前 Key 下可用的豆包对话/Embedding 模型名称。"""
from openai import OpenAI
from config import settings

client = OpenAI(api_key=settings.ark_api_key, base_url=settings.ark_base_url)

emb_candidates = [
    "doubao-embedding-text-240715",
    "doubao-embedding-large-text-240915",
    "doubao-embedding-text-240515",
    "doubao-embedding-large-text-250515",
    "doubao-embedding-text-250314",
]
chat_candidates = [
    "doubao-pro-32k",
    "doubao-pro-32k-241215",
    "doubao-1-5-pro-32k-250115",
    "doubao-seed-1-6-250615",
    "doubao-seed-1-6-flash-250615",
]

print("===== Embedding =====")
for m in emb_candidates:
    try:
        client.embeddings.create(model=m, input=["测试"])
        print("OK  ", m)
    except Exception as e:
        print("FAIL", m, str(e)[:80])

print("===== Chat =====")
for m in chat_candidates:
    try:
        r = client.chat.completions.create(
            model=m, messages=[{"role": "user", "content": "说一个字"}], max_tokens=5
        )
        print("OK  ", m, "->", r.choices[0].message.content)
    except Exception as e:
        print("FAIL", m, str(e)[:80])
