"""
Pydantic 请求 / 响应数据模型
"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """问答请求体。"""
    question: str = Field(..., min_length=1, description="用户提问内容")


class DocumentInfo(BaseModel):
    """已上传文档信息。"""
    doc_id: str
    filename: str
    chunk_count: int


class UploadResponse(BaseModel):
    """上传成功响应。"""
    message: str
    document: DocumentInfo
