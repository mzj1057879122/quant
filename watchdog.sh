#!/bin/bash
# 后端守护进程：每5秒检测，挂了自动拉起
while true; do
  if ! ss -tlnp | grep -q ':8072'; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 后端挂了，重启..." >> /tmp/quant-watchdog.log
    fuser -k 8072/tcp 2>/dev/null
    sleep 1
    cd /home/zejianma/quant/backend
    nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8072 >> /tmp/quant-backend.log 2>&1 &
    sleep 8
  fi
  sleep 5
done
