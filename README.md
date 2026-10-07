# 课程知识问答 RAG 智能体

基于 **FastAPI + ChromaDB + 豆包大模型 + Vue3 + Element Plus** 的前后端分离课程知识问答系统。
上传课程课件（PDF / Word）后，系统自动解析文本、语义切块、向量化入库；提问时先做向量相似度检索，
再把 Top3 相关片段与问题拼接后交给豆包模型作答；检索不到相关内容时**强制拒答**，杜绝模型编造。

---

## 一、项目目录结构

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
│   ├── config.py                    # 全局配置（读取 .env）
│   ├── schemas.py                   # 请求/响应数据模型
│   ├── document_parser.py           # PDF / Word 文档解析
│   ├── text_splitter.py             # 文本语义切块（滑窗+重叠）
│   ├── embeddings.py                # 豆包 Embedding + Chroma 嵌入函数
│   ├── vector_store.py              # ChromaDB 本地向量库（余弦距离）
│   ├── llm.py                       # 豆包对话接口与系统提示词
│   ├── evaluator.py                 # 评测记录生成与读取
│   ├── rag_service.py               # RAG 核心业务流程
│   ├── probe_models.py              # 工具：探测当前 Key 可用的模型名（排错用）
│   ├── build_os_book.py             # 工具：生成《操作系统》课程知识库 Word 文档
│   ├── start_backend.bat            # 单独启动后端（调试用）
│   ├── 操作系统课程知识库.docx        # 示例课件（可直接上传测试）
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
3. **豆包（火山方舟 Ark）API Key 与模型开通** —— 见下方第 3 步，**这是最容易踩坑的一步**

### 3. 开通模型并配置 Key（必做，否则上传/提问必定失败）

在 <https://console.volcengine.com/ark> 完成以下三步：

1. **开通模型**：进入「**开通管理**」，开通
   - 一个**对话模型**（如 Doubao-pro / Doubao-seed 系列）
   - 一个**向量化模型**（如 Doubao-embedding 系列）

   > ⚠️ 只创建 API Key 而**没有在「开通管理」里开通模型**时，接口会返回
   > `ModelNotOpen` 或 `InvalidEndpointOrModel.NotFound`，表现为「上传课件失败」「提问报错」。
   > 注意：接口返回的 `/models` 列表是平台模型目录，**不代表你的账号已开通**。

2. **创建 API Key**：在「API Key 管理」中新建，复制形如 `ark-xxxxxxxx` 的密钥。

3. **创建两个推理接入点**（推荐，最稳妥）：进入「**在线推理**」→「**创建推理接入点**」，
   分别创建一个**对话**接入点和一个**向量化**接入点，各得到一个 `ep-xxxxx` ID。

   > 为什么推荐接入点而不是直接用模型名？模型版本号会「即将下线」，一旦下线，
   > 按模型名调用就会报 `InvalidEndpointOrModel.NotFound`；而接入点会锁定版本，不受影响。

   ⚠️ **创建向量化接入点时请注意模型类型**：如果选到的是 **Doubao-embedding-vision**
   这类**多模态**模型，它**不支持标准 `/embeddings` 接口**（调用会报
   `400 ... does not support this api`），必须走 `/embeddings/multimodal` 接口。
   本项目已支持自动适配，只需把 `EMBEDDING_MODE` 设为 `multimodal`（或保持 `auto`）。

4. **填写 `backend/.env`**：

   ```ini
   ARK_API_KEY=你的火山方舟_API_Key
   ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
   CHAT_MODEL=ep-20240xxxxxx-xxxxx          # 对话接入点 ID
   EMBEDDING_MODEL=ep-20240xxxxxx-yyyyy     # 向量化接入点 ID
   EMBEDDING_MODE=multimodal                # 文本模型填 text；多模态/不确定填 auto
   ```

