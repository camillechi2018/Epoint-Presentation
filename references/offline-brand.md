# 知识库不可用时的内容页局部草稿

Skill 内置 `assets/brand/brand-baseline.json`、`assets/brand/logo-config.json`、SVG 与 PNG Logo。品牌配置只管蓝、红、深蓝科技风的颜色、字体、Logo 和固定品牌文案；`assets/layouts/offline-core.json` 独立管理 16:9 画布、Logo 锚点、轻量封面／封底位置及基础正文页面清单。这相当于“Brand 负责身份、Layout 负责页面结构”的分层；本地主题是新绘页面的离线底座，不是原稿对象换色清单。字体只记录名称，不分发字体文件；生成环境缺少指定字体时需改用配置的 fallback 并复核实际换行。

黑、白、浅灰、中灰、深灰与深底次要文字从所选主题的 `neutral` 读取，全部角色还须与 `brand-palette-lock.json` 完全一致。离线渲染器在写文件前检查配色锁，保存后固化页面及母版的颜色引用，再扫描 PPTX 页面、所用版式、母版和原生图表中的显式 RGB；出现锁定变量之外的颜色、变量与锁不一致或仍依赖母版颜色槽就拒绝交付。其他自由编排脚本也必须运行 `scripts/audit_new_drawn_palette.py --input <PPTX> --theme <主题> --report <报告>` 和 `scripts/audit_component_color_independence.py --input <PPTX> --report <报告>`，不因视觉上近似就允许新造灰阶。

离线模式默认采用**无阴影**的平面图形语言：卡片、流程框、指标框、分隔线、图标容器和标题装饰均不添加投影或内阴影。用留白、边框、色块和字号层级区分信息。`offline-core.json` 将 `visual_effects.shadows` 固定为 `none`；渲染脚本会清除新建图形继承的 PowerPoint 主题效果引用，并在保存后检查是否残留阴影。用户明确要求特定阴影效果时，再为该项目单独设计和验收，不改变此默认规则。

蓝红简约新绘正文的底层画布是可编辑矩形，其上按 `offline-core.json.content_atmosphere` 放置两枚可编辑的半透明椭圆，以 220 pt 柔化边缘。科技风新绘正文和登记为 `skill_tech` 的知识库纯正文共用 `assets/layouts/tech-content-header.pptx` 中的母版背景。该资产同时提供原生顶部装饰图形组。新绘科技正文使用居中白色标题、右上角白色 Logo 和 `#05193A` 卡片表面。PowerPoint 组装后核对公共背景图片及顶部图形。

Git 知识库获取或校验失败时，完整出稿停止。若用户只需正文局部草稿，可保留错误原因，按本次材料建立内容页计划，再用 `scripts/render_offline_brand.py` 输出基础可编辑 PPTX。命令：

```powershell
py -3 scripts/render_offline_brand.py --input <逐页计划.json> --out <结果.pptx> [--theme blue|red|deep-blue-tech]
```

输入结构：`{"theme":"blue|red|deep-blue-tech","complete_deck":false,"pages":[...]}`。每页须有 `title`；正文 `type` 可用 `bullets`、`cards`、`process`、`comparison`、`metrics` 与十种关系结构。`bullets` 支持 `balanced|compact|spacious|lead`，`metrics` 支持 `grid|hero|lead_support`，默认 `variant=auto`；主次变体用从 0 开始的 `featured_index`。`cover`、`directory`、`section`、`closing` 均被拒绝；完整演示稿也被拒绝，须恢复知识库后从源页制作。内容事实与数值只取用户材料，不把示例文本带入结果。脚本对超项数和长标题拒绝出稿，返回明确错误，需调整页计划再运行。

正文关系版式还支持 `assertion_evidence`、`priority_grid`、`evidence_matrix`、`problem_solution_outcome`、`layered_architecture`、`longform_metric`、`data_table`、`milestone_timeline`、`image_case`、`comparison_chart`。字段契约、适用关系和来源说明见[正文托底排版](body-fallback-layouts.md)。若未显式传 `type`，渲染器先识别 `categories+series` 的对比图，再识别 `series` 趋势图，随后识别主次、证据、问题、层级、长文、表格、时间轴和图文案例；均无时使用 `bullets`。数值、日期、图片和来源必须由材料提供，不能由版式规则补写。全部版式均遵守锁色、单 Logo、无阴影和可编辑性检查。

脚本会在每页放入本地 Logo：蓝色浅底使用原色，红色浅底使用黑色、深底使用白色，科技风深底使用白色；红色风格不允许蓝红彩色 Logo。文本与图形均可编辑，`.audit.json` 记录 `library_used=false`、`brand_profile`、`layout_profile`、自动补页、每页 Logo 数与可编辑文本对象数。交付前还须实际打开或渲染 PowerPoint，复核中文换行、Logo 避让、视觉节奏及事实。离线局部稿不宣称使用了模板封面、目录、章节页、封底、图库或源稿动效，状态保持 `draft_pending_review`。

如果用户指定必须使用某张远端模板页，报告中应说明该资产不可用并暂停该页出稿；知识库恢复后重新规划并选用原稿模板。不要悄悄使用不受校验的旧缓存冒充最新知识库。

## 正文页眉、画布与疏密

知识库模板保留已验收来源页。蓝红简约的新绘正文页仍使用 `assets/layouts/offline-core.json.content_header`：左上角 24 pt 标题、同起点的细分隔线、右上角 Logo。科技风的技能排版与自由编排正文页使用 `offline-core.json.tech_content_header` 和技能自带的 `assets/layouts/tech-content-header.pptx`：复用科技知识库 `content-tech-021` 的原生顶部图形组，28 pt 白色可编辑标题居中，白色 Logo 位于右上角，不画简约版横线。正文排版仍依原有内容关系规则。红色浅底 Logo 固定黑色，红色来源页已有灰色单色标识可保留。组装后分别核对三种风格的页眉和实际渲染。

正文编排读取 `assets/style-kits/composition-rules.json`。这份规则从已验收知识库正文页归纳并附来源 ID：先辨认并列、流程、对比、数据、时间线或主次关系，再按文字密度选择尺寸。2–3 项同权并列使用一行开放分栏；四项用 2×2，五项用 3＋2，六项用 3×2。卡片高度按最窄列预计正文行数计算；短内容不得用高空卡片撑满页面。短流程用开放轨道、长说明用阶段卡；四条短支撑信息可用上主下辅，其余用左主右辅；5–6 个里程碑用纵向时间线避免横排拥挤。短对比也要收紧内容区，不改变事实或字号下限。绘制器按相同规则计算实际几何，PowerPoint 导出后仍需检查视觉平衡。

基础正文的 `process` 流程卡片与 `comparison` 双列对比衬底使用直角矩形；绘制器和本地预览均按此规则生成。
