# 课程知识问答 RAG 智能体

基于 **FastAPI + ChromaDB + DeepSeek + Vue3 + Element Plus** 的前后端分离课程知识问答系统。

上传课程课件（PDF / Word）后，系统自动解析文本、语义切块、向量化入库；提问时先做向量相似度检索，
再把 Top-K 相关片段与问题拼接后交给大模型作答；检索不到相关内容时**强制拒答**，杜绝模型编造。

---

## 一、先搞清一件事：对话和向量化是两个独立部件

新手最容易踩的坑是「把对话模型和向量化模型当成一回事」。本项目的配置把它们**分开**：

| 部件 | 作用 | 默认实现 |
| --- | --- | --- |
| **对话模型** | 读检索到的资料，生成回答 | DeepSeek（`deepseek-flash`） |
| **向量化模型** | 把文本转成向量，供检索用 | **本地离线模型**（BAAI/bge-small-zh-v1.5） |

> ⚠️ **DeepSeek 官方没有 embedding 接口**。它只提供对话接口（模型只有 `deepseek-flash`
> 与 `deepseek-v4-pro`），所以「全部换成 DeepSeek」在技术上做不到——RAG 必须有向量化。
>
> 本项目因此默认用**本地离线模型**做向量化：不消耗任何 API 额度、不需要任何 Key、下载后完全离线。
> 如果你更想用云端向量化，把 `EMBEDDING_PROVIDER` 改成 `ark` 即可切回火山方舟。

两者都可以独立切换：

```ini
CHAT_PROVIDER=deepseek      # deepseek | ark
EMBEDDING_PROVIDER=local    # local    | ark
```

---

## 二、目录结构

```
course-rag-agent/
├── ① 首次安装（双击我）.bat          # 一键安装依赖（后端 venv + 前端 npm，走国内镜像）
├── ② 启动项目（双击我）.bat          # 一键启动前后端并自动打开浏览器
├── ③ 停止项目（双击我）.bat          # 一键关闭前后端服务
│
├── backend/                         # 后端 FastAPI 项目
│   ├── .env.example                 # 环境变量示例（复制为 .env 使用）
│   ├── .env                         # 真实配置（含密钥，已被 .gitignore 排除）
│   ├── requirements.txt             # Python 依赖
│   ├── main.py                      # FastAPI 入口与路由
│   ├── config.py                    # 全局配置（读取 .env，含 provider 切换）
│   ├── schemas.py                   # 请求/响应数据模型
│   ├── document_parser.py           # PDF / Word 文档解析
│   ├── text_splitter.py             # 文本语义切块（段落合并 + 标题对齐）
│   ├── embeddings.py                # 向量化（本地离线模型 / 火山方舟 两套实现）
│   ├── vector_store.py              # ChromaDB 本地向量库（余弦距离）
│   ├── llm.py                       # 对话接口（DeepSeek / 火山方舟）与系统提示词
│   ├── evaluator.py                 # 评测记录生成与读取
│   ├── rag_service.py               # RAG 核心业务流程
│   ├── probe_models.py              # 工具：探测火山方舟 Key 可用的模型名（排错用）
│   ├── build_os_book.py             # 工具：生成《操作系统》课程知识库 Word 文档
│   ├── start_backend.bat            # 单独启动后端（调试用）
│   ├── 操作系统课程知识库.docx        # 示例课件（可直接上传测试）
│   └── data/                        # 运行时自动生成（向量库/上传文件/评测记录/本地模型）
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

## 三、前置准备

1. **Python 3.10+**（命令行验证：`python --version`）
2. **Node.js 16+**（推荐 18/20，验证：`node -v`）
3. **DeepSeek API Key**：在 <https://platform.deepseek.com/api_keys> 申请，填入 `backend/.env` 的
   `DEEPSEEK_API_KEY`。
4. **本地向量化模型**：**无需手动准备**。首次使用时会自动下载
   `BAAI/bge-small-zh-v1.5`（约 100MB）到 `backend/data/models/`，之后完全离线运行。

### 关于模型名（很重要）

DeepSeek 现在的模型名是 **`deepseek-flash`** 和 **`deepseek-v4-pro`**。
网上大量教程还在用 `deepseek-chat` / `deepseek-reasoner`，这两个已不在官方文档中，
照抄很可能报 404。本项目默认用 `deepseek-flash`（快且便宜），想要更强推理可改 `deepseek-v4-pro`。

---

## 四、国内镜像（本项目已全部配好）

国内直连境外源普遍超时，本项目的所有下载都已指向国内镜像：

| 下载内容 | 镜像 | 配置位置 |
| --- | --- | --- |
| Python 依赖（pip） | 清华 `pypi.tuna.tsinghua.edu.cn` | `① 首次安装（双击我）.bat` |
| 前端依赖（npm） | 淘宝 `registry.npmmirror.com` | `① 首次安装（双击我）.bat`、`package-lock.json` |
| 本地向量化模型（HuggingFace） | `hf-mirror.com` | `backend/config.py` 的 `HF_ENDPOINT` |

模型镜像通过 `HF_ENDPOINT` 环境变量生效，`config.py` 会在导入时自动设置（默认
`https://hf-mirror.com`）。若你想改用官方源，把 `.env` 的 `HF_ENDPOINT` 留空即可；
模型下载完成后本地已有缓存，**即使断网也能正常运行**。

