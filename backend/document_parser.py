"""
文档解析模块
支持 PDF 与 Word(.docx) 两种课程课件格式，提取纯文本内容。
"""
import os

from PyPDF2 import PdfReader
from docx import Document


def parse_pdf(file_path: str) -> str:
    """解析 PDF 文件，逐页提取文本并拼接。"""
    reader = PdfReader(file_path)
    pages_text = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)
    return "\n".join(pages_text)


def parse_docx(file_path: str) -> str:
    """解析 Word(.docx) 文件，提取所有段落文本。"""
    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def parse_document(file_path: str) -> str:
    """
    根据文件扩展名选择解析器，返回文档纯文本。
    不支持的格式抛出 ValueError。
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return parse_pdf(file_path)
    if ext == ".docx":
        return parse_docx(file_path)
    raise ValueError(f"不支持的文件格式：{ext}，目前仅支持 PDF / DOCX")
