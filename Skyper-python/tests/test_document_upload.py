"""Upload limits and independent file requests, without production DB/cloud calls."""
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI, UploadFile

from app.common.exception.exceptions import BusinessException, ForbiddenException
from app.common.exception.handlers import business_exception_handler, forbidden_exception_handler
from app.common.security.context import AuthenticatedUser
from app.document.limits import MAX_FILE_SIZE, read_upload_file, validate_file_size
from app.document.schemas import UploadInitRequest
from app.document.service import DocumentUploadService
from app.document import router as routes


@pytest.mark.parametrize('size', [1, 10 * 1024 * 1024 + 1, MAX_FILE_SIZE])
def test_size_accepts_up_to_30_mib_inclusive(size):
    validate_file_size(size)


@pytest.mark.parametrize('size', [MAX_FILE_SIZE + 1, 256 * 1024 * 1024])
def test_size_rejects_over_limit(size):
    with pytest.raises(BusinessException, match='30 MB'):
        validate_file_size(size)


@pytest.mark.asyncio
async def test_metadata_rejection_happens_before_read():
    file = SimpleNamespace(size=MAX_FILE_SIZE + 1, read=AsyncMock())
    with pytest.raises(BusinessException, match='30 MB'):
        await read_upload_file(file)
    file.read.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('declared_size', [None, 1])
async def test_bounded_read_checks_actual_bytes(declared_size):
    file = SimpleNamespace(size=declared_size, read=AsyncMock(return_value=b'x' * (MAX_FILE_SIZE + 1)))
    with pytest.raises(BusinessException, match='30 MB'):
        await read_upload_file(file)
    file.read.assert_awaited_once_with(MAX_FILE_SIZE + 1)


@pytest.mark.asyncio
async def test_empty_file_rejected():
    file = UploadFile(io.BytesIO(b''), filename='empty.txt', size=0)
    with pytest.raises(BusinessException, match='空文件'):
        await read_upload_file(file)


@pytest.mark.asyncio
async def test_service_enforces_limit_even_without_http_route():
    session = AsyncMock()
    service = DocumentUploadService(session)
    with pytest.raises(BusinessException, match='30 MB'):
        await service.direct_upload(1, 2, b'x' * (MAX_FILE_SIZE + 1), 'big.txt', 'text/plain', 'hash')
    session.execute.assert_not_awaited()


def init_request(size=MAX_FILE_SIZE, chunk_size=5 * 1024 * 1024, count=6):
    return UploadInitRequest(groupId=2, fileName='test.pdf', fileSize=size, fileHash='hash',
                             chunkSize=chunk_size, chunkCount=count)


@pytest.mark.asyncio
async def test_chunk_init_accepts_boundary_and_group_alias():
    session = AsyncMock()
    session.add = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result
    await DocumentUploadService(session).init_upload(1, init_request())
    created = session.add.call_args.args[0]
    assert created.group_id == 2 and created.file_size == MAX_FILE_SIZE


