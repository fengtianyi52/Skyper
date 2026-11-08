"""Upload regression tests; no cloud calls and no production database mutations."""
import io
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from docx import Document as WordDocument
from sqlalchemy.exc import IntegrityError

from app.document.models import Document
from app.document.service import DocumentQueryService, enqueue_document_retry
from app.ingestion.errors import IngestionError, public_reason
from app.ingestion.job_service import IngestionJobWorker
from app.ingestion.parsers.factory import DocumentParserFactory
from app.ingestion.parsers.local_parser import DocxParser, PdfParser
from app.ingestion.parsers.mineru_parser import MineruParser


def docx_bytes():
    word = WordDocument()
    word.add_paragraph('协作小组知识库：Word 上传回归测试。')
    word.add_table(rows=1, cols=2).rows[0].cells[0].text = '表格内容'
    word.add_paragraph('最后一个段落')
    buffer = io.BytesIO()
    word.save(buffer)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_docx_paragraphs_tables_and_order_without_cloud(monkeypatch):
    cloud = AsyncMock(side_effect=AssertionError('Local DOCX must not call cloud'))
    monkeypatch.setattr(MineruParser, 'parse', cloud)
    docs = await DocumentParserFactory.get('.DOCX').parse(docx_bytes(), '测试.docx')
    text = docs[0].page_content
    assert '协作小组知识库' in text and '表格内容' in text
    assert text.index('协作小组') < text.index('表格内容') < text.index('最后一个段落')
    assert chr(10) in text
    assert docs[0].metadata['parser'] == 'local-docx'
    cloud.assert_not_awaited()


@pytest.mark.asyncio
async def test_corrupt_docx_has_actionable_message():
    with pytest.raises(IngestionError, match='另存为 .docx'):
        await DocxParser().parse(b'not a zip file', 'bad.docx')


@pytest.mark.asyncio
async def test_drawing_text_is_extracted_without_cloud(monkeypatch):
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    word = WordDocument()
    paragraph = word.add_paragraph()
    paragraph._p.append(parse_xml(
        '<w:r ' + nsdecls('w', 'a') + '><w:drawing><a:p><a:r>'
        '<a:t>文本框中的有效文字</a:t></a:r></a:p></w:drawing></w:r>'
    ))
    assert paragraph.text == ''
    buffer = io.BytesIO()
    word.save(buffer)
    cloud = AsyncMock(side_effect=AssertionError('Drawing text must be local'))
    monkeypatch.setattr(MineruParser, 'parse', cloud)
    result = await DocxParser().parse(buffer.getvalue(), 'drawing.docx')
    assert '文本框中的有效文字' in result[0].page_content
    cloud.assert_not_awaited()


@pytest.mark.asyncio
async def test_pdf_text_pages_use_local_parser(monkeypatch):
    import pdfplumber
    pdf = MagicMock()
    pdf.__enter__.return_value.pages = [SimpleNamespace(extract_text=lambda: 'PDF text', images=[])]
    monkeypatch.setattr(pdfplumber, 'open', lambda *_: pdf)
    cloud = AsyncMock(side_effect=AssertionError('Text PDF must not call cloud'))
    monkeypatch.setattr(MineruParser, 'parse', cloud)
    docs = await PdfParser().parse(b'fake-pdf', 'text.pdf')
    assert docs[0].page_content == 'PDF text' and docs[0].metadata['page'] == 1
    cloud.assert_not_awaited()


@pytest.mark.asyncio
async def test_mixed_pdf_does_not_silently_drop_scanned_pages(monkeypatch):
    import pdfplumber
    pdf = MagicMock()
    pdf.__enter__.return_value.pages = [
        SimpleNamespace(extract_text=lambda: 'text page', images=[]),
        SimpleNamespace(extract_text=lambda: '', images=[{}]),
    ]
    monkeypatch.setattr(pdfplumber, 'open', lambda *_: pdf)
    cloud = AsyncMock(side_effect=IngestionError('请配置 MinerU Token'))
    monkeypatch.setattr(MineruParser, 'parse', cloud)
    with pytest.raises(IngestionError, match='MinerU'):
        await PdfParser().parse(b'fake-pdf', 'mixed.pdf')
    cloud.assert_awaited_once()


