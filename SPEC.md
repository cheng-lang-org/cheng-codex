# SPEC: cheng-codex CLI 生产闭环 (完整功能)

## 目标 (Goals)
- 与 codex-rs/cli 保持 1:1 行为对齐 (含 MCP / MCP Server)。
- 固化 "需求 → SPEC/CONTRACT/ACCEPTANCE → TASK_MATRIX → 并行执行 → 门禁 → 报告" 的闭环工作流。
- 所有关键输出可机器验收 (JSON/文件落盘)，并可在 CI 里非交互运行。

## 非目标 (Non-goals)
- IDE/插件市场/调试器等 UI 生态。
- 超出 codex-rs/cli 现有行为的新增 CLI 命令。

## 范围 (In-scope Commands)
- exec, review, resume, fork
- login, logout
- app-server (generate-ts / generate-json-schema)
- app (macOS desktop launcher)
- debug (app-server send-message-v2)
- completion
- sandbox (macos/linux/windows)
- execpolicy check
- apply (task_id)
- cloud (exec/status/list/apply/diff)
- responses-api-proxy
- stdio-to-uds
- features list
- mcp / mcp-server

## 约束 (Constraints)
- 兼容配置与凭据路径: ~/.codex-cheng 优先, 不存在时回退 ~/.codex。
- prompt 读取规则、exit code、flag 冲突规则要与 codex-rs/cli 一致。
- 不新增/修改与 CODEX_SANDBOX_* 环境变量相关的实现细节。

## 输入 / 输出
- 输入: SPEC.md, CONTRACT.md, ACCEPTANCE.md, TASK_MATRIX.yaml
- 输出: build/closed-loop/report.{txt,json}

## 风险与对策
- OAuth 登录需要浏览器: 默认离线跳过, 需显式开启 ONLINE gate。
- 平台差异 (macOS/Linux/Windows): sandbox 命令需按平台分层验收。
- MCP OAuth 与 app-server 生态变化快: 固化本地协议与行为回归样例, 每次发布前执行闭环门禁以防回归。

## 发布 / 回滚
- 发布前必须通过 closed-loop 门禁。
- 回滚策略: 保留上一个可用的 codex-cheng 二进制与配置。
