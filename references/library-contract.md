# 知识库数据契约

`relation-taxonomy.json` 汇总已验收组件的统一信息关系与同义词；`catalog.json` 同时保留具体 `information_relation` 和统一 `canonical_relation`。部分已验收组件还登记经审定的中文 `search_label`，供内容目的与版式的轻量排序。普通正文检索在明确关系时可跨相容正文角色；指定具体结构名仍精确匹配。四类结构页角色不放宽。该索引不改变 `classification_status`，也不放宽主题、项数、字段容量和媒体门槛。

自动选稿池不在 Skill 中维护固定数量。每次从当前 Git commit 的 `catalog.json` 读取 `classification_status`、`pptx_support`、`status` 和主题范围；再读 `layout_rules.json.verified_counts`、字段容量及媒体状态。来源审计与对象颜色清单只供追溯，不等于能力验收。

组件的静态 PPTX、长文案、变项数、动效、HTML、扩展色系各有独立验收边界。`semantic-review.json` 与 `review/` 保存专项证据；不能因为某组件曾在代表样张中通过短文案测试，就推断其他能力已开放。

`knowledge-base.json` 唯一指向 GitHub 现有仓库的 `main` 分支。每次任务固定一次 Git commit；用 `scripts/library_location.py` 拉取后记录 commit，后续脚本传同一 checkout 的 `--library`。远端不可用时先复验完整缓存，必要时复验内置最小包。无法验证任何合格来源时停止完整出稿；记录错误和实际使用的提交。

来源 PPTX 保留原始母版，便于追溯与再次提取。填充器把选中页面、版式和母版中的主题色引用固化到单页组件；知识库 `themes/*.json` 中的中性色令牌与 Skill 本地 `brand-baseline.json` 对齐。装配与最终保存后检查组件颜色独立性。这个操作只固定原生配色，不等于已验收任意跨色系换色。

`catalog.json` 提供组件候选；`source-pages.json` 记录当前已入库的物理来源页；数量以本次 Git commit 为准。`sources/{blue,red,cover,tech}.pptx` 是四份可编辑原稿，`source_page` 标记页号；调用时只将选中的页提取成单页空版，避免每页重复存储整套母版与媒体。科技风使用 `style_family=deep-blue-tech` 与 `*-tech-*` 独立 ID；`select_cover.py` 和 `select_closing.py` 按角色分选，`plan_deck.py` 未显式指定风格时排除科技风。`bindings.json` 登记字段和对象，科技风另有递归 `shape-tree.json` 和初步 `item-groups.json`；`layout_rules.json` 登记**已验证**可用项数，`motion.json` 登记动效能力。`classification_status=visual_initial`、`html_support=not_implemented`、`cardinality_mode=fixed_until_validated` 按字面理解，不代表已支持。 目录若支持重排，读取当前组件的 `verified_counts`、`directory_item_fields`、`directory_long_copy_profile` 和字段长度约束；超过实测上限时换版或拆分目录。目录项测试不自动开放其他页面的长文案、HTML 或动效；各能力按对应组件当前记录独立判定。

科技风及其他风格的组件若有 `semantic-review.json`，读取其中的结构、适用关系和数据限制。各页面的可变项数只按当前 `layout_rules.json.verified_counts` 和执行器能力开放；内部原型须显式启用并逐页渲染审核，不能当作常规生产能力。

原模板的单项原子和各项数变体作为独立条目登记。其 `atomic_variant` 记录父组件 `parent_id`、固定项数 `count`、具体业务关系 `relation`、可用别名 `aliases` 及 `item_fields`、`page_fields`。变体与父组件共用结构家族，实际来源与各色绑定由子条目的常规来源字段确定。绑定以 `page.title`、`page.<字段>`、`items[i].<字段>` 指向单页原生形状。新增项数应按自身固定项数、源文件和字段容量单独验证，父条目的旧请求仍沿用原有规则。

蓝红配对只是顶层形状签名的首轮候选。使用红版时选 `red_source`，不能假设蓝版改色后与红稿完全等价。对缺图、媒体关系异常、未复核占位的页，先排除自动选版。

