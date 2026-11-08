"""Public ingestion errors: actionable messages without credentials or document text."""
import re

import httpx


class IngestionError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False, waiting: bool = False):
        super().__init__(message)
        self.retryable = retryable
        self.waiting = waiting


def is_placeholder(value: str | None) -> bool:
    value = (value or "").strip().lower()
    return not value or any(marker in value for marker in ("sk-your", "your-api", "your-token", "your-key", "change-me", "placeholder"))


def public_reason(value: str | None) -> str | None:
    if not value:
        return None
    # Also protect historical errors already stored in the database.
    value = re.sub(r"https?://\S+", "[服务地址已隐藏]", value)
    value = re.sub(r"(?i)bearer\s+\S+", "Bearer [已隐藏]", value)
    value = re.sub(r"(?i)\bsk-[\w-]+|\beyJ[\w.-]+", "[密钥已隐藏]", value)
    value = re.sub(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+", r"\1=[已隐藏]", value)
    if "mineru" in value.lower() and any(word in value.lower() for word in ("expired", "unauthorized", "401")):
        return "解析失败：MinerU Token 无效或已过期，请管理员更新文档解析配置后重试。DOCX 和文字型 PDF 可使用本地解析。"
    return value[:1000]


def ingestion_error(exc: Exception, stage: str) -> IngestionError:
    if isinstance(exc, IngestionError):
        return exc
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return IngestionError(f"{stage}失败：无法连接依赖服务或请求超时。请检查 Docker 服务和网络后重试。", retryable=True)
    # Do not return raw SQL/provider exception text to users: it may contain data or secrets.
    return IngestionError(f"{stage}失败（{type(exc).__name__}）。文件已保存，请联系管理员查看后台日志后重试。", retryable=True)
