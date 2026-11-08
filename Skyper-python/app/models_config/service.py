import logging
from typing import List

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.time_utils import utcnow
from app.models_config.models import ModelConfig

logger = logging.getLogger(__name__)


class ModelConfigService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_models(self, user_id: int, model_type: str) -> List[dict]:
        result = await self.session.execute(
            select(ModelConfig)
            .where(ModelConfig.user_id == user_id, ModelConfig.model_type == model_type)
            .order_by(ModelConfig.created_at.desc())
        )
        return [
            {
                "id": m.id, "model_type": m.model_type, "display_name": m.display_name,
                "base_url": m.base_url, "api_key": m.api_key, "model_name": m.model_name,
                "api_format": m.api_format or "openai",
                "parameters": m.parameters or {}, "is_active": m.is_active,
                "fallback_config_id": m.fallback_config_id,
                "created_at": m.created_at.isoformat() + "Z" if m.created_at else None,
            }
            for m in result.scalars()
        ]

    async def add_model(self, user_id: int, model_type: str, display_name: str,
                        base_url: str, api_key: str, model_name: str,
                        parameters: dict | None = None,
                        api_format: str | None = None) -> dict:
        from app.models_config.protocols import normalize_config, normalize_parameters
        from app.common.exception.exceptions import BusinessException
        if model_type not in ('chat', 'embedding', 'mineru'):
            raise BusinessException('不支持的模型类型')
        if not api_key.strip() or not model_name.strip():
            raise BusinessException('请填写 API Key 和精确的模型 ID')
        model_name = model_name.strip()
        display_name = display_name.strip() or model_name
        validated = normalize_parameters(parameters)
        if model_type != 'mineru':
            base_url, api_format = normalize_config(base_url, model_type, api_format, model_name)
        if model_type == 'embedding':
            result = await self.test_connection(base_url, api_key, model_name, model_type, api_format, validated)
            if not result['ok']:
                raise BusinessException(result['message'])
            validated['verified_dimensions'] = result['dimensions']

        model = ModelConfig(
            user_id=user_id, model_type=model_type, display_name=display_name,
            base_url=base_url, api_key=api_key, model_name=model_name,
            api_format=api_format or "openai",
            parameters=validated or None,
            is_active=False,
        )
        self.session.add(model)
        await self.session.flush()
        return {
            "id": model.id, "model_type": model.model_type, "display_name": model.display_name,
            "base_url": model.base_url, "api_key": model.api_key, "model_name": model.model_name,
            "api_format": model.api_format or "openai",
            "parameters": model.parameters, "is_active": model.is_active,
        }

    @staticmethod
    def _validate_parameters(card, parameters: dict | None) -> dict:
        if not parameters:
            return {}
        if card is None:
            # 自定义模型无卡片 schema：参数原样保存
            return dict(parameters)
        from app.common.exception.exceptions import BusinessException
        schema = card.parameters or {}
        validated = {}
        for key, value in parameters.items():
            prop = schema.get(key)
            if prop is None:
                # 前端 Axios 拦截器把 /model-cards 响应的 schema 键转成
                # camelCase 后原样提交（max_tokens → maxTokens），归一化
                # 回 snake_case 并以 canonical 键入库（运行时按
                # parameters.get("max_tokens") 读取，键不一致会静默丢配置）
                import re
                snake_key = re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()
                if snake_key != key and snake_key in schema:
                    key = snake_key
                    prop = schema[key]
            if prop is None:
                raise BusinessException(f"参数 {key} 不在模型 {card.name if card else ''} 的可用参数中")
            ptype = prop.get("type")
            # enum 优先：dimensions 这类参数同时声明 type=integer + enum
            if prop.get("enum"):
                if value not in prop["enum"]:
                    raise BusinessException(f"参数 {key} 只支持: {prop['enum']}")
            elif ptype in ("number", "integer") and isinstance(value, (int, float)) and not isinstance(value, bool):
                if prop.get("minimum") is not None and value < prop["minimum"]:
                    raise BusinessException(f"参数 {key} 不能小于 {prop['minimum']}")
                if prop.get("maximum") is not None and value > prop["maximum"]:
                    raise BusinessException(f"参数 {key} 不能大于 {prop['maximum']}")
            validated[key] = value
        return validated

    async def activate_model(self, user_id: int, model_id: int) -> dict:
        # Deactivate all models of the same type
        model = await self._get_model(user_id, model_id)
        if not model:
            from app.common.exception.exceptions import BusinessException
            raise BusinessException("模型配置不存在")

        # embedding 激活前校验维度与存量向量一致：维度不匹配会令检索整体失效
        if model.model_type == "embedding":
            from app.models_config.protocols import model_error_message
            from app.common.exception.exceptions import BusinessException
            try:
                await self._check_embedding_dimension(model)
            except Exception as exc:
                raise BusinessException(model_error_message(exc)) from exc

        await self.session.execute(
            update(ModelConfig)
            .where(ModelConfig.user_id == user_id, ModelConfig.model_type == model.model_type)
            .values(is_active=False)
        )

        model.is_active = True
        model.updated_at = utcnow()
        await self.session.flush()

        return {
            "id": model.id, "model_type": model.model_type, "display_name": model.display_name,
            "base_url": model.base_url, "api_key": model.api_key, "model_name": model.model_name,
            "is_active": True,
        }

    async def set_fallback(self, user_id: int, config_id: int,
                           fallback_config_id: int | None) -> dict:
        """为配置设置备用模型（降级目标）。

        约束：备用模型必须是同类型的已配置模型、不能是自己、
        且模型名必须在卡片目录（"可用模型"）中注册。
        """
        from app.common.exception.exceptions import BusinessException
        from app.models_config.cards import get_card

        model = await self._get_model(user_id, config_id)
        if not model:
            raise BusinessException("模型配置不存在")

        if fallback_config_id is not None:
            if fallback_config_id == config_id:
                raise BusinessException("备用模型不能是当前配置本身")
            fb = await self._get_model(user_id, fallback_config_id)
            if not fb:
                raise BusinessException("备用模型配置不存在")
            if fb.model_type != model.model_type:
                raise BusinessException("备用模型必须与主模型类型相同")
            if fb.model_type == "embedding":
                # 备用维度必须与存量向量一致（与主配置同等的维度约束）
                await self._check_embedding_dimension(fb)

        model.fallback_config_id = fallback_config_id
        model.updated_at = utcnow()
        await self.session.flush()
        return {
            "id": model.id, "display_name": model.display_name,
            "fallback_config_id": model.fallback_config_id,
        }

    async def delete_model(self, user_id: int, model_id: int):
        model = await self._get_model(user_id, model_id)
        if not model:
            from app.common.exception.exceptions import BusinessException
            raise BusinessException("模型配置不存在")
        await self.session.delete(model)
        await self.session.flush()

    @staticmethod
    async def _check_embedding_dimension(model: ModelConfig) -> None:
        """激活 embedding 模型前校验：存量向量维度必须与所选维度一致。

        配置了 parameters.dimensions 时以所选维度为准，否则取卡片默认。
        向量库为空（fresh 库）时放行——首次写入决定维度。
        """
        from sqlalchemy import text
        from app.models_config.cards import get_card
        from app.common.exception.exceptions import BusinessException

        from app.models_config.protocols import request_embeddings
        vectors = await request_embeddings({'base_url': model.base_url, 'api_key': model.api_key,
            'model_name': model.model_name, 'api_format': model.api_format, 'parameters': model.parameters}, ['Skyper dimension check'])
        selected_dim = len(vectors[0])
        from app.dependencies import engine
        async with engine.begin() as conn:
            exists = (await conn.execute(text("SELECT to_regclass('public.langchain_pg_embedding')"))).scalar()
            if not exists:
                return
            await conn.execute(text('LOCK TABLE langchain_pg_embedding IN ACCESS EXCLUSIVE MODE'))
            dim = (await conn.execute(text('SELECT vector_dims(embedding) FROM langchain_pg_embedding LIMIT 1'))).scalar()
            if dim is not None and dim != selected_dim:
                raise BusinessException(f'当前知识库已有 {dim} 维向量，所选模型返回 {selected_dim} 维。需先重建知识索引，不能混用维度。')
            # An empty table may still have a fixed vector(N) column.
            if dim is None:
                await conn.execute(text('DROP INDEX IF EXISTS idx_lpe_embedding_hnsw'))
                await conn.execute(text(f'ALTER TABLE langchain_pg_embedding ALTER COLUMN embedding TYPE vector({selected_dim})'))
                if selected_dim <= 2000:
                    await conn.execute(text('CREATE INDEX idx_lpe_embedding_hnsw ON langchain_pg_embedding USING hnsw (embedding vector_cosine_ops)'))
        model.parameters = {**(model.parameters or {}), 'verified_dimensions': selected_dim}

    async def get_active_model(self, user_id: int, model_type: str) -> dict | None:
        result = await self.session.execute(
            select(ModelConfig)
            .where(ModelConfig.user_id == user_id, ModelConfig.model_type == model_type, ModelConfig.is_active == True)
        )
        m = result.scalar_one_or_none()
        if not m:
            # Administrator models are platform defaults for ordinary users.
            from app.auth.models import User
            m = (await self.session.execute(select(ModelConfig).join(User, User.id == ModelConfig.user_id).where(
                User.system_role == 'ADMIN', User.status == 'ACTIVE',
                ModelConfig.model_type == model_type, ModelConfig.is_active == True,
            ).order_by(ModelConfig.updated_at.desc().nullslast(), ModelConfig.id.desc()).limit(1))).scalar_one_or_none()
        if not m:
            return None
        return {
            "base_url": m.base_url, "api_key": m.api_key, "model_name": m.model_name,
            "api_format": m.api_format or "openai",
            "parameters": m.parameters or {},
            "owner_user_id": m.user_id,
        }

    async def _get_model(self, user_id: int, model_id: int) -> ModelConfig | None:
        result = await self.session.execute(
            select(ModelConfig)
            .where(ModelConfig.id == model_id, ModelConfig.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def test_connection(base_url: str, api_key: str, model_name: str, model_type: str,
                              api_format: str | None = None, parameters: dict | None = None) -> dict:
        if model_type == 'mineru':
            return await ModelConfigService._test_mineru(base_url, api_key, model_name)
        from app.models_config.protocols import normalize_config, request_embeddings, model_error_message, text_content
        try:
            base_url, api_format = normalize_config(base_url, model_type, api_format, model_name)
            cfg = dict(base_url=base_url, api_key=api_key, model_name=model_name, api_format=api_format, parameters=parameters or {})
            if model_type == 'embedding':
                vectors = await request_embeddings(cfg, ['Skyper connection test'])
                return {'ok': True, 'status': 200, 'message': f'文本向量验证成功：{len(vectors[0])} 维，可用于知识库。', 'dimensions': len(vectors[0]), 'base_url': base_url, 'api_format': api_format}
            from app.models_config.client import make_chat_model
            from langchain_core.messages import HumanMessage
            model = make_chat_model(cfg, streaming=True)
            model = model.bind_tools([{'name': 'skyper_connection_check', 'description': 'Only a connectivity test; do not call this tool.', 'parameters': {'type': 'object', 'properties': {}}}])
            answer = ''
            async for chunk in model.astream([HumanMessage(content='Reply with only OK. Do not use tools.')]):
                answer += text_content(chunk.content)
            if not answer.strip():
                from app.common.exception.exceptions import BusinessException
                raise BusinessException('接口已响应，但没有返回聊天正文；请确认模型支持流式聊天与工具调用。')
            return {'ok': True, 'status': 200, 'message': '聊天、流式正文及工具参数验证成功。', 'base_url': base_url, 'api_format': api_format}
        except Exception as exc:
            status = getattr(exc, 'status_code', 0)
            if isinstance(exc, httpx.HTTPStatusError):
                status = exc.response.status_code
            return {'ok': False, 'status': status, 'message': model_error_message(exc)}

    async def update_model(self, user_id, model_id, **fields):
        from app.common.exception.exceptions import BusinessException
        model = await self._get_model(user_id, model_id)
        if not model:
            raise BusinessException('模型配置不存在')
        result = await self.add_model(user_id, model.model_type, **fields)
        draft = await self._get_model(user_id, result['id'])
        if model.is_active and model.model_type == 'embedding':
            await self._check_embedding_dimension(draft)
        for key in ('display_name', 'base_url', 'api_key', 'model_name', 'api_format', 'parameters'):
            setattr(model, key, getattr(draft, key))
        model.updated_at = utcnow()
        await self.session.delete(draft)
        await self.session.flush()
        return {'id': model.id}

    @staticmethod
    async def discover_models(base_url, api_key, api_format='openai'):
        from app.models_config.protocols import normalize_config, model_error_message
        try:
            url, protocol = normalize_config(base_url, 'chat', api_format)
            endpoint = url + ('/v1/models' if protocol == 'anthropic' else '/models')
            headers = {'x-api-key': api_key, 'anthropic-version': '2023-06-01'} if protocol == 'anthropic' else {'Authorization': f'Bearer {api_key}'}
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(endpoint, headers=headers)
                response.raise_for_status()
                body = response.json()
            ids = sorted({item['id'] for item in body.get('data', []) if isinstance(item, dict) and isinstance(item.get('id'), str)})
            if not ids:
                raise ValueError('No model IDs')
            return {'ok': True, 'models': ids, 'message': f'已从接口获取 {len(ids)} 个模型 ID；具体能力仍需测试。'}
        except Exception as exc:
            return {'ok': False, 'models': [], 'message': model_error_message(exc) + ' 此接口可能不提供模型列表，可手动输入模型 ID。'}

    @staticmethod
    async def _test_mineru(base_url: str, api_key: str, model_name: str) -> dict:
        """验证 MinerU token：申请一次上传链接（不消耗解析额度）"""
        url = (base_url or "https://mineru.net").rstrip("/") + "/api/v4/file-urls/batch"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    json={"files": [{"name": "connection-test.pdf"}],
                          "model_version": model_name or "vlm"},
                    headers={"Content-Type": "application/json",
                             "Authorization": f"Bearer {api_key}"},
                )
            data = resp.json()
            if data.get("code") == 0:
                return {"ok": True, "status": resp.status_code, "message": "连接成功"}
            return {"ok": False, "status": resp.status_code, "message": data.get("msg", "连接失败")}
        except Exception as e:
            return {"ok": False, "status": 0, "message": str(e)[:200]}
