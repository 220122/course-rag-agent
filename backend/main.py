"""
FastAPI 应用入口
提供课程知识库管理（上传 / 列表 / 删除）、智能问答、评测记录查询接口。

启动方式（在 backend 目录下）：
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
import os
import shutil

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

import rag_service
import evaluator
from config import settings
from schemas import ChatRequest

# 确保上传目录存在
os.makedirs(settings.upload_dir, exist_ok=True)

app = FastAPI(title="课程知识问答 RAG 智能体", version="1.0.0")

# 跨域配置：允许前端 Vite 开发服务器（5173）访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 允许上传的文件扩展名
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


@app.get("/api/health")
def health():
    """健康检查接口。"""
    return {"status": "ok"}


# ===================== 知识库管理接口 =====================

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传 PDF / Word 课件，解析切块并向量化入库。"""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="仅支持 PDF / DOCX 格式文件")

    # 保存到本地上传目录
    save_path = os.path.join(settings.upload_dir, file.filename)
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        doc_info = rag_service.add_document(save_path, file.filename)
    except Exception as e:
        # 入库失败时清理已保存文件
        if os.path.exists(save_path):
            os.remove(save_path)
        raise HTTPException(status_code=500, detail=f"文档处理失败：{e}")

    return {"message": "上传并入库成功", "document": doc_info}


@app.get("/api/documents")
def get_documents():
    """获取已上传文档列表。"""
    return rag_service.list_documents()


@app.delete("/api/documents/{doc_id}")
def remove_document(doc_id: str):
    """删除指定文档及其全部向量片段。"""
    rag_service.delete_document(doc_id)
    return {"message": "删除成功", "doc_id": doc_id}


# ===================== 智能问答接口 =====================

@app.post("/api/chat")
def chat(req: ChatRequest):
    """
    RAG 问答接口：
    检索相关课程片段，有则调用豆包作答，无则返回固定拒答话术，
    响应中同时携带本次问答的评测信息。
    """
    try:
        return rag_service.answer_question(req.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"问答服务异常：{e}")


# ===================== 评测记录接口 =====================

@app.get("/api/evaluations")
def get_evaluations():
    """获取全部问答评测记录（时间倒序）。"""
    return evaluator.load_evaluations()


if __name__ == "__main__":
    # 也可直接 python main.py 启动
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
