# Skyper

Skyper 是一个面向个人和小团队的 Agent 工作台。它以 Argus RAG 项目为原型，保留文档知识库、混合检索、群组协作和 LangGraph Agent 能力，并补充可观察的工具调用、权限控制、高风险操作确认和离线回归评测。

项目仓库：[Fty-RAG-Agent](https://github.com/fengtianyi52/Fty-RAG-Agent)

## 中文说明

### 项目定位

Skyper 的目标不只是生成回答，而是让 Agent 能在明确的权限边界内读取私有知识、调用工具、返回证据，并让开发者检查其行为。系统由三个主要环节组成：

1. **知识层**：解析和切分文档，建立全文及向量索引。
2. **行动层**：使用 LangGraph 编排对话、知识库问答和工具调用，并通过 SSE 流式返回事件。
3. **可靠性层**：使用 Python 离线检查工具选择、参数、角色权限及高风险操作确认。

### 主要功能

- Agent 对话工作台、会话管理和上下文查看。
- 知识库问答，支持 Elasticsearch 全文检索、PostgreSQL/pgvector 向量检索及引用信息。
- TXT、Markdown 文档可本地解析；PDF、Office 文档和图片由 MinerU 云端解析，并支持分块上传、续传、后台处理、状态查询和失败重试。
- MinerU 适用于复杂版式、扫描件、表格和公式；处理这些文件类型时需要配置 MinerU Token。
- 群组、成员邀请、加入申请和知识访问控制。
- JWT 登录、bcrypt 密码哈希、普通用户/管理员角色和后端权限校验。
- 管理员 Agent 高风险写操作确认；普通用户不能执行管理员写操作。
- Python 离线 Agent 回归评测，不需要调用真实 LLM。
- 管理 API：用户、文档、问答历史、模型配置、API Token、审计和指标。
- 可定制工作台主题：切换强调色、上传背景图片、调整遮罩。背景图保存在当前浏览器 localStorage，不会上传到服务器。

### 系统架构

~~~text
Browser
  Vue 3 + TypeScript + Vite + Element Plus + Pinia
              │ HTTP / SSE
              ▼
FastAPI backend (Python 3.11+)
  ├─ Auth / Users / Groups / Documents
  ├─ QA retrieval and citations
  ├─ LangGraph Agent and tool policy
  ├─ Offline Agent evaluator
  └─ Admin / Metrics / Audit / Open API
              │
              ├─ PostgreSQL 16 + pgvector
              ├─ Elasticsearch 8 + IK
              └─ MinIO object storage
~~~

### 技术栈

| 层次 | 技术 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite、Vue Router、Pinia、Element Plus、Axios |
| 后端 | Python 3.11+、FastAPI、Uvicorn、Pydantic Settings、SQLAlchemy Async、asyncpg |
| Agent | LangChain、LangGraph、SSE、OpenAI-compatible Chat/Embedding API |
| 检索 | PostgreSQL + pgvector、Elasticsearch 8、IK 中文分词 |
| 文件存储 | MinIO（S3 兼容） |
| 文档解析 | TXT/Markdown 本地解析；PDF、Office 和图片通过 MinerU 解析 |
| 测试 | pytest、pytest-asyncio、HTTPX、离线 Agent 评测 |
| 本地基础设施 | Docker Compose |

### 代码目录

~~~text
skyper/
├─ Argus-frontend/             # Vue 前端
│  └─ src/
│     ├─ api/                  # API 客户端
│     ├─ components/           # 登录、主题面板和共享组件
│     ├─ stores/               # 认证、应用及主题状态
│     └─ views/                # 总览、Agent、QA、文档和管理页面
├─ Argus-python/               # FastAPI 后端
│  ├─ app/
│  │  ├─ assistant/            # LangGraph Agent、会话和工具
│  │  ├─ auth/                 # 登录、JWT 和权限依赖
│  │  ├─ document/             # 文档上传和管理
│  │  ├─ engine/               # Elasticsearch、MinIO、pgvector 适配器
│  │  ├─ evaluation/           # 离线 Agent 评测器
│  │  ├─ group/                # 群组、邀请和加入申请
│  │  ├─ ingestion/            # 文档解析、分块和后台任务
│  │  └─ qa/                   # 检索、问答和引用
│  ├─ .env.example             # 环境变量模板
│  └─ tests/                   # API 和 Agent 回归测试
├─ elasticsearch-ik/           # Elasticsearch + IK 镜像定义
├─ docker-compose.yml          # 本地依赖服务
└─ STARTUP.md                  # 启动补充说明
~~~

目录名 Argus-frontend 和 Argus-python 为兼容现有工程而保留。

### 环境要求

- Docker Desktop
- Python 3.11+
- Node.js 20.19+ 或 22.12+（见 Argus-frontend/package.json）
- npm、Git
- 实际使用聊天和知识库问答时，需要有效的聊天模型及 Embedding API Key

### 本地运行

以下以 Windows PowerShell 为例。

#### 1. 获取项目并创建配置

~~~powershell
git clone https://github.com/fengtianyi52/Fty-RAG-Agent.git
cd Fty-RAG-Agent
Copy-Item Argus-python/.env.example Argus-python/.env
~~~

编辑 Argus-python/.env，至少设置：

~~~env
CHAT_API_KEY=你的聊天模型API密钥
EMBEDDING_API_KEY=你的向量模型API密钥
AUTH_JWT_SECRET=一段足够长且随机的密钥
~~~

.env 仅用于本地配置并已被 Git 忽略。不要提交 API Key、JWT Secret 或其他凭据。

#### 2. 启动 PostgreSQL、MinIO 和 Elasticsearch

~~~powershell
docker compose up -d
docker compose ps
~~~

等待三个服务健康后继续。首次构建 Elasticsearch + IK 镜像可能需要较长时间。

| 服务 | 地址 | 本地默认凭据 |
| --- | --- | --- |
| PostgreSQL + pgvector | 127.0.0.1:5432 | postgres / postgres |
| MinIO API | http://127.0.0.1:9000 | minioadmin / minioadmin |
| MinIO Console | http://127.0.0.1:9001 | minioadmin / minioadmin |
| Elasticsearch + IK | http://127.0.0.1:9200 | 默认无认证 |

#### 3. 安装并启动 Python 后端

~~~powershell
cd Argus-python
python -m venv .venv
.venv/Scripts/Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 10001 --reload
~~~

开发启动流程会创建数据库表、检查 Elasticsearch 索引、初始化开发管理员并启动文档处理任务。

#### 4. 安装并启动 Vue 前端

从项目根目录另开一个 PowerShell：

~~~powershell
cd Argus-frontend
npm install
npm run dev
~~~

打开 http://127.0.0.1:5173。Vite 会将 /api 请求代理到 http://127.0.0.1:10001。

### 登录与常用入口

开发管理员由 .env 中的 DEV_ADMIN_ENABLED、DEV_ADMIN_USERNAME 和 DEV_ADMIN_PASSWORD 控制。示例配置使用 admin / Admin@123456；首次登录后应立即改密。生产环境不要沿用示例密码，并应关闭开发管理员。

| 用途 | 地址 |
| --- | --- |
| Skyper 前端 | http://127.0.0.1:5173 |
| FastAPI Swagger | http://127.0.0.1:10001/docs |
| FastAPI ReDoc | http://127.0.0.1:10001/redoc |
| 管理员系统健康检查 | http://127.0.0.1:10001/api/admin/health（需管理员登录） |

### 测试和离线评测

离线评测不调用外部 LLM：

~~~powershell
cd Argus-python
python -m app.evaluation.runner
python -m app.evaluation.runner --json
pytest -q tests/test_agent_regression.py
~~~

它覆盖预期工具顺序、必需参数、普通用户越权拒绝、破坏性操作确认，以及普通对话不应触发工具等行为。完整 API 测试需要安装后端依赖并启动数据库：

~~~powershell
pytest -q
~~~

### API 分区

- /api/auth：注册、登录、当前用户及密码管理
- /api/assistant：Agent 会话、普通聊天及 SSE 流式聊天
- /api/qa：知识库问答、流式问答和问答历史
- /api/documents：文档上传、预览、下载和重试
- /api/groups：群组、成员、邀请和加入申请
- /api/admin：管理用户、文档、问答、模型、指标、审计和 API Token
- /api/open：受保护的外部集成 API

完整接口参数请查看 Swagger 文档。

### 重要配置

| 配置 | 说明 |
| --- | --- |
| DATABASE_URL | PostgreSQL asyncpg 连接串 |
| CHAT_BASE_URL、CHAT_API_KEY、CHAT_MODEL_NAME | 聊天模型 |
| EMBEDDING_BASE_URL、EMBEDDING_API_KEY、EMBEDDING_MODEL_NAME | 向量模型 |
| EMBEDDING_DIMENSIONS | 向量维度，须与 Embedding 模型匹配 |
| AUTH_JWT_SECRET | JWT 签名密钥，部署时必须更换 |
| CORS_ORIGINS | 允许访问后端的来源 |
| MINIO_* | MinIO 地址和凭据 |
| ES_HOST、ES_PORT | Elasticsearch 地址 |
| MINERU_TOKEN、MINERU_MODEL | PDF、Office 文档和图片解析所用的 MinerU 云服务 |

### 安全说明及当前限制

- Docker Compose 默认凭据仅用于本地开发，部署前必须更换。
- 生产部署应使用强随机 JWT Secret、限制 CORS 来源并关闭开发管理员。
- 权限检查由后端执行；前端界面状态不是安全边界。
- 没有有效的模型 API Key 时，登录、页面浏览及离线评测可运行，但真实 Agent/问答无法调用模型。
- 当前 Docker Compose 面向本地开发，不包含生产级 TLS、反向代理、密钥管理或高可用配置。
- Elasticsearch 默认是单节点开发设置；生产部署需要单独配置认证、容量和备份。
- MinerU 是 PDF、Office 文档和图片解析所需的外部服务，使用这些格式时需单独申请 Token。
- 仓库目前没有单独的 LICENSE 文件；公开分发前请补充合适的许可证。

---

## English Documentation

### Overview

Skyper is an Agent workspace for individuals and small teams, based on the Argus RAG project. It combines private document knowledge, hybrid retrieval, group collaboration and LangGraph agents with observable tool execution, authorization boundaries, confirmation for high-risk actions and offline regression evaluation.

The project is organized into three layers:

1. **Knowledge**: parse and chunk documents, then index them for full-text and vector retrieval.
2. **Action**: orchestrate conversations, knowledge-base Q&A and tool use with LangGraph and stream events over SSE.
3. **Reliability**: use deterministic Python checks for tool selection, arguments, role permissions and destructive-action confirmation.

Repository: [Fty-RAG-Agent](https://github.com/fengtianyi52/Fty-RAG-Agent)

### Features

- Agent chat workspace with session management and context inspection.
- Knowledge-base Q&A with Elasticsearch full-text search, PostgreSQL/pgvector retrieval and citations.
- Local parsing for TXT and Markdown; PDF, Office documents and images are parsed by MinerU, with chunked/resumable uploads, background processing, status tracking and retries.
- MinerU handles complex layouts, scans, tables and formulas; a token is required for those file types.
- Groups, invitations, join requests and backend-enforced knowledge access.
- JWT authentication, bcrypt password hashing and user/admin roles.
- Confirmation before high-risk admin Agent writes; normal users cannot execute admin writes.
- Offline Agent regression evaluation without calling an LLM.
- Admin APIs for users, documents, Q&A history, models, API tokens, audit and metrics.
- Customizable UI with accent colors and a locally uploaded background image. The image is stored in browser localStorage and is not sent to the server.

### Architecture and Stack

~~~text
Browser: Vue 3 + TypeScript + Vite + Element Plus + Pinia
                         │ HTTP / SSE
                         ▼
Backend: Python 3.11+ + FastAPI + SQLAlchemy Async
  ├─ LangChain / LangGraph Agent and tool policy
  ├─ Authentication, groups, documents and Q&A
  ├─ Offline evaluator, admin, metrics and audit APIs
  └─ PostgreSQL + pgvector / Elasticsearch + IK / MinIO
~~~

| Layer | Technologies |
| --- | --- |
| Frontend | Vue 3, TypeScript, Vite, Vue Router, Pinia, Element Plus, Axios |
| Backend | Python 3.11+, FastAPI, Uvicorn, Pydantic Settings, SQLAlchemy Async, asyncpg |
| Agent | LangChain, LangGraph, SSE, OpenAI-compatible chat and embedding APIs |
| Retrieval | PostgreSQL + pgvector, Elasticsearch 8, IK Chinese analyzer |
| Storage | MinIO, an S3-compatible object store |
| Documents | Local TXT/Markdown parsers; MinerU for PDF, Office documents and images |
| Tests | pytest, pytest-asyncio, HTTPX and offline Agent evaluation |
| Infrastructure | Docker Compose |

### Repository Layout

~~~text
Argus-frontend/    Vue application: API clients, stores, components and views
Argus-python/      FastAPI application: assistant, auth, documents, groups, QA and tests
elasticsearch-ik/  Elasticsearch image with IK analyzer
docker-compose.yml Local PostgreSQL, MinIO and Elasticsearch services
STARTUP.md         Additional startup and troubleshooting guide
~~~

The Argus-frontend and Argus-python directory names are retained for compatibility with the existing project structure.

### Requirements

- Docker Desktop
- Python 3.11+
- Node.js 20.19+ or 22.12+ (see Argus-frontend/package.json)
- npm and Git
- Valid chat and embedding API keys for live Agent and retrieval requests

### Quick Start (Windows PowerShell)

Clone the repository and create the local environment file:

~~~powershell
git clone https://github.com/fengtianyi52/Fty-RAG-Agent.git
cd Fty-RAG-Agent
Copy-Item Argus-python/.env.example Argus-python/.env
~~~

Set at least the following values in Argus-python/.env:

~~~env
CHAT_API_KEY=your-chat-model-key
EMBEDDING_API_KEY=your-embedding-model-key
AUTH_JWT_SECRET=long-random-secret
~~~

Start the infrastructure:

~~~powershell
docker compose up -d
docker compose ps
~~~

Wait for PostgreSQL, MinIO and Elasticsearch to become healthy. Then install and run the backend:

~~~powershell
cd Argus-python
python -m venv .venv
.venv/Scripts/Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 10001 --reload
~~~

In another terminal, from the repository root, install and run the frontend:

~~~powershell
cd Argus-frontend
npm install
npm run dev
~~~

Open http://127.0.0.1:5173. The Vite development server proxies /api requests to http://127.0.0.1:10001.

### Development Login and Endpoints

The development account is controlled by DEV_ADMIN_ENABLED, DEV_ADMIN_USERNAME and DEV_ADMIN_PASSWORD in .env. The example uses admin / Admin@123456. Change this password immediately and do not use it in production. Disable the development admin for production deployments.

| Purpose | URL |
| --- | --- |
| Frontend | http://127.0.0.1:5173 |
| FastAPI Swagger | http://127.0.0.1:10001/docs |
| FastAPI ReDoc | http://127.0.0.1:10001/redoc |
| Admin system health check | http://127.0.0.1:10001/api/admin/health (admin login required) |

### Tests

Run the offline evaluator and focused tests:

~~~powershell
cd Argus-python
python -m app.evaluation.runner
python -m app.evaluation.runner --json
pytest -q tests/test_agent_regression.py
~~~

The evaluator checks expected tool order, required arguments, denial of unauthorized writes, confirmation before destructive actions and avoiding unnecessary tools in plain chat. The full API suite requires installed dependencies and running database services:

~~~powershell
pytest -q
~~~

### API Areas

- /api/auth: registration, login, current user and password management
- /api/assistant: Agent sessions, chat and SSE streaming
- /api/qa: knowledge Q&A, streaming Q&A and history
- /api/documents: document listing, upload, preview, download and retry
- /api/groups: groups, members, invitations and join requests
- /api/admin: admin users, documents, Q&A, models, metrics, audit and API tokens
- /api/open: protected APIs for external integrations

See the Swagger page for exact request and response schemas.

### Configuration

| Variable | Purpose |
| --- | --- |
| DATABASE_URL | PostgreSQL asyncpg connection string |
| CHAT_BASE_URL, CHAT_API_KEY, CHAT_MODEL_NAME | Chat model configuration |
| EMBEDDING_BASE_URL, EMBEDDING_API_KEY, EMBEDDING_MODEL_NAME | Embedding model configuration |
| EMBEDDING_DIMENSIONS | Vector size; must match the embedding model |
| AUTH_JWT_SECRET | JWT signing secret; replace before deployment |
| CORS_ORIGINS | Allowed frontend origins |
| MINIO_* | MinIO endpoint and credentials |
| ES_HOST, ES_PORT | Elasticsearch endpoint |
| MINERU_TOKEN, MINERU_MODEL | MinerU cloud parser for PDF, Office documents and images |

### Security and Limitations

- Compose credentials are for local development only; replace them before deployment.
- Use a strong random JWT secret, restrict CORS origins and disable the development admin in production.
- Authorization is enforced by the backend; frontend controls are not a security boundary.
- Without valid model keys, login, navigation and offline evaluation can work, but live Agent and Q&A requests cannot call models.
- Compose is a local-development setup and does not provide production TLS, reverse proxy, secret management or high availability.
- Elasticsearch runs as a single development node by default; production requires its own authentication, capacity and backup plan.
- MinerU requires a separate token for PDF, Office document and image parsing.
- The repository currently has no separate LICENSE file. Add an appropriate license before external distribution.
