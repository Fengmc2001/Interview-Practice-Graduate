#!/bin/bash
# 双击此文件启动面接練習App（会打开终端窗口，使用期间请不要关闭）
cd "$(dirname "$0")"
( sleep 1 && open "http://localhost:8765" ) &
echo "面接練習App 已启动: http://localhost:8765  （按 Ctrl+C 退出）"
python3 -m http.server 8765
