---
name: epoint-presentation
description: 制作新点品牌可编辑 PPTX；Skill 自带 Logo、锁定色系、字体、三风格资料包和已校验结构页最小包。优先读取 Git 知识库，断网时使用本地已校验模板；正文可灵活编排。
metadata:
  version: "1.0.35"
---

# 新点企业演示文稿

## 从材料到逐页请求

1. 用 `scripts/run.py --read-material --input <原文件> --out <事实清单.json>` 读取 Word、Excel、PPTX、HTML、TXT 或 Markdown。PDF 和 PNG/JPEG 先用平台提取文字或 OCR，再加 `--extraction <平台提取.json>`。核对页码、表格、图片、公式缓存和识别疑点。除非用户指定视觉参考，旧演示稿只提供内容。详见[材料接入](references/material-ingestion.md)。
2. 每页写明结论、证据、项数和真实信息关系。普通列表由 Agent 提炼 `content.item_titles` 并保留 `content.items` 原文，再运行 `scripts/run.py --structure-content --request <草稿.json> --out <逐页请求.json> --report <整理报告.json>`。处理 `needs_agent_structure`；确需纯文字时填写 `keep_bullets_reason`。详见[材料结构化](references/content-structuring.md)。
3. 沿用用户已确认的整套风格。未指定时展示[三种风格预览](assets/style-previews/index.html)，让用户选择蓝色、红色或科技风；用户明确采用默认值时用蓝色。记录 `theme`、`style_family` 和任务 `font_profile`。科技风显式使用 `deep-blue-tech`。运行 `scripts/read_style_kit.py --theme <主题>` 并打开对应样图，按[风格选择](references/style-selection.md)执行。

## 选稿与试填

运行 `scripts/run.py --request <逐页请求.json> --out <预检报告.json> --plan-out <逐页计划.json>`。记录知识库来源、提交号和失败原因，后续入口使用同一 `--library`。显式离线加 `--offline`。依次使用已校验的远端快照、完整缓存和内置最小包；使用最小包时说明正文候选覆盖。完整性异常保留文件、来源和哈希证据，只使用验证通过的来源，无合格来源时阻断完整稿。[知识库数据契约](references/library-contract.md)

**结构页。** 完整稿按顺序使用已校验模板的封面、目录、章节页和封底。每页提供真实字段；目录项数可确定时与章节数一致。首个章节页实填后锁定 `layout_id`，后续章节沿用。遇到超限，先调整内容或整套章节版式；仍无合格模板则停止完整出稿。明确只做局部正文时设 `complete_deck:false`。[封面选择](references/cover-selection.md) · [目录长文案容量](references/directory-longcopy.md)

**正文。** 按关系、项数、数据与字段契约筛候选，读取选中组件的绑定、容量、媒体与审批状态。缺少输入事实、超出硬限制或会丢失原文时记录原因并试下一项。按请求上限实际试填后，仍不适配则选同风格的技能排版，再考虑带有理由和元素坐标的自由编排。只有成功提取并填充来源页才计入模板复用。详见[选版与试填](references/deck-planning.md)、[结构字段](references/structural-template-fields.md)、[正文托底排版](references/body-fallback-layouts.md)和[自由编排](references/free-composition.md)。

使用当前提交登记的能力，分别判断静态 PPTX、长文案、动效、配色和 HTML。草稿资产须显式允许并标记待审阅。三种风格遵循各自的页眉、锁定色、字体及 Logo 规则；任务字体缺失时暂停完整出稿。[品牌与颜色](references/theme-and-brand.md) · [离线品牌排版](references/offline-brand.md) · [动效](references/motion.md) · [HTML 输出](references/html-output.md)

## 从候选稿到交付

1. 每页 `content` 齐备、完整稿预检为 `ready` 时，在同一条预检命令加 `--execute-out <成稿.pptx>`。Windows 默认核实微软 PowerPoint 并做限时保存、重开、导出检查；失败时报告阻断。macOS/Linux 默认用原生后端生成候选。安装、升级或解释器问题见[运行环境与自检](references/cross-platform-runtime.md)，显式选择后端见[跨平台组装](references/cross-platform-assembly.md)。
2. 将结构页的 `layout_id`、`library_commit` 和 `source_stamp` 对应到最终页，核对组装关系、字体、Logo 可见尺寸和组件颜色。最终保存后执行 `scripts/audit_component_color_independence.py --input <成稿.pptx> --report <报告.json>`。逐页来源和质量检查见[来源与验收](references/source-and-qa.md)。
3. 生成候选时退出码为 3，报告为 `candidate_created`、`deliverable=false`。PowerPoint 实际打开并逐页导出、证据与最终文件哈希一致后，进入 `pending_visual_review`。打开逐页导出图，对照来源预览核对文字换行、遮挡、字体、Logo、颜色和页面顺序，再记录交付结论。详见[Office 后端与交付状态](references/office-delivery-safety.md)。
