# CONTRACT: cheng-codex CLI 对齐规范 (完整功能)

> 目标: 与 codex-rs/cli 行为一致, 覆盖全部 CLI 功能。

## 全局约定
- 统一命令名展示为 `codex` (即使实际二进制名为 codex-cheng)。
- 全局配置覆盖: `-c/--config <key=value>` (可重复)。
- 特性开关: `--enable <feature>` / `--disable <feature>` (可重复)。
- 退出码: 成功为 0; 失败为非 0 (保留具体错误提示)。
- 基线冻结: `codex-rs@ebe359b8` 作为对齐目标。
- 语义 1:1: 命令行为、参数冲突、退出码、协议字段、副作用一致；非关键排版差异可接受。
- 差分验收: 离线门禁必须包含 codex-rs vs cheng-codex 双实现场景对比 (`tooling/parity/run_parity.py`)。
- parity 覆盖契约: 同时维护 crate 级 `tooling/parity/parity_manifest.yaml` 与行为级 `tooling/parity/behavior_manifest.yaml`。

## arg0 / argv0 兼容
- `argv0` 分发必须与 codex-rs 对齐:
  - `apply_patch` / `applypatch` 作为 argv0 时直接进入 patch 执行路径，不进入 interactive/root parser。
  - `codex-linux-sandbox` 作为 argv0 时直接进入 `sandbox linux` 执行路径。
- `--codex-run-as-apply-patch` 作为隐藏入口保留，缺少 PATCH 参数时必须返回非 0，并输出:
  - `--codex-run-as-apply-patch requires a UTF-8 PATCH argument.`
- 隐藏根命令 `apply_patch` / `applypatch` 可达，并与 argv0/隐藏参数共享同一 patch 语义与退出码约束。
- 启动阶段加载 `.env` 时必须过滤所有 `CODEX_*` 键，避免注入覆盖运行时受保护环境。
- 启动阶段必须将 `CODEX_HOME/tmp/arg0` helper 目录 prepend 到 `PATH`，并生成 `apply_patch`/`applypatch`（Linux 额外 `codex-linux-sandbox`）helper 入口。

## hooks (legacy notify)
- 配置 `notify = ["<program>", "<arg1>", ...]` 时，agent turn 完成后必须触发一次通知命令。
- 行为与 codex-rs legacy notify 对齐:
  - 以 argv 方式执行配置命令，并在末尾追加一个 JSON 参数。
  - JSON payload 使用 kebab-case 字段，`type` 为 `agent-turn-complete`。
  - payload 字段至少包含: `thread-id`、`turn-id`、`cwd`、`input-messages`、`last-assistant-message`。
- `notify` 未配置时不得触发外部命令。
- tool 生命周期内部事件 `after_tool_use` 必须记录并保持字段语义稳定:
  - 顶层字段: `session_id`、`cwd`、`triggered_at`、`hook_event`
  - `hook_event` 字段至少包含: `event_type`、`turn_id`、`call_id`、`tool_name`、`tool_kind`、`tool_input`、`executed`、`success`、`duration_ms`、`mutating`、`sandbox`、`sandbox_policy`、`output_preview`

## exec
`codex exec [OPTIONS] [PROMPT]`

- `--image/-i <FILE>`: 可重复, 逗号分隔。
- `--model/-m <MODEL>`
- `--oss` / `--local-provider <lmstudio|ollama|ollama-chat>`
- `--sandbox/-s <workspace-write|read-only|...>`
- `--profile/-p <PROFILE>`
- `--full-auto`: 等价于低摩擦自动执行 (approval_policy=on-request, sandbox=workspace-write)。
- `--dangerously-bypass-approvals-and-sandbox` / `--yolo`: 跳过审批且不启 sandbox (与 --full-auto 互斥)。
- `--cd/-C <DIR>`
- `--add-dir <DIR>` (可重复)
- `--output-schema <FILE>`
- `--color <auto|always|never>`
- `--json` / `--experimental-json`
- `--output-last-message/-o <FILE>`
- `[PROMPT]`: 缺省或 `-` 时从 stdin 读取。

## review
`codex review [--uncommitted | --base <BRANCH> | --commit <SHA>] [--title <TITLE>] [PROMPT|-]`

- `--uncommitted` 与 `--base/--commit/--prompt` 互斥。
- `--base` 与 `--commit` 互斥。
- `--title` 仅在 `--commit` 时有效。
- `[PROMPT]` 省略或 `-` 时从 stdin 读取。

## resume
`codex resume [SESSION_ID] [--last] [--all]`

