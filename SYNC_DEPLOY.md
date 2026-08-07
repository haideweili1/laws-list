# 同步功能（多人协同编辑）部署指南

## 作用
让同事打开网页就能增 / 删 / 改法规，且所有人看到同一份最新清单。
**同事端零门槛：免登录、免令牌、免安装**，打开链接就能一起改。

## 原理（已做防欠费加固）
- **读**云端修改：直接读 GitHub Pages 上的 `user-edits.json`（免费静态文件，不消耗任何付费资源）。
- **写**云端修改：通过腾讯云 SCF 云函数代理，把修改写回 GitHub。**仅当你点网页「同步」按钮时才写，绝不自动轮询 / 心跳**，所以消耗极低。

## 你需要做（约 2 分钟）
1. 登录腾讯云控制台 → **云函数 SCF** → **新建函数**
   - 创建方式：**Web 函数**
   - 运行环境：**Node.js 18**
   - 函数名称：随意，例如 `laws-sync-proxy`
2. 进入函数 → **函数代码** → 把本仓库 `tencentcloud-scf-proxy-web.js` 的**全部内容**粘贴进 `src/app.js`（覆盖原内容）→ 点**部署**
3. **函数配置 → 环境变量** → 新增：
   - 键：`GITHUB_TOKEN`
   - 值：一个 GitHub **细粒度令牌（Fine-grained token）**，需对 `haideweili1/laws-list` 仓库有 `contents: write` 权限
   - 申请入口：GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
4. **触发管理** → 开启「Web 函数 URL」公网访问，复制函数 URL（形如 `https://xxxx.ap-guangzhou.tencentcs.com`）
5. 把这个函数 URL 发给我（或自行改 `index.html` 第 257 行 `SYNC_PROXY` 常量），我帮你重新部署网页即可。

## 完成标志
网页右上角同步状态变为「已同步云端」，同事的修改会实时出现在你的网页上。

## 费用与风控
- SCF 前 3 个月免费，之后约 **0.5 元 / 月**（用量极小）。
- 已做风控：读完全免费（静态文件），写仅在点击「同步」时触发，无任何自动轮询，从根上避免再次欠费。
