# Skyper 本机环境安装清单

配置日期：2026 年 11 月 11 日。项目位置：`D:\default\Desktop\origin\codex_project\skyper`。

## 当前完成情况

开发工具和前后端依赖已安装，前端构建、64 项后端离线回归测试、4 项 Agent 离线评测全部通过。Python 依赖完整性检查通过。

**本机配置和首次初始化已完成。** Windows 重启后 WSL 和虚拟机平台已生效；PostgreSQL、MinIO、Elasticsearch 三个服务均健康，前后端已运行。管理员通过前端代理登录、受保护接口、后台文档任务和 MinIO 文件读写校验通过。

日常双击 **`start.bat`** 即可启动，双击 **`stop.bat`** 停止。`finish-setup.bat` 可用于重新检查安装状态，不再需要重复安装环境或重启 Windows。首次下载和重新构建镜像需要联网，请先启用本机网络代理；现有镜像的日常启动无需重新下载。

访问 <http://127.0.0.1:5173/>；API 文档为 <http://127.0.0.1:10001/docs>。本机开发管理员为 `admin`，密码以现有 `.env` 的 `DEV_ADMIN_PASSWORD` 为准。首次验证结果保存在 `.runtime\installation-verified.json`；登录与存储读写验证保存在 `.runtime\runtime-verification.json`，不包含密码或令牌。

## 已安装条目

| 条目 | 版本 / 数量 | 安装位置 | 状态 |
| --- | --- | --- | --- |
| Python（uv 管理的完整独立发行版） | 3.12.16 | `D:\develop\python\cpython-3.12.16-windows-x86_64-none` | 已验证 |
| Python 环境管理工具 uv | 0.13.7 | `D:\develop\uv` | 已验证 |
| 项目 Python 虚拟环境 | 110 个包，含 pip、后端与开发测试依赖 | `D:\develop\skyper-python\.venv` | 已验证 |
| Node.js LTS | 24.22.2 | `D:\develop\nodejs\node-v24.22.2-win-x64` | 已验证 |
| npm（随 Node.js 安装） | 11.19.1 | 同上 | 已验证 |
| 前端依赖 | 按 package-lock.json 安装 353 个包 | `D:\develop\skyper-frontend\node_modules` | 已构建验证 |
| Git for Windows 便携版 | 2.56.1.windows.1 | `D:\develop\git` | 已验证 |
| Docker Desktop | 4.99.0 | `D:\develop\docker` | Linux 引擎运行正常 |
| Docker CLI | 29.9.3 | `D:\develop\docker\resources\bin` | 已验证客户端版本 |
| Docker Compose | 5.7.0 | Docker 随附组件，位于 `D:\develop\docker` | 已验证配置 |
| WSL | 3.0.5.0 | `C:\Program Files\WSL` | 已安装，系统组件 |
| Windows Virtual Machine Platform / WSL 功能 | 随系统维护 | Windows 系统目录 | 已生效 |

系统盘仅保留 Windows/WSL 系统组件及安装器、Docker 必需的注册信息、服务、配置和日志。Docker 程序主体和 Linux 数据磁盘均已指定 D 盘；没有额外安装 Ubuntu、Java、Conda 或独立数据库程序。

### 已初始化并验证的数据服务

| 服务 | 项目指定镜像 / 版本 | 本地端口 | 存储方式 |
| --- | --- | --- | --- |
| PostgreSQL + pgvector | PostgreSQL 16.15 + pgvector 0.8.7；`pgvector/pgvector:pg16` | 5432 | 独立 `pgdata` 数据卷 |
| MinIO | 官方源码构建 `skyper-minio:RELEASE.2025-10-15T17-29-55Z` | API 9000、控制台 9001 | 独立 `miniodata` 数据卷 |
| Elasticsearch + IK | Elasticsearch 8.15.0 + IK 8.15.0；本地构建 `skyper-es-ik:8.15.0` | 9200 | 独立 `esdata` 数据卷 |

以上由 Docker 管理，各服务数据卷相互独立。镜像、编译缓存和数据卷统一存放于 `D:\develop\docker-data` 下的 Linux 虚拟磁盘内部，不是直接可浏览的三个 Windows 数据文件夹。已核实 `D:\develop\docker-data\disk\docker_data.vhdx` 和 `D:\develop\docker-data\main\ext4.vhdx` 实际存在。MinIO 的 Go 工具只安装于 Docker 构建阶段，没有额外安装到 Windows。

