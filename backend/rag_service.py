"""
RAG 核心业务服务
串联：文档入库（解析 -> 切块 -> 向量化存入 Chroma）、
检索问答（向量相似度检索 -> 相关性判定 -> 拒答 / 调用豆包生成）、
文档管理与评测记录生成。
"""
import os
import uuid

from config import settings
from document_parser import parse_document
from text_splitter import split_text
from vector_store import collection
from llm import generate_answer
import evaluator

# 检索不到相关内容时的固定拒答话术（禁止模型自行编造）
REFUSAL_TEXT = "当前课程知识库中没有该知识点，无法作答。"


# ===================== 知识库管理 =====================

def add_document(file_path: str, filename: str) -> dict:
    """
    将一个课件入库：
    解析文本 -> 语义切块 -> 批量写入 Chroma 向量库。
    返回文档信息（doc_id、文件名、块数量）。
    """
    doc_id = str(uuid.uuid4())

    # 1. 解析文档纯文本
    text = parse_document(file_path)
    # 2. 语义切块
    chunks = split_text(text)
    if not chunks:
        raise ValueError("文档内容为空或无法提取文本")

    # 3. 写入向量库（embedding 由 DoubaoEmbeddingFunction 自动完成）
    collection.add(
        ids=[f"{doc_id}_{i}" for i in range(len(chunks))],
        documents=chunks,
        metadatas=[
            {"doc_id": doc_id, "filename": filename, "chunk_index": i}
            for i in range(len(chunks))
        ],
    )

    return {"doc_id": doc_id, "filename": filename, "chunk_count": len(chunks)}


def list_documents() -> list[dict]:
    """聚合查询已上传文档列表（按 doc_id 去重，统计块数量）。"""
    data = collection.get(include=["metadatas"])
    docs: dict[str, dict] = {}
    for meta in data.get("metadatas", []):
        doc_id = meta["doc_id"]
        if doc_id not in docs:
            docs[doc_id] = {
                "doc_id": doc_id,
                "filename": meta["filename"],
                "chunk_count": 0,
            }
        docs[doc_id]["chunk_count"] += 1
    return list(docs.values())


def delete_document(doc_id: str) -> None:
    """根据 doc_id 删除该文档的全部文本块（向量）。"""
    collection.delete(where={"doc_id": doc_id})


# ===================== 检索问答 =====================

def retrieve(question: str) -> list[dict]:
    """
    向量相似度检索：
    返回相似度距离 <= 阈值的 Top-K 片段（按相似度从高到低）。
    """
    result = collection.query(
        query_texts=[question],
        n_results=settings.top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    hits = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        # Chroma 余弦距离：0 完全相同，越大越不相关
        if dist <= settings.relevance_threshold:
            hits.append(
                {
                    "content": doc,
                    "filename": meta["filename"],
                    "distance": round(float(dist), 4),
                }
            )
    return hits


def answer_question(question: str) -> dict:
    """
    RAG 问答主流程：
    1. 向量检索 Top-K 相关片段；
    2. 无有效片段 -> 固定拒答（不调用模型，杜绝编造）；
    3. 有有效片段 -> 拼接提示词调用豆包生成回答；
    4. 生成并保存评测记录。
    """
    hits = retrieve(question)
    retrieved = len(hits) > 0

    # 检索片段摘要，用于评测展示
    chunk_summaries = [
        {
            "filename": h["filename"],
            "distance": h["distance"],
            "summary": h["content"][:100] + ("..." if len(h["content"]) > 100 else ""),
        }
        for h in hits
    ]

    if not retrieved:
        # 强制拒答：直接返回固定话术，不调用大模型
        answer = REFUSAL_TEXT
        refused = True
    else:
        contexts = [h["content"] for h in hits]
        answer = generate_answer(question, contexts)
        # 模型若仍返回拒答话术，也如实标记
        refused = REFUSAL_TEXT in answer

    # 生成并持久化评测记录
    evaluation = evaluator.build_evaluation(
        question=question,
        retrieved=retrieved,
        refused=refused,
        chunk_summaries=chunk_summaries,
        answer=answer,
    )
    evaluator.save_evaluation(evaluation)

    return {
        "question": question,
        "answer": answer,
        "retrieved": retrieved,
        "refused": refused,
        "evaluation": evaluation,
    }
