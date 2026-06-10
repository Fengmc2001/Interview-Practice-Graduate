# 部署到 Cloudflare Pages（带密码保护的远程访问）

目标：得到一个 `https://xxx.pages.dev` 网址，手机/平板/任何设备都能访问，**但需要密码**，
你的个人面试回答不会被陌生人看到。免费，且每次你 `git push` 后会自动更新。

> 密码门由仓库里的 `functions/_middleware.js` 实现，运行在 Cloudflare 边缘服务器上，
> 连 `data/*.js`（你的回答）都一并保护。

## 一次性设置（约 5 分钟，在浏览器里操作）

1. 注册 / 登录 Cloudflare：https://dash.cloudflare.com （免费）
2. 左侧进入 **Workers & Pages** → **Create** → 选 **Pages** 标签 → **Connect to Git**
3. 授权 GitHub，选择仓库 **Interview-Practice-Graduate**
4. 构建设置（这是纯静态站点，无需构建）：
   - **Framework preset**：`None`
   - **Build command**：留空
   - **Build output directory**：`/`（根目录）
   - 点 **Save and Deploy**，等待首次部署完成
5. 设置访问密码：项目页 → **Settings** → **Variables and Secrets**（环境变量）→ **Add**
   - 变量名：`SITE_PASSWORD`
   - 值：你自己定的密码（例如一串只有你知道的字符）
   - 保存
6. 让密码生效：回到 **Deployments**，对最新部署点 **Retry deployment**（或随便 push 一次）
7. 打开分配给你的网址 `https://<项目名>.pages.dev`
   - 浏览器弹出登录框：**用户名随便填**，**密码填上一步的 SITE_PASSWORD**
   - 进入后录音、高音质语音、字幕都可用（pages.dev 是 https）

## 日常更新

以后在本地改完问题、跑完 `generate_audio.py`，照常：

```bash
git add -A
git commit -m "更新问题"
git push
```

Cloudflare 检测到 push 会**自动重新部署**，几十秒后线上就是最新的。

## 改密码

Cloudflare 项目 → Settings → Variables → 改 `SITE_PASSWORD` 的值 → Retry deployment。

## 想临时关闭密码门

把仓库里的 `functions/` 文件夹删掉再 push（不推荐，会变成无密码公开）。
或在 Cloudflare 删除整个 Pages 项目即可下线网址。
