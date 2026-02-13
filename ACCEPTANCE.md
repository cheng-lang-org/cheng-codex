# ACCEPTANCE: cheng-codex 生产闭环验收

> 分为离线门禁 (必过) 与在线门禁 (可选, 需要 API key/网络)。

## 本轮执行边界 (2026-02-13 锁定)
- 本轮仅交付“1:1 代码重写 + parity 场景补齐 + 文档同步”。
- 本轮不执行编译/测试/在线门禁，门禁执行作为下一轮单独收敛。
- 本轮静态完成标志:
  - `tooling/parity/behavior_manifest.yaml` 已落盘并覆盖关键行为域。
  - `tooling/parity/coverage_table.md` 已落盘并汇总 crate + behavior 双视角覆盖。
  - `tooling/parity/scenarios/` 已包含 arg0/hooks 行为场景定义。

## 离线门禁 (必须全绿)
1) 规格文件齐全
- SPEC.md / CONTRACT.md / ACCEPTANCE.md / TASK_MATRIX.yaml 存在且非空。

2) 构建可用
- `./build.sh` 成功产出 `build/codex-cheng`。

3) parity 差分门禁可用
- `python3 tooling/parity/generate_manifest.py --codex-rs-dir <path> --cheng-root .` 成功输出 `tooling/parity/parity_manifest.yaml`。
- `tooling/parity/parity_manifest.yaml` summary 必须满足：`implemented == total_crates` 且 `missing == 0`（当前基线为 61/61）。
- `tooling/parity/behavior_manifest.yaml` summary 必须满足：`implemented == total_behaviors` 且 `scenarized == total_behaviors`。
- `python3 tooling/parity/run_parity.py --codex-rs-dir <path> --cheng-root . --cheng-bin ./build/codex-cheng` 成功输出 `build/parity/report.{txt,json}`。
- parity 报告 summary: `fail == 0`。

4) execpolicy 可用
- `codex-cheng execpolicy check --rules <file> git push origin main` 返回 JSON。

5) completion 参数对齐
- `codex-cheng completion --shell bash` 成功输出脚本。

6) app-server 代码生成可用
- `codex-cheng app-server generate-ts --out <dir>` 产出 `.ts` 文件。
- `codex-cheng app-server generate-json-schema --out <dir>` 产出 `.json` 文件。
- Plan mode 协议关键文件必须存在:
  - TS: `CollaborationMode.ts`、`ModeKind.ts`、`v2/TurnStartParams.ts`、`v2/ThreadItem.ts`、`v2/PlanDeltaNotification.ts`、`v2/ToolRequestUserInput*.ts`
  - JSON: `v2/PlanDeltaNotification.json`、`ToolRequestUserInputParams.json`、`ToolRequestUserInputResponse.json`、`v2/TurnStartParams.json`

7) app 命令面可用
- `codex-cheng app --help` 返回 0。

8) debug 命令面可用
- `codex-cheng debug --help` 返回 0。

9) mcp 命令面可用
- `codex-cheng mcp add/list/get/remove` 在隔离 HOME 下可完成生命周期操作。
- `mcp list/get --json` 返回 transport/auth/status 等字段。

10) mcp-server 协议面可用
- 向 `codex-cheng mcp-server` 写入 initialize 请求，返回 JSON-RPC initialize response。

11) TUI 命令面可用 (纯 Cheng)
- `codex-cheng --help` 可正常返回，且源码门禁包含：
  - `src/interactive.cheng` 含 `interactiveMenuChoiceTui`
  - `src/exec_cmd.cheng` 含 `selectThreadIdTui`
  - `src/main.cheng` 默认无子命令进入 `runInteractiveWithOpts`

## 在线门禁 (需要显式开启)
12) 登录 + 执行 smoke
- `tooling/login_smoke.sh` 成功。
- `codex-cheng exec --json --output-last-message <file> "Say OK."` 输出非空。

## BDD 场景 (核心行为)
- Scenario: exec 读取 stdin
  - Given: PROMPT 为 `-`
  - When: `printf "Say OK." | codex-cheng exec --json -`
  - Then: exit code = 0 且 last-message 文件非空

- Scenario: review 参数互斥
  - Given: `--uncommitted` 与 `--base` 同时传入
  - When: 运行命令
  - Then: 退出码非 0 且提示冲突

- Scenario: resume/fork 选择
  - Given: `--last`
  - When: 运行命令
  - Then: 不要求 SESSION_ID

- Scenario: login status
  - Given: 已登录
  - When: `codex-cheng login status`
  - Then: 输出包含登录方式与脱敏信息

- Scenario: plan mode proposed plan streaming
  - Given: plan mode turn 返回 `<proposed_plan>...</proposed_plan>`
  - When: app-server 处理 turn
  - Then: 发出 `item/started(type=plan)`、`item/plan/delta`、`item/completed(type=plan)`，非 plan 文本走 `agentMessage` item

- Scenario: request_user_input in plan mode
  - Given: mode=plan 且模型发出 `request_user_input`
  - When: app-server 处理 tool call
  - Then: 发出 `item/tool/requestUserInput` request 并接受 response；若 options 为空则返回 `request_user_input requires non-empty options for every question`

- Scenario: arg0 apply_patch compat
  - Given: 使用隐藏入口 `--codex-run-as-apply-patch`
  - When: 缺少 PATCH 参数
  - Then: 退出码非 0 且输出 `--codex-run-as-apply-patch requires a UTF-8 PATCH argument.`

- Scenario: arg0 argv0 alias dispatch
  - Given: 以 `apply_patch` / `applypatch` 作为 argv0 调起进程
  - When: 从 stdin 输入 patch
  - Then: 不进入 interactive/root parser，直接执行 patch，退出码与基线一致

- Scenario: arg0 dotenv filtering
  - Given: `~/.codex/.env` 或 `~/.codex-cheng/.env` 含 `CODEX_HOME=...`
  - When: 运行命令读取配置 home
  - Then: 非 `CODEX_*` 键可生效，`CODEX_*` 键被过滤不注入

- Scenario: arg0 PATH helper lifecycle
  - Given: 启动时注入 `CODEX_HOME`
  - When: 子进程执行 `command -v apply_patch`（Linux 额外 `codex-linux-sandbox`）
  - Then: helper 可发现且位于 `CODEX_HOME/tmp/arg0` 语义路径

- Scenario: legacy notify hook payload
  - Given: config 设置 `notify = ["<program>", ...]`
  - When: 完成一次 agent turn
  - Then: 外部命令收到追加 JSON 参数，包含 `type=agent-turn-complete`、`thread-id`、`turn-id`、`cwd`、`input-messages`、`last-assistant-message`

- Scenario: after_tool_use hook payload
  - Given: 任一工具调用完成并写入 thread event
  - When: hook dispatcher 触发 `after_tool_use`
  - Then: payload 包含 `session_id/cwd/triggered_at/hook_event`，且 `hook_event.event_type=after_tool_use`

## 门禁工具
- `codex-cheng ship "<需求>"` (原生 Cheng 闭环入口)
- `--no-closed-loop` 可跳过闭环
- 设置 `CODEX_CHENG_ONLINE=1` 开启在线门禁
- `tooling/closed_loop.sh` 仅作为遗留脚本
- `tooling/closed_loop.sh --check parity` 可单独执行双实现差分门禁
