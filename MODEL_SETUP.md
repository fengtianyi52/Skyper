# Skyper 模型配置 / Model setup

更新日期 / Updated: 2026-10-27

## 中文

在管理员侧栏打开「模型配置」。添加聊天或嵌入模型后：

1. 选择服务商。官方 API 预设自动填写地址和协议；自建服务或代理选择「自定义 API · OpenAI 兼容」。
2. 填写该服务商、区域或工作空间的 API Key。密钥仅填写到本地配置页面。
3. 从建议列表选择、直接输入精确模型 ID，或点击「获取最新模型」。显示名称不是模型 ID，大小写须与服务商一致。
4. 点击「测试连接」或直接「验证并保存」。聊天测试请求一段流式正文并携带工具定义；向量测试检查真实数值向量并检测维度。测试会产生少量 API 用量。
5. 勾选「保存后启用」。启用的管理员模型供普通用户使用；用户无需再次填密钥。

已有配置可以点击「编辑 / 测试」修改，不必删除重建。修改字段后，旧测试结果会失效。厂商不支持 Models API 时，手动输入准确模型 ID 即可；模型出现在列表中不代表支持 Agent 工具调用或当前账户有额度。

### 协议和地址

| 用途 | 协议 | 地址填写方式 |
| --- | --- | --- |
| 通用聊天或文本向量 | OpenAI 兼容 | Base URL，如 https://api.openai.com/v1 。也接受以 /chat/completions 或 /embeddings 结尾的完整地址，自动去掉重复后缀。 |
| Anthropic / 阿里云 Anthropic 兼容聊天 | Anthropic Messages | https://api.anthropic.com 或 https://dashscope.aliyuncs.com/apps/anthropic ，客户端调用 /v1/messages。 |
| 阿里云原生文本向量 | DashScope 原生文本向量 | /api/v1/services/embeddings/text-embedding/text-embedding，请求使用 input.texts。 |
| 阿里云原生多模态向量 | DashScope 原生多模态向量 | /api/v1/services/embeddings/multimodal-embedding/multimodal-embedding，当前只发送 input.contents[].text，不代表已实现图片检索。 |

阿里云新工作空间和国际区域的地址可能不同，请替换为控制台给出的 Base URL；不能把 /apps/anthropic 与 OpenAI 协议混用。Coding Plan 专用地址和按量付费 API 地址也不能随意混用。

自定义 Embedding 无需注册 YAML 模型卡片。保存时发送一条测试文本，检测实际向量维度；请求维度留空时采用模型默认值。激活时会核对现有向量数据：已有向量不匹配时拒绝切换，空库可自动调整列维度。超过 2000 维的向量使用精确检索，不创建 vector HNSW 索引。

### 本次问题与修复

- 聊天配置使用 Anthropic 地址，却记录为 OpenAI 协议，错误请求 /apps/anthropic/chat/completions，返回 404。现有 Qwen 配置已按原地址修正协议，并以真实流式请求验证。
- Agent 曾吞掉异常、保存空回复并发送成功事件。现在会显示明确错误，保留错误状态，刷新后也能看到。
- 旧连接测试将所有小于 500 的 HTTP 状态视为成功，包括 401、403 和 404。新版按真实结果验证；空向量、错误数量、维度不一致也会失败。
- 原先运行时依赖模型卡片推断协议，测试和运行路径不一致。现统一使用配置选择的协议和端点；自定义接口不再被转发到卡片中的其他厂商地址。

已验证 text-embedding-v4 的阿里云 OpenAI 兼容接口能返回 1024 维文本向量。第三方服务的 Qwen-VL-Embedding 是否提供同名模型、是否支持文本输入、需要哪种协议，仍须以该服务商资料和实际测试为准；不会把它冒充官方模型 ID。

### 模型目录来源

预设仅列已核对的示例；当前账户的模型列表可在线刷新。OpenAI、Anthropic、Gemini、xAI 当前模型 ID 未在本次环境中可靠取得的，保留在线获取或手填，不猜测“最新型号”。

- 阿里云协议：https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope
- 阿里云 Anthropic：https://help.aliyun.com/zh/model-studio/anthropic-api-messages
- 阿里云向量：https://help.aliyun.com/zh/model-studio/embedding
- DeepSeek：https://api-docs.deepseek.com/quick_start/pricing
- Kimi：https://platform.moonshot.cn/docs/guide/kimi-k2-quickstart
- 智谱：https://docs.bigmodel.cn/cn/guide/models/text
- OpenAI：https://platform.openai.com/docs/models
- Anthropic：https://platform.claude.com/docs/en/api/models/list
- Gemini：https://ai.google.dev/gemini-api/docs/openai
- xAI：https://docs.x.ai/developers/models

## English

Open **Model configuration** as an administrator. Choose an official provider or a custom OpenAI-compatible service, enter the API key, and select or type the exact model ID. **Fetch latest models** queries the provider's live Models API. If unsupported, enter an ID from that provider's console. Preset IDs are examples, not an exhaustive availability guarantee.

**Verify and save** checks a real streamed chat response with tool definitions, or real numeric embedding vectors. These small requests may incur provider charges. The first configuration defaults to **Activate after saving**. Administrator models are shared with regular users. Existing configurations can be edited in place.

The selected protocol is authoritative for both testing and inference. OpenAI, Anthropic Messages, DashScope native text embeddings, and DashScope native multimodal embeddings (text input only) have separate request formats. Complete OpenAI endpoint URLs are normalized to avoid duplicate path suffixes. Custom embeddings no longer need model cards: dimensions are detected and checked against existing data. Existing vectors are never deleted to force a model change.

HTTP errors, empty outputs, invalid vectors and early stream termination are no longer reported as success. Agent failures remain visible after reload. The existing Qwen chat configuration and official text-embedding-v4 endpoint were tested with real responses. Third-party model names, access rights and multimodal capabilities remain subject to that provider's API contract.
