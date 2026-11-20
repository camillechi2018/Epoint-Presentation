# 跨系统运行：S5 候选实现

当前默认组装规则见[跨平台组装与验证](cross-platform-assembly.md)：Windows 使用 PowerPoint，macOS/Linux 使用原生组装；旧 S2—S5 实验记录保留为历史证据，不作为必须传实验参数的现行要求。

本轮已完成发布字节校验、隔离依赖安装、独立自检、知识库缓存迁移和 S2/S3 代表性验收。S4 已完成 Windows/Linux 字体与渲染定点验证。用户确认 macOS 实机使用技能 `23e32c5` 与知识库 `58d4977` 测试，安装及效果通过；目标应用版本和逐页证据尚未归档，不单独宣称 Mac PowerPoint 正式签收。安装成功或自检通过不等于整稿交付通过。

## 安装与运行

需要可执行的 Python 3.10 或更高版本。Windows 在技能根目录执行 `powershell -File .\install.ps1`；macOS/Linux 执行 `sh ./install.sh`。启动器会实际运行候选 Python，不要求用户机械替换 python/python3。WorkBuddy 用户技能目录可为 `~/.workbuddy/skills/epoint-presentation`；安装后新开会话或刷新技能列表，再确认技能被发现。

安装器先核对 `runtime.json` 指向的已有虚拟环境、依赖版本、材料读取与模板包；合格时直接复用，即使 PATH 首位是 Agent 自带的其他 Python，也不新建环境。首次安装或旧环境失效时，在用户状态目录创建版本化虚拟环境；完成依赖和本地模板包校验后才原子更新 `runtime.json`。失败保留先前的活动解释器，也保留半成品目录供诊断，不自动删除个人文件。`VENV_CREATE_FAILED` 会返回脱敏后的原始子进程错误、选中的解释器和半成品路径；该代码本身不等于系统缺少 venv/ensurepip。安装器使用系统文件锁，崩溃退出后锁可自动释放。核心直接依赖记录于 `requirements-core.txt`，实际安装的直接和间接依赖版本记录在 `runtime.json`。不同 OS/架构仍需实测，不因依赖能安装就声明完整支持。

安装到指定位置：两个安装脚本都支持 `--state-dir <目录>`。后续设置 `EPOINT_STATE_DIR` 为同一目录，再用启动器选中的 Python 执行 `scripts/run.py`。该入口读取活动解释器，转调原有统一工作流并原样传递参数。旧入口仍可使用，但须自行指定正确解释器。

离线依赖安装支持 `--wheelhouse <目录>`，仅从提供的兼容 wheel 目录安装。模板离线包不包含 Python/Office/字体安装包；首次断网且没有兼容 wheels 时，应报告依赖安装失败，不伪报就绪。安装器不修改全局 Python 或系统代理。

离线 wheel 必须与实际选中的 Python 主次版本、操作系统和处理器架构一致。例如 Linux Python 3.12 不能复用仅含 `cp310` 的 Pillow/lxml wheel；此时安装器返回 `OFFLINE_WHEEL_INCOMPATIBLE`，应提供匹配的 wheelhouse 后重试。

回退时先验证记录中的 `previous_python` 存在，再使用该解释器直接调用统一入口；旧环境不会被安装器删除。本轮未提供自动卸载或一键回退命令。

若要绕过 PATH 中的 Agent 内嵌 Python 并使用指定解释器首次安装，可设置 `EPOINT_PYTHON` 后使用安装脚本。macOS 实例：`EPOINT_PYTHON="$HOME/.local/bin/python3" sh ./install.sh`；也可直接运行 `<指定的 Python 3.10+> scripts/install_runtime.py`。先检查安装输出中的 `candidate_python` 与 `detail`，不要仅凭 `VENV_CREATE_FAILED` 安装额外的系统组件。`scripts/run.py` 始终调用已登记的解释器。

## 自检

`<Python> scripts/run_presentation.py --doctor --out runtime-report.json`

也可直接执行 `<Python> scripts/doctor.py`。自检只用标准库启动；依赖导入放在有超时限制的子进程内，缺少 pptx/Pillow 时仍输出 JSON。`--library` 指定待校验知识库，默认校验安装包内最小模板包。