填充输入只使用本次用户材料。图表必须提供横轴数据、系列、数值、单位、时间和出处。普通图表的横轴使用 `categories`。登记为数值轴散点趋势的图表使用严格递增的数值数组 `x_values`，每个系列的 `values` 按坐标逐一对应，允许不等间距。模板示例文本和数据不得作为项目事实。未明确字段语义的页仅用于人工指定和审阅，自动规划只选已明确字段语义的组件。

技能自带的正文资产位于 assets/body-components，与原模板候选共用选版和试填流程。目录合并以组件 ID 去重，历史知识库中已登记的同名组件优先，便于复跑。内置资产按随包清单校验，离线最小包也能匹配。报告按「知识库模板」和「技能内置组件」分别计数，后者的来源印记使用 skill/ 路径前缀，并在装配校验记录资产来源提交和哈希。

## 长文案与组件专项证据

在当前知识库 `review/body-longcopy-capacity.json` 中按组件 ID 和 `semantic_path` 读取逐字段的 `recommended_max_cjk_chars`、`registered_min_max_chars` 与 `use_for_planning_cjk_chars`。内容规划以 `use_for_planning_cjk_chars` 为参考，实际填充仍须通过 `bindings.json` 的字符数、行数、行宽及 PowerPoint 边界验收。长正文自动选稿还须检查该组件的 `long_copy_review_status=长文案已验收`；`视觉复核未通过`、填充失败和标题溢出状态不可用于长正文自动选稿。参考值由蓝红科技版本逐字段测量，蓝红共用较小值；适用于中文单段自动换行。短标签与标题不能当作正文槽，`preparation_methods` 含 `source_fallback` 的组件还需正常填充路径复核。**结构复用新增的短文案跨业务试填只验证新字段映射，不会重置该组件既有的长文案验收；报告中分别记录结构映射验收、逐字段长文案验收和整稿视觉复核。**每次从固定知识库 commit 读取，不在 Skill 中复制组件数值。

需要修整版源页时按 `ready_source_by_theme` 取用；普通正文的字重按组件 `normal_body_weight` 执行，标题、指标和刻意强调文字不套用。目录重排、步骤次序、日期连续性、图表合计、百分比联动、Logo 替换与背景覆盖依各组件的规则和脚本检查；不得把某一页的例外复制给整套稿。新增或修订普通组件只更新知识库的目录、绑定、规则和审阅证据；若引入脚本尚不支持的新形状、图表、动效或输出格式，需先扩展执行器并通过专项验收。
正文绑定可以声明 `preserve_source_text_styles`。替换时逐段保留来源段落的格式，按目标文字中的短标签拆分行首标签与正文的样式。此规则适用于经过试填的多段正文槽位。
带 `month_axis_schedule` 规则的年度排期使用固定原生行和阶段。可编辑阶段标题来自 `items[].stages[].label`，每段的 `start_month`、`end_month` 为 1–12 的整数，包含首尾月。同一行按月升序，阶段之间可留空月。试填按月轴边界调整原生条带的位置和宽度。

带 `period_axis_schedule` 规则的分组排期保留原生任务行。阶段填写在 `items[].tasks[].stages[]`，单项目一行的 P194 使用 `items[].stages[]`。月轴用 `start_month`、`end_month`，季度轴用 `start_quarter`、`end_quarter`。区间包含首尾，同一行各段按升序排列且互不重叠。P192 的 `stages[].value` 同时决定百分比文字和已完成进度的位置。

带 `progress_rings` 规则的组件使用同一字段填充进度文字和原生进度环。P153 的 `items[].progress.value` 接受 0–100 的整数百分比，如 `65%`，`0%` 显示底轨，`100%` 显示完整圆环。

`shared_text_paths` 列出的语义字段可对应多个原生文字框。P245 每步只填写一个标题，左栏与右侧卡片同步更新，各自沿用原版字色和步骤编号。

纯正文的主题契约可带 `bindings_by_count`，为已验证项数登记各自的绑定路径及 SHA-256。容量预检和填充按同一项数读取绑定，复用该主题的纯正文对象与已验收的重排规则。现有可变项数组件保留原编号，采用另一种计数单位或槽位结构的固定版使用 `-body-fixed` 编号。
