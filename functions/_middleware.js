// Cloudflare Pages 密码门（HTTP Basic Auth）
// 部署到 Cloudflare Pages 后，在项目设置里加一个环境变量 SITE_PASSWORD，
// 访问站点时浏览器会弹出登录框：用户名随意，密码填 SITE_PASSWORD 的值。
// 这道门在 Cloudflare 边缘服务器上运行，连 data/*.js（你的回答）也一并保护，
// 不是前端糊弄的弹窗。未设置密码时一律拒绝访问（安全默认）。

export async function onRequest(context) {
  const { request, env, next } = context;
  const expected = env.SITE_PASSWORD;

  if (!expected) {
    return new Response(
      "未配置访问密码：请在 Cloudflare Pages 项目的「环境变量」中添加 SITE_PASSWORD 后重新部署。",
      { status: 503, headers: { "content-type": "text/plain; charset=utf-8" } }
    );
  }

  const header = request.headers.get("Authorization") || "";
  if (header.startsWith("Basic ")) {
    try {
      const decoded = atob(header.slice(6));
      const password = decoded.slice(decoded.indexOf(":") + 1); // 取冒号后的密码部分，用户名忽略
      if (password === expected) {
        return next();
      }
    } catch (e) {
      // 解码失败，落到下面的 401
    }
  }

  return new Response("認証が必要です（需要密码）", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="面接コーチ", charset="UTF-8"',
      "content-type": "text/plain; charset=utf-8",
    },
  });
}