5. **验证模型可用**（强烈建议，可省去大量排错时间）：

   ```bash
   cd backend
   .venv\Scripts\python probe_models.py
   ```

   输出中对应模型显示 `OK` 即表示可用；若显示 `FAIL ... ModelNotOpen`，
   说明该模型**尚未开通**，请回到第 1 步。

---

## 三、一键启动（推荐，最省事）

直接双击项目根目录下的脚本即可，无需手敲命令：

| 顺序 | 脚本 | 作用 |
| ---- | ---- | ---- |
| ① | `① 首次安装（双击我）.bat` | 自动创建 venv、装后端依赖（清华镜像）、装前端依赖（淘宝镜像）；若缺少 `.env` 会自动生成并打开记事本让你填 Key |
| ② | `② 启动项目（双击我）.bat` | 分别启动后端（8000）与前端（5173），等待约 8 秒后自动打开浏览器 |
| ③ | `③ 停止项目（双击我）.bat` | 关闭前后端两个服务窗口 |

> 脚本使用 **GBK + CRLF + `chcp 936`** 编码编写，请勿用编辑器另存为 UTF-8，否则中文会乱码。

若喜欢手动控制，见下方第四、五节。

---

## 四、后端启动步骤（手动）

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

## 五、前端启动步骤（手动）

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

## 六、使用流程

1. 打开页面，进入 **知识库管理**，上传课程 PDF / Word 课件（可上传多份）；
2. 切换到 **智能问答**，输入课程相关问题；
3. 系统检索知识库并生成回答，回答下方「评测信息」可展开查看：
   - 是否检索到有效资料、是否触发拒答；
   - 命中片段的来源文件、相似度距离与内容摘要。
4. 当问题与知识库无关时，系统固定返回：
   **「当前课程知识库中没有该知识点，无法作答。」**

> 首次使用可先上传 `backend/操作系统课程知识库.docx` 作为测试课件。

---

## 七、主要接口说明

| 方法   | 路径                          | 说明                     |
| ------ | ----------------------------- | ------------------------ |
| POST   | `/api/documents/upload`       | 上传 PDF/DOCX 并入库     |
| GET    | `/api/documents`              | 查询已上传文档列表       |
| DELETE | `/api/documents/{doc_id}`     | 删除指定文档及向量       |
| POST   | `/api/chat`                   | RAG 问答（含评测信息）   |
| GET    | `/api/evaluations`            | 查询全部评测记录         |
| GET    | `/api/health`                 | 健康检查                 |

---

## 八、可调参数说明（backend/.env）

| 参数                 | 含义                                                       |
| -------------------- | ---------------------------------------------------------- |
| `CHUNK_SIZE`         | 文本切块最大字符数（默认 500）                             |
| `CHUNK_OVERLAP`      | 相邻块重叠字符数（默认 80）                                |
| `TOP_K`              | 检索片段数量（默认 3）                                     |
| `RELEVANCE_THRESHOLD`| 余弦距离相关性阈值，越小越严格；误拒答可调大，乱答可调小   |
| `EMBEDDING_MODE`     | 向量化接口形态：`text` / `multimodal` / `auto`（默认 `auto`）|
| `EMBEDDING_CONCURRENCY` | `multimodal` 模式下的并发请求数（默认 8）               |

> **关于 `EMBEDDING_MODE`**：火山方舟有两套向量化接口。
> `doubao-embedding-text-*` 等纯文本模型走标准 `/embeddings`，一次请求可批量返回多条向量；
> `doubao-embedding-vision-*` 等多模态模型必须走 `/embeddings/multimodal`，且该接口会把
> **整批输入融合成一条向量**，因此本项目在多模态模式下改为**每个文本块发一次请求**
> （靠 `EMBEDDING_CONCURRENCY` 并发提速）。`auto` 会先试标准接口，遇到
> `does not support this api` 时自动回退到多模态。

