# 待办 / Roadmap

## 1. 更逼真的语音（高优先）

**现状**：用微软 `edge-tts` 神经语音（男声 Keita）预生成 mp3，免费、自然度已不错，但仍是固定语调。

**目标**：可选接入更高自然度的 TTS API，按问题/答案重要程度选择性升级。

**候选引擎**
| 引擎 | 自然度 | 成本 | 备注 |
|---|---|---|---|
| OpenAI TTS (`gpt-4o-mini-tts` / `tts-1-hd`) | 高 | 低（文本量小，几乎可忽略） | 可用 `instructions` 控制语气、语速、正式度；声音 onyx/alloy 等 |
| ElevenLabs | 很高 | 中 | 多语言音色克隆强，日语自然 |
| Google Neural2 / Azure Neural | 高 | 低 | 需账号配置，声调标准 |

**实现思路（不改网页，只扩 `generate_audio.py`）**
1. 加 `--engine {edge,openai}` 参数，默认 `edge`（保持现状）。
2. `engine=openai` 时：
   - 从环境变量读 `OPENAI_API_KEY`（绝不写进代码 / 不进 Git）。
   - 调用 TTS 接口，输入 = 问题或答案文本，输出 mp3，落地路径不变（`audio/<id>.mp3` / `audio/<id>-a.mp3`）。
   - manifest 里 `source` 记为 `openai`，`hash` 规则不变（文本没改就跳过，省 API 调用）。
3. 网页侧零改动：它只认 `audio/*.mp3` 是否存在。

**注意**
- 先小批量（2~3 句）试听对比 edge-tts vs OpenAI，确认日语自然度确有提升再全量切换。
- API key 用 `export OPENAI_API_KEY=...` 或本地未跟踪的 `.env`（已被 `.gitignore` 覆盖思路，必要时补一行 `.env`）。

## 2. 其他可选改进
- [ ] 模拟面试录音的本地持久化（IndexedDB），关页面不丢失。
- [ ] 跟读模式增加「假名注音」开关，辅助生词发音。
- [ ] 回答思路页支持搜索 / 标记「已背熟」。
