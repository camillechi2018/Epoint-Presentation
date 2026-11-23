# Office 后端与交付状态

组装与应用验证分别记录，默认后端详见[跨平台组装与验证](cross-platform-assembly.md)。Windows 默认 PowerPoint 组装仅接受经核实的 Microsoft PowerPoint。检查 COM 注册对应的可执行文件、厂商信息以及实际启动应用的名称和路径。WPS 的兼容注册不能当作微软 PowerPoint；不自动切换原生后端。

Windows 完整出稿先识别 PowerPoint 并填充临时单页，再在组装前自动进行保存、关闭、重新打开、导出一页的实际操作测试。完整出稿在同一 PowerPoint 会话内完成测试、组装和最终验证。完成全部文件修整后，从磁盘重开最终成稿并逐页导出。macOS/Linux 默认原生组装不执行 Windows Office 操作。手动诊断可运行 `scripts/run.py --doctor --goal assemble --office-smoke --out <诊断.json>`。普通 doctor 不启动 Office，只把已识别应用标为未验证。

Office 检测限时 15 秒，冒烟限时 45 秒；正式组装和最终打开/逐页导出分别默认限时 300 秒。请求可用整数 `office_timeout_seconds` 调整为 1–3600 秒。独立 `assemble_deck.ps1` 支持 `-TimeoutSeconds`。失败记录保留在任务目录；超时返回 `OFFICE_OPERATION_TIMEOUT`。仅对登记为本次新建、且 PID、启动时间、路径仍吻合的 Office 进程尝试清理，不按进程名关闭 Office，不关闭已存在的用户会话。若 COM 启动阶段就阻塞、尚未取得进程归属，则保留未确认的进程并报告该限制。

交付只要求 Microsoft PowerPoint 实际打开与逐页导出验证，不设置 WPS 验证标识或目标软件选择。报告用 `powerpoint_validation_status` 表示这项检查；通过后进入视觉复核，不再等待 WPS。LibreOffice 等输出仅作为预览，不能自动标记 PowerPoint 验证通过。Windows 显式原生组装若检出合格微软 PowerPoint，使用它验证成稿；否则按可用预览器处理。历史请求中的 `target_application` 字段不再影响验收标准。

实际打开/导出的证据记录应用、版本、页数和最终文件 SHA-256。PowerPoint 证据写入 `powerpoint-validation.json`；图片须全部存在且能解码，文件改动后旧证据失效，不得重用旧预览目录。

生成请求输出 `status=candidate_created`，不再把预检的 `ready` 当作生成完成。所有自动生成的候选均为 `deliverable=false`：

| delivery_status | 含义 |
| --- | --- |
| pending_render | 无有效导出结果，或导出失败 |
| pending_powerpoint_validation | 有可用预览，但没有 PowerPoint 对当前文件的验证 |
| pending_visual_review | 当前文件已通过 PowerPoint 打开与逐页导出，仍待视觉复核 |
| blocked | 必要执行步骤失败 |

统一入口和独立 COM 组装入口以退出码 **3** 表示候选生成、尚待验收，退出码 **2** 表示统一入口阻断，规划成功为 **0**。集成方须读取 JSON 的 `delivery_status` 和 `deliverable`，不可把退出码 3 当作需要反复重生成的故障，也不能把候选宣布为最终验收通过。人工复核后的交付结论需另附真实复核记录，本轮不提供自动设置 `deliverable=true` 的开关。

母版、版式去重与来源标记规则本轮保持不变。
