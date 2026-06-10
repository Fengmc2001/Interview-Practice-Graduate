#!/usr/bin/env python3
"""批量生成面试问题/答案的高质量日语语音。

用法:
    python3 generate_audio.py                               # 用 edge-tts 生成缺失或文本已修改的语音
    python3 generate_audio.py --engine openai               # 用 OpenAI 生成更自然的语音
    python3 generate_audio.py --engine openai --voice cedar # 换 OpenAI 声音
    python3 generate_audio.py --only tb-01,tb-01-a          # 只生成指定问题/答案音频
    python3 generate_audio.py --natural-pauses --force      # 给长句加入音频专用停顿后重生成
    python3 generate_audio.py --voice ja-JP-NanamiNeural    # edge-tts 换女声
    python3 generate_audio.py --rate -10%                   # edge-tts 整体放慢 10%

规则:
  - 问题音频 -> audio/<id>.mp3，答案音频 -> audio/<id>-a.mp3
  - audio/manifest.json 记录每个文件的来源:
      "tts"    = edge-tts 生成，文本改动后会自动重新生成
      "openai" = OpenAI Speech API 生成，文本/模型/声音/指令改动后会自动重新生成
      "human"  = 真人录音（手动剪切放入的），脚本默认永远不会覆盖
  - 占位答案「（ここに…」不生成答案音频
"""
import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data" / "questions.js"
AUDIO_DIR = ROOT / "audio"
MANIFEST = AUDIO_DIR / "manifest.json"
OPENAI_SPEECH_URL = "https://api.openai.com/v1/audio/speech"
DEFAULT_OPENAI_INSTRUCTIONS = (
    "Speak in natural, polite Japanese for graduate school interview practice. "
    "Use clear pronunciation, calm confidence, natural intonation, and short pauses. "
    "Keep a moderate speed and do not add or omit any words."
)
TERM_READINGS = [
    (r"active comparator new-user design", "アクティブ・コンパレーター・ニュー・ユーザー・デザイン"),
    (r"real-world data", "リアルワールドデータ"),
    (r"target trial emulation", "ターゲット・トライアル・エミュレーション"),
    (r"new-user design", "ニュー・ユーザー・デザイン"),
    (r"pooled logistic", "プールド・ロジスティック"),
    (r"propensity score", "プロペンシティ・スコア"),
    (r"g-formula", "ジー・フォーミュラ"),
    (r"E-value", "イー・バリュー"),
    (r"robustness value", "ロバストネス・バリュー"),
    (r"cross-fitting", "クロス・フィッティング"),
    (r"nuisance model", "ニューサンス・モデル"),
    (r"outcome model", "アウトカム・モデル"),
    (r"grace period", "グレース・ピリオド"),
    (r"window", "ウィンドウ"),
    (r"estimand", "エスティマンド"),
    (r"protocol", "プロトコル"),
    (r"(?<![A-Za-z])AIPCW(?![A-Za-z])", "エー・アイ・ピー・シー・ダブリュー"),
    (r"(?<![A-Za-z])IPCW(?![A-Za-z])", "アイ・ピー・シー・ダブリュー"),
    (r"(?<![A-Za-z])DML(?![A-Za-z])", "ディー・エム・エル"),
    (r"(?<![A-Za-z])CCW(?![A-Za-z])", "シー・シー・ダブリュー"),
    (r"(?<![A-Za-z])MSM(?![A-Za-z])", "エム・エス・エム"),
    (r"(?<![A-Za-z])LLM(?![A-Za-z])", "エル・エル・エム"),
    (r"(?<![A-Za-z])AI(?![A-Za-z])", "エー・アイ"),
    (r"(?<![A-Za-z])TOEFL(?![A-Za-z])", "トーフル"),
    (r"(?<![A-Za-z])Listening(?![A-Za-z])", "リスニング"),
    (r"(?<![A-Za-z])Neyman(?![A-Za-z])", "ネイマン"),
]
DISCOURSE_WORDS = (
    "まず",
    "また",
    "さらに",
    "特に",
    "ただし",
    "一方で",
    "そのため",
    "本来",
    "現実上には",
    "将来は",
    "現在は",
    "例えば",
    "つまり",
    "むしろ",
    "ご指摘の通り",
    "本研究では",
)
CLAUSE_MARKERS = (
    "において",
    "においては",
    "に対して",
    "に対しては",
    "に関して",
    "によって",
    "により",
    "として",
    "上で",
    "上では",
    "中で",
    "中では",
    "点で",
    "点では",
    "場合",
    "場合は",
    "場合には",
    "ため",
    "ながら",
    "一方で",
)


def load_questions():
    text = DATA_FILE.read_text(encoding="utf-8")
    m = re.search(r"window\.INTERVIEW_DATA\s*=\s*(\{.*\})\s*;?\s*$", text, re.S)
    if not m:
        sys.exit("无法解析 data/questions.js（请保持 window.INTERVIEW_DATA = {...}; 的格式，内容为合法 JSON）")
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError as e:
        sys.exit(f"data/questions.js 中的 JSON 有语法错误: {e}")