- `--last` 与 `SESSION_ID` 互斥。
- `--all`: 显示全部会话 (不做 cwd 过滤)。

## fork
`codex fork [SESSION_ID] [--last] [--all]`

- 语义与 resume 一致, 但创建分叉会话。

## login
`codex login [--with-api-key] [--device-auth] [status]`

- `--with-api-key`: 从 stdin 读取 API key。
- `--device-auth`: 设备码登录。
- 隐藏: `--experimental_issuer`, `--experimental_client-id`。
- `login status`: 输出当前登录方式与脱敏信息。
- 受 config 强制登录方式影响 (forced_login_method)。

## logout
`codex logout`

- 清理本地凭据并退出。

## app-server
`codex app-server [--analytics-default-enabled]`

子命令:
- `generate-ts --out <DIR> [--prettier <PRETTIER_BIN>]`
- `generate-json-schema --out <DIR>`

### Plan mode / collaboration mode (app-server v2)
- `turn/start` 支持 `collaborationMode`，并按 mode 覆盖 model/reasoning/developer instructions 语义。
- `collaborationMode/list` 返回至少 `plan` 与 `default` 预设。
- Plan mode 下:
  - `request_user_input` 走 `item/tool/requestUserInput` request/response 往返。
  - `update_plan` 返回错误: `update_plan is a TODO/checklist tool and is not allowed in Plan mode`。
  - 解析 `<proposed_plan>...</proposed_plan>`，发出 plan item 生命周期与 `item/plan/delta`。
- 协议产物必须包含:
  - `protocol/ServerRequest.ts` 中 `item/tool/requestUserInput`
  - `protocol/ServerNotification.ts` 中 `item/plan/delta`
  - `protocol/v2/TurnStartParams.ts` 中 `collaborationMode`
  - `protocol/v2/ThreadItem.ts` 中 `plan` variant

## app (macOS)
`codex app [PATH] [--download-url <URL>]`

- 在 macOS 上打开 Codex Desktop 并定位到工作区路径。
- 若本地未安装，输出下载链接并尝试打开下载 URL。

## debug
`codex debug app-server send-message-v2 <USER_MESSAGE>`

## completion
`codex completion --shell <bash|zsh|fish|elvish|powershell>`

## sandbox
`codex sandbox <macos|linux|windows> [--full-auto] [--log-denials] -- <CMD...>`

- `codex debug` 为 `sandbox` 的别名。
- macOS: `--log-denials` 仅适用于 seatbelt。
- Linux: landlock+seccomp。
- Windows: restricted token。

## execpolicy
`codex execpolicy check --rules <PATH>... [--pretty] <COMMAND...>`

- JSON 输出包含 `decision` 与 `matchedRules`。

## apply
`codex apply <TASK_ID>`

- 从 Codex Cloud 拉取 diff 并 `git apply`。

## cloud
`codex cloud [exec|status|list|apply|diff] ...`

- `exec --env <ENV_ID> [--attempts 1-4] [--branch <BRANCH>] [QUERY]`
- `status <TASK_ID>`
- `list [--env <ENV_ID>] [--limit 1-20] [--cursor <CURSOR>] [--json]`
- `apply <TASK_ID> [--attempt 1-4]`
- `diff <TASK_ID> [--attempt 1-4]`

## responses-api-proxy (internal)
`codex responses-api-proxy [--port <PORT>] [--server-info <FILE>] [--http-shutdown] [--upstream-url <URL>]`

- 从 stdin 读取 Authorization header 并转发到 /v1/responses。

## stdio-to-uds (internal)
`codex stdio-to-uds <SOCKET_PATH>`

## features
`codex features list`

- 输出特性名、阶段 (experimental/beta/stable/deprecated/removed) 与生效状态。

## mcp
`codex mcp [list|get|add|remove|login|logout] ...`

## mcp-server
`codex mcp-server`

## 兼容策略
- 全量路径使用 Cheng 原生实现。
- 不依赖 codex-rs 二进制委托。
- cheng 专有能力可保留，但必须标记实验/隐藏，不污染 `codex` 主帮助面。

## cheng-codex 专有: ship
`codex-cheng ship [options] [PROMPT]`

- 从需求生成 SPEC/CONTRACT/ACCEPTANCE → TASK_MATRIX → 并发执行 → 闭环门禁。
- 默认在完成后自动运行生产闭环门禁。
- `--no-closed-loop` / `--skip-closed-loop` 跳过闭环门禁。
- 在线门禁由环境变量 `CODEX_CHENG_ONLINE=1` 控制。
