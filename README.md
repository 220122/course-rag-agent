# 课程知识问答 RAG 智能体

基于 **FastAPI + ChromaDB + 豆包大模型 + Vue3 + Element Plus** 的前后端分离课程知识问答系统。
上传课程课件（PDF / Word）后，系统自动解析文本、语义切块、向量化入库；提问时先做向量相似度检索，
再把 Top3 相关片段与问题拼接后交给豆包模型作答；检索不到相关内容时**强制拒答**，杜绝模型编造。

---

## 一、项目目录结构

```
course-rag-agent/
├── backend/                         # 后端 FastAPI 项目
│   ├── .env.example                 # 环境变量示例（复制为 .env 使用）
│   ├── requirements.txt             # Python 依赖
│   ├── main.py                      # FastAPI 入口与路由
│   ├── config.py                    # 全局配置（读取 .env）
│   ├── schemas.py                   # 请求/响应数据模型
│   ├── document_parser.py           # PDF / Word 文档解析
│   ├── text_splitter.py             # 文本语义切块（滑窗+重叠）
│   ├── embeddings.py                # 豆包 Embedding + Chroma 嵌入函数
│   ├── vector_store.py              # ChromaDB 本地向量库
│   ├── llm.py                       # 豆包对话接口与系统提示词
│   ├── evaluator.py                 # 评测记录生成与读取
│   ├── rag_service.py               # RAG 核心业务流程
│   └── data/                        # 运行时自动生成（向量库/上传文件/评测记录）
│
├── frontend/                        # 前端 Vue3 单页应用
│   ├── package.json                 # 前端依赖
│   ├── vite.config.js               # Vite 配置（/api 代理到 8000）
│   ├── index.html
│   └── src/
│       ├── main.js                  # 应用入口（注册 Element Plus）
│       ├── App.vue                  # 整体布局与页面切换
│       ├── api/index.js             # axios 接口统一封装
│       └── views/
│           ├── ChatView.vue         # 智能问答页（聊天界面 + 评测折叠）
│           └── KnowledgeBase.vue    # 知识库管理页（上传/列表/删除）
│
├── .gitignore
└── README.md
```

---

## 二、前置准备

1. **Python 3.10+**（命令行验证：`python --version`）
2. **Node.js 16+**（推荐 18/20，验证：`node -v`）
3. **豆包（火山方舟 Ark）API Key**：在 <https://console.volcengine.com/ark> 开通并创建：
   - 一个**对话模型**推理接入点（如 doubao-pro 系列）；
   - 一个 **Embedding 向量化模型**推理接入点（如 doubao-embedding 系列）。

---

## 三、后端启动步骤

```bash
# 1. 进入后端目录
cd backend

# 2. （推荐）创建并激活虚拟环境
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 复制环境变量配置文件，并填入真实 API Key、模型/接入点信息
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux

# 5. 启动服务（默认 8000 端口）
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

启动成功后：

- 接口服务地址：<http://localhost:8000>
- 自动生成的交互式 API 文档（Swagger）：<http://localhost:8000/docs>

---

## 四、前端启动步骤

```bash
# 1. 新开一个终端，进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
```

浏览器访问 <http://localhost:5173> 即可使用。
开发环境下 `/api` 请求由 Vite 自动代理到后端 `http://localhost:8000`，无需处理跨域。

---

## 五、使用流程

1. 打开页面，进入 **知识库管理**，上传课程 PDF / Word 课件（可上传多份）；
2. 切换到 **智能问答**，输入课程相关问题；
3. 系统检索知识库并生成回答，回答下方「评测信息」可展开查看：
   - 是否检索到有效资料、是否触发拒答；
   - 命中片段的来源文件、相似度距离与内容摘要。
4. 当问题与知识库无关时，系统固定返回：
   **「当前课程知识库中没有该知识点，无法作答。」**

---

## 六、主要接口说明

| 方法   | 路径                          | 说明                     |
| ------ | ----------------------------- | ------------------------ |
| POST   | `/api/documents/upload`       | 上传 PDF/DOCX 并入库     |
| GET    | `/api/documents`              | 查询已上传文档列表       |
| DELETE | `/api/documents/{doc_id}`     | 删除指定文档及向量       |
| POST   | `/api/chat`                   | RAG 问答（含评测信息）   |
| GET    | `/api/evaluations`            | 查询全部评测记录         |
| GET    | `/api/health`                 | 健康检查                 |

---

## 七、可调参数说明（backend/.env）

| 参数                 | 含义                                                       |
| -------------------- | ---------------------------------------------------------- |
| `CHUNK_SIZE`         | 文本切块最大字符数（默认 500）                             |
| `CHUNK_OVERLAP`      | 相邻块重叠字符数（默认 80）                                |
| `TOP_K`              | 检索片段数量（默认 3）                                     |
| `RELEVANCE_THRESHOLD`| 余弦距离相关性阈值，越小越严格；误拒答可调大，乱答可调小   |

> 说明：Chroma 使用余弦距离（0 表示完全相同），距离大于阈值的片段视为不相关。
> 若使用不同的 Embedding 模型，建议根据实际效果微调该阈值。
