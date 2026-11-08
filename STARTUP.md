# Skyper：启动、登录与电脑重启后的操作

## 现在如何打开页面

在项目文件夹双击 **start.bat**。本机位置是 D:/Desktop/codex_project/skyper/start.bat。

它依次检查 Python 和 Node.js，启动 Docker Desktop（如果尚未运行且位于默认安装位置），等待 PostgreSQL、MinIO、Elasticsearch 全部健康，启动后端和前端，检查实际 HTTP 响应，然后打开 http://127.0.0.1:5173/。

本地示例管理员：用户名 admin，密码 Admin@123456。如果你已自行改密，应使用新密码；启动脚本不会重置已有用户密码。

也可以在 PowerShell 中执行：

~~~powershell
cd D:/Desktop/codex_project/skyper
.\start.bat
~~~

出现绿色的 Skyper is ready 表示前后端都能响应；脚本正常结束后可关闭启动窗口，后台服务会继续运行。重复执行 start.bat 会复用正常运行的服务，端口被其他应用占用时会报告错误。

## 电脑重启后

前后端目录分别为 `Skyper-frontend` 和 `Skyper-python`，所有启动命令均已同步。更新项目命名后，JWT 签发标识与刷新 Cookie 也统一为 Skyper；已有浏览器会话可能需要重新登录一次，账号、密码、文档和模型配置不变。

1. 打开 Docker Desktop，等待引擎就绪；如果安装在默认位置，start.bat 也会尝试自动启动它。
2. 双击项目中的 start.bat，等待就绪后用浏览器登录。
3. 无需再次安装 Python/npm 依赖，无需重新创建数据库，也无需重新注册账号。

Docker Desktop 只负责本项目的三个数据服务；FastAPI 后端和 Vite 前端在 Windows 上运行，因此只打开 Docker Desktop 并不能恢复网页。本脚本会把这三部分一起启动。电脑重启会停止本地前后端进程，需重新运行脚本。

可选：在 Docker Desktop 的 Settings → General 中启用 **Start Docker Desktop when you sign in to your computer**。这只是让 Docker Desktop 随登录启动；仍需运行 start.bat 来启动 Skyper 前后端。本次未安装 Windows 开机任务。

## 停止和查看状态

不用时双击 **stop.bat**。脚本仅停止自己记录的 Skyper 前后端进程，再执行 docker compose stop；不会删除容器、数据库卷或已上传文件，也不会退出 Docker Desktop 的其他项目。

~~~powershell
cd D:/Desktop/codex_project/skyper
.\stop.bat
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\skyper.ps1 -Action Status
docker compose ps -a
~~~

不要把 docker compose down -v 当作日常关机步骤：-v 会移除数据卷。正常重启/停止不会清空账号和文档。启动脚本不会先删除容器，也不会将已运行的 skyper-pg 误判为 5432 端口冲突。

如果前后端是你在其他终端手动启动的，先在对应终端按 Ctrl+C；stop.bat 不会强制结束不属于它的进程。

## 日志与常见问题

启动日志保存在项目 .runtime/ 目录，它已被 Git 忽略：

- backend.stderr.log：后端启动日志、数据库连接及异常。
- backend.stdout.log：后端标准输出。
- frontend.stdout.log / frontend.stderr.log：前端启动与代理错误。
- services.json：本脚本启动的进程编号、启动时间和可执行文件，用于准确停止进程。

~~~powershell
Get-Content .runtime/backend.stderr.log -Tail 60
Get-Content .runtime/frontend.stdout.log -Tail 40
docker compose logs --tail 50
~~~

| 现象 | 检查与处理 |
| --- | --- |
| 浏览器 ERR_CONNECTION_REFUSED | 5173 前端未运行；先运行 start.bat，查看它是否报告就绪。 |
| 页面能打开，登录报网络错误/502 | 检查 10001 后端是否就绪，以及 backend.stderr.log；默认代理已固定为 127.0.0.1:10001。 |
| 登录提示账号密码错误 | 使用已有账号和当前密码；重启不会重置密码。 |
| Docker 无法连接 | 打开 Docker Desktop，确认 Linux 容器引擎就绪；若安装位置不同，先手动打开。 |
| Compose 报端口占用 | 查看错误所指端口的实际进程；不要直接停止未知 PostgreSQL 服务。 |
| Python dependencies missing | 按下方首次安装步骤准备环境，再运行 start.bat。 |
| 修改了后端代码 | stop.bat 后重新 start.bat；便捷启动默认不启用热重载，手动开发可使用下方 --reload 命令。 |

