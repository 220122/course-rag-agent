<template>
  <!-- 知识库管理页：上传文档 + 文档列表 -->
  <el-card class="kb-card">
    <template #header>
      <div class="card-header">
        <el-icon><FolderOpened /></el-icon>
        <span>知识库管理</span>
      </div>
    </template>

    <!-- 上传区域 -->
    <el-upload
      drag
      :auto-upload="false"
      :show-file-list="false"
      accept=".pdf,.docx"
      :on-change="handleFileChange"
    >
      <el-icon class="el-icon--upload"><upload-filled /></el-icon>
      <div class="el-upload__text">
        将 PDF / Word 课件拖到此处，或<em>点击选择文件</em>
      </div>
      <template #tip>
        <div class="el-upload__tip">仅支持 .pdf / .docx 格式，上传后自动解析、切块并向量化入库</div>
      </template>
    </el-upload>

    <!-- 文档列表 -->
    <el-divider content-position="left">已上传文档</el-divider>
    <el-table :data="documents" v-loading="loading" stripe style="width: 100%">
      <el-table-column type="index" label="序号" width="70" align="center" />
      <el-table-column prop="filename" label="文件名" min-width="260">
        <template #default="{ row }">
          <el-icon>
            <document v-if="row.filename.endsWith('.docx')" />
            <document-copy v-else />
          </el-icon>
          <span style="margin-left: 6px">{{ row.filename }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="chunk_count" label="文本块数量" width="130" align="center" />
      <el-table-column label="操作" width="120" align="center">
        <template #default="{ row }">
          <el-button type="danger" size="small" @click="handleDelete(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无文档，请先上传课程课件" />
      </template>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, Document, DocumentCopy } from '@element-plus/icons-vue'
import { uploadDocument, fetchDocuments, deleteDocument } from '../api'

const documents = ref([])
const loading = ref(false)

/** 加载文档列表 */
async function loadDocuments() {
  loading.value = true
  try {
    const { data } = await fetchDocuments()
    documents.value = data
  } catch (e) {
    ElMessage.error('获取文档列表失败，请确认后端已启动')
  } finally {
    loading.value = false
  }
}

/** 选择文件后立即上传 */
async function handleFileChange(uploadFile) {
  const file = uploadFile.raw
  if (!file) return
  const ext = file.name.split('.').pop().toLowerCase()
  if (!['pdf', 'docx'].includes(ext)) {
    ElMessage.warning('仅支持 PDF / DOCX 格式')
    return
  }
  try {
    ElMessage.info('正在解析并向量化，请稍候...')
    await uploadDocument(file)
    ElMessage.success('上传并入库成功')
    loadDocuments()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '上传失败')
  }
}

/** 删除文档（二次确认） */
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除文档「${row.filename}」吗？其全部向量片段将被移除。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' }
    )
    await deleteDocument(row.doc_id)
    ElMessage.success('删除成功')
    loadDocuments()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

onMounted(loadDocuments)
</script>

<style scoped>
.kb-card {
  max-width: 900px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
  font-size: 16px;
}
</style>
