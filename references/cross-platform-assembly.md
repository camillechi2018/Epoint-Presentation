# 跨平台组装与验证

统一入口按系统选择组装后端，生成 PPTX 不再要求 macOS 或 Linux 安装 Windows PowerPoint。此变更属于开发候选，平台实测范围以配套验证记录为准。

| 系统 | 默认组装 | 预览与应用验证 |
| --- | --- | --- |
| Windows | Microsoft PowerPoint | 保留身份检查、限时冒烟、实际重开和逐页导出 |
| macOS | Python 原生组装 | 无 Office 也可生成；需用 Mac PowerPoint 打开、逐页导出并复核 |
| Linux | Python 原生组装 | 检测到 LibreOffice 与 pdftoppm 时生成预览；未安装也保留已通过静态检查的候选 |

安装依赖后，三个系统使用同一组命令：

```sh
python3 scripts/run.py --doctor --goal assemble --out doctor.json
python3 scripts/run.py --request request.json --out report.json --plan-out plan.json --execute-out candidate.pptx
```

Windows 可将 `python3` 替换为本机可用的 `python`。统一入口会转调安装器登记的解释器。任务字体省略时按系统选择：Windows 微软雅黑/Arial、macOS 苹方/Helvetica Neue、Linux Noto Sans CJK SC/Noto Sans；缺少必需字体时阻断，不能用静默替换规避。

`--assembly-backend auto|native|powerpoint` 可指定组装方式，默认 `auto`。Windows 无 Office 时可明确选择 `native`；默认 PowerPoint 失败不自动切换。macOS/Linux 明确要求 `powerpoint` 时仍报告该 Windows 自动化后端不可用，不把选择忽略。

旧 `--native-experimental` 仍兼容，相当于 `--assembly-backend native`；与 `--assembly-backend powerpoint` 同时使用时报参数冲突。报告统一使用 `assembly_backend=native` 或 `powerpoint`，集成方应读取该字段的新取值。`--goal native-assemble` 保留为原生自检别名。原生自检仅检查模块与依赖，不能代替真实出稿。

`--office-smoke` 只用于 Windows PowerPoint 后端；原生后端不忽略此参数，而是要求明确选择合适的后端。三个系统执行相同的知识库完整性、来源、字段容量、结构页、章节一致性、字体、颜色、Logo、媒体及最终包检查。

## 状态处理

- 预检可执行为 `ready` / 退出码 0。
- PPTX 已生成并通过静态检查为 `candidate_created` / 退出码 3。不要将 3 当作失败反复重生成。
- 无渲染器、Mac 等待手动导出或渲染失败为 `pending_render`，保留候选及具体原因。
- Linux LibreOffice 预览成功为 `pending_powerpoint_validation`，不冒充 PowerPoint 验证。
- 当前文件经 PowerPoint 实际打开并完整导出，且哈希与图片证据通过，才进入 `pending_visual_review`。
- 必要的生成步骤失败为 `blocked` / 退出码 2。

所有自动候选保持 `deliverable=false`。macOS/Linux 能生成文件，不代表该文件的字体、断行和效果已经在目标应用验收；不同平台需要各自出稿和记录。Mac 手工打开与导出应另附应用版本、PPTX 哈希、页数与逐页复核记录，不手改自动报告。本轮不提供自动伪造验收的开关，也不安装 Office 或 LibreOffice。
