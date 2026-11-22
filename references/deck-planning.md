# 整套内容规划与选版

先按[风格选择](style-selection.md)确定整套 `style_choice`、`theme` 与 `style_family`；用户已指定则直接沿用，未指定则展示预览并收集选择。随后确定每页结论、证据、信息关系、项数、字段字数、图片来源、图表数据和交付格式，再检索组件。信息关系优先于视觉喜好；数量超出已验收范围就换版或拆页。

开始选版前实际运行知识库解析并记录 commit；解析失败时记录错误并停止完整出稿；只允许制作不含封面、目录、章节页、封底的内容页局部草稿，不能因为看到了 Skill 本地预览图就标记 `library_used=true`。逐页计划记录候选数、淘汰理由和实现路径；整套报告分别统计原稿模板复用页、借用模板视觉语言重新编排页、自主编排页。模板复用页必须有知识库来源 ID 与最终成稿来源核验；其余两类不可计入模板匹配率。简约蓝红知识库旧记录未显式写 `style_family` 时，脚本将其视为 `legacy-blue-red`，但仍按 `theme=blue` 或 `theme=red` 严格筛色。

正文页无合格候选或候选达到试填上限仍无合格项时，使用 Skill 本地[正文托底排版](body-fallback-layouts.md)按信息关系选结构。基础结构 5 类、关系结构按当前托底配置读取；要点与指标在原 ID 下根据内容疏密和主次选择 `variant`。新增精确表格、日期里程碑、来源图片案例和分类数据对比。记录 `fallback_layout_id`、`variant` 与未复用原因。不得为了套用结构伪造数值、日期、来源、图片或辅助要点；字段不匹配时换结构或拆页。托底页保持 `library_used=false`，仍需与前后页面共同做视觉节奏复核。

若技能排版也不适用，按[自由编排协议](free-composition.md)让模型设计正文元素的位置与主次，并提交 `layout_assessment.reason`、`free_layout.rationale` 和元素几何。模型可自由安排信息，绘制器仍锁定整稿主题色、字体、Logo、安全边距与无阴影规则。逐页 `selection_label` 使用“知识库模板／技能排版／自由编排”；执行后以最终成功方式为准，不把计划候选误算为模板复用。自由编排输入缺失或验收失败时拆页、精简或报告阻断，不静默回退成通用要点页。

硬筛：状态、页面职责、信息关系、字段容量、图片／图表／表格槽、主题、输出格式、媒体完备性、动效能力。未分类组件不进入自动候选，仅能人工指定并记录理由。信息关系先查知识库 `relation-taxonomy.json`：原始 `information_relation` 是具体结构，`canonical_relation` 是统一类型，同义词仅在统一类型内扩展；指定具体结构名时仍精确匹配。封面、目录、章节、封底的角色严格一致。正文页如果提供可识别的信息关系，可在已验收的 `content`、`process`、`framework`、`timeline` 等正文角色中检索；未提供关系时仍按原角色，不做宽泛放行。若页面给出 `items`，规划器直接以数组长度验证项数；同时传 `needs.item_count` 时两者必须一致。旧版固定组件缺 `verified_counts` 时，只接受已验收、来源 `supported_counts=[source_count]` 的固定版，或 `semantic-review.json` 已标记静态 PPTX 验收的原生项数。普通结构组件按图形关系、字段映射、容量风险、原生项数及结构重复度排序；仅按专用语义选择的候选使用登记的语义特征。随机 seed 仅打散同分候选，不能越过硬筛。使用 `select_layout.py --verified-only --allow-draft --brief --purpose "页面目的" --item-count N` 查看短名单，不能把临时分类页当作可用组件。

按整套选版而非逐页随机。记录每页入选组件、候选数、淘汰原因、结构家族和 `diversity_gap`。同一组件的蓝红色系和不同项数不算新结构。对连续重复可换候选；没有合格候选时保留正确结构并明确重复原因。

## 原模板正文原子变体

从同一份材料提炼页面的具体业务关系，将每条成果、步骤、或完整的问题与措施配对分别放入 `content.items`。用 `scripts/select_layout.py --atomic-variants --verified-only --allow-draft --theme <主题> --relation <具体关系> --item-count <实际项数> --brief` 查看可用字段。省略 `--relation` 可浏览各家族的具体关系和同义词。

