"""Shared protocol handling for configuration tests and live inference."""
import math
import re
from urllib.parse import urlsplit, urlunsplit

import httpx
from app.common.exception.exceptions import BusinessException


def normalize_parameters(parameters):
    return {re.sub(r'(?<!^)(?=[A-Z])', '_', k).lower(): v
            for k, v in (parameters or {}).items() if v is not None}


def normalize_config(base_url, model_type, api_format=None, model_name=''):
    url = (base_url or '').strip().rstrip('/')
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise BusinessException('API 地址须为完整 http(s) 地址，不能包含密钥、查询参数或账号密码。')
    path = parts.path.rstrip('/')
    if not api_format:
        if '/anthropic' in path or parts.hostname == 'api.anthropic.com':
            api_format = 'anthropic'
        elif '/services/embeddings/multimodal-embedding' in path:
            api_format = 'dashscope_mm'
        elif '/services/embeddings/text-embedding' in path:
            api_format = 'dashscope'
        else:
            api_format = 'openai'
    allowed = ('openai', 'anthropic') if model_type == 'chat' else ('openai', 'dashscope', 'dashscope_mm')
    if model_type not in ('chat', 'embedding') or api_format not in allowed:
        raise BusinessException('模型类型与协议不匹配：聊天支持 OpenAI / Anthropic；Embedding 支持 OpenAI / DashScope 原生文本或多模态协议。')
    if api_format == 'openai':
        if '/anthropic' in path or '/services/embeddings/' in path or parts.hostname == 'api.anthropic.com':
            raise BusinessException('接口地址与 OpenAI 协议不匹配。请重新选择厂商预设；阿里云 OpenAI 地址为 compatible-mode/v1，Anthropic 地址不能混用。')
        for suffix in ('/chat/completions', '/embeddings', '/models'):
            if path.endswith(suffix):
                path = path[:-len(suffix)]
                break
        if path.endswith('/responses'):
            raise BusinessException('当前 Agent 使用 Chat Completions 协议，请填写支持 /chat/completions 的 Base URL。')
    elif api_format == 'anthropic':
        if '/compatible-mode' in path or path.endswith('/chat/completions'):
            raise BusinessException('该地址是 OpenAI 兼容接口，请将协议改为 OpenAI。')
        if path.endswith('/messages'):
            path = path[:-len('/messages')]
        if path.endswith('/v1'):
            path = path[:-3]
    else:
        service = 'multimodal-embedding' if api_format == 'dashscope_mm' else 'text-embedding'
        expected = f'/api/v1/services/embeddings/{service}/{service}'
        if '/compatible-mode' in path:
            raise BusinessException('compatible-mode 地址应选择 OpenAI 协议；DashScope 原生协议请使用厂商预设地址。')
        if not path or path in ('/api', '/api/v1'):
            path = expected
        elif not path.endswith(f'/services/embeddings/{service}/{service}'):
            raise BusinessException('DashScope 原生 Embedding 地址与所选协议不匹配，请使用厂商预设或完整原生端点。')
    return urlunsplit((parts.scheme, parts.netloc, path, '', '')), api_format


def text_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ''.join(block.get('text', '') for block in content
                       if isinstance(block, dict) and block.get('type') in ('text', 'text_delta'))
    return ''


def model_error_message(exc):
    if isinstance(exc, BusinessException):
        return str(exc)
    status = getattr(exc, 'status_code', None)
    if status is None and isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
    messages = {
        400: '请求参数或模型协议不兼容，请检查模型 ID、工具调用支持和高级参数。',
        401: 'API Key 无效或已过期，请核对密钥与厂商及区域是否匹配。',
        402: '模型账户余额不足，请检查厂商计费账户。',
        403: '当前 API Key 无权使用此模型，请检查模型权限、区域或套餐。',
        404: '模型或接口不存在，请检查模型 ID、Base URL 和协议；不能混用 OpenAI 与 Anthropic 地址。',
        429: '模型服务限流或额度不足，请检查余额、配额后重试。',
    }
    if status:
        return f'模型调用失败（HTTP {status}）：' + messages.get(status, '模型服务暂不可用，请稍后重试。')
    if isinstance(exc, (httpx.TimeoutException, TimeoutError)) or 'timeout' in type(exc).__name__.lower():
        return '模型请求超时，请检查网络、服务地址或稍后重试。'
    if isinstance(exc, httpx.TransportError) or 'connection' in type(exc).__name__.lower():
        return '无法连接模型服务，请检查网络、代理和 API 地址。'
    return f'模型调用失败（{type(exc).__name__}），请在模型配置中测试连接并查看后台日志。'


async def request_embeddings(cfg, texts):
    url, protocol = normalize_config(cfg['base_url'], 'embedding', cfg.get('api_format'), cfg['model_name'])
    params = normalize_parameters(cfg.get('parameters'))
    dimensions = params.get('dimensions')
    if dimensions is not None and (isinstance(dimensions, bool) or not isinstance(dimensions, int) or not 1 <= dimensions <= 16000):
        raise BusinessException('向量维度必须为 1 到 16000 的整数。')
    if protocol == 'openai':
        url += '/embeddings'
        payload = {'model': cfg['model_name'], 'input': texts, 'encoding_format': 'float'}
        if dimensions:
            payload['dimensions'] = dimensions
    else:
        inputs = {'texts': texts} if protocol == 'dashscope' else {'contents': [{'text': text} for text in texts]}
        payload = {'model': cfg['model_name'], 'input': inputs}
        if dimensions:
            payload['parameters'] = {'dimension': dimensions}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, json=payload, headers={'Authorization': f"Bearer {cfg['api_key']}"})
        response.raise_for_status()
        body = response.json()
    if not isinstance(body, dict) or body.get('error') or body.get('code') not in (None, 0, '0', ''):
        raise BusinessException('向量接口返回业务错误，请检查模型、密钥和协议。')
    items = body.get('data') if protocol == 'openai' else body.get('output', {}).get('embeddings')
    index_key = 'index' if protocol == 'openai' else ('text_index' if protocol == 'dashscope' else 'index')
    if not isinstance(items, list) or len(items) != len(texts):
        raise BusinessException('向量接口未返回正确数量的 embedding；请确认接口支持文本向量及所选协议。')
    if any(not isinstance(item, dict) for item in items):
        raise BusinessException('向量接口响应格式无效。')
    if all(index_key in item for item in items):
        if sorted(item[index_key] for item in items) != list(range(len(texts))):
            raise BusinessException('向量接口返回的索引重复或不完整。')
        items.sort(key=lambda item: item[index_key])
    elif len(items) > 1:
        raise BusinessException('批量向量缺少索引，无法保证与原文正确对应。')
    vectors = [item.get('embedding') for item in items]
    for vector in vectors:
        if not isinstance(vector, list) or not vector or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in vector):
            raise BusinessException('向量接口必须返回非空、有限数值数组，不能返回 base64 或空结果。')
    if len({len(v) for v in vectors}) != 1:
        raise BusinessException('向量接口返回的维度不一致。')
    expected = dimensions or params.get('verified_dimensions')
    if expected and len(vectors[0]) != expected:
        raise BusinessException(f'实际向量维度 {len(vectors[0])} 与配置维度 {expected} 不一致。')
    return vectors