- `--goal inspect`：校验环境和模板包。可选依赖缺失会报告，但不阻断检查本身。
- `--goal fill`：另外要求核心 Python 包能导入；不代表已经完成实际单页或视觉验收。
- `--goal read`：要求 Excel/Word 只读提取所需的 openpyxl、xlrd 和 python-docx 能导入；不代表已完成内容规划或整稿。
- `--goal assemble`：检查当前系统选择的组装后端。macOS/Linux 默认检查原生模块与依赖；Windows 检测核实 PowerPoint 身份，普通检查仍标记 `untested`，加 `--office-smoke` 执行限时保存、重开及导出验证。PowerPoint 后端执行前自动运行该验证，详见 [Office 后端与交付状态](office-delivery-safety.md)。
- `--goal native-assemble`：保留的原生自检别名，与 `--goal assemble --assembly-backend native` 一致。通过只表示模块及必要依赖可加载，实际组装、渲染和应用视觉复核仍需按真实任务检查。

显式添加 `--deep` 时，在指定用户状态目录及缓存目录写入并读取临时文件，并用当前 Python 创建一页含中文可编辑文本的 PPTX，保存后重开核对。`--state-dir` 与 `EPOINT_CACHE_DIR` 可指定这些检查使用的目录；检查报告的 `deep_checks` 记录结果。此检查验证写入与 PPTX 基础往返，不代表已有模板的合并、目标 Office 打开、导出或视觉验收。

结果区分 available、unavailable、untested，stdout 仅输出 ASCII 安全的机器 JSON；报告文件为 UTF-8。基础自检不会启动 Office、自动上传材料、安装依赖或调整网络设置。S4 起 `--font-profile windows|macos|linux` 探测任务字体是否安装；`fill`/`assemble` 缺字体现为 `FONT_PROFILE_RESOURCE_MISSING`。macOS 优先通过 CoreText 查询已注册字体族，覆盖系统动态字体资产；仅在系统 API 查询失败时使用字体枚举和文件路径兜底，报告 `fonts.detection` 说明检测路径。字体文件存在、资源探测通过均不证明字体在目标渲染器内的字形、换行或版面正确；应用打开与导出仍需校准。`PingFang SC`／`Helvetica Neue` 是本技能的 macOS 排版配置，不表示两者都是 macOS 系统界面的默认字体。

## 分发与校验

源码文本采用 `.gitattributes` 定义的 LF 规范；Windows PowerShell 脚本保留 UTF-8 BOM；二进制不转换。发布字节规范化与清单生成已迁至私有维护仓库，用户端仅校验，不执行清单重写。

发布者在隔离工作区审核来源、规范化文本并验证知识库清单后，提交拟分发文件。安装包制作器从固定提交及 `distribution-files.json` 明确清单读取内容，不吸收未跟踪或未提交文件；最终包附来源提交和逐文件哈希。维护仓库的清单重建命令不属于用户出稿流程。

运行时校验只计算原始文件字节哈希，不自动修复、改写或忽略换行差异。跨平台修复应发布新版本，不覆盖旧标签；仓库 `main` 与已发布标签是不同快照。

## 知识库缓存与升级

知识库默认缓存位于用户状态目录下的 `cache/libraries/<来源标识>/`，可以通过 `EPOINT_CACHE_DIR` 指定其他可写目录。来源标识区分仓库 URL、分支、库内路径和知识库版本；不依赖当前工作目录。状态目录由 `EPOINT_STATE_DIR` 或系统用户目录决定。

在线解析先查询远端提交，再下载到候选目录；完整校验原始文件哈希、来源及提交后，将目录保存为 `snapshots/<commit>/`，原子更新 `last-good.json`。下载采用包含当前提交全部文件的浅克隆，不使用延迟下载 blob 的部分克隆。并发更新使用系统文件锁；进程异常退出会释放锁，不以锁文件存在判断占用。

更新失败保留上次有效快照及记录。显式 `--offline` 不连接远端；优先复验当前完整快照，损坏时尝试记录中的上一有效快照，然后尝试旧版完整缓存，最后使用技能自带最小包。每次回退保留原因，不把坏缓存标为有效。`knowledge-base.json` 中带 `legacy_` 前缀的相对路径仅用于只读兼容旧缓存；新下载只写入用户状态目录，不在 WorkBuddy 技能目录旁创建知识库或缓存。