## 首次安装或迁移到另一台电脑

需要 Python 3.11+、Node.js（package.json 要求 ^20.19.0 或 >=22.12.0）、Docker Desktop 和 Git。当前机器已具备运行依赖，日常启动不需重复此节。旧 init.bat 仍是历史 Conda 初始化脚本，首次安装请按本节操作。

从项目根目录执行：

~~~powershell
# 只有 .env 不存在时才复制，保留已有配置
if (-not (Test-Path Skyper-python/.env)) {
    Copy-Item Skyper-python/.env.example Skyper-python/.env
}
cd Skyper-python
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd ../Skyper-frontend
npm ci
cd ..
.\start.bat
~~~

启动器按顺序寻找已安装依赖的项目 .venv、当前激活的 Conda 环境、PATH 中的 Python；不强制绑定特定名称的 Conda 环境。不会打印 .env 内容或登录令牌。

.env 中配置 CHAT_API_KEY、EMBEDDING_API_KEY 和 AUTH_JWT_SECRET。模型密钥不影响已有账号登录，但真实聊天/知识库问答需要有效模型配置。TXT/Markdown、DOCX 和文字型 PDF 可本地解析；扫描件、图片及其他 Office 格式还需要有效 MinerU Token。

### 文档已上传但不能问答

文档空间支持一次选择或拖入多个文件。单个文件上限为 30 MB（31,457,280 字节，含边界），不是整批合计上限。点击“开始上传”后按队列逐一上传；单个文件失败不会中断其余文件，可查看该文件的失败原因并点击“重试”或“重试失败”。上传成功后仍需等待后台解析和索引完成。

- **已解析，待配置**：文件和文字分块已保存，可预览和下载。管理员在“模型管理”中添加并激活 Embedding 模型（也可修改 .env 的 EMBEDDING_API_KEY 后重启后端），然后在文档列表点击“重新处理”。变成“就绪”后才完成向量化和全文索引。
- **云端解析未配置 / Token 已过期**：请管理员更新 MinerU 配置，或把文件转换为含文字的 DOCX、PDF、TXT。仅把图片放进 Word 不等于可提取文字。
- **文件损坏或加密**：请用原软件重新导出未加密文件。
- **自动重试中**：暂时性网络错误会重试；配置错误不会重复发送无效请求。页面会展示具体原因。
- 模型密钥只需填写到本地 .env 或管理页面，不要发送到聊天中。配置模型时需同时核对模型名、API 地址和向量维度。
- 新版管理页面可按厂商自动填写协议与地址，支持在线获取模型和自定义 Embedding。保存前会真实测试；完整说明见 [MODEL_SETUP.md](MODEL_SETUP.md)。

## 手动启动（开发时可用）

在三个终端分别执行，并保持后两者运行：

~~~powershell
# 终端一：项目根目录
cd D:/Desktop/codex_project/skyper
docker compose up -d --wait --wait-timeout 180

# 终端二：后端；若使用 .venv，把 python 替换为 ./.venv/Scripts/python.exe
cd D:/Desktop/codex_project/skyper/Skyper-python
python -m uvicorn app.main:app --host 127.0.0.1 --port 10001 --reload

# 终端三：前端
cd D:/Desktop/codex_project/skyper/Skyper-frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
~~~

| 服务 | 本地地址 |
| --- | --- |
| 网页 | http://127.0.0.1:5173/ |
| 后端 API 文档 | http://127.0.0.1:10001/docs |
| 管理员系统检查 | /api/admin/health，需管理员 Bearer Token |
| PostgreSQL | 127.0.0.1:5432 |
| MinIO Console | http://127.0.0.1:9001/ |
| Elasticsearch | http://127.0.0.1:9200/ |

使用开发示例账号和服务密码仅适合本机开发。

## 官方参考

- [Docker Desktop 启动设置](https://docs.docker.com/desktop/settings-and-maintenance/settings/)
- [docker compose up 与 --wait](https://docs.docker.com/reference/cli/docker/compose/up/)
- [docker compose stop](https://docs.docker.com/reference/cli/docker/compose/stop/)