def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


def text_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def has_pause_after(text: str, idx: int) -> bool:
    return idx < len(text) and text[idx : idx + 1] in "、。！？\n"


def add_comma_after(text: str, phrase: str, start: int) -> str:
    end = start + len(phrase)
    if has_pause_after(text, end):
        return text
    if end < len(text) and text[end] in "はもがをにでと":
        return text
    return text[:end] + "、" + text[end:]


def replace_term_readings(text: str) -> str:
    for pattern, reading in TERM_READINGS:
        text = re.sub(pattern, reading, text, flags=re.IGNORECASE)
    return text


def insert_discourse_pauses(text: str) -> str:
    for word in DISCOURSE_WORDS:
        text = re.sub(rf"(^|[。\n])({re.escape(word)})(?![、。！？\n])", rf"\1\2、", text)
    return text


def insert_clause_pauses(segment: str) -> str:
    if len(segment) < 28:
        return segment

    for marker in CLAUSE_MARKERS:
        pos = 0
        while True:
            idx = segment.find(marker, pos)
            if idx < 0:
                break
            if idx + len(marker) >= len(segment) - 4:
                pos = idx + len(marker)
                continue
            segment = add_comma_after(segment, marker, idx)
            pos = idx + len(marker) + 1
    return segment


def soften_long_run(run: str, max_len: int = 34) -> str:
    if len(run) <= max_len:
        return run

    parts = []
    rest = run
    safe_breaks = (
        "ですが",
        "けれども",
        "けれど",
        "ため",
        "ので",
        "場合",
        "一方で",
        "として",
        "において",
        "に対して",
        "について",
        "によって",
        "により",
        "上で",
        "中で",
        "点で",
        "ながら",
        "ことから",
        "ことにより",
    )
    while len(rest) > max_len:
        window = rest[: max_len + 1]
        break_at = -1
        for marker in safe_breaks:
            idx = window.rfind(marker, 16)
            if idx > break_at:
                break_at = idx + len(marker)
        if break_at < 16:
            return "、".join(parts + [rest]) if parts else run
        parts.append(rest[:break_at])
        rest = rest[break_at:]
    parts.append(rest)
    return "、".join(p for p in parts if p)


def soften_long_segments(text: str) -> str:
    result = []
    run = []
    delimiters = set("、。！？\n")
    for ch in text:
        if ch in delimiters:
            result.append(soften_long_run("".join(run)))
            result.append(ch)
            run = []
        else:
            run.append(ch)
    result.append(soften_long_run("".join(run)))
    return "".join(result)


