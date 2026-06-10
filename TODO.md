# 待办 / Roadmap

## 1. 更逼真的语音（已完成）

**现状**：`generate_audio.py` 已支持 `--engine openai`，当前全量音频使用 `gpt-4o-mini-tts` + `cedar` 生成 mp3；微软 `edge-tts` 仍保留为免费备用。

常用命令：

```bash
.venv/bin/python generate_audio.py --engine openai --voice cedar --speed 1.0 --natural-pauses
```

## 2. 快退按钮 + Word 一键导入（已完成）

- [x] 跟读 / 面试页「快退 3 秒」按钮（mp3 有效；浏览器 TTS 不支持定位会提示）。
- [x] Word 导入工作流文档化：`IMPORT.md`（agent 操作手册）+ 项目级 `CLAUDE.md`（agent 自动加载）。用法：把 .docx 丢给 agent 说「导入到 XX」。

## 3. 其他可选改进
- [ ] 模拟面试录音的本地持久化（IndexedDB），关页面不丢失。
- [ ] 跟读模式增加「假名注音」开关，辅助生词发音。
- [ ] 回答思路页支持搜索 / 标记「已背熟」。