@pytest.mark.asyncio
@pytest.mark.parametrize('size,chunk_size,count', [
    (MAX_FILE_SIZE + 1, 5 * 1024 * 1024, 7),
    (MAX_FILE_SIZE, 0, 6),
    (MAX_FILE_SIZE, 5 * 1024 * 1024, 5),
])
async def test_chunk_init_rejects_invalid_declarations(size, chunk_size, count):
    session = AsyncMock()
    with pytest.raises(BusinessException):
        await DocumentUploadService(session).init_upload(1, init_request(size, chunk_size, count))
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('index,data', [(-1, b'ab'), (2, b'ab'), (0, b'abc')])
async def test_chunk_cannot_exceed_declared_range_or_size(monkeypatch, index, data):
    session = AsyncMock()
    found = MagicMock()
    found.scalar_one_or_none.return_value = SimpleNamespace(
        uploader_user_id=1, status='INIT', file_size=4, chunk_count=2, chunk_size=2)
    session.execute.return_value = found
    from app.document import service
    upload = AsyncMock()
    monkeypatch.setattr(service.storage_service, 'upload', upload)
    with pytest.raises(BusinessException):
        await DocumentUploadService(session).upload_chunk(1, 'USER', 'id', index, data, '')
    upload.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('chunks', [
    [(0, MAX_FILE_SIZE), (1, 1)],
    [(0, 1), (1, 1)],
    [(0, MAX_FILE_SIZE // 2), (0, MAX_FILE_SIZE // 2)],
])
async def test_merge_revalidates_total_and_indices(monkeypatch, chunks):
    session = AsyncMock()
    found, parts = MagicMock(), MagicMock()
    found.scalar_one_or_none.return_value = SimpleNamespace(
        uploader_user_id=1, status='UPLOADING', file_size=MAX_FILE_SIZE, chunk_count=2)
    parts.scalars.return_value.all.return_value = [
        SimpleNamespace(chunk_index=i, chunk_size=size) for i, size in chunks]
    session.execute.side_effect = [found, parts]
    from app.document import service
    compose = AsyncMock()
    monkeypatch.setattr(service.storage_service, 'compose', compose)
    with pytest.raises(BusinessException):
        await DocumentUploadService(session).complete_upload(1, 'USER', 'id')
    compose.assert_not_awaited()


@pytest_asyncio.fixture
async def upload_client(monkeypatch):
    app = FastAPI()
    app.include_router(routes.router, prefix='/api')
    app.add_exception_handler(BusinessException, business_exception_handler)
    app.add_exception_handler(ForbiddenException, forbidden_exception_handler)
    app.dependency_overrides[routes.get_current_user] = lambda: AuthenticatedUser(
        user_id=1, user_code='upload-test', display_name='Upload Test', system_role='USER')
    app.dependency_overrides[routes.get_db] = lambda: AsyncMock()
    monkeypatch.setattr(routes, 'require_group_access', AsyncMock())
    monkeypatch.setattr(routes, '_document_audit_context', AsyncMock(return_value={}))
    monkeypatch.setattr(routes, 'log_audit', AsyncMock())
    uploaded = AsyncMock(return_value={'document_id': 12, 'file_name': 'test.txt', 'is_duplicate': False})
    monkeypatch.setattr(DocumentUploadService, 'direct_upload', uploaded)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        yield client, uploaded


@pytest.mark.asyncio
async def test_http_boundary_and_failure_do_not_block_next_file(upload_client):
    client, uploaded = upload_client
    exact = await client.post('/api/documents/upload', data={'groupId': '2'},
                              files={'file': ('test.txt', b'x' * MAX_FILE_SIZE, 'text/plain')})
    assert exact.status_code == 200 and exact.json()['data']['documentId'] == 12
    assert len(uploaded.call_args.args[2]) == MAX_FILE_SIZE
    oversized = await client.post('/api/documents/upload', data={'groupId': '2'},
                                  files={'file': ('big.txt', b'x' * (MAX_FILE_SIZE + 1), 'text/plain')})
    assert oversized.status_code == 400 and '30 MB' in oversized.json()['message']
    small = await client.post('/api/documents/upload', data={'groupId': '2'},
                              files={'file': ('next.txt', b'next', 'text/plain')})
    assert small.status_code == 200 and uploaded.await_count == 2


@pytest.mark.asyncio
async def test_upload_keeps_group_access_checks(upload_client, monkeypatch):
    client, uploaded = upload_client
    monkeypatch.setattr(routes, 'require_group_access', AsyncMock(side_effect=ForbiddenException('无权访问该群组')))
    response = await client.post('/api/documents/upload', data={'groupId': '2'},
                                 files={'file': ('test.txt', b'test', 'text/plain')})
    assert response.status_code == 403
    uploaded.assert_not_awaited()
