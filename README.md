# 法律法规及其他要求清单（自动更新版）

制造业体系工程师用的法律法规清单网页。**纯静态托管在 GitHub Pages，数据由 GitHub Actions 每周一北京时间 9 点自动联网检索更新**，无需在你的电脑上运行任何东西。

## 功能
- 四大分类：三体系（ISO 9001/14001/45001）、社会责任、反恐/供应链安全、信息安全
- 每条法规带政府官网来源链接（可点击）
- 网页内可「编辑法规」：新增 / 修改 / 删除（存于浏览器本地）
- 导出 Excel / PDF / 图片
- GitHub Actions 每周自动检索中国政府网、人大网等，更新 `laws.json`

## 费用
- **GitHub Pages**：免费
- **更新检索**：用 Google Gemini 免费额度 + Google 搜索接地（grounding），每周跑一次完全在免费额度内，**不花钱**，只需要一个免费申请的 `GEMINI_API_KEY`

## 一键部署步骤

### 1. 创建 GitHub 仓库并推送
在你的 GitHub 上新建一个**公开**仓库（例如 `laws-list`），然后把本目录内容推上去：

```bash
cd github-repo
git init
git add .
git commit -m "init laws site"
git remote add origin https://github.com/你的用户名/laws-list.git
git branch -M main
git push -u origin main
```

> 如果你已经在本地建过 git 仓库，跳过 `git init`，直接 `git remote add` + `git push` 即可。

### 2. 开启 GitHub Pages
1. 进入仓库 **Settings → Pages**
2. Source 选择 **Deploy from a branch**
3. Branch 选 **main**，目录选 **/ (root)**
4. 保存。几分钟后访问 `https://你的用户名.github.io/laws-list/`

### 3. 配置免费的 Gemini API Key（自动更新必需）
1. 打开 https://aistudio.google.com/apikey ，用 Google 账号**免费**申请一个 API Key
2. 进入仓库 **Settings → Secrets and variables → Actions → Secrets → New repository secret**
3. Name 填 `GEMINI_API_KEY`，Value 粘贴刚申请的 Key，保存

（可选）仓库 **Settings → Secrets and variables → Actions → Variables** 里可加变量 `MODEL`，值填 `gemini-2.5-flash`（默认即此；若免费额度不支持 grounding，可改 `gemini-2.0-flash`）。

### 4. 让它跑起来
- **自动**：每周一北京时间 9 点自动运行（已配置 cron）
- **手动**：仓库 **Actions → 法律法规清单自动更新 → Run workflow** 可立即触发一次

推送 `laws.json` 变更后，GitHub Pages 会自动重新发布，刷新网页即可看到最新数据。

## 目录结构
```
index.html                 # 网页（纯前端，依赖公共 CDN 库）
laws.json                  # 法规数据（由 Actions 自动更新）
update_laws_action.py      # 自动更新脚本（Gemini + 联网检索）
requirements.txt           # Python 依赖
.github/workflows/update.yml  # 定时任务配置
```

## 已知限制
- 网页里的「手动添加法规」存在**浏览器本地（localStorage）**，换设备/清缓存会丢失，且**自动更新读不到它们**。若希望手动法规也能被自动验证并共享，需要把它们改为存成仓库里的文件（如需此功能可另行扩展）。

## 原 WorkBuddy 自动化
迁移到 GitHub 后，原来 WorkBuddy 里「每周一更新本地 laws.json 并部署 CloudStudio」的自动化已不再需要，建议在 WorkBuddy 中**暂停**它，避免与 GitHub 版本的数据产生分歧。
