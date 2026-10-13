<div align="center">
  <img src="desktop/app/resource/images/logo/CocoDownloader.png" alt="CoCo Downloader Logo" width="112" height="112" />
  <h1>CoCo Downloader</h1>
  <p>一个覆盖 Web 与桌面端的音乐搜索、播放和下载项目。</p>
</div>

<div align="center">

![Next.js](https://img.shields.io/badge/Next.js-16-black)
![React](https://img.shields.io/badge/React-19-149eca)
![TypeScript](https://img.shields.io/badge/TypeScript-5-blue)
![PyQt5](https://img.shields.io/badge/PyQt5-Desktop-41cd52)
![QFluentWidgets](https://img.shields.io/badge/QFluentWidgets-UI-0078d4)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

## 项目定位

CoCo Downloader 不是单一页面应用，而是一组围绕“音乐检索与获取体验”组织的 Web 与桌面客户端实现。

仓库当前包含两条主线：

- `src/`：主 Web 应用，提供音乐搜索、在线试听、批量下载、播放栏和主题体验。
- `desktop/`：PyQt5 桌面端，提供原生窗口、搜索列表、播放栏、下载任务管理和本地配置能力。

Web 端适合浏览器和 Docker 部署；桌面端适合打包成 Windows 安装包或便携版。

## 功能概览

### Web 应用

- 多音源聚合搜索
- 在线播放与底部播放器
- 播放、暂停、上一曲、下一曲、进度拖动、音量控制和播放模式切换
- 批量下载与下载抽屉
- NAS 保存：将歌曲、标签与歌词写入挂载的音乐库
- AAC 自动转 MP3：默认开启并记住选择，兼容浏览器下载、NAS 保存和批量任务，非 AAC 编码保持不变
- JOOX 音质选择弹窗
- 深色 / 浅色 / 跟随系统主题切换，支持涟漪过渡
- 基于 Next.js App Router 的 API Routes

### 桌面端

`desktop/` 是 PyQt5 桌面客户端，核心体验更接近本地音乐工具。

主要能力：

- 搜索音乐并展示结果列表
- 播放、暂停、上一曲、下一曲、播放模式切换
- 播放进度拖动与音量控制
- 单曲下载与下载任务展示
- 下载目录和文件命名规则配置
- 浅色 / 深色 / 跟随系统主题
- 用户配置保存到系统 AppData 目录
- 支持 Nuitka 打包和 Inno Setup 安装包制作

## 架构解析

```text
coco-downloader/
├─ src/                         # 主 Web 应用
│  ├─ app/                      # Next.js App Router 页面与 API Routes
│  │  ├─ api/download/          # 下载接口
│  │  ├─ api/search/            # 搜索接口
│  │  └─ api/url/               # 播放直链接口
│  ├─ components/               # Web UI 组件
│  ├─ lib/providers/            # 音源 provider 策略实现
│  └─ types/                    # TypeScript 类型
├─ desktop/                     # PyQt5 桌面端
│  ├─ CoCo-downloader.py        # 桌面端入口
│  ├─ app/common/               # 配置、资源、信号总线和样式管理
│  ├─ app/components/           # 播放栏、搜索卡片、下载任务卡片等复用组件
│  ├─ app/services/             # 搜索、下载、播放和 provider 服务
│  ├─ app/view/                 # 主窗口、首页、下载页、设置页
│  └─ app/resource/             # qrc、qss、图片、翻译资源
├─ Dockerfile
├─ docker-compose.yml
└─ package.json
```

### Web 端分层

Web 主应用把“页面交互”和“音源解析”拆开：

- `src/app/page.tsx` 负责组织首页体验。
- `src/components/PlayerBar.tsx`、`DownloadDrawer.tsx`、`QualitySelectModal.tsx` 等组件承载交互界面。
- `src/app/api/*` 是浏览器调用的服务入口。
- `src/lib/providers/impl/*` 是各个音源的实际解析实现。

这种结构让前端不直接关心每个音源的细节。新增音源时，优先在 `providers` 层补实现，再在统一入口注册。

### 桌面端分层

桌面端按 Qt 应用常见边界拆分：

- `view/`：页面和窗口，如主窗口、首页、下载页、设置页。
- `components/`：可复用 UI 组件，如播放栏、搜索卡片、下载任务卡片。
- `services/`：业务服务，如搜索服务、下载服务、播放服务。
- `services/providers/`：不同音源 provider。
- `common/`：配置、资源、样式、信号总线等基础设施。
- `models/`：音乐数据模型。

配置文件通过 `QStandardPaths.AppDataLocation` 写入用户级 AppData 目录，避免打包后写入安装目录。

## 快速开始

### Web 主应用

使用 Node.js 20.9 或更新版本。使用 AAC 自动转 MP3 时，服务器需安装 `ffmpeg`（支持 `libmp3lame`）和 `ffprobe` 并加入 `PATH`；本仓库构建的 Docker 镜像已包含二者。

```bash
npm install
npm run dev
```

默认访问：

```text
http://localhost:3000
```

生产构建：

```bash
npm run build
npm run start
```

### AAC 自动转 MP3

在首页「NAS 保存」下方使用「AAC 自动转 MP3」开关，默认开启，关闭后保留原音频格式。开关只影响新建下载任务，已经排队的批量任务使用创建时的设置。

开启后，服务端先下载到临时目录，用 `ffprobe` 检测实际编码，仅将 AAC（含 `.aac`、M4A 中的 AAC，以及扩展名不准确的 AAC）通过 `ffmpeg` / `libmp3lame` 转成 MP3（VBR 质量等级 2）。MP3、FLAC、ALAC 等其他编码不会重新编码；浏览器下载的文件名和响应类型会匹配输出格式。转码属于有损转换，不会提升音质，会增加等待时间、CPU 与临时磁盘占用。

NAS 模式仍会尝试写入歌曲信息、封面和歌词；转码失败会明确显示错误，不会把 AAC 仅改名为 MP3，也不会以失败结果覆盖已有歌曲。可检查服务端依赖，或关闭转换后重试。

API 的 GET 查询参数或 POST JSON 支持 `convertAacToMp3`（GET 为 `true`/`false` 或 `1`/`0`，POST 为布尔值）。省略此参数保留原有不转码行为；`saveToNas=false` 可在已配置 NAS 的情况下选择浏览器下载。渠道所需的 `extra`（例如音质或会话信息）同样支持两种方式：GET 传 JSON 字符串，POST 传 JSON 对象，浏览器下载和 NAS 保存均会透传。

回归测试使用本地生成的测试音频，无需访问音乐源；运行前安装依赖、`ffmpeg` 和 `ffprobe`，并使用 Node.js 20 或更新版本：

```bash
npm run test:download
```

### 涟漪主题切换
在 `src/components/Navbar.tsx` 中，我们利用了浏览器原生的 `document.startViewTransition` API 配合 CSS `clip-path` 属性。
当用户点击主题切换按钮时，计算点击坐标，以该坐标为圆心，计算覆盖全屏所需的最大半径，然后执行圆形扩散遮罩动画。这比传统的 CSS `transition` 全局淡入淡出更具动感和现代感。

### 音乐源扩展
项目后端采用策略模式设计。在 `src/lib/providers` 下定义了统一的接口。若需添加新的音乐网站源，只需新建一个实现类并在工厂方法中注册即可，无需大幅修改前端逻辑。

### Docker

本地定制功能（NAS 保存、AAC 转 MP3）需要从本仓库源码构建；上游发布的镜像不包含这些改动。

#### 使用 Docker Compose 从源码构建

```bash
cp .env.example .env
# 编辑 .env，按需设置宿主机端口和音乐库路径
mkdir -p music
docker compose up -d --build
```

- `PORT`：宿主机端口，默认 `3001`；容器内部固定使用 `3000`。
- `MUSIC_LIBRARY_HOST_DIR`：宿主机音乐库路径，默认 `./music`。NAS 部署时改为实际的绝对路径。
- `MUSIC_LIBRARY_DIR`：容器内音乐库路径，默认 `/music`，无需填写宿主机路径。
- `ENABLE_DOWNLOAD` / `SAVE_TO_NAS`：默认均为 `1`，设为 `0` 可分别关闭下载或 NAS 保存。

音乐库目录需事先创建，并确保容器用户（UID `1001`、GID `1001`）有写入权限；NAS 可通过目录 ACL 授权。

版本控制保留 [Dockerfile](./Dockerfile)、[docker-compose.yml](./docker-compose.yml)、[.dockerignore](./.dockerignore) 和 [.env.example](./.env.example)。本机 `.env`、Compose override 配置和默认 `music/` 运行数据已同时排除在 Git 提交及 Docker 构建上下文之外。自定义音乐库建议使用仓库外路径；若放在仓库内的其他目录，需同步补充 [.gitignore](./.gitignore) 和 [.dockerignore](./.dockerignore)。

#### NAS 落盘模式

如果你希望点击下载后直接保存到 NAS 挂载目录，并自动按歌手/专辑/歌曲命名，可以在容器里额外挂载一个音乐库目录，并设置环境变量：

```bash
docker run -d \
   -p 3000:3000 \
   -e MUSIC_LIBRARY_DIR=/music \
   -e SAVE_TO_NAS=1 \
   -v /volume1/music:/music \
   --name coco-downloader \
   coco-downloader:latest
```

上述镜像需先通过 `docker compose build` 构建。保存模式会优先写入 `MUSIC_LIBRARY_DIR`，文件命名为「歌手 - 歌名.扩展名」，并且会尽量写入：

- 歌词 `.lrc` 旁路文件
- 通过 ffmpeg 尽量嵌入封面及音频标签，例如标题、歌手、专辑、专辑歌手

Navidrome 直接扫描这个目录即可使用。

### 桌面端

建议使用 Python 3.12，并为桌面端单独创建虚拟环境。Windows PowerShell：

```powershell
cd desktop
uv venv .venv --python 3.12
uv pip install --python .venv/Scripts/python.exe -r requirements-lock.txt
.\.venv\Scripts\python.exe CoCo-downloader.py
```

已有上述环境时直接运行启动命令，无需重复创建；`.venv` 是 uv 管理的项目环境目录。
`requirements.txt` 是直接依赖列表，`requirements-lock.txt` 记录本次 Windows Python 3.12 验证环境。

桌面回归测试（模拟网络响应，不下载第三方音乐）：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

如果修改了 `resource.qrc`，需要重新生成 Qt 资源文件：

```bash
python -m PyQt5.pyrcc_main app/resource/resource.qrc -o app/common/resource.py
```

Windows 打包：

```powershell
cd desktop
.\.venv\Scripts\python.exe deploy.py
$env:APP_VERSION = '0.0.3'
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" CoCo-downloader.iss
```

Windows 编译使用本机 MSVC（Visual Studio C++ Build Tools），默认 4 个编译任务。
Nuitka 生成 `desktop/build/CoCo-downloader.dist` 后，使用 Inno Setup 6.5 或更高版本编译安装脚本。
安装工具：`winget install --id JRSoftware.InnoSetup -e --source winget`。
打开下列 `.iss` 文件并点击 Compile，或使用安装目录中的 `ISCC.exe` 编译。

安装包脚本位于：

```text
desktop/CoCo-downloader.iss
```

安装包输出到 `desktop/dist/`。简体中文语言文件随仓库提供，来源为
[Inno Setup 6.7.3 官方仓库](https://github.com/jrsoftware/issrc/blob/is-6_7_3/Files/Languages/Unofficial/ChineseSimplified.isl)。

## 音源说明

### 桌面端渠道实测（2026-10-11）

本次使用“晴天”和“稻香”分别搜索，每个渠道抽取前两条结果，校验音频文件头；
另对每个有可用音频的渠道至少一首歌曲执行静音 Qt 播放，确认播放进度实际推进。
这代表测试样本通过，不保证全部歌曲、全部音质或之后的服务可用性。

| 状态 | 渠道 | 实测结果 |
| --- | --- | --- |
| 样本通过 | 云音乐、QQ、酷狗、歌曲海、波点、QQMP3、煎饼1–4 | 两个关键词均返回歌曲与有效音频；Qt 实播通过 |
| 部分可用 | 咪咕 | 两个关键词的 Live 版本可用，原版仍返回服务错误；失败不再当作音频交给播放器 |
| 未恢复 | 力音 | 官网对“晴天、稻香、周杰伦”均返回空结果，没有可验证的播放样本 |

修复包括：煎饼访客会话初始化、波点主备解析、咪咕音频响应校验和音质回退、QQ 的 MP3 试听策略，以及 QQMP3 试听入口。
0.0.3 同步修复 Web：歌曲海改用当前搜索入口并保留播放会话，QQMP3 校验音频后自动切换备用接口。
桌面端使用 QFluentWidgets InfoBar 提示搜索、播放、下载和未捕获 Python 异常；Web 对应显示 Toast。
两端首页均说明第三方渠道稳定性限制。桌面异常日志位于应用配置目录的 `app.log`。
QQ 下载仍按高音质优先，试听使用 Qt5 可正常播放的 MP3 流。
原始结果保存在 `desktop/diagnostics/provider-status-2026-10-11.json`。
追加桌面复测见 `desktop/diagnostics/provider-followup-2026-10-11.json`；
Web 实际音频与封面验证见 `desktop/diagnostics/web-provider-status-2026-10-11.json`。

在 `desktop` 目录重新实测（会联网，静音播放片段）：

```powershell
.\.venv\Scripts\python.exe tools/probe_providers.py --playback
```

使用 `--query 稻香` 更换关键词，`--only qq bodian` 指定渠道，`--output build/results.json` 指定报告路径。

项目内聚合了多个第三方音乐搜索与解析来源。当前代码中包含的 provider 主要包括：

- 爱听
- 波点音乐
- 布谷音乐
- 歌曲宝
- 歌曲海
- 煎饼音乐系列（支持多平台解析）
- JOOX
- 米兔音乐
- LivePoo
- 咪咕音乐
- cenguigui解析（cenguigui API）
- 海棠解析（haitang API）
- XCVTS解析（xcvts/cyapi/vkeys API）
- QQMP3

不同音源的可用性、音质和返回字段会随第三方站点变化而变化。项目通过 provider 层隔离这些差异，尽量把上层 UI 和 API 保持稳定。

## 技术栈

### Web

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS
- Framer Motion / motion
- Lucide React
- Axios
- Cheerio

### Desktop

- Python
- PyQt5
- PyQt-Fluent-Widgets
- PyQt5-Frameless-Window
- Nuitka
- Inno Setup


## 致谢

桌面端界面基于 [QFluentWidgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) 构建。QFluentWidgets 为 PyQt/PySide 提供了 Fluent Design 风格的组件、设置卡片、导航、主题和图标体系，让桌面端能够以较低成本获得现代化的 Windows 应用体验。

感谢LINUXDO社区提供的帮助：https://linux.do/
感谢开源项目musicdl的部分接口支持： https://github.com/CharlesPikachu/musicdl

## 免责声明

1. 本项目仅供个人学习、技术研究与交流使用，严禁用于商业用途。
2. 项目不存储任何音乐文件，所有音乐内容均来自第三方公开API接口。
3. 项目中使用的所有音源接口均为第三方服务提供。
4. 第三方音源的可用性、数据准确性和版权状态不由本项目保证。
6. 请勿将本项目用于任何违反当地法律法规的行为，请尊重音乐版权。
7. 如本项目内容侵犯了您的权益，请通过 GitHub Issues 联系处理，我们会及时响应。
8. **下载的音乐文件仅供个人学习研究使用，，请支持正版音乐。**

## 许可证

本项目使用 MIT License。