在线成功不再重建安装目录内的最小包；新的完整快照本身支持离线调用。最小包仅在发布构建时更新，继续作为首次离线的补救措施，不扩充模板数量。旧快照当前不会自动删除，避免删除正在被其他出稿任务引用的版本。

错误区分代理 `git_proxy`、TLS `git_tls`、认证权限 `git_permission`、网络 `git_network`、超时 `git_timeout`、Git 缺失及清单/缓存异常；不改变系统代理或关闭证书校验。在线失败不代表所有离线能力不可用，报告以实际采用的来源和提交为准。

## 本轮边界

已抽取公共路径与进程模块并用于新自检和安装器；知识库更新已迁入用户缓存，缓存子流程完成 Windows 与 WSL Linux 的更新、回退、并发和故障验证。Linux 已实测只读安装目录，Windows 已检查安装文件无变更；尚未据此宣称完整出稿工作流均支持只读安装。离线依赖安装矩阵、失败运行环境升级、深度环境自检、原生模板组装和系统字体配置仍按计划推进。macOS 仍待用户实机验证。

## S2 原生组装试点

安装后用 `<Python> scripts/run.py --read-material --input <材料> --out <提取.json>` 调用已登记解释器中的材料入口，避免误用 Agent 自带 Python。`.xlsx` 逐个有效单元格读取，保留合并区域、公式表达式和缓存值状态；`.xls` 保留有效行和合并区域，但 BIFF 读取器不能可靠恢复公式来源或内嵌图片；`.docx` 保留正文段落、表格、媒体引用与文件清单。`.txt`、`.md` 按行读取；`.pptx` 读取逐页可编辑文字、表格与图片引用；`.html`／`.htm` 读取源码文本与图片地址，不执行浏览器脚本。PDF 与 PNG/JPEG 的文字通过当前 Agent 平台工具提取，再按[多格式材料接入](material-ingestion.md)交接。提取结果是事实清单，不自动生成逐页计划，也不意味着所有内容已入稿；缺失公式缓存、图片内文字和 OCR 错漏不得猜测。

`scripts/assemble_native.py --experimental --pages <已填充单页1.pptx> <已填充单页2.pptx> ... --out <输出.pptx>` 是至少接收两张单页的隔离试点；原有 `--first/--second` 两页参数仍可用。它复制源部件及关系，只登记实际使用的母版，并统一备注母版及重新分配复制版式 ID。Linux 原生组装的蓝、红、科技风目录＋章节＋代表正文三页包，以及蓝色原生图表/表格和科技风流程/对比/指标混合正文包，均由 Windows PowerPoint 16.0 打开导出；已比对的正文页与单页源稿像素一致。蓝色 8/16/24 页重复组件压力包亦能打开导出。S5 的显式实验整稿入口复用这一组装器，保留正式完整稿的来源与交付门禁。

