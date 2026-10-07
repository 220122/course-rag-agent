/**
 * 后端 API 统一封装
 * 使用 axios，开发环境通过 Vite 代理转发到 http://localhost:8000
 */
import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 60000, // 文档向量化可能较慢，超时设为 60s
})

// ===== 知识库管理 =====

/** 上传课程文档（multipart/form-data） */
export function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** 获取已上传文档列表 */
export function fetchDocuments() {
  return request.get('/documents')
}

/** 删除指定文档 */
export function deleteDocument(docId) {
  return request.delete(`/documents/${docId}`)
}

// ===== 智能问答 =====

/** 提交问题，获取 RAG 回答与评测信息 */
export function sendQuestion(question) {
  return request.post('/chat', { question })
}

// ===== 评测记录 =====

/** 获取全部评测记录 */
export function fetchEvaluations() {
  return request.get('/evaluations')
}