本次解决了两个下载问题：Docker 构建客户端没有自动读取系统代理，现已由本机启动配置同步；原 MinIO 公共镜像返回未授权，现改为校验固定官方源码后构建。构建细节见 `minio\README.md`。MinIO 应用存储桶 `skyper-documents` 已初始化。

## 缓存、清单和原有文件

| 内容 | 目录 / 文件 |
| --- | --- |
| 官方安装包和安装日志 | `D:\develop\installers` |
| uv 下载缓存 | `D:\develop\uv-cache` |
| pip 缓存 | `D:\develop\pip-cache` |
| npm 缓存 | `D:\develop\npm-cache` |
| npm 全局包目录 | `D:\develop\npm-global` |
| Docker CLI 配置 | `D:\develop\docker-config` |
| 项目启动时的临时目录 | `D:\develop\temp` |
| Python 全部已安装版本 | `D:\develop\skyper-python\installed-requirements.txt` |
| 前端直接依赖版本 | `D:\develop\skyper-frontend\installed-packages.json` |
| 前端完整版本锁定清单 | 项目 `Skyper-frontend\package-lock.json`；安装目录也保留副本 |
| 原有前端依赖备份 | `D:\develop\skyper-frontend\node_modules-before-setup` |
| 修改前的用户环境变量备份 | `D:\develop\installers\environment-before-skyper.json` |

项目中的 `Skyper-python\.venv` 和 `Skyper-frontend\node_modules` 是指向 D 盘安装目录的目录联接；依赖实体位于 `D:\develop`。原有前端依赖已保留，没有删除。原有 `.env` 和已有项目修改均保留。

已设置当前用户的工具 PATH、uv/pip/npm 缓存、npm 全局包目录和 Docker CLI 配置目录。**新开的终端生效**。项目启动器还会读取被 Git 忽略的 `.runtime\environment.ps1`，因此无需手动激活环境，并能找到安装在 D 盘的 Docker Desktop。该配置在系统代理开启时同步 HTTP_PROXY/HTTPS_PROXY，并让本机接口绕过代理。Docker 引擎探测设置 10 秒超时；停止脚本会终止已验证的进程及其子进程，避免 Windows Python 启动器退出后留下占用端口的后端。

## 验证记录与限制

- `npm run build`：类型检查和生产构建通过。项目原有开发工具的 Vite peer 版本警告以及大文件体积提示不影响本次构建结果。
- 后端 `app.main` 导入通过。
- `pip check`：无依赖冲突。
- `test_agent_regression.py`、`test_document_ingestion.py`、`test_document_upload.py`、`test_model_protocols.py`：64 项通过。
- `python -m app.evaluation.runner`：4 项全部 PASS。
- PowerShell 启动脚本语法检查及 `docker compose config --quiet` 通过。
- `finish-setup.ps1` 完整执行成功；三个容器均为 healthy，前端和后端返回正常 HTTP 响应。
- 中文 IK 分词、pgvector 扩展和应用数据库初始化通过。
- 管理员通过前端 `/api` 代理登录、读取个人资料和管理健康接口通过；文档处理工作进程运行正常。
- MinIO 临时文件写入、读回比对和清理通过；应用存储桶已创建。
- 实际执行停止再启动，确认前后端端口释放、数据卷保留、服务可恢复。
- 后端 Elasticsearch 客户端限制在 8.x，以匹配项目服务端；bcrypt 遵守项目要求为 4.0.1；补充安装 Windows 所需的 `psycopg-binary` 和声明的开发测试工具。

## 仍需你填写的配置

现有 `Skyper-python\.env` 中 `CHAT_API_KEY`、`EMBEDDING_API_KEY` 和 `MINERU_TOKEN` 仍为占位值，本次未修改或伪造密钥。聊天和知识库问答需要真实聊天/Embedding 配置；扫描 PDF、图片及其他云端文档解析需要 MinerU Token。可按 `MODEL_SETUP.md` 在管理页面配置模型；无需把密钥发送到聊天中。

本地环境现已可用。真实模型调用与云端文档解析仍需以上有效密钥，未进行真实模型调用验证。
