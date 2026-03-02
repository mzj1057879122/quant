#!/bin/bash
# 公网服务器一键部署 frps
# 用法: bash setup-server.sh

set -e

FRP_VERSION="0.61.1"
ARCH="amd64"

# 下载 frp
if [ ! -f frps ]; then
    echo "下载 frp v${FRP_VERSION}..."
    curl -L -o frp.tar.gz "https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_${ARCH}.tar.gz"
    tar -xzf frp.tar.gz
    cp "frp_${FRP_VERSION}_linux_${ARCH}/frps" .
    rm -rf "frp_${FRP_VERSION}_linux_${ARCH}" frp.tar.gz
    chmod +x frps
fi

# 停掉旧进程
pkill frps 2>/dev/null || true
sleep 1

# 启动
nohup ./frps -c frps.toml > frps.log 2>&1 &
echo "frps 已启动 (PID $!)"
echo "记得开放防火墙端口: 7000(frp通信) + 8073(前端) + 8072(后端API)"