@pytest.mark.asyncio
async def test_placeholder_mineru_key_rejected_before_network(monkeypatch):
    from app.models_config import resolver
    monkeypatch.setattr(resolver, 'get_mineru_config', AsyncMock(return_value={'api_key': 'sk-your-mineru-token'}))
    submit = AsyncMock(side_effect=AssertionError('Must fail locally'))
    monkeypatch.setattr(MineruParser, '_submit_batch', submit)
    with pytest.raises(IngestionError, match='云端解析未配置'):
        await MineruParser().parse(b'image', 'scan.png')
    submit.assert_not_awaited()


def test_expired_mineru_key_is_not_retried():
    with pytest.raises(IngestionError, match='已过期') as caught:
        MineruParser._check_response(401, {'msg': 'user token expired'})
    assert not caught.value.retryable


@pytest.mark.asyncio
async def test_missing_embedding_preserves_parsed_state(monkeypatch):
    from app.engine import vector_store
    monkeypatch.setattr(vector_store, '_resolve_embedding', AsyncMock(return_value=({'api_key': 'sk-your-dashscope-key'}, None)))
    with pytest.raises(IngestionError, match='文件已上传并解析') as caught:
        await vector_store._embed_texts(['hello'])
    assert caught.value.waiting and not caught.value.retryable


def test_public_failure_redacts_credentials():
    text = public_reason('Bearer abc123 sk-real-secret token=private https://example.com/file?signature=private')
    assert 'abc123' not in text and 'sk-real-secret' not in text and 'private' not in text


def test_list_returns_group_and_failure_reason():
    doc = Document(id=10, group_id=20, uploader_user_id=30, file_name='a.docx', status='FAILED', failure_reason='解析失败：请重试', created_at=datetime(2026, 10, 26))
    item = DocumentQueryService._to_list_item(doc)
    assert item['groupId'] == 20
    assert item['failureReason'] == doc.failure_reason
    assert item['createdAt'].endswith('Z')


@pytest.mark.asyncio
async def test_preview_uses_extracted_text_not_binary(monkeypatch):
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ['段落一', '表格二']
    session.execute.return_value = result
    service = DocumentQueryService(session)
    monkeypatch.setattr(service, '_get_doc', AsyncMock(return_value=SimpleNamespace(id=1, group_id=2, file_name='word.docx', status='PARSED', preview_text='')))
    preview = await service.get_preview(1)
    assert preview['previewText'] == '段落一\n\n表格二'


@pytest.mark.asyncio
async def test_retry_clears_reason_and_rejects_active_job():
    session = AsyncMock()
    session.add = MagicMock()
    doc = SimpleNamespace(status='PARSED', failure_reason='配置缺失', group_id=1)
    found, active = MagicMock(), MagicMock()
    found.scalar_one_or_none.return_value = doc
    active.scalar_one_or_none.return_value = SimpleNamespace(status='PENDING')
    session.execute.side_effect = [found, active]
    with pytest.raises(Exception, match='已有处理任务'):
        await enqueue_document_retry(session, 1)
    session.add.assert_not_called()
    active.scalar_one_or_none.return_value = None
    session.execute.side_effect = [found, active]
    await enqueue_document_retry(session, 1)
    assert doc.status == 'UPLOADED' and doc.failure_reason is None
    session.add.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize('failure,status', [
    (IngestionError('请配置向量模型', waiting=True), 'PARSED'),
    (IngestionError('文件损坏'), 'FAILED'),
    (IngestionError('服务超时', retryable=True), 'PENDING'),
    (IntegrityError('sensitive SQL', {'secret': 'never expose'}, Exception('database error')), 'PENDING'),
])
async def test_worker_rolls_back_then_persists_reason(monkeypatch, failure, status):
    from app.ingestion import job_service
    session = AsyncMock()
    processor = SimpleNamespace(process=AsyncMock(side_effect=failure))
    monkeypatch.setattr(job_service, 'create_ingestion_processor', lambda _: processor)
    job = SimpleNamespace(id=1, document_id=2, group_id=3, retry_count=0, max_retries=3)
    await IngestionJobWorker()._execute_job(session, job)
    session.rollback.assert_awaited_once()
    updates = [call.args[0].compile().params for call in session.execute.await_args_list]
    assert updates[-1]['status'] == status
    assert updates[-1]['failure_reason']
    assert 'sensitive' not in updates[-1]['failure_reason']
    assert 'secret' not in updates[-1]['failure_reason']
