# MinIO 本地镜像

项目使用官方源码发布 `RELEASE.2025-10-15T17-29-55Z`，按 [官方发布说明](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z) 从源码构建。原 Docker Hub 和 Quay 镜像在本机安装时均返回未授权错误。

Dockerfile 从 MinIO 官方 GitHub 仓库下载固定版本源码，使用 SHA-256 校验，并通过源码中的 go.sum 校验 Go 依赖。Go 编译工具仅存在于构建阶段，最终镜像包含 MinIO、证书和健康检查所需的 curl。镜像中保留 MinIO 的 AGPL 许可证。

在项目根目录执行 `docker compose build minio`。构建完成后，日常启动不需要重新编译。

若网络需要代理，Windows 中的 Docker 构建客户端需要 HTTP_PROXY/HTTPS_PROXY；容器内编译所用代理地址必须使用 `host.docker.internal`，不能使用 Windows 的 `127.0.0.1`。本机代理端口为 7890 时，可在已设置客户端代理的终端执行：

```powershell
docker compose build --build-arg HTTP_PROXY=http://host.docker.internal:7890 --build-arg HTTPS_PROXY=http://host.docker.internal:7890 minio
```

代理参数只用于构建，不写入运行容器的环境变量。构建缓存由 Docker 管理，本机位于 `D:\develop\docker-data`。