- 逐页请求使用 `content.type=atomic_items`、`page.information_relation` 及 `content.items`。关系取知识库 `atomic_variant.relation` 或其登记别名。也可用 `content.relation`。具体关系和字段都匹配时，普通含 `items` 的卡片、流程、对比等请求也能使用变体。
- 每项按 `atomic_variant.item_fields` 提供真实内容，页面标题写在逐页请求的 `title`。共用说明等 `page_fields` 填在 `content.page` 或 `content` 同名字段。实际数组长度决定选用哪一种项数，显式项数必须一致。跨项连接或上下配对由变体的原生分组保持。
- 无适合主题、项数或字段形态时，原子请求走可编辑要点托底。全部输入字段必须能完整放下，否则拆页或提供自由编排。源版仍可用原 ID 和生效绑定调用，已登记子 ID 也可明确指定。
- 计划、试填及装配记录均包含子 ID、父 ID、实际使用项数和来源，可核对候选到最终成稿的一致性。

当前多数提取组件为 `provisional`，不能以它作为无人值守生成全套 PPT 的依据。首批 14 页视觉初审条目标为 `visual_reviewed`；内部试排可显式传 `allow_draft=true`、`allow_visual_reviewed=true`，结果仍有 `manual_review_required=true`。先补字段语义、容量和实际渲染 QA，才能升为 `verified`。

蓝红补充稿的 `supp-*` 版式已完成 38 个主题变体的短文案静态 PPTX 验收，其中目录已扩展为变项数，可在 `allow_draft=true` 下参与自动选版。蓝红六款目录均支持 2–8 项自动重排，按信息关系、可读容量及相邻页多样性选择；科技风五款目录支持 2–6 项。章节、封面和封底均按源结构字段填充。红色独有封面与章节仅在 `theme=red` 时入选。补充版式共 28 条记录，和原蓝红内容池合计 94 条简约版静态草稿记录；同一家族不同色系不算新结构。目录项长文案按[目录项长文案容量](directory-longcopy.md)和 `directory_long_copy_profile` 及各字段 `max_chars`、`max_width_units` 选版；其他字段按已实填的安全上限；超限时换版或拆页。


## 四类结构页的强制来源

完整 PPTX／HTML 中，封面、目录、章节页、封底每页都要选择知识库对应角色的原稿组件，记录 `layout_id`、`library_commit`、`source_stamp`，并在最终 PPTX 逐页核验。不得用自由编排、离线基础稿或封面图库快照冒充。正文仍可选择 `source_template`、`guided_composition` 或 `free_composition`。目录项数以知识库 `verified_counts` 为准：蓝红简约六款目录支持 2–8 项，科技风五款支持 2–6 项。逐项输入 `items`，按所选版式的 `directory_item_fields` 提供 `title`、必要的 `subtitle` 等字段；脚本连同编号整体增减、自动重排。选择前比较内容关系、各版式长文案容量、密度与相邻页差异，不固定优先某一款。超过上限或字段超限时拆分目录或调整章节结构。知识库不可用或四类结构页无合格候选时，完整出稿应停止并报告原因。

## 候选试填与容量

默认最多实填 6 个候选，`max_template_trials` 可取 1–8。记录每次试填的容量证据、缺失字段、换行和换版原因。

对当前知识库候选读取 `bindings.json` 的字符数、行数和视觉宽度硬限制、`layout_rules.json` 的专用标题/编号规则，以及 `review/body-longcopy-capacity.json` 的已测正文建议值和对应预检政策。建议值只用于风险排序，不覆盖原生绑定硬限制；单段自动换行的建议值不能冒充手动换行验收。字段完整且容量宽裕的候选优先试填；仅宽度超限而原槽允许两行时可插入不改变文字的一次换行，并在试填记录中标注视觉复核。正文建议换行若标记 `mid_phrase_wrap_review`，须目视检查是否拆开词组；不自然时由当前 Agent 根据原文忠实调整句式后重试，或换版，不把程序填充成功直接视为视觉通过。超出硬限制或内容事实无法完整承载时换候选；最终以原生填充和 PowerPoint 渲染为准。逐候选记录容量文件与绑定哈希、风险、换行、试填结果及换版原因。

已登记 `body_component_contract` v2、v3 或 v4 的组件从知识库读取可编辑纯正文页和独立绑定。v2、v3 单页资产读取第 1 页。原模板原子变体使用 v4，先按实际项数选中记录，再从同主题正文包读取契约的 `asset_page` 及该页绑定。技能用逐页 `title` 生成公共页标题、Logo 和蓝红正文下划线，正文摘要、内部标题和可选字段按纯正文绑定填充。科技风 v3、v4 资产由技能恢复公共标题装饰和 `skill_tech` 母版背景。执行记录保留实际读取的资产、页码、哈希和框架。无兼容纯正文契约的组件沿用整页路径。PPTX 请求可以显式设置 `"body_header_pilot": false` 复测整页路径。

