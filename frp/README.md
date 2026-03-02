# frp 内网穿透配置

## 架构

```
公网用户 :8073 → 公网服务器(frps) → 内网穿透 → 内网服务器(:8071前端 + :8072后端)
```

## 部署步骤

### 1. 公网服务器（运行 frps）

把 `server/` 目录上传到公网服务器，执行：

```bash
bash setup-server.sh
```

### 2. 内网服务器（运行 frpc）

修改 `client/frpc.toml` 中的公网 IP，然后执行：

```bash
bash setup-client.sh
```

### 3. 访问

浏览器打开 `http://公网IP:8073` 即可。
