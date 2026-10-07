<template>
  <!-- 智能问答页：聊天式界面，评测信息默认折叠 -->
  <div class="chat-wrapper">
    <!-- 消息展示区 -->
    <div class="chat-messages" ref="messageBox">
      <el-empty v-if="messages.length === 0" description="请输入你的课程问题开始提问" />

      <div v-for="msg in messages" :key="msg.id" class="message-item">
        <!-- 用户消息 -->
        <div v-if="msg.role === 'user'" class="message user-message">
          <el-avatar :size="36" class="avatar user-avatar">
            <el-icon><User /></el-icon>
          </el-avatar>
          <div class="bubble user-bubble">{{ msg.content }}</div>
        </div>

        <!-- 助手消息 -->
        <div v-else class="message assistant-message">
          <el-avatar :size="36" class="avatar assistant-avatar">
            <el-icon><Cpu /></el-icon>
          </el-avatar>
          <div class="bubble assistant-bubble">
            <!-- 加载中 -->
            <div v-if="msg.loading" class="loading-row">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>正在检索课程知识库并生成回答...</span>
            </div>
            <template v-else>
              <div class="answer-text">{{ msg.content }}</div>

              <!-- 评测信息：默认折叠，可展开 -->
              <el-collapse v-if="msg.evaluation" class="eval-collapse">
                <el-collapse-item name="eval">
                  <template #title>
                    <span class="eval-title">
                      <el-icon><DataAnalysis /></el-icon>
                      评测信息
                      <el-tag
                        size="small"
                        :type="msg.evaluation.retrieved ? 'success' : 'info'"
                        style="margin-left: 8px"
                      >
                        {{ msg.evaluation.retrieved ? '检索到资料' : '未检索到资料' }}
                      </el-tag>
                      <el-tag
                        size="small"
                        :type="msg.evaluation.refused ? 'danger' : 'success'"
                        style="margin-left: 6px"
                      >
                        {{ msg.evaluation.refused ? '已触发拒答' : '正常作答' }}
                      </el-tag>
                    </span>
                  </template>

                  <el-descriptions :column="1" border size="small">
                    <el-descriptions-item label="提问时间">
                      {{ msg.evaluation.timestamp }}
                    </el-descriptions-item>
                    <el-descriptions-item label="检索片段摘要">
                      <div v-if="msg.evaluation.chunk_summaries.length === 0">无命中片段</div>
                      <div
                        v-for="(chunk, i) in msg.evaluation.chunk_summaries"
                        :key="i"
                        class="chunk-item"
                      >
                        <el-tag size="small" type="warning">片段{{ i + 1 }}</el-tag>
                        <span class="chunk-meta">
                          来源：{{ chunk.filename }} ｜ 距离：{{ chunk.distance }}
                        </span>
                        <div class="chunk-summary">{{ chunk.summary }}</div>
                      </div>
                    </el-descriptions-item>
                  </el-descriptions>
                </el-collapse-item>
              </el-collapse>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区 -->
    <div class="chat-input">
      <el-input
        v-model="inputQuestion"
        type="textarea"
        :rows="2"
        resize="none"
        placeholder="请输入课程相关问题，按 Enter 发送（Shift+Enter 换行）"
        @keydown.enter.exact.prevent="handleSend"
      />
      <el-button
        type="primary"
        :loading="sending"
        class="send-btn"
        @click="handleSend"
      >
        发送
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { User, Cpu, Loading, DataAnalysis } from '@element-plus/icons-vue'
import { sendQuestion } from '../api'

const inputQuestion = ref('')
const sending = ref(false)
const messageBox = ref(null)

// 消息列表：{ id, role, content, loading, evaluation }
const messages = ref([])
let msgId = 0

/** 滚动到底部 */
async function scrollToBottom() {
  await nextTick()
  if (messageBox.value) messageBox.value.scrollTop = messageBox.value.scrollHeight
}

/** 发送问题 */
async function handleSend() {
  const question = inputQuestion.value.trim()
  if (!question) {
    ElMessage.warning('请输入问题')
    return
  }
  if (sending.value) return

  // 追加用户消息 + 助手占位消息（加载态）
  messages.value.push({ id: ++msgId, role: 'user', content: question })
  const assistantMsg = { id: ++msgId, role: 'assistant', content: '', loading: true }
  messages.value.push(assistantMsg)
  inputQuestion.value = ''
  sending.value = true
  scrollToBottom()

  try {
    const { data } = await sendQuestion(question)
    assistantMsg.content = data.answer
    assistantMsg.evaluation = data.evaluation
  } catch (e) {
    assistantMsg.content = '服务异常，请确认后端已启动且 API Key 配置正确。'
    ElMessage.error(e.response?.data?.detail || '请求失败')
  } finally {
    assistantMsg.loading = false
    sending.value = false
    scrollToBottom()
  }
}
</script>

<style scoped>
.chat-wrapper {
  max-width: 900px;
  height: 100%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.message {
  display: flex;
  margin-bottom: 18px;
}

.assistant-message {
  justify-content: flex-start;
}

.user-message {
  justify-content: flex-end;
}

.avatar {
  flex-shrink: 0;
}

.user-avatar {
  background-color: #409eff;
  margin-left: 10px;
  order: 2;
}

.assistant-avatar {
  background-color: #67c23a;
  margin-right: 10px;
}

.bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 8px;
  line-height: 1.6;
  font-size: 14px;
  word-break: break-word;
}

.user-bubble {
  background-color: #ecf5ff;
  border: 1px solid #d9ecff;
}

.assistant-bubble {
  background-color: #f4f4f5;
  border: 1px solid #e9e9eb;
}

.loading-row {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
}

.eval-collapse {
  margin-top: 10px;
  border-top: 1px dashed #dcdfe6;
}

.eval-title {
  display: inline-flex;
  align-items: center;
  font-size: 13px;
  color: #606266;
}

.chunk-item {
  margin-bottom: 8px;
}

.chunk-meta {
  margin-left: 6px;
  font-size: 12px;
  color: #909399;
}

.chunk-summary {
  margin-top: 4px;
  color: #606266;
  font-size: 13px;
}

.chat-input {
  display: flex;
  gap: 10px;
  padding: 14px 20px;
  border-top: 1px solid #ebeef5;
  background: #fafafa;
}

.send-btn {
  align-self: flex-end;
}
</style>
