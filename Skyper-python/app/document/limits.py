"""Shared document upload limits (30 MiB per file, inclusive)."""
from app.common.exception.exceptions import BusinessException

MAX_FILE_SIZE = 30 * 1024 * 1024


def validate_file_size(size: int) -> None:
    if size <= 0:
        raise BusinessException("不能上传空文件")
    if size > MAX_FILE_SIZE:
        raise BusinessException("单个文件大小不能超过 30 MB（31,457,280 字节）")


async def read_upload_file(file) -> bytes:
    """Reject oversize metadata early and bound the in-memory read as well."""
    if file.size is not None:
        validate_file_size(file.size)
    data = await file.read(MAX_FILE_SIZE + 1)
    validate_file_size(len(data))
    return data