def normalize_pause_marks(text: str) -> str:
    text = re.sub(r"、{2,}", "、", text)
    text = re.sub(r"、([。！？])", r"\1", text)
    text = re.sub(r"([。！？])、", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    jp = r"ぁ-んァ-ヶー一-龯々"
    text = re.sub(rf"([{jp}]) ([{jp}])", r"\1\2", text)
    text = re.sub(rf"([、。！？]) ([{jp}])", r"\1\2", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def naturalize_for_tts(text: str) -> str:
    text = replace_term_readings(text)
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            lines.append("")
            continue
        line = insert_discourse_pauses(line)
        pieces = re.split(r"([。！？、])", line)
        rebuilt = []
        for i in range(0, len(pieces), 2):
            segment = pieces[i]
            punct = pieces[i + 1] if i + 1 < len(pieces) else ""
            rebuilt.append(insert_clause_pauses(segment))
            rebuilt.append(punct)
        line = soften_long_segments("".join(rebuilt))
        if line and line[-1] not in "。！？":
            line += "。"
        lines.append(line)
    return normalize_pause_marks("\n".join(lines))


def load_openai_api_key():
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key

    env_file = ROOT / ".env"
    if not env_file.exists():
        return ""

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == "OPENAI_API_KEY":
            return value.strip().strip('"').strip("'")
    return ""


def generation_metadata(args, source_text, speech_text, voice):
    source = "openai" if args.engine == "openai" else "tts"
    meta = {
        "hash": text_hash(speech_text),
        "source_hash": text_hash(source_text),
        "source": source,
        "voice": voice,
        "natural_pauses": args.natural_pauses,
    }
    if args.engine == "openai":
        meta.update(
            {
                "model": args.model,
                "instructions_hash": text_hash(args.instructions),
                "response_format": "mp3",
                "speed": args.speed,
            }
        )
    else:
        meta["rate"] = args.rate
        meta["pitch"] = args.pitch
    return meta


def can_skip(path, entry, meta, args):
    if args.force or not path.exists():
        return False
    if entry.get("hash") != meta["hash"] or entry.get("source") != meta["source"]:
        return False
    if entry.get("voice") != meta["voice"]:
        return False
    if args.engine == "openai":
        return (
            entry.get("model") == meta["model"]
            and entry.get("instructions_hash") == meta["instructions_hash"]
            and entry.get("response_format", "mp3") == "mp3"
            and float(entry.get("speed", 1.0)) == args.speed
        )
    return entry.get("rate", "+0%") == args.rate and entry.get("pitch", "+0Hz") == args.pitch


async def save_edge_tts(text, path, voice, rate, pitch):
    try:
        import edge_tts
    except ImportError:
        sys.exit("缺少 edge-tts，请先运行: .venv/bin/pip install edge-tts")

    await edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch).save(str(path))


def save_openai_tts(text, path, voice, args, api_key):
    payload = {
        "model": args.model,
        "input": text,
        "voice": voice,
        "instructions": args.instructions,
        "response_format": "mp3",
        "speed": args.speed,
    }
    req = urllib.request.Request(
        OPENAI_SPEECH_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            tmp.write_bytes(response.read())
        tmp.replace(path)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if tmp.exists():
            tmp.unlink()
        sys.exit(f"OpenAI TTS 请求失败: HTTP {e.code}\n{body}")
    except urllib.error.URLError as e:
        if tmp.exists():
            tmp.unlink()
        sys.exit(f"OpenAI TTS 网络请求失败: {e}")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["edge", "openai"], default="edge", help="语音引擎")
    ap.add_argument("--voice", default=None, help="语音名；edge 默认 Keita，OpenAI 默认 marin")
    ap.add_argument("--rate", default="+0%", help="edge-tts 语速，如 -10%% 或 +10%%")
    ap.add_argument("--pitch", default="+0Hz", help="edge-tts 音高，如 -2Hz 或 +2Hz")
    ap.add_argument("--model", default="gpt-4o-mini-tts", help="OpenAI TTS 模型")
    ap.add_argument("--instructions", default=DEFAULT_OPENAI_INSTRUCTIONS, help="OpenAI 语音风格指令")
    ap.add_argument("--speed", type=float, default=1.0, help="OpenAI 语速，范围 0.25 到 4.0")
    ap.add_argument("--natural-pauses", action="store_true", help="生成前加入音频专用术语读法和长句停顿")
    ap.add_argument("--only", default="", help="只生成指定 key，逗号分隔，如 tb-01,tb-01-a")
    ap.add_argument("--force", action="store_true", help="即使 manifest 匹配也重新生成")
    ap.add_argument("--include-human", action="store_true", help="允许覆盖 manifest 中标记为 human 的真人录音")
    args = ap.parse_args()

    if not 0.25 <= args.speed <= 4.0:
        sys.exit("--speed 必须在 0.25 到 4.0 之间")

    voice = args.voice or ("marin" if args.engine == "openai" else "ja-JP-KeitaNeural")
    api_key = ""
    if args.engine == "openai":
        api_key = load_openai_api_key()
        if not api_key:
            sys.exit("未找到 OPENAI_API_KEY。请先 export OPENAI_API_KEY=...，或在本目录未跟踪的 .env 中写入。")

    AUDIO_DIR.mkdir(exist_ok=True)
    data = load_questions()
    manifest = load_manifest()

    jobs = []  # (key, text, path)
    for school in data["schools"]:
        for q in school["questions"]:
            jobs.append((q["id"], q["q"], AUDIO_DIR / f"{q['id']}.mp3"))
            ans = (q.get("a") or "").strip()
            if ans and not ans.startswith("（ここに"):
                jobs.append((q["id"] + "-a", ans, AUDIO_DIR / f"{q['id']}-a.mp3"))

    if args.only.strip():
        only = {x.strip() for x in args.only.split(",") if x.strip()}
        jobs = [job for job in jobs if job[0] in only]
        missing = sorted(only - {job[0] for job in jobs})
        if missing:
            sys.exit(f"--only 中没有匹配到这些 key: {', '.join(missing)}")

    made = skipped = 0
    for key, text, path in jobs:
        speech_text = naturalize_for_tts(text) if args.natural_pauses else text
        meta = generation_metadata(args, text, speech_text, voice)
        entry = manifest.get(key, {})
        if entry.get("source") == "human" and path.exists() and not args.include_human:
            print(f"  保留真人录音: {path.name}")
            skipped += 1
            continue
        if can_skip(path, entry, meta, args):
            skipped += 1
            continue
        print(f"  生成: {path.name}  ({text[:24]}…)" if len(text) > 24 else f"  生成: {path.name}  ({text})")
        if args.engine == "openai":
            save_openai_tts(speech_text, path, voice, args, api_key)
        else:
            await save_edge_tts(speech_text, path, voice, args.rate, args.pitch)
        manifest[key] = meta
        made += 1

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完成：engine={args.engine}，voice={voice}，新生成 {made} 个，跳过 {skipped} 个。")


if __name__ == "__main__":
    asyncio.run(main())