> **关于切块**：`text_splitter.py` 不是「一段一块」，而是把**连续段落累积合并**到接近
> `CHUNK_SIZE` 再成块，并在**章节标题处对齐块边界**。原因：
> ① 电子书/课件常「一行即一段」，逐段成块会产生大量碎块，每块上下文太少、检索命中率差，
> 且会放大向量化接口的每请求固定开销；
> ② 标题若独立成块，会因关键词高度匹配而挤占 Top-K 名额，造成「检索到了却答不出来」。
>
> 标题识别只认**多级编号**（`1.1` / `1.2.3`）、`第X章/节`、中文数字顿号（`一、`），
> 并且排除以句末标点结尾的段落——否则「`1.试说明…`」这类编号习题会被误判成标题，
> 导致整份习题粘连成一个超大块。
> 同时会过滤页码与重复出现的页眉页脚短行。
> 只有**段落本身**超过 `CHUNK_SIZE` 时才滑窗切分并保留 `CHUNK_OVERLAP` 重叠。
>
> 实测效果（424,783 字符的教材）：逐段成块为 3,146 块（平均 134 字符），
> 改后为 1,112 块（平均 376 字符，上限 500），并过滤掉 389 个页码与 419 个重复页眉。

> **关于阈值**：Chroma 使用余弦距离（0 表示完全相同），距离大于阈值的片段视为不相关。
> 该阈值**与所用 Embedding 模型和知识库内容都强相关**，更换模型或大改资料后必须重新校准——
> 分别用若干课内问题和课外问题观察距离分布，取「课内最大距离」与「课外最小距离」之间。
> 另外本系统有两层防编造：阈值这一层拒掉明显无关的提问，`llm.py` 的系统提示词
> 再兜一层——检索到的资料若不足以回答，模型会输出固定拒答话术。
> 因此阈值可略偏宽松，避免误拒答真正相关的问题。
>
> 实测参考（`doubao-embedding-vision-251215` + 本仓库的操作系统教材，1,112 块）：
> 课内问题最近距离 0.22~0.38，课外问题 0.66~0.78，两者完全可分，故取中点 `0.52`。
> 若只放一份很小的知识库（如 28 块的摘要文档），分布会明显收窄（0.60 / 0.63），
> 此时阈值需要重新测。

---

## 九、常见问题排错

| 现象 | 原因与解决 |
| ---- | ---------- |
| 上传课件提示「上传失败」/ 提问报错 | 多为模型未开通。运行 `python probe_models.py` 确认；若为 `ModelNotOpen`，去「开通管理」开通模型 |
| 报 `400 ... does not support this api` | 向量化接入点用的是**多模态**模型，不支持标准 `/embeddings`。把 `EMBEDDING_MODE` 设为 `multimodal` 或 `auto` |
| 报 `InvalidEndpointOrModel.NotFound`（模型名正确） | 该模型版本已「即将下线」，按模型名不再提供服务。改用「在线推理」创建的 `ep-xxxxx` **接入点** |
| 启动即报 `AttributeError: 'Settings' object has no attribute 'ark_api_key'` | `config.py` 与 `llm.py`/`embeddings.py` 字段不一致。本仓库已修复（commit `151d5fa`），请勿回退该文件 |
| 上传成功但知识库列表为空 | 检查 `backend/data/chroma/` 是否可写；确认模型确实可用（向量化失败会导致入库中断） |
| 检索到了片段，模型仍答「没有该知识点」 | 两种可能：① 命中的是「有词无内容」的标题块 → 已通过切块时合并短段落修复；② 资料确实未涵盖该知识点，此时拒答是**正确**的防编造行为 |
| 提问总返回「没有该知识点」 | 知识库为空，或 `RELEVANCE_THRESHOLD` 过小。先确认已上传文档，再重新校准阈值（见第八节） |
| 一键脚本中文乱码 | 脚本须保持 GBK 编码，勿另存为 UTF-8 |
| 前端 5173 打不开接口 | 确认后端 8000 已启动；`vite.config.js` 中代理目标为 `http://localhost:8000` |
