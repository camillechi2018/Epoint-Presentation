# HTML 输出边界

本文件讨论把已整理内容**输出**为 HTML。把用户提供的 `.html`／`.htm` 作为原始材料时，先按[多格式材料接入](material-ingestion.md)提取内容；源页面的 CSS 与脚本不会自动成为 PPT 模板。

HTML 需要复现同一信息关系，文字须可选择，图形／图表采用 DOM、SVG 或浏览器原生绘制。整页 PNG 截图只能作为预览，不能冒充可编辑或结构化 HTML 组件。要求离线资源、16:9 缩放、全屏、动效关闭后终态完整。

技能的统一入口目前对整稿 HTML 返回 `HTML_TEMPLATE_UNVERIFIED`。评估单页 HTML 时，核对知识库中该组件的 `html_support` 和实际执行能力。封面和流程单页的内部原型及复现命令见[维护仓库的专项诊断说明](https://github.com/camillechi2018/Epoint-Presentation-Maintenance#宿主校准与专项诊断)。

# 深蓝科技风状态

科技风 P001 的预览见知识库 `review/tech-cover-001-html-prototype.png`。该页 `html_support=prototype_requires_cross_format_review`，还需与 PPTX 对照和其他浏览器检查。
