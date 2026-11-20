# Epoint Presentation

把材料整理成符合新点品牌风格、可继续编辑的企业演示文稿。先选 **蓝色系、红色系或科技风格**，再由 Agent 梳理内容与信息关系，优先试用知识库组件；正文不适配时使用技能内的排版规则，仍保持同一套色彩、字体和 Logo。

**当前版本：1.0.34。** [查看技能入口](SKILL.md) · [查看 v1.0.34 发布版](https://github.com/camillechi2018/Epoint-Presentation/releases/tag/v1.0.34) · [查看完整模板知识库](https://github.com/camillechi2018/Epoint-Presentation-KnowledgeBase)

**配套知识库：v1.0.3。** [下载固定知识库快照](https://github.com/camillechi2018/Epoint-Presentation-KnowledgeBase/releases/tag/v1.0.3)。默认配置仍从知识库 `main` 获取更新；需要复现本次配套版本或离线部署时，使用该标签或发布页 ZIP，并通过本地知识库目录参数指定。技能安装包与完整知识库分开分发，普通用户不需要访问私有维护仓库。

统一入口默认按系统选择组装方式：Windows 使用 PowerPoint，macOS/Linux 使用 Python 原生组装。来源与内容审计保持一致，生成、预览和 PowerPoint 验收分别记录。v1.0.33 完成技能与私有维护工具拆分；Mac 三色各 20 页完整材料生成及内容保真实测通过，后续应用、逐页视觉与 DSL 项目由项目负责人接受为本次发布豁免，未作为已实测结果。该发布决定不改变每份成稿的验收规则。

## 先看三种风格

| 页面 | 蓝色系 · 蓝白简约 | 红色系 · 红白简约 | 科技风格 · 深蓝科技 |
| --- | --- | --- | --- |
| 封面 | ![蓝色系 P001 封面样张](assets/minimal-template-pack/source-previews/cover/P001.png) | ![红色系封面样张](assets/minimal-template-pack/source-previews/red-supplement/P006.png) | ![科技风格封面样张](assets/minimal-template-pack/source-previews/tech/P001.png) |
| 目录 | ![蓝色系目录预览](assets/style-previews/blue.png) | ![红色系目录预览](assets/style-previews/red.png) | ![科技风格目录预览](assets/minimal-template-pack/source-previews/tech/P006.png) |
| 正文 | ![蓝色系流程正文样张](assets/style-kits/blue/process-content-blue-060.png) | ![红色系对比正文样张](assets/style-kits/red/comparison-content-blue-133.png) | ![科技风格并列正文样张](assets/style-kits/deep-blue-tech/parallel-content-tech-021.png) |

图片取自技能包内的模板样张，文字是演示内容，实际出稿会按用户材料替换。预览用于选择整稿视觉方向，不表示最终一定使用图中的页面。实际封面、目录、章节页和封底从适配的知识库模板或已校验的本地最小包中选择。

## 正文组件预览

每种风格各选取 **16 张已验收正文组件**，拼成一张预览图，展示流程、对比、时间线、指标、表格等不同信息结构。蓝红两组对应相同组件的不同色系；实际选版仍以当次知识库的验收状态、字段和内容容量为准。图片中的文字与数字来自模板示例，不作为出稿事实。[查看组件 ID、来源与知识库提交](assets/style-previews/component-gallery-sources.json)。

### 蓝色系 · 蓝白简约

![蓝色系 16 张正文组件拼图](assets/style-previews/component-gallery-blue-16.png)

### 红色系 · 红白简约

![红色系 16 张正文组件拼图](assets/style-previews/component-gallery-red-16.png)

### 科技风格 · 深蓝科技

![科技风格 16 张正文组件拼图](assets/style-previews/component-gallery-tech-16.png)

## 简要说明

把文档、旧 PPT 或一段汇报思路整理成可编辑的 PPTX 初稿。用户可先看预览，再选择蓝色系、红色系或科技风格。版式从数百页源模板中提炼，按当前验收状态匹配可用组件；正文没有合适模板时，继续使用技能内的排版规则。默认加入企业 Logo，文字和适用的原生图形可在 PowerPoint 中继续修改；图表等对象的可编辑范围取决于所选组件。

## 使用优势

- **品牌规范：** 每页默认放置独立 Logo。浅色背景按风格使用适合的彩色或单色版本，深色背景使用白色版本；Logo 的品牌颜色不跟随正文主题色任意改变。
- **字体适配：** 按 Windows、macOS、Linux 的已安装字体为任务副本选择明确的中英文字体，并检查正文、表格、图表及母版。跨设备打开仍需复核字形和实际换行。
- **整稿协调：** 根据封面、目录、章节、流程、对比、数据等页面职责，以及内容关系和容量选择版式；封面配图优先匹配所选主题色。章节页在同一整稿中保持统一。
- **先规划再组装：** 先梳理每页讲什么、适合什么版式，再逐页填充和组装，方便发现内容与模板不匹配的问题。
- **运行前验证：** Windows 正式生成前核实微软 PowerPoint，并实际测试保存、关闭、重新打开和导出；仅有兼容 COM 注册不算后端可用。
- **交付前检查：** 对最终 PPTX 执行 PowerPoint 打开与逐页导出，记录对应文件的验证证据，再检查压字、溢出、图片裁切和 Logo 位置。生成成功、渲染成功与视觉验收分别记录；数据与案例以用户材料为准，不编造。

## 适用场景

- 周报、月度汇报、项目方案、售前材料等常规企业演示文稿。
- 从一句话思路生成 PPT 大纲；补充事实材料后，再制作可自行编辑的 PPTX。
- 将旧 PPT 作为内容来源重新编排，并切换到所选风格；具体版式和动画需按新稿复核。

最省事的试用方式：提供一份现有材料或旧 PPT，先看逐页计划是否符合你的表达思路，再检查生成的初稿。欢迎反馈实际案例、问题与建议。

## 快速开始

需要 Python 3.10 或更高版本。Windows 默认 PowerPoint 后端需要安装并通过检查的 **Microsoft PowerPoint**；macOS/Linux 默认使用 Python 原生组装，无需 Windows Office。Windows 也可显式选择原生组装。安装技能和 Python 依赖不会自动安装 Office。

将本仓库完整克隆到所用 Agent 的技能目录，确保 `SKILL.md`、`assets/`、`references/` 和 `scripts/` 都在同一目录。以 Codex 的用户技能目录为例：

```powershell
git clone https://github.com/camillechi2018/Epoint-Presentation.git "$HOME/.codex/skills/epoint-presentation"
cd "$HOME/.codex/skills/epoint-presentation"
powershell -File .\install.ps1
```

WorkBuddy 用户可使用其用户级技能目录；以下以 `$HOME/.workbuddy/skills` 为例，若平台配置了其他目录，替换为实际位置。

Windows PowerShell：

```powershell
git clone https://github.com/camillechi2018/Epoint-Presentation.git "$HOME/.workbuddy/skills/epoint-presentation"
cd "$HOME/.workbuddy/skills/epoint-presentation"
powershell -File .\install.ps1
```

macOS / Linux：

```sh
git clone https://github.com/camillechi2018/Epoint-Presentation.git "$HOME/.workbuddy/skills/epoint-presentation"
cd "$HOME/.workbuddy/skills/epoint-presentation"
sh ./install.sh
```

安装后新开 WorkBuddy 会话或刷新技能列表，再确认 `epoint-presentation` 已出现；技能文件安装成功与当前会话立即发现是两项检查。

升级时先检查技能目录是否有本地修改。若远端历史发生 `forced update`，不要直接 `git pull` 或覆盖有修改的目录；将旧副本移出 `skills/` 后重新克隆，再按需迁移个人配置。备份目录不要放在 Agent 的 `skills/` 下，避免被识别为另一项旧版技能。

如果已克隆技能但尚未安装依赖，在技能目录执行对应命令，安装隔离的运行环境：

| 系统 | 安装命令 |
| --- | --- |
| Windows | `powershell -File .\install.ps1` |
| macOS、Linux | `sh ./install.sh` |

安装器先复验并复用已登记的有效运行环境，避免 PATH 中的 Agent 内嵌 Python 触发重复安装；首次安装仍会选用可执行的 Python。需要指定解释器时，先设置 `EPOINT_PYTHON` 为 Python 3.10+ 的完整路径。断网安装可提供兼容的 `--wheelhouse <目录>`。跨系统安装成功不代表具备正式组装后端；各平台字体与预览边界见[跨系统安装与验证说明](references/cross-platform-runtime.md)。

材料入口直接读取 `.xlsx`、`.xls`、`.docx`、`.txt`、`.md`、`.pptx` 和 `.html`，安装后通过 `scripts/run.py --read-material` 使用。PDF 和 PNG/JPEG 的文字由当前 Agent 平台提取或 OCR，再以统一 JSON 交给材料入口；没有可用平台工具时明确报告，技能不会猜写。旧 PPT/HTML 仅作为内容来源，不自动复用原页面设计。[查看多格式材料接入方法](references/material-ingestion.md)。

在 Windows 的 Git Bash 中调用 Windows Python 时，输入与输出路径使用 Windows Python 能识别的绝对路径；临时目录由 Python `tempfile` 取得，避免把 Bash 的 `/tmp` 当成 Windows 路径。

然后在支持技能的 Agent 中附上材料，例如：

> 调用 epoint-presentation，用这份报告制作一套可编辑 PPTX。先给我蓝色系、红色系、科技风格的预览供选择；保留材料中的事实和数字。

如果已指定风格，可直接说“用蓝色系制作”，不需要再次选择。完整模板知识库由 [`knowledge-base.json`](knowledge-base.json) 指向独立 Git 仓库；首次使用远端模板需要能够访问 GitHub，离线时按校验结果使用本地缓存或最小模板包。

## 跨平台统一出稿

安装后使用 `python3 scripts/run.py --doctor --goal assemble --out doctor.json` 检查所选后端，再运行 `python3 scripts/run.py --request request.json --out report.json --execute-out candidate.pptx`。Windows 可使用 `python`。macOS/Linux 不再需要 `--native-experimental`，旧参数仍兼容；可用 `--assembly-backend auto|native|powerpoint` 指定后端。[查看平台差异及验收步骤](references/cross-platform-assembly.md)。

## PowerPoint 验证与生成状态

正式流程原本就使用 PowerPoint 打开和导出成稿；当前版本加强了后端识别、超时处理和验证证据检查。**交付只要求 PowerPoint 验证，不增加 WPS 验证步骤。** PowerPoint 打开、逐页导出通过后，仍须检查实际画面的文字、图形和排版。

Windows 安装后，可在技能目录运行诊断。下例使用 Python Launcher；没有 `py` 命令时，使用本机可运行的 Python 3.10+ 解释器启动同一个入口。`run.py` 会转调安装器已登记的运行环境。

```powershell
# 只检查环境，不启动 Office
py -3 scripts/run.py --doctor --out environment-check.json

# 核实 PowerPoint，并实际测试保存、重开和导出
py -3 scripts/run.py --doctor --goal assemble --office-smoke --out powerpoint-check.json
```

Windows PowerPoint 后端执行前自动进行上述 Office 操作测试。仅检测到程序时标记为未验证；操作失败则阻断该后端，不自动切换原生组装。macOS/Linux 默认走原生后端，不执行 Windows Office 冒烟。组装和最终打开／逐页导出分别默认限时 300 秒，失败保留诊断记录；只对确认属于本次任务的 Office 进程尝试清理。

生成结果按以下状态读取：

| 状态 | 含义与下一步 |
| --- | --- |
| `status=ready` | 预检可执行，不表示已生成或已验收。 |
| `status=candidate_created` | 候选 PPTX 已生成，继续查看 `delivery_status`。 |
| `delivery_status=pending_render` | 尚无有效导出结果，或导出失败，需处理渲染问题。 |
| `delivery_status=pending_powerpoint_validation` | 已有预览，但缺少 PowerPoint 对当前文件的验证。 |
| `delivery_status=pending_visual_review` | PowerPoint 打开及逐页导出通过，待人工或 Agent 实际视觉复核。 |
| `delivery_status=blocked` | 必要执行步骤失败，查看错误代码和任务记录。 |

PowerPoint 验证同时核对应用身份、页数、可解码的预览图片及最终文件 SHA-256；修改 PPTX 后，旧证据不能继续作为验证结果。自动生成的候选保持 `deliverable=false`，不会自动宣称整稿验收完成。

接入脚本时注意：规划成功退出码为 **0**；统一入口阻断为 **2**；候选生成但仍待验收为 **3**。退出码 3 不是重新生成的理由，应读取报告并继续验证或视觉复核。超时配置、错误记录及完整状态说明见 [Office 后端与交付状态](references/office-delivery-safety.md)。

## 它怎样组织一份 PPT

材料提取后，Agent 会先整理标题、正文、指标和真实信息关系，再匹配组件。并列条目可通过 `scripts/run.py --structure-content` 规范为“标题＋原文正文”，保留来源；未完成整理的页面会列出待办。[查看材料结构化流程](references/content-structuring.md)。

1. **理解材料。** 先提炼结论、证据、信息关系和页次，不把模板示例文字当成业务事实。
2. **锁定风格。** 整稿使用所选色系、字体、Logo 和页面规则；红色系使用单色 Logo。
3. **优先匹配知识库。** 按页面职责、信息关系、字段和容量试填组件。封面、目录、章节页、封底必须使用合格的模板；同一整稿的章节页保持同一版式。
4. **补足正文。** 没有合适组件时，先使用技能内的正文排版规则；仍不适用时，在所选风格约束下自由编排，并记录页面来源。
5. **检查成稿。** 核对来源、字体、颜色、Logo 和资源引用，验证最终文件能被 PowerPoint 打开并逐页导出，再检查实际文字边界、图片和排版；保留尚未完成的审阅状态。

详细规则见[选版与知识库契约](references/library-contract.md)、[正文托底排版](references/body-fallback-layouts.md)和[质量检查](references/source-and-qa.md)。

## 能力与边界

| 场景 | 当前处理方式 |
| --- | --- |
| 可编辑 PPTX | 保留可编辑文字和适用的原生图形；知识库组件按当前验收状态开放。 |
| 三种风格 | 技能自带颜色、字体、Logo 规则和预览；科技风格独立于简约蓝红版。 |
| 目录变项数 | 依据具体目录组件的已验证项数和文字容量选版。 |
| 知识库暂不可达 | 可检查已校验的本地结构页最小包；无合格结构页时停止完整出稿。仅制作正文局部草稿可使用离线品牌排版。 |
| Windows 正式组装 | 要求经身份核实及实际操作测试的微软 PowerPoint；WPS 的兼容注册不能代替它。 |
| 跨系统安装 | Windows、macOS、Linux 使用对应安装入口；依赖安装与正式组装后端分别检查。 |
| 跨平台原生组装 | macOS/Linux 默认启用，Windows 可指定 `--assembly-backend native`；继续执行来源、字体、颜色、媒体和 Logo 检查，生成候选后另行验收。 |
| 跨系统预览 | LibreOffice 导出只作为预览，不等于 PowerPoint 验证通过；macOS 当前需手动在 PowerPoint 中打开、导出和复核。 |
| 母版与版式 | 本轮未实施跨页去重优化，不承诺组装后自动合并相同母版或精简全部冗余版式。 |
| HTML 与动效 | 按具体组件的独立验收状态判断，不能从静态 PPTX 可用推断其已可用。 |

技能默认添加 Logo，并锁定主题变量；具体页面仍须用本次材料试填。模板和品牌素材目前标记为 `draft_pending_review`，这是审阅状态，不是正式品牌授权或交付质量保证。

## 仓库结构

```text
Epoint-Presentation/
├── SKILL.md                 Agent 的调用规则
├── knowledge-base.json      完整知识库的 Git 地址与本地回退配置
├── assets/
│   ├── brand/               Logo、颜色与字体变量
│   ├── style-kits/          蓝、红、科技三套风格资料
│   ├── style-previews/      风格和正文组件预览
│   ├── layouts/             正文托底排版规则
│   └── minimal-template-pack/  离线结构页最小包
├── references/              按任务读取的细则
├── scripts/                 选版、填充、组装及审计工具
└── install.ps1 / install.sh 跨系统运行环境安装入口
```

完整模板、组件目录和专项验收记录位于[独立知识库仓库](https://github.com/camillechi2018/Epoint-Presentation-KnowledgeBase)，不随本技能仓库重复分发。历史本地备份 `assets/minimal-template-pack.previous/` 不进入 Git 仓库。

## 授权状态

本仓库采用[专有授权声明](LICENSE)。代码及所含的新点品牌 Logo、原稿模板、图片等内容的授权由**国泰新点软件股份有限公司**管理。仓库公开可读不代表获得再分发或商用许可；对外复用前须确认具体授权范围，第三方素材还须遵守相应许可。

## 运行包与维护工具

本仓库保留出稿、安装、诊断和审计工具。知识库建设、批次整理、历史修复和发布资源制作已迁入私有维护仓库 `camillechi2018/Epoint-Presentation-Maintenance`，普通用户无需访问该仓库。现有 `scripts/run.py`、独立审计入口、Office worker 和本地最小包继续保留。

`distribution-files.json` 是安装压缩包的明确文件清单。维护发布器从固定 Git 提交读取文件，不打包开发测试、维护工具和本地缓存；最终包附 `skill-package-manifest.json`，记录来源提交及逐文件 SHA-256。回归测试、原稿颜色盘点与清单重建工具由维护仓库管理。


本轮工具分离不修改正文适配行为；macOS 实机、真实 PowerPoint 整稿和人工视觉验收仍需按目标环境完成，候选安装包不等于正式版本签收。
