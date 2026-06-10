# 面接コーチ — Agent 须知

日本大学院面试练习网页（纯前端，本地 `start.command` 启动于 http://localhost:8765）。

## 用户丢来 Word 文档（.docx）时

这是**导入新面试问题**的请求。按 `IMPORT.md` 的 5 步流程执行：
读取 docx（`textutil -convert txt -stdout`）→ 整理成 q/a 卡片 → 写入 `data/questions.js` → node 校验 → `generate_audio.py --engine openai` 生成语音。
无需用户再解释格式，细节、id 规则、坑都在 `IMPORT.md`。

## 关键文件

- `data/questions.js` — 题库（`window.INTERVIEW_DATA = {...}`，内容必须是合法 JSON）
- `data/guide.js` — 「回答思路」页内容
- `generate_audio.py` — OpenAI TTS 批量生成（key 读 env 或本目录 `.env`，增量、不覆盖 human 录音）
- `audio/` — 预生成 mp3 + manifest.json；文件名 = 问题 id
- `index.html` — 整个网页（样式 + 逻辑单文件）

## 硬规则

1. **不要改已有问题的 id**——音频按 id 命名，改了就断链。
2. 用户的日文回答**原文照搬不改写**，除非明确要求润色。
3. API key 只能放环境变量或未跟踪的 `.env`，绝不进 Git。
4. UI 改动必须遵守「复古学术试卷」设计规范（见 README 设计语言一节）：
   零圆角（`border-radius: 0`）、零渐变、零模糊；2px 墨色边框 + 硬偏移阴影（`5px 5px 0`）；
   色板只用 `:root` 里的变量（paper/panel/surface/ink/ink-soft/blue/red/gold）。
5. 改完 `questions.js` 必须跑 `IMPORT.md` 第 4 步的 node 校验。
6. 完成后在 `CHANGELOG.md` 顶部加记录；用户要求时才 commit/push。
