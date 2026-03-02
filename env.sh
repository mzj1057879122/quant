#!/bin/bash
# 公共配置，deploy.sh 和 run.sh 共用
# 修改端口、数据库名等在这里改一处即可

BACKEND_PORT=8072
FRONTEND_PORT=8071
MYSQL_PORT=3306
MYSQL_CONTAINER="mysql8"
DB_NAME="quant"