---

## 五、一键启动（推荐，最省事）

直接双击项目根目录下的脚本即可，无需手敲命令：

| 顺序 | 脚本 | 作用 |
| ---- | ---- | ---- |
| ① | `① 首次安装（双击我）.bat` | 自动创建 venv、装后端依赖（清华镜像）、装前端依赖（淘宝镜像）；若缺少 `.env` 会自动生成并打开记事本让你填 Key |
| ② | `② 启动项目（双击我）.bat` | 分别启动后端（8000）与前端（5173），等待约 8 秒后自动打开浏览器 |
| ③ | `③ 停止项目（双击我）.bat` | 关闭前后端两个服务窗口 |

> 脚本使用 **GBK + CRLF + `chcp 936`** 编码编写，请勿用编辑器另存为 UTF-8，否则中文会乱码。

若喜欢手动控制，见下方第六、七节。

---

## 六、后端启动步骤（手动）

```bash
# 1. 进入后端目录
cd backend

# 2. （推荐）创建并激活虚拟环境
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate

# 3. 安装依赖（国内建议加清华镜像）
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 复制环境变量配置文件，并填入 DeepSeek API Key
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux

# 5. 启动服务（默认 8000 端口）
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

启动成功后：

- 接口服务地址：<http://localhost:8000>
- 自动生成的交互式 API 文档（Swagger）：<http://localhost:8000/docs>

---

## 七、前端启动步骤（手动）

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

## 八、使用流程

1. 打开页面，进入 **知识库管理**，上传课程 PDF / Word 课件（可上传多份）；
2. 切换到 **智能问答**，输入课程相关问题；
3. 系统检索知识库并生成回答，回答下方「评测信息」可展开查看：
   - 是否检索到有效资料、是否触发拒答；
   - 命中片段的来源文件、相似度距离与内容摘要。
4. 当问题与知识库无关时，系统固定返回：
   **「当前课程知识库中没有该知识点，无法作答。」**

> 首次使用可先上传 `backend/操作系统课程知识库.docx` 作为测试课件。

---

## 九、主要接口说明

| 方法   | 路径                          | 说明                     |
| ------ | ----------------------------- | ------------------------ |
| POST   | `/api/documents/upload`       | 上传 PDF/DOCX 并入库     |
| GET    | `/api/documents`              | 查询已上传文档列表       |
| DELETE | `/api/documents/{doc_id}`     | 删除指定文档及向量       |
| POST   | `/api/chat`                   | RAG 问答（含评测信息）   |
| GET    | `/api/evaluations`            | 查询全部评测记录         |
| GET    | `/api/health`                 | 健康检查                 |

---

## 十、可调参数说明（backend/.env）

### 对话模型

| 参数 | 含义 |
| --- | --- |
| `CHAT_PROVIDER` | `deepseek`（默认）或 `ark`（火山方舟） |
| `CHAT_MODEL` | 模型名。DeepSeek 用 `deepseek-flash` / `deepseek-v4-pro`；方舟填接入点 `ep-xxxx` |
| `CHAT_THINKING` | 是否开启思考模式，默认 `false`。RAG 答案已被检索资料约束，开启只会明显变慢 |
| `DEEPSEEK_API_KEY` | DeepSeek 密钥 |
| `DEEPSEEK_BASE_URL` | 默认 `https://api.deepseek.com` |

### 向量化模型

| 参数 | 含义 |
| --- | --- |
| `EMBEDDING_PROVIDER` | `local`（默认，离线免费）或 `ark`（火山方舟） |
| `LOCAL_EMBEDDING_MODEL` | 本地模型，默认 `BAAI/bge-small-zh-v1.5`；可换 `bge-base-zh-v1.5` / `bge-large-zh-v1.5` 提升效果 |
| `LOCAL_EMBEDDING_CACHE_DIR` | 模型缓存目录，默认 `./data/models` |
| `HF_ENDPOINT` | HuggingFace 镜像，默认 `https://hf-mirror.com`，留空则用官方源 |
| `ARK_API_KEY` / `ARK_BASE_URL` | 仅当上面两项选了 `ark` 时才需要 |
| `ARK_EMBEDDING_MODEL` | 方舟向量化接入点 `ep-xxxx` |
| `EMBEDDING_MODE` | 方舟接口形态：`text` / `multimodal` / `auto` |

### RAG 参数

