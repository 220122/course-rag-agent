"""
评测记录模块
每条问答自动生成一条评测记录，以 JSON Lines（.jsonl）格式追加保存到本地，
同时提供读取接口，供前端与后续效果分析使用。
"""
import json
import os
from datetime import datetime

from config import settings

os.makedirs(os.path.dirname(settings.eval_file) or ".", exist_ok=True)


def save_evaluation(record: dict) -> None:
    """追加写入一条评测记录（每行一个 JSON 对象）。"""
    with open(settings.eval_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_evaluations() -> list[dict]:
    """读取全部评测记录，按时间倒序返回。"""
    if not os.path.exists(settings.eval_file):
        return []
    records = []
    with open(settings.eval_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    records.reverse()
    return records


def build_evaluation(
    question: str,
    retrieved: bool,
    refused: bool,
    chunk_summaries: list[dict],
    answer: str,
) -> dict:
    """
    构造一条评测记录。
    :param question: 用户问题
    :param retrieved: 是否检索到有效资料
    :param refused: 是否触发拒答
    :param chunk_summaries: 命中片段摘要（含来源文件名、相似度距离、内容摘要）
    :param answer: 最终回答
    """
    return {
        "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "retrieved": retrieved,       # 是否检索到有效资料
        "refused": refused,           # 是否触发拒答
        "chunk_summaries": chunk_summaries,  # 检索片段摘要
        "answer": answer,
    }