科技风按组件保留已核对的标题宽度、Logo 净空及装饰层顺序。P033 的历史字段 `bottom_conclusion` 是顶部页标题的输入别名，正文结论仍使用 `heading`。P055 的中央 `heading` 保留在正文绑定中，公共页眉使用单独的页面标题，省略原构图没有的顶部装饰。

选版诊断、`audit_matching.py --trial` 和正式试填使用同一份生效绑定。纯正文路径的必填项和容量来自 `body-*-bindings.json`。纯正文组件和技能简约正文在校验公共页眉标题时，使用所选页眉规格声明的单行宽度上限。匹配审计报告会记录实际试填的纯正文来源。候选召回、试填通过和整稿视觉通过分别计数。

四项并列接收 `cards` 的 `items[].title` 和 `items[].body`。已验证组件的 `matching_contract.title_body_fields` 登记页标题、按视觉阅读顺序排列的条目绑定，以及可用的页面辅助字段。科技风 `content-tech-048` 需要材料支持的 `conclusion`，可选 `summary`。蓝红 `content-blue-112` 按同一输入契约填四项，并清理来源业务图标。旧知识库仍可用原有字段适配器，显式提供原生 `texts` 时沿用原字段路径。已验收的蓝红六项长文案版接收六组标题与正文，保持六项并列关系并按生效绑定做容量校验。

图文、指标说明和单论点正文允许逐页提供 `body_match`。选版和试填读取该声明整理出的匹配字段，技能排版或自由编排时继续使用原 `content`。声明无法从原内容得到完整字段时，计划记录 `body_match_rejected` 并沿用原内容选版。

| `body_match.type` | 适用关系 | 原内容和声明 |
| --- | --- | --- |
| `image_gallery` | `image-text` | `free_composition` 依次放入图片及正下方对应图注，共 4 或 5 对。原图为可访问的 PNG 或 JPEG 绝对路径，试填按比例缩放并保留图注。 |
| `metric_evidence` | `metrics`、`data` | `bullets` 含 2、3、5 或 6 段原文。声明 `metric` 的 `label`、`value`、可选 `period` 均来自 `evidence_index` 指定的同一原段，索引从零开始。提供页面 `source_refs`。醒目位置引用原数值，全部原段照录，保留单位、时期、口径和限制。 |
| `single_focus` | `single-focus` | `bullets` 含三段原文。用 `thesis_index` 指定原文中承担论点的段落，索引从零开始。其余两段作为依据，保留两段之间的原顺序。 |
| `parallel_cards` | `parallel-points` | `bullets` 的每段对应一个有来源的 `item_titles` 短标题。按原顺序映射为 `cards`，逐条保留正文原句。知识库可按蓝红和科技风所登记的固定项数及容量选择长文版。 |
| `text_hierarchy` | `hierarchy` | `bullets` 的五段原文按 `groups:[{heading,indices}]` 分为三组，段数为 2、2、1。索引从零开始，完整覆盖并保持原顺序。版式用三层信息分组呈现背景、方法、目标等内容。 |
| `report_table` | `data-table` | `bullets` 的五段原始摘要对应五项 `row_labels`，`columns` 提供两个列名。原生表格用表头加五行呈现项目与原文，保留数值、公式表现及口径说明。数据仍使用原材料的来源和业务状态。 |

也可在有对应知识库组件的请求中直接提供同名 `content.type`。图库的 `items` 各项为 `image_path`、`caption`，指标说明、单论点、层级和表格沿用 `items` 原段及各自标注字段。并列正文的直接输入沿用 `cards`；也可继续用 `--structure-content` 把原列表与 `content.item_titles` 整理为卡片。

登记 `matching_contract.body_wrap_width_units` 的卡片在试填时按实测行宽加入换行，复核符号、数值与单位的相邻关系，避免常用闭合标点单独断到下一行。换行保留所有原字符，仍执行对应绑定的单段字数和行数上限。

封面、目录、章节、封底从当前固定知识库提交的 `review/structure-page-capacity.json` 读取主题、项数和逐字段已测容量；实际选版仍执行各组件 `bindings.json` 的字符、行数、行宽限制与 PowerPoint 渲染检查。目录按支持项数和每项标题／副标题分别校验；封面核对标题、副标题、署名与日期；章节页核对编号、标题和辅助文字，并保持整稿同一 `layout_id`；封底核对结束语与署名。已测字数只是对应压力样例的规划参考，不保证任意同长度文字均适配。封面、章节、封底的全部可编辑文字字段必须提供真实非空内容，缺失则改选版式或停止完整出稿，不保留来源示例文案。`visual_review=pending_final_deck_review` 的目录须在成稿中逐页目视复核。
