#!/usr/bin/env bash
# cursor-ios-batch：Flutter / iOS 批量生产交互式入口
# 用法：./run.sh

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
    echo "  [3/3] 环境就绪（ui-ux-pro-max 由 skill.design 运行时加载）..."
    echo "  ✅ 跳过 uupm 本地快照同步"
    echo ""
    echo "  环境初始化完成！"
    echo ""
    sleep 1
else
    source .venv/bin/activate
fi

export PYTHONPATH="${PWD}/scripts${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m batch
