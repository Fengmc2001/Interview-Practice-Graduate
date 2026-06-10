# 面接コーチ — 大学院面试练习 App

日本大学院（修士）面试的**影子跟读 + 模拟面试**练习网页。纯前端、零后端、本地运行。

- **跟读练习**：按学校分标签页，逐题播放标准日语发音（可调语速、循环遍数、跟读间隔），下方直接显示你写好的回答。
- **模拟面试**：卡片式随机抽题，自动朗读问题 → 录音 → 当场回放 / 下载，可开「实时识别字幕」（Chrome）。
- **回答思路**：独立标签页，30 个高频问题的题意 / 日英问法 / 面试官意图 / 回答结构与注意点。
- 高音质日语语音由微软 `edge-tts` 神经语音（男声 Keita）**预生成为 mp3**；没有 mp3 的问题自动降级用浏览器 TTS。

---

## 一、启动

双击 `start.command`（开启本地服务器并自动打开浏览器 http://localhost:8765）。推荐 **Chrome**。

> 不要直接双击 `index.html`：`file://` 方式下高音质音频和录音都不可用。

---

## 二、目录结构

```
面试练习/
├── index.html            # 网页本体（视觉 + 逻辑，一般不用动）
├── data/
│   ├── questions.js      # ★ 各学校的问题与你的回答（最常改的文件）
│   └── guide.js          # 「回答思路」标签页的内容
├── audio/                # 预生成的 mp3 + manifest.json（记录来源）
├── uploads/              # 你上传的原始录音（不进 Git）
├── generate_audio.py     # 批量生成日语语音的脚本
├── start.command         # 双击启动
└── .venv/                # Python 环境（不进 Git）
```

---

## 三、修改 / 新增问题（最常用）

编辑 `data/questions.js`。每所学校是 `schools` 数组里的一项：

```js
{
  "id": "todai-biostat",        // 学校 id（英文、唯一、别改已有的）
  "name": "東大 生物統計情報",   // 标签页显示名
  "questions": [
    {
      "id": "tb-01",            // 问题 id（英文、全局唯一，音频按它命名）
      "q": "1分程度で自己紹介をお願いします。",   // 日文问题（会被朗读）
      "a": "はい、私は…"          // 你的日文回答（跟读模式直接显示）
    }
  ]
}
```

- **新增一所学校** = 在 `schools` 数组里加一个 `{ id, name, questions: [...] }`。
- **新增一题** = 在该学校 `questions` 里加一项，`id` 取个没用过的（如 `tb-19`）。
- 未填的回答写 `（ここに…）` 占位即可，脚本不会为占位答案生成语音。
- 必须是**合法 JSON**：注意逗号、引号配对；多行文本用 `\n` 换行。改完**刷新网页**即生效（语音需另跑脚本，见下）。

---

## 四、重新生成高音质语音

问题或答案文本改动后，在 `面试练习/` 目录下运行：

```bash
.venv/bin/python generate_audio.py
```

- 默认男声 `ja-JP-KeitaNeural`、语速适中。可选参数：
  - `--rate -10%`（放慢 10%）/ `--rate +10%`（加快）
  - `--voice ja-JP-NanamiNeural`（换女声）
- 脚本**只生成新增或文本改过的**音频，已生成且没改的会跳过；标记为真人录音（`human`）的永远不覆盖。
- 需要联网（调用微软语音服务）。

---

## 五、用 Word 发给我改稿时（给 Claude 的处理流程）

> 这一节是写给 AI 助手看的工作流，方便你（用户）每次只需把 Word 丢过来说一句「加进 XX 学校」。

当用户提供一份 `.docx`（新学校问题稿，或对已有问题的修改）时，按以下步骤处理：

1. **读取 Word**：`textutil -convert txt -stdout "路径.docx"`（macOS 自带，无需安装）。
2. **整理为卡片格式**：
   - 中文小标题转成面试现场会问的**自然日语问法**作为 `q`；用户已写好的日文回答原文放入 `a`，**保持原文不改写**（包括口语化措辞），除非用户明确要求润色。
   - 一段标题下若有多个问题（用分隔线隔开多个答案），拆成多张卡片。
   - 内容重复的问题合并为一张，避免冗余。
3. **写入 `data/questions.js`**：新学校就新增一个 school 对象；改稿就定位到对应 `id` 修改 `q`/`a`。`id` 用学校缩写 + 序号（如 `tb-01`）。
4. **校验 JSON**：用 `node -e` 加载 `questions.js` 确认无语法错误、统计题数。
5. **生成语音**：跑 `generate_audio.py`，只会补生成新增/改动的音频。
6. **（如已建仓）提交**：`git add -A && git commit -m "..."`，按需 `git push`。

---

## 六、上传真人录音（替换 TTS 为真人发音）

把原始录音（任意格式，可以是一整段连续录音）放进 `uploads/`，告诉我哪段对应哪题。
我会用 ffmpeg 剪切后放到 `audio/<问题id>.mp3`，并在 `audio/manifest.json` 标记为 `human`。
之后脚本不会覆盖它，网页会优先播放真人录音并显示「高音質」。

---

## 七、GitHub 备份与同步

仓库已在本地初始化（`面试练习/` 为根）。首次连接远程并上传：

```bash
# 1) 在 GitHub 网站新建一个空仓库（名字如 interview-practice-graduate），不要勾选 README
# 2) 回到本目录，替换成你的仓库地址执行：
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git branch -M main
git push -u origin main
```

以后每次改完问题 / 重生成语音后同步：

```bash
git add -A
git commit -m "更新面试问题"
git push
```

> `.venv/` 和 `uploads/`（你的录音）已被 `.gitignore` 排除，不会上传。`audio/` 的 mp3 会一起上传，方便换电脑直接用。

---

## 八、下一步待办：更逼真的语音（OpenAI TTS 等）

当前语音用微软 `edge-tts`（免费、神经语音，已相当自然）。若想进一步提升自然度，计划支持可选的高质量 API：

- **候选**：OpenAI TTS（`gpt-4o-mini-tts` / `tts-1-hd`，声音如 `alloy`/`onyx` 等，可用 instructions 控制语气）、ElevenLabs、Google / Azure Neural2。
- **改造思路**：给 `generate_audio.py` 增加 `--engine openai` 选项；engine=openai 时读环境变量 `OPENAI_API_KEY`，调用 TTS 接口生成 mp3，落地路径与 manifest 规则不变（网页侧零改动）。
- **注意**：API key 不写进代码、不进 Git（放环境变量或本地未跟踪的配置文件）；日语自然度 OpenAI 不一定明显胜过 edge-tts，建议先小批量试听对比再决定是否全量切换。

详见 `TODO.md`。
