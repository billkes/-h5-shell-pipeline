#!/usr/bin/env bash
# h5-shell-pipeline：H5 Shell 批量生产交互式入口
# 用法：./run.sh [python -m batch 参数]

set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "  首次运行，正在初始化环境..."
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "  [1/3] 创建虚拟环境..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "  ❌ 创建虚拟环境失败，请确保已安装 Python3"
        exit 1
    fi
    echo "  ✅ 虚拟环境创建成功"

    echo ""
    echo "  [2/3] 安装依赖..."
    source .venv/bin/activate
    pip install -r requirements.txt -q
    if [ $? -ne 0 ]; then
        echo "  ❌ 安装依赖失败"
        exit 1
    fi
    echo "  ✅ 依赖安装成功"
    echo ""
else
    source .venv/bin/activate
fi

export PYTHONPATH="${PWD}/scripts${PYTHONPATH:+:$PYTHONPATH}"

# 默认进入帮助；传递参数则直接执行对应命令
if [ $# -eq 0 ]; then
    echo ""
    echo "h5-shell-pipeline task CLI"
    echo ""
    echo "常用命令："
    echo "  ./run.sh task-init --batch-id <id> --rows <n>"
    echo "  ./run.sh task-add --rows <n>"
    echo "  ./run.sh task-validate"
    echo "  ./run.sh task-list"
    echo "  ./run.sh task-show <应用主名称>"
    echo "  ./run.sh task-ready"
    echo "  ./run.sh build-all --h5-host <host> --team-id <id>"
    echo "  ./run.sh build <应用主名称>"
    echo ""
    exec python3 -m batch --help
fi

exec python3 -m batch "$@"
