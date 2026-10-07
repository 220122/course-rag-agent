<template>
  <!-- 整体布局：顶部标题 + 菜单导航 + 内容区 -->
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="logo">
        <el-icon :size="26"><Reading /></el-icon>
        <span>课程知识问答 RAG 智能体</span>
      </div>
      <el-menu
        mode="horizontal"
        :default-active="activePage"
        class="app-menu"
        @select="activePage = $event"
      >
        <el-menu-item index="chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能问答</span>
        </el-menu-item>
        <el-menu-item index="kb">
          <el-icon><FolderOpened /></el-icon>
          <span>知识库管理</span>
        </el-menu-item>
      </el-menu>
    </el-header>

    <el-main class="app-main">
      <!-- 根据菜单切换两个页面 -->
      <ChatView v-if="activePage === 'chat'" />
      <KnowledgeBase v-else />
    </el-main>
  </el-container>
</template>

<script setup>
import { ref } from 'vue'
import ChatView from './views/ChatView.vue'
import KnowledgeBase from './views/KnowledgeBase.vue'

// 当前激活页面，默认进入智能问答
const activePage = ref('chat')
</script>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html,
body,
#app {
  height: 100%;
}

body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background-color: #f5f7fa;
}
</style>

<style scoped>
.app-container {
  height: 100%;
}

.app-header {
  display: flex;
  align-items: center;
  background: linear-gradient(90deg, #409eff, #3375bb);
  color: #fff;
  padding: 0 24px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: bold;
  white-space: nowrap;
  margin-right: 48px;
}

.app-menu {
  background: transparent;
  border-bottom: none;
  flex: 1;
}

.app-menu :deep(.el-menu-item) {
  color: #e8f1ff;
  font-size: 15px;
}

.app-menu :deep(.el-menu-item.is-active) {
  color: #fff;
  background-color: rgba(255, 255, 255, 0.18);
  border-bottom-color: #fff;
}

.app-main {
  padding: 20px;
  height: calc(100% - 60px);
}
</style>
