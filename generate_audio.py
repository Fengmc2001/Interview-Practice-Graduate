#!/usr/bin/env python3
"""批量生成面试问题/答案的高质量日语语音（微软 edge-tts 神经语音）。

用法:
    python3 generate_audio.py                 # 生成缺失的或文本已修改的语音
    python3 generate_audio.py --voice ja-JP-NanamiNeural   # 换成女声
    python3 generate_audio.py --rate -10%     # 整体放慢 10%

规则:
  - 问题音频 -> audio/<id>.mp3，答案音频 -> audio/<id>-a.mp3
  - audio/manifest.json 记录每个文件的来源:
      "tts"   = 本脚本生成，文本改动后会自动重新生成
      "human" = 真人录音（手动剪切放入的），脚本永远不会覆盖
  - 占位答案「（ここに…」不生成答案音频
"""
import argparse
import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import edge_tts
except ImportError:
    sys.exit("缺少 edge-tts，请先运行: .venv/bin/pip install edge-tts")

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data" / "questions.js"
AUDIO_DIR = ROOT / "audio"
MANIFEST = AUDIO_DIR / "manifest.json"


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


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="ja-JP-KeitaNeural", help="语音名（男声 KeitaNeural / 女声 NanamiNeural）")
    ap.add_argument("--rate", default="+0%", help="语速，如 -10%% 或 +10%%")
    args = ap.parse_args()

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

    made = skipped = 0
    for key, text, path in jobs:
        entry = manifest.get(key, {})
        if entry.get("source") == "human" and path.exists():
            print(f"  保留真人录音: {path.name}")
            skipped += 1
            continue
        if path.exists() and entry.get("hash") == text_hash(text):
            skipped += 1
            continue
        print(f"  生成: {path.name}  ({text[:24]}…)" if len(text) > 24 else f"  生成: {path.name}  ({text})")
        await edge_tts.Communicate(text, voice=args.voice, rate=args.rate).save(str(path))
        manifest[key] = {"hash": text_hash(text), "source": "tts", "voice": args.voice}
        made += 1

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完成：新生成 {made} 个，跳过 {skipped} 个。")


if __name__ == "__main__":
    asyncio.run(main())
