---
name: epoint-presentation
description: 制作新点品牌可编辑 PPTX；Skill 自带 Logo、锁定色系、字体、三风格资料包和已校验结构页最小包。优先读取 Git 知识库，断网时使用本地已校验模板；正文可灵活编排。
metadata:
  version: "1.0.37"
---

# 新点企业演示文稿

## 从材料到逐页请求

默认在文案定型前读取原文并检索同主题知识库。Word 案例可用 `scripts/run.py --material <原文.docx> --theme <主题> --out <报告.json> --cover-gallery-out <封面候选.png>` 准备逐页请求和封面预览。入口从原文分段、辨认信息关系和项数，检索已校验组件的必需字段及容量，再编排文字。比较页必须能从材料区分两侧；流程所需的动作、对象和标签必须有原文依据。记录来源段落、初选清单和最终实际出稿。正文页的讲者备注保留相应 Word 原文。其他材料经事实提取后，在逐页草稿定型前同样核对候选结构与真实字段；已有逐页请求可直接预览。

1. 用 `scripts/run.py --read-material --input <原文件> --out <事实清单.json>` 读取 Word、Excel、PPTX、HTML、TXT 或 Markdown。PDF 和 PNG/JPEG 先用平台提取文字或 OCR，再加 `--extraction <平台提取.json>`。核对页码、表格、图片、公式缓存和识别疑点。除非用户指定视觉参考，旧演示稿只提供内容。详见[材料接入](references/material-ingestion.md)。
2. 依据事实清单形成逐页草稿，保留原段、来源、图片及真实信息关系。选版入口自动整理并列短标题、单项指标、多指标分组和层级，也可用 `scripts/run.py --structure-content --request <草稿.json> --out <逐页请求.json> --report <整理报告.json>` 单独核对整理结果。缺少可靠依据的内容按原结构进入选版或技能排版。详见[材料结构化](references/content-structuring.md)。
3. 沿用用户已确认的整套风格。未指定时展示[三种风格预览](assets/style-previews/index.html)，让用户选择蓝色、红色或科技风；用户明确采用默认值时用蓝色。记录 `theme`、`style_family` 和任务 `font_profile`。科技风显式使用 `deep-blue-tech`。运行 `scripts/read_style_kit.py --theme <主题>` 并打开对应样图，按[风格选择](references/style-selection.md)执行。

## 选稿与试填

在拟定正文文案前，每页用 `purpose` 写明读者需要看懂什么，并用 `information_relation` 表达原材料支持的关系，如比较、分组、流程或清单。保留事实和来源，按真实关系组织输入。先用 `--plan-out` 和 `--body-gallery-out` 查看整稿初选和带页码的原稿缩略图，再按适合的候选槽位调整文案。自动选版先试同主题知识库原稿。原稿试填未通过时，按内容关系、主题和容量选择技能排版规则。合格候选优先尝试整份正文里较少使用的版式家族；准确表达同类内容时可复用。用户要换一页时，展示该页的少量原稿预览与容量，选定后设置 `layout_id` 和 `layout_locked:true`，并核对其余页。详见[正文选版](references/deck-planning.md)。

运行 `scripts/run.py --request <逐页请求.json> --out <预检报告.json> --plan-out <逐页计划.json>`。记录知识库来源、提交号和失败原因，后续入口使用同一 `--library`。显式离线加 `--offline`。依次使用已校验的远端快照、完整缓存和内置最小包；使用最小包时说明正文候选覆盖。完整性异常保留文件、来源和哈希证据，只使用验证通过的来源，无合格来源时阻断完整稿。[知识库数据契约](references/library-contract.md)

