# Word 文档导入流程（给 AI Agent 的标准操作手册）

> 用户的使用方式：把一个 `.docx` 丢给 agent，说一句「导入到共通質問」或「新学校 ○○大学」。
> Agent 看到 Word 文档 + 导入意图，就按本文件从头到尾执行，**不需要用户再解释**。

## 总流程（5 步）

```
读取 docx → 整理成问题卡片 → 写入 data/questions.js → 校验 → 生成 OpenAI 语音
```

---

## 第 1 步：读取 Word 文档

macOS 自带工具，无需安装：

```bash
textutil -convert txt -stdout "/路径/文件名.docx"
```

读不出来时的备选（按顺序尝试）：

```bash
pandoc "/路径/文件名.docx" -t plain        # 若装了 pandoc
python3 -c "import docx" 2>/dev/null && python3 -m pip show python-docx   # python-docx 方案
```

仍失败就告诉用户「请另存为 .docx 格式或直接粘贴文本」。

## 第 2 步：整理成问题卡片

Word 里通常是「中文小标题 + 日文回答」的松散结构。整理规则：

1. **`q`（问题）**：把小标题转成面试现场会问的**自然日语问法**（敬体）。
   例：标题「自我介绍」→ `1分程度で自己紹介をお願いします。`
2. **`a`（回答）**：用户写好的日文回答**原文照搬，不改写**（包括口语化措辞），除非用户明确要求润色。多行用 `\n`。
3. 一个标题下有多个问题/多段答案（用分隔线隔开）→ **拆成多张卡片**。
4. 与已有问题内容重复 → **合并为一张**，不要造冗余卡。
5. 用户没写答案的问题 → `a` 填占位 `（ここに回答を書く）`，脚本会自动跳过其语音。

## 第 3 步：写入 `data/questions.js`

文件格式是 `window.INTERVIEW_DATA = { "schools": [...] };`，内容必须是**合法 JSON**。

- **加进已有学校**：定位到对应 school 的 `questions` 数组末尾追加。
- **新学校**：在 `schools` 数组里新增 `{ "id": "...", "name": "...", "questions": [...] }`。
  题库末尾有一个 `id: "template"` 的「〇〇大学（テンプレート）」——**每所学校的专门问题都应覆盖这 17 个模版问题**。
  新建学校时把模版的 17 题复制过去（id 换成新学校前缀），再把 `〇〇`/`分野A`/`XXX` 替换成具体的研究科、教授名、专业领域，最后追加该校特有的专业题。
  模版学校本身不生成语音（`generate_audio.py` 用 `--only` 跳过它，或生成后忽略 tpl-* 即可）。
- **id 规则（重要）**：
  - school id：英文小写短横线，如 `kyodai-biostat`。
  - 问题 id：学校缩写 + 两位序号，如 `tb-19`、`ky-01`，**全局唯一**。
  - **绝对不要改已有问题的 id**——音频文件按 id 命名（`audio/<id>.mp3` / `<id>-a.mp3`），改了就对不上了。
- 改已有问题的措辞 → 直接改对应 `q`/`a`，id 不动，语音脚本会按文本哈希自动重生成。

## 第 4 步：校验

```bash
node -e "global.window={}; require('./data/questions.js'); const d=window.INTERVIEW_DATA;
const ids=new Set(); let dup=[];
for (const s of d.schools) for (const q of s.questions) { if(ids.has(q.id)) dup.push(q.id); ids.add(q.id); }
console.log(d.schools.map(s=>s.id+': '+s.questions.length+'题').join('\n'));
if (dup.length) { console.error('重复 id: '+dup); process.exit(1); }"
```

报错就修到通过为止，再进下一步。

## 第 5 步：生成 OpenAI 语音

```bash
.venv/bin/python generate_audio.py --engine openai --voice cedar --speed 1.0 --natural-pauses
```

- **API key**：脚本自动从环境变量 `OPENAI_API_KEY` 或本目录未跟踪的 `.env` 文件（`OPENAI_API_KEY=sk-...`）读取。找不到 key 时提示用户在 `.env` 里写入，**不要把 key 写进任何会进 Git 的文件**。
- 脚本是增量的：只生成**新增或文本改过的**音频；`manifest.json` 里标记 `human` 的真人录音永远不覆盖。
- 只想补个别音频：`--only tb-19,tb-19-a`。
- 没有 OpenAI key 的免费备选：`--engine edge --voice ja-JP-KeitaNeural --rate=-8% --pitch=-2Hz`。

## 第 6 步：收尾

1. 检查 `audio/` 下新 id 的 mp3 是否生成（问题 `<id>.mp3`；有答案的还有 `<id>-a.mp3`）。
2. 向用户汇报：导入了几题、id 范围、生成了几个音频、有没有占位答案待补。
3. 在 `CHANGELOG.md` 顶部加一条记录。
4. 用户要求时才 `git add -A && git commit && git push`。

---

## 常见坑

| 症状 | 原因 / 处理 |
|---|---|
| 网页不显示新题 | `questions.js` JSON 语法错误（多/少逗号、引号没配对），跑第 4 步校验 |
| 新题朗读是机器音（TTS 徽章） | 还没跑第 5 步，或生成失败；mp3 缺失时网页自动降级浏览器 TTS |
| 脚本说找不到 key | `.env` 不在本目录、或变量名拼错（必须是 `OPENAI_API_KEY`） |
| 改了问题文本但语音没变 | 浏览器缓存——网页已加时间戳防缓存，强刷一次即可；或确认脚本输出里确实重生成了 |
