// Sealos Devbox 上的反向代理
// 监听 8000，前端请求转发到 9071，API 请求转发到 9072
// 9071/9072 由 SSH 反向隧道映射到内网的 8071/8072

const http = require("http");

const FRONTEND_PORT = 9071;
const BACKEND_PORT = 9072;
const LISTEN_PORT = 8000;

const server = http.createServer((req, res) => {
  // /api 开头的请求转发到后端
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

server.listen(LISTEN_PORT, "0.0.0.0", () => {
  console.log(`代理已启动: :${LISTEN_PORT} -> 前端:${FRONTEND_PORT} / API:${BACKEND_PORT}`);
});