**封面选择。** 整套风格确认后、完整 PPTX 首次出稿前，生成并展示当前风格的带编号封面缩略图，提供按图号选择和“自动选择”。用户选定后写入封面的 `layout_id`，按该版绑定准备真实文字。已有明确封面、用户未另选或预览无法展示时，沿用原请求。操作步骤见[出稿前选封面](references/cover-selection.md#出稿前选封面)。

**结构页。** 完整稿按顺序使用已校验模板的封面、目录、章节页和封底。每页提供真实字段；目录项数可确定时与章节数一致。首个章节页实填后锁定 `layout_id`，后续章节沿用。遇到超限，先调整内容或整套章节版式；仍无合格模板则停止完整出稿。明确只做局部正文时设 `complete_deck:false`。[目录长文案容量](references/directory-longcopy.md)

**正文。** 按关系、项数、数据与字段契约筛候选，读取选中组件的绑定、容量、媒体与审批状态。缺少输入事实、超出硬限制或会丢失原文时记录原因并试下一项。按请求上限实际试填后，仍不适配则选同风格的技能排版，再考虑带有理由和元素坐标的自由编排。只有成功提取并填充来源页才计入模板复用。详见[选版与试填](references/deck-planning.md)、[结构字段](references/structural-template-fields.md)、[正文托底排版](references/body-fallback-layouts.md)和[自由编排](references/free-composition.md)。

**原模板原子变体。** 按材料整理具体业务关系与 `content.items`。先看知识库同关系下原子的字段与可用项数，再提交正文，不必指定组件 ID。技能用实际数组长度精确选择单项原子或已验收变体。默认读取所选主题和项数的纯正文页，保留配对字段与原生分组，再生成页标题、Logo 和蓝红正文下划线。详见[原子变体输入和检索](references/deck-planning.md#原模板正文原子变体)。

使用当前提交登记的能力，分别判断静态 PPTX、长文案、动效、配色和 HTML。草稿资产须显式允许并标记待审阅。三种风格遵循各自的页眉、锁定色、字体及 Logo 规则；任务字体缺失时暂停完整出稿。[品牌与颜色](references/theme-and-brand.md) · [离线品牌排版](references/offline-brand.md) · [动效](references/motion.md) · [HTML 输出](references/html-output.md)

## 从候选稿到交付

蓝红通用页眉的分割线须显式关闭主题阴影。蓝红新绘正文和已登记组件共用可编辑画布和两层柔边弥散背景。技能排版规则覆盖并列卡片、条目与原文依据表格、并列指标、单一论点与两条依据、层级分组、指标与原文证据及四图、五图图集。对应变体沿用已确认的几何、样式与容量。整稿保存后按页核对分割线和背景图层，异常时阻止出稿。见[正文页眉与背景验收](references/source-and-qa.md#正文页眉与背景验收)。

1. 每页 `content` 齐备、完整稿预检为 `ready` 时，使用正式请求和同一知识库执行 `scripts/run.py --request <正式请求.json> --library <知识库路径> --out <出稿报告.json> --plan-out <选版.json> --execute-out <成稿.pptx>`。Windows 默认核实微软 PowerPoint 并做限时保存、重开、导出检查；失败时报告阻断。macOS/Linux 默认用原生后端生成候选。安装、升级或解释器问题见[运行环境与自检](references/cross-platform-runtime.md)，显式选择后端见[跨平台组装](references/cross-platform-assembly.md)。
2. 将结构页的 `layout_id`、`library_commit` 和 `source_stamp` 对应到最终页，核对组装关系、字体、Logo 可见尺寸和组件颜色。最终保存后执行 `scripts/audit_component_color_independence.py --input <成稿.pptx> --report <报告.json>`。逐页来源和质量检查见[来源与验收](references/source-and-qa.md)。
3. 生成候选时退出码为 3，报告为 `candidate_created`、`deliverable=false`。PowerPoint 实际打开并逐页导出、证据与最终文件哈希一致后，进入 `pending_visual_review`。打开逐页导出图，对照来源预览核对文字换行、遮挡、字体、Logo、颜色和页面顺序。色块上的标题、描述、编号和标签逐项按同主题原版对应位置核对字色。原子变体按父组件对应的文字角色和实际底色核对，再记录交付结论。[色块文字验收](references/source-and-qa.md#色块文字验收) · [Office 后端与交付状态](references/office-delivery-safety.md)
