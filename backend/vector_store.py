"""
向量库模块
使用 ChromaDB 本地持久化客户端，集合（Collection）中每个文本块对应一条记录，
metadata 中保存所属文档 ID、文件名、块序号，便于按文档查询与删除。
"""
import os

import chromadb

from config import settings
from embeddings import get_embedding_function

# 确保持久化目录存在
os.makedirs(settings.chroma_dir, exist_ok=True)

# 本地持久化客户端（数据落盘，重启不丢失）
chroma_client = chromadb.PersistentClient(path=settings.chroma_dir)

# 课程知识库集合，使用余弦距离
# 嵌入函数按 EMBEDDING_PROVIDER 自动选择（本地离线模型 / 火山方舟）
collection = chroma_client.get_or_create_collection(
    name="course_knowledge",
    embedding_function=get_embedding_function(),
    metadata={"hnsw:space": "cosine"},
)
