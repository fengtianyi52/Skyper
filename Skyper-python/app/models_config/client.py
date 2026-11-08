"""The same chat client for tests, Agent, and knowledge answers."""
from app.models_config.protocols import normalize_config, normalize_parameters

def make_chat_model(cfg, streaming=False, temperature=None, max_tokens=None):
    url, protocol = normalize_config(cfg['base_url'], 'chat', cfg.get('api_format'), cfg['model_name'])
    params = normalize_parameters(cfg.get('parameters'))
    temp = temperature if temperature is not None else params.get('temperature')
    limit = max_tokens if max_tokens is not None else params.get('max_tokens')
    kwargs = dict(model=cfg['model_name'], api_key=cfg['api_key'], base_url=url, timeout=60, max_retries=0)
    if streaming:
        kwargs['streaming'] = True
    if protocol == 'anthropic':
        from langchain_anthropic import ChatAnthropic
        kwargs['max_tokens'] = limit or 4096
        if temp is not None:
            kwargs['temperature'] = temp
        return ChatAnthropic(**kwargs)
    from langchain_openai import ChatOpenAI
    if temp is not None:
        kwargs['temperature'] = temp
    if limit:
        kwargs['max_tokens'] = limit
    if isinstance(params.get('extra_body'), dict):
        kwargs['extra_body'] = params['extra_body']
    if streaming:
        kwargs['stream_usage'] = True
    return ChatOpenAI(**kwargs)