S2 原生组装专项审计的运行方法见[维护仓库的专项诊断说明](https://github.com/camillechi2018/Epoint-Presentation-Maintenance#宿主校准与专项诊断)。正式出稿的包关系及来源检查由统一入口执行。静态检查通过后，按目标 Office 核对实际打开、逐页导出和视觉效果。

S2 代表性签收另覆盖四图表与表格混合包、含 PNG/SVG/WDP 和嵌入字体的封面包，以及删除图表工作簿、SVG 后必拒绝的负例。样本在 Windows PowerPoint 16.0 打开导出，组装页与源单页逐像素相同。该结论只覆盖已测对象组合；`content-blue-196` 的单页文字叠压另行修复，未分类来源图片的图文页不进入正例。原生入口继续标记实验性，S3 完成正式入口、可信来源与交付门禁后才可用于正式整稿。

## S3 必要交付门槛

正式完整稿要求封面、目录、至少一张章节页和封底，且章节使用同一 `layout_id`。目录条目数可读取时，必须与章节页数一致；目录四项只生成一张章节页会报 `DIRECTORY_SECTION_COUNT_MISMATCH`。组装前 `delivery_gate.py` 复验固定知识库清单、源文件哈希、组件来源页、填充单页哈希与标记；组装后检查包关系、页数和最终页关联。正常样本及缺目录、章节混用、伪造来源、坏包反例各跑一次即可，不重新验收知识库全部组件。`run_presentation.py` 的 `status=ready` 只表示候选生成；成稿另报告 `delivery_status`，未做人工视觉复核时保持 `pending_visual_review`。Mac PowerPoint 与真实材料三风格整稿仍待验证。

## S4 字体配置与渲染校准

完整出稿请求可设置 `font_profile` 为 `windows`、`macos` 或 `linux`。省略时按当前系统选择；整个任务的填充、技能新绘、组装归一、字体审计和报告使用同一配置。当前配置为 Windows 微软雅黑／Arial、macOS 苹方／Helvetica Neue、Linux Noto Sans CJK SC／Noto Sans。缺少字体时完整出稿阻断并指出缺失字体，不静默回退。不同系统原生字体须分别生成和验收 PPTX，不能期待同一文件自动切换字体。源知识库不改写；仅处理任务副本。对已通过 Windows 字体容量验收的组件，换字体后仍须复核窄槽、表格及接近容量上限的文案。

用 `scripts/font_profile.py --profile <配置> --out <诊断.json>` 检查字体资源。在 Windows 上可运行 `scripts/run.py --doctor --goal assemble --office-smoke --out <诊断.json>`，验证 PowerPoint 能保存、重新打开并导出。

使用已知正常的 PPTX 排查宿主或字体配置时，按[维护仓库的渲染校准说明](https://github.com/camillechi2018/Epoint-Presentation-Maintenance#宿主校准与专项诊断)运行样本校准工具。按导出图核对文字边界、缺字、重叠、Logo、背景、图表和透明素材。需要验收 PowerPoint 效果时，用 PowerPoint 实际打开和导出。

Linux 任务副本中，LibreOffice 不能正确显示的可编辑文字渐变会转换成其最亮可见色标的纯色；转换次数写入 `font_normalization.gradient_text_fallbacks`。此适配只处理 Linux 输出，不修改知识库原稿，也不改变 Windows/Mac 文件。其视觉颜色仍须与目标应用逐页复核；渐变效果本身不会在 Linux 版本中保留。

Mac 实机已在字体检测修复后完成安装和 `doctor --goal fill`，早期 22 页候选 PPTX 可由 Keynote 打开；随后用户确认最新技能 `23e32c5` 与知识库 `58d4977` 的 macOS 测试效果通过。安装适配和代表性出稿可按用户反馈记为通过。目标应用、版本和逐页导出证据尚未归档时，不将该反馈扩大为 PowerPoint 全量视觉验收。复测应使用安装器记录的解释器，不手写运行时记录或改用系统默认 Python 绕过门禁。

旧 Mac 候选文件为 96.84 MiB，压缩后的嵌入字体部件占 78.86 MiB，是体积的主要来源。知识库 `sources/cover.pptx` 已移除旧字体部件并更新哈希；任务副本归一字体时也会清除旧嵌入，避免历史缓存继续放大成稿。旧 22 页稿的副本实测降至 17.98 MiB，字体审计 195 个文本运行项通过，在本机 Windows PowerPoint 导出的 22 页逐像素一致。此结果不替代 Mac 目标应用复核，仍须检查字形、换行、柔边和可编辑性。旧源稿 SHA-256 保留在知识库 `source-manifest.json`，运行时不得绕过当前清单校验。

## S5 原生整稿入口及当前默认选择

S5 最初由 `--native-experimental` 显式启用，当前统一入口已默认在 macOS/Linux 选择该原生组装流程，旧参数继续兼容。使用 `scripts/run.py --request <请求.json> --library <知识库> --out <报告.json> --execute-out <成稿.pptx>` 即可，不再因缺少 Windows PowerPoint 阻断候选生成。

报告使用 `assembly_backend=native`；Windows 默认仍为 `powerpoint`，失败不静默切换。候选筛选、真实字段试填、结构与来源校验、字体归一及最终审计继续执行。Linux LibreOffice 预览成功为 `pending_powerpoint_validation`；macOS 自动渲染仍为 `pending_manual`，交付状态为 `pending_render`，须在 Mac PowerPoint 打开、导出并另记复核结果。没有渲染器或渲染失败时保留已通过静态检查的候选，不标记最终交付。

支持入口不等于所有平台和所有材料已验收；新候选的真实运行范围、Mac 实机反馈和未完成项须单独记录。完整参数与步骤见[跨平台组装与验证](cross-platform-assembly.md)。
