# 下班搭子 · 官网与角色资源库

独立于桌宠客户端的网站项目。提供首页、软件下载与版本记录、可搜索的角色库、动态动作预览、角色包下载、使用指南。普通访客无需注册登录。

## 本地运行

建议 Python 3.11 或更新版本。前端为原生 HTML/CSS/JavaScript，不需要 Node 构建。

```powershell
cd E:\study\python\offwork-pet-web
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 导入同级桌宠仓库的角色包；不修改源包。
.venv\Scripts\python.exe -m portal.manage import-pack ..\offwork-pet\offwork_pet\assets\starter-packs

# 从发布者已有的签名清单读取展示信息，不修改签名更新机制。
.venv\Scripts\python.exe -m portal.manage import-release ..\offwork-pet\dist\latest.json

.\start.ps1
```

打开 http://127.0.0.1:8766 。没有导入数据也能启动，页面会展示空状态。软件清单是导入时的快照，发布新版本后需要重新导入；网站不会把本机版本号自动当作线上最新版本。首次下载链接仍指向已有的软件下载服务。

角色库目前提供“网页下载 → 客户端导入”。客户端内在线浏览、一键安装、角色更新提醒和唤起桌宠的协议尚未接入；API 为后续客户端复用预留。

## 内容与存储

- `portal/`：FastAPI、SQLite 目录与发布 CLI。
- `static/`：网站页面与品牌图标；桌面、手机布局。
- `var/catalog.sqlite3`：角色信息、版本、上下架状态、软件版本展示快照。
- `var/packs/<id>/<version>/character.petpack`：原始角色包，下载字节保持一致。
- `var/media/<id>/<version>/`：自动生成的缩略图、默认动画和包内菜单动作预览。

`var/` 已被 Git 忽略。部署时单独备份数据库和资源目录，不把凭据、角色原始素材或运行数据推送 Git。新克隆需重新导入内容。素材作者、原始来源、许可与修改说明沿用包内声明，网站不统一改变素材许可。

```powershell
python -m portal.manage import-pack path\to\character.petpack
python -m portal.manage hide character-id
python -m portal.manage show character-id
python -m portal.manage list
```

同一包标识与版本不允许用不同内容覆盖。导入旧版会保留历史版本，不会把当前版本降级。下架后列表、详情、预览和下载接口均不可访问，但服务器上的内容保留。预览生成支持当前帧图集、序列帧与 `drawRect`；每段预览最多 256 帧，最多展示包内前 12 个菜单动作。包内没有固定动作要求。

导入工具检查路径、重复文件、包大小、图片预算和用于预览的引用；它不是桌宠完整规则校验器的替代。正式发布前仍应在桌宠项目运行 `tools/character_pack.py check`。网站不执行角色包脚本，也没有公开上传或修改接口。

## 只读 API

| 路径 | 用途 |
| --- | --- |
| `/api/catalog/health` | 网站健康检查 |
| `/api/catalog/characters?q=&tag=` | 列表、搜索、能力筛选 |
| `/api/catalog/characters/{id}` | 当前版本详情与实际能力 |
| `/api/catalog/characters/{id}/versions` | 历史版本 |
| `/api/catalog/characters/{id}/download?version=` | 下载原始包 |
| `/api/catalog/releases` | 已导入的软件版本信息 |

包信息包含版本、格式版本、所需能力、大小、SHA-256、作者与许可。客户端接入时应对照自身能力判断兼容性，并继续使用原有暂存、校验、安装与更新回滚流程。

## 未来部署：公开入口为 80 端口

本仓库附带 `deploy/nginx.conf` 与 `deploy/offwork-pet-web.service` 模板，尚未部署。

建议放置：代码 `/srv/offwork-pet-web`，运行数据 `/var/lib/offwork-pet-web`，系统用户 `offwork-web`。服务只监听 `127.0.0.1:8766`，由已有宿主机 Nginx 在 80 端口转发。无需重新启动旧网站的 Docker 容器。

模板继续引入桌宠已有的 `/etc/nginx/snippets/offwork-pet.conf`，保留搭子 `/health`、`/v1/`、`/v2/` 和软件 `/offwork-pet/updates/`、`/offwork-pet/releases/`。签名文件、发布私钥和桌宠数据库仍由原项目管理。网站数据库与搭子数据库各自独立。

真正切换前需备份 Nginx 配置和内容数据，检查 `sites-enabled` 中旧默认站点及其备份文件，逐项确认其他网站路由是否保留；不能把备份站点配置留在通配加载目录中。创建服务用户及上述目录、建立虚拟环境、安装依赖并导入内容后，再启用服务。运行 `nginx -t` 成功后才重载；随后验证网站、角色下载、搭子健康、更新清单及原有连接接口。若失败，恢复配置并重载即可回退。

## 验证

```powershell
python -m unittest discover -s tests -v
node --check static/app.js
```

## 加入 Codex 项目

在“下班搭子 → 编辑项目 → 添加文件夹”中选择 `E:\study\python\offwork-pet-web` 并保存。保留 `offwork-pet` 为原有主文件夹，两个仓库可以在同一项目中协同工作。
