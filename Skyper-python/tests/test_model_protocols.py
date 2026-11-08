"""Offline regressions for provider routing and failed Agent turns."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from langchain_core.messages import AIMessageChunk
from app.common.exception.exceptions import BusinessException
from app.models_config import protocols
from app.models_config.service import ModelConfigService


@pytest.mark.parametrize('kind,url,expected', [
    ('chat', 'https://example.test/v1/chat/completions', 'https://example.test/v1'),
    ('embedding', 'https://example.test/v1/embeddings/', 'https://example.test/v1'),
    ('embedding', 'https://example.test/compatible-mode/v1', 'https://example.test/compatible-mode/v1'),
])
def test_full_endpoint_normalization(kind, url, expected):
    assert protocols.normalize_config(url, kind, 'openai') == (expected, 'openai')


def test_protocol_mismatch_is_rejected_before_network():
    with pytest.raises(BusinessException, match='不匹配'):
        protocols.normalize_config('https://dashscope.aliyuncs.com/apps/anthropic', 'chat', 'openai')
    with pytest.raises(BusinessException, match='不匹配'):
        protocols.normalize_config('https://api.anthropic.com', 'embedding', 'anthropic')
    assert protocols.normalize_config('https://api.anthropic.com/v1/messages', 'chat', 'anthropic') == ('https://api.anthropic.com', 'anthropic')


def mock_http(monkeypatch, status, body):
    calls = []
    async def post(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(status, json=body, request=httpx.Request('POST', url))
    client = AsyncMock()
    client.post.side_effect = post
    context = AsyncMock()
    context.__aenter__.return_value = client
    monkeypatch.setattr(protocols.httpx, 'AsyncClient', lambda **kw: context)
    return calls


@pytest.mark.asyncio
@pytest.mark.parametrize('status', [400, 401, 403, 404, 429, 500])
async def test_http_errors_are_never_connection_success(monkeypatch, status):
    mock_http(monkeypatch, status, {'error': {'message': 'private provider detail'}})
    result = await ModelConfigService.test_connection('https://example.test/v1/embeddings', 'secret', 'custom-vector', 'embedding', 'openai')
    assert result['ok'] is False and result['status'] == status
    assert str(status) in result['message']
    assert 'secret' not in result['message'] and 'private provider detail' not in result['message']


@pytest.mark.asyncio
async def test_custom_embedding_detects_dimension_and_orders_indices(monkeypatch):
    calls = mock_http(monkeypatch, 200, {'data': [{'index': 1, 'embedding': [3., 4.]}, {'index': 0, 'embedding': [1., 2.]}]})
    vectors = await protocols.request_embeddings({'base_url': 'https://example.test/v1/embeddings', 'api_key': 'secret', 'model_name': 'new-custom', 'api_format': 'openai'}, ['first', 'second'])
    assert vectors == [[1., 2.], [3., 4.]]
    assert calls[0][0] == 'https://example.test/v1/embeddings'
    assert calls[0][1]['json']['input'] == ['first', 'second']
    assert 'dimensions' not in calls[0][1]['json']


@pytest.mark.asyncio
@pytest.mark.parametrize('protocol,input_key,index_key', [('dashscope', 'texts', 'text_index'), ('dashscope_mm', 'contents', 'index')])
async def test_native_embedding_uses_configured_endpoint(monkeypatch, protocol, input_key, index_key):
    calls = mock_http(monkeypatch, 200, {'output': {'embeddings': [{index_key: 0, 'embedding': [1., 2.]}]}})
    result = await ModelConfigService.test_connection('https://workspace.example/api/v1', 'secret', 'custom-native', 'embedding', protocol)
    assert result['ok'] and result['dimensions'] == 2
    assert calls[0][0].startswith('https://workspace.example/api/v1/services/embeddings/')
    assert input_key in calls[0][1]['json']['input']


@pytest.mark.asyncio
@pytest.mark.parametrize('body', [{'data': []}, {'data': [{'embedding': []}]}, {'data': [{'embedding': 'encoded'}]}, {'error': {'message': 'not allowed'}}])
async def test_200_without_valid_vectors_fails(monkeypatch, body):
    mock_http(monkeypatch, 200, body)
    result = await ModelConfigService.test_connection('https://example.test/v1', 'secret', 'custom-vector', 'embedding', 'openai')
    assert not result['ok']


@pytest.mark.asyncio
async def test_selected_dimension_validated(monkeypatch):
    mock_http(monkeypatch, 200, {'data': [{'index': 0, 'embedding': [1., 2.]}]})
    result = await ModelConfigService.test_connection('https://example.test/v1', 'secret', 'custom-vector', 'embedding', 'openai', {'dimensions': 3})
    assert not result['ok'] and '维度' in result['message']


@pytest.mark.asyncio
async def test_custom_embedding_save_no_card_required(monkeypatch):
    session = AsyncMock()
    session.add = MagicMock()
    monkeypatch.setattr(ModelConfigService, 'test_connection', AsyncMock(return_value={'ok': True, 'dimensions': 768}))
    result = await ModelConfigService(session).add_model(1, 'embedding', 'My vector', 'https://example.test/v1/embeddings', 'secret', 'new-vector-not-in-card', api_format='openai')
    assert result['parameters']['verified_dimensions'] == 768
    assert result['base_url'] == 'https://example.test/v1'
    assert result['api_format'] == 'openai'


@pytest.mark.asyncio
async def test_agent_keeps_repeated_deltas_and_anthropic_blocks(monkeypatch):
    from app.assistant.agent import facade
    async def events(*args, **kwargs):
        for content in ['哈', '哈', [{'type': 'text', 'text': '你好'}]]:
            yield {'event': 'on_chat_model_stream', 'data': {'chunk': AIMessageChunk(content=content)}}
    agent = SimpleNamespace(astream_events=events, aget_state=AsyncMock(return_value=SimpleNamespace(tasks=[])))
    monkeypatch.setattr(facade.factory, '_get_chat_model', AsyncMock(return_value=object()))
    monkeypatch.setattr(facade.factory, 'create_agent', lambda *args: (agent, []))
    output = [e async for e in facade.chat_stream('system', 'hello', 'CHAT', None, 'test')]
    assert ''.join(e['data'] for e in output if e['event'] == 'delta') == '哈哈你好'


@pytest.mark.asyncio
async def test_agent_error_reaches_service(monkeypatch):
    from app.assistant.agent import facade
    async def events(*args, **kwargs):
        yield {'event': 'on_chat_model_stream', 'data': {'chunk': AIMessageChunk(content='partial')}}
        raise httpx.HTTPStatusError('private', request=httpx.Request('POST', 'https://example.test'), response=httpx.Response(404))
    agent = SimpleNamespace(astream_events=events)
    monkeypatch.setattr(facade.factory, '_get_chat_model', AsyncMock(return_value=object()))
    monkeypatch.setattr(facade.factory, 'create_agent', lambda *args: (agent, []))
    with pytest.raises(httpx.HTTPStatusError):
        _ = [e async for e in facade.chat_stream('system', 'hello', 'CHAT', None, 'test')]


@pytest.mark.asyncio
@pytest.mark.parametrize('empty', [False, True])
async def test_service_emits_and_persists_failed_turn(monkeypatch, empty):
    from app.assistant.service import AssistantService
    from app.assistant.agent import facade
    from app.assistant.models import AssistantMessage
    session = AsyncMock()
    session.add = MagicMock()
    service = AssistantService(session)
    service.memory = SimpleNamespace(maintain_before_response=AsyncMock(), load_context=AsyncMock(return_value={}))
    monkeypatch.setattr(service, '_ensure_session', AsyncMock(return_value=10))
    monkeypatch.setattr(service, '_build_instruction', lambda *args: 'system')
    async def broken(*args, **kwargs):
        if empty:
            yield {'event': 'done', 'data': {'reason': 'completed'}}
        else:
            raise httpx.HTTPStatusError('private', request=httpx.Request('POST', 'https://example.test'), response=httpx.Response(404))
    monkeypatch.setattr(facade, 'chat_stream', broken)
    events = [event async for event in service.chat_stream(1, 10, 'hi')]
    assert [event['event'] for event in events] == ['error', 'done']
    assert events[-1]['data']['reason'] == 'failed'
    saved = [c.args[0] for c in session.add.call_args_list if isinstance(c.args[0], AssistantMessage) and c.args[0].role == 'ASSISTANT'][0]
    assert saved.structured_payload['failed']
    assert saved.structured_payload['failure_message']
