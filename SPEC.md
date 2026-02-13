# SPEC: cheng-codex CLI 生产闭环 (完整功能)

## 目标 (Goals)
- 与 codex-rs/cli 保持 1:1 行为对齐 (含 MCP / MCP Server)。
- 基线固定为 `/Users/lbcheng/codex-lbcheng` 的 `main@ebe359b8`，对齐范围扩展到 codex-rs 工作区公开语义。
- 固化 "需求 → SPEC/CONTRACT/ACCEPTANCE → TASK_MATRIX → 并行执行 → 门禁 → 报告" 的闭环工作流。
- 所有关键输出可机器验收 (JSON/文件落盘)，并可在 CI 里非交互运行。
- Plan mode 优先落地: `<proposed_plan>` 语义、`item/plan/delta` 事件、`request_user_input` 协议与 app-server schema 同步。
- parity 验收从“crate 映射”升级为“双清单”: crate 级 `parity_manifest` + 行为级 `behavior_manifest`。

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
- 对齐严格度为语义 1:1: 行为/副作用/错误类型/退出码一致，非关键空白与排版允许差异。
- `cheng-codex` 专有命令保留但标记实验/隐藏，不进入主帮助面。

## 输入 / 输出
- 输入: SPEC.md, CONTRACT.md, ACCEPTANCE.md, TASK_MATRIX.yaml
- 输出: build/closed-loop/report.{txt,json}
- 输出: tooling/parity/parity_manifest.yaml
- 输出: tooling/parity/behavior_manifest.yaml
- 输出: tooling/parity/coverage_table.md
- 输出: build/parity/report.{txt,json}

## 风险与对策
- OAuth 登录需要浏览器: 默认离线跳过, 需显式开启 ONLINE gate。
- 平台差异 (macOS/Linux/Windows): sandbox 命令需按平台分层验收。
- MCP OAuth 与 app-server 生态变化快: 固化本地协议与行为回归样例, 每次发布前执行闭环门禁以防回归。
- 基线回归定位成本高: 增加双实现差分框架 (`tooling/parity`) 直接对比 codex-rs 与 cheng-codex 结果。
- Plan mode 失败常见于“运行时已补齐但协议产物未同步”: 将 `app-server generate-ts/json-schema` 纳入 parity 场景并检查关键文件存在。

## 当前状态 (Locked Result)
1. Plan mode 运行时已落地: `src/app_server.cheng` 已实现 `<proposed_plan>` 解析、plan item started/completed、`item/plan/delta`。
2. Plan mode 协议面已落地: `protocol/` 已包含 `CollaborationMode/ModeKind/Settings`、`ToolRequestUserInput*`、`PlanDeltaNotification`、`TurnStartParams.collaborationMode`。
3. Parity 场景已接入: `tooling/parity/scenarios/app_server.yaml` 已覆盖 Plan mode 协议产物检查。
4. crate 映射已收口: `tooling/parity/parity_manifest.yaml` 当前为 `implemented=61, missing=0`。
5. 行为清单已收口: `tooling/parity/behavior_manifest.yaml` 当前为 `implemented=20, scenarized=20, verification_status=pending_execution`。
6. arg0/apply_patch 兼容已落地: `src/main.cheng` 支持 argv0 分发 (`apply_patch` / `applypatch` / `codex-linux-sandbox`)、隐藏参数 `--codex-run-as-apply-patch`、隐藏根命令 `apply_patch` / `applypatch`。
7. arg0 启动语义已落地: 启动阶段加载 `.env` 且过滤 `CODEX_*` 注入，创建 `CODEX_HOME/tmp/arg0` PATH helper 并进行 janitor 清理。
8. hooks 收口已落地: legacy notify (`agent-turn-complete`) 与 tool 生命周期 `after_tool_use` 内部事件都已接通 turn/call 上下文。
9. 本轮边界锁定为“代码重写 + parity 场景补齐”，编译/测试门禁留待下一轮执行验证。

## 发布 / 回滚
- 发布前必须通过离线 closed-loop 全部门禁 (含 parity)。
- 在线门禁 (login/exec smoke) 作为可选步骤单独出具 pass/skip 结果，不阻断离线发布结论。
- 回滚策略: 保留上一个可用的 codex-cheng 二进制与配置。