| 参数                 | 含义                                                       |
| -------------------- | ---------------------------------------------------------- |
| `CHUNK_SIZE`         | 文本切块最大字符数（默认 500）                             |
| `CHUNK_OVERLAP`      | 相邻块重叠字符数（默认 80）                                |
| `TOP_K`              | 检索片段数量（默认 8）。教材类大知识库建议 6~8：答案常分散在多个片段里，取 3 容易只覆盖一部分。调大它**不会**削弱拒答——拒答由阈值控制 |
| `RELEVANCE_THRESHOLD`| 余弦距离相关性阈值，越小越严格；误拒答可调大，乱答可调小   |

> ⚠️ **切换向量化 provider（local ↔ ark）会导致向量维度变化**
> （BGE-small-zh 为 512 维，豆包多模态为 2048 维），
> **必须清空并重建知识库**，否则 Chroma 会因维度不一致报错。
> 做法：删除 `backend/data/chroma/` 目录，重启后端后重新上传课件。

> **关于切块**：`text_splitter.py` 不是「一段一块」，而是把**连续段落累积合并**到接近
> `CHUNK_SIZE` 再成块，并在**章节标题处对齐块边界**。原因：
> ① 电子书/课件常「一行即一段」，逐段成块会产生大量碎块，每块上下文太少、检索命中率差；
> ② 标题若独立成块，会因关键词高度匹配而挤占 Top-K 名额，造成「检索到了却答不出来」。
>
> 标题识别只认**多级编号**（`1.1` / `1.2.3`）、`第X章/节`、中文数字顿号（`一、`），
> 并排除以句末标点结尾的段落——否则「`1.试说明…`」这类编号习题会被误判成标题，
> 导致整份习题粘连成一个超大块。同时会过滤页码与重复出现的页眉页脚短行。
>
> 实测效果（424,783 字符的教材）：逐段成块为 3,146 块（平均 134 字符），
> 改后为 1,112 块（平均 376 字符，上限 500），并过滤掉 389 个页码与 419 个重复页眉。

> **关于阈值**：Chroma 使用余弦距离（0 表示完全相同），距离大于阈值的片段视为不相关。
> 该阈值**与所用向量化模型和知识库内容都强相关**，更换模型或大改资料后必须重新校准——
> 分别用若干课内问题和课外问题观察距离分布，取「课内最大距离」与「课外最小距离」之间。
> 另外本系统有两层防编造：阈值这一层拒掉明显无关的提问，`llm.py` 的系统提示词
> 再兜一层——检索到的资料若不足以回答，模型会输出固定拒答话术。
> 因此阈值可略偏宽松，避免误拒答真正相关的问题。
>
> 实测参考（本地 `bge-small-zh-v1.5` + 本仓库的操作系统教材，1,112 块）：
> 课内问题最近距离 0.16~0.36，课外问题 0.51~0.70，两者完全可分，故取中点 `0.43`。

---

## 十一、常见问题排错

| 现象 | 原因与解决 |
| ---- | ---------- |
| 报 `401 Unauthorized` / 未配置 Key | DeepSeek 的 Key 没填或填错，检查 `.env` 的 `DEEPSEEK_API_KEY` |
| 报 `404` 且模型名看着没错 | DeepSeek 请用 `deepseek-flash` / `deepseek-v4-pro`；旧名 `deepseek-chat`、`deepseek-reasoner` 已不在官方文档中 |
| 首次上传课件卡很久 | 是在下载本地向量化模型（约 100MB），属正常；之后会走本地缓存，秒级完成 |
| 模型下载超时 / 连接失败 | 确认 `HF_ENDPOINT=https://hf-mirror.com` 未被清空（本项目默认已配） |
| 报 `Could not load model ... from any source` | 模型下载失败。检查网络与 `HF_ENDPOINT`，或删除 `backend/data/models/` 后重试 |
| 报向量维度不一致 / `dimension mismatch` | 切换过 `EMBEDDING_PROVIDER`。删除 `backend/data/chroma/` 后重新上传课件重建 |
| 上传成功但知识库列表为空 | 检查 `backend/data/chroma/` 是否可写（向量化失败会导致入库中断） |
| 检索到了片段，模型仍答「没有该知识点」 | 两种可能：① 命中的是「有词无内容」的标题块 → 已通过切块时合并短段落修复；② 资料确实未涵盖该知识点，此时拒答是**正确**的防编造行为 |
| 提问总返回「没有该知识点」 | 知识库为空，或 `RELEVANCE_THRESHOLD` 过小。先确认已上传文档，再重新校准阈值（见第十节） |
| 回答很慢 | 确认 `CHAT_THINKING=false`（默认已是）；`deepseek-flash` 比 `deepseek-v4-pro` 快很多 |
| 一键脚本中文乱码 | 脚本须保持 GBK 编码，勿另存为 UTF-8 |
| 前端 5173 打不开接口 | 确认后端 8000 已启动；`vite.config.js` 中代理目标为 `http://localhost:8000` |
