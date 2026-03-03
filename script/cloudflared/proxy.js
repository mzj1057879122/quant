// 本地合并代理：将前端和后端合并到一个端口
// /api 开头 → 后端 8072
// 其他请求 → 前端 8071

const http = require("http");

const LISTEN_PORT = 8090;
const FRONTEND_PORT = 8071;
const BACKEND_PORT = 8072;

const server = http.createServer((req, res) => {
  const isApi = req.url.startsWith("/api");
  const targetPort = isApi ? BACKEND_PORT : FRONTEND_PORT;

  const options = {
    hostname: "127.0.0.1",
    port: targetPort,
    path: req.url,
    method: req.method,
    headers: req.headers,
  };

  const proxy = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res);
  });

  proxy.on("error", (err) => {
    res.writeHead(502);
    res.end("Bad Gateway: " + err.message);
  });

  req.pipe(proxy);
});

server.listen(LISTEN_PORT, "127.0.0.1", () => {
  console.log(`代理已启动 :${LISTEN_PORT} -> 前端:${FRONTEND_PORT} / API:${BACKEND_PORT}`);
});
