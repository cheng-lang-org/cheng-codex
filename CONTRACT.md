# CONTRACT: cheng-codex CLI 对齐规范 (完整功能)

> 目标: 与 codex-rs/cli 行为一致, 覆盖全部 CLI 功能。

## 全局约定
- 统一命令名展示为 `codex` (即使实际二进制名为 codex-cheng)。
- 全局配置覆盖: `-c/--config <key=value>` (可重复)。
- 特性开关: `--enable <feature>` / `--disable <feature>` (可重复)。
- 退出码: 成功为 0; 失败为非 0 (保留具体错误提示)。

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

## cheng-codex 专有: ship
`codex-cheng ship [options] [PROMPT]`

- 从需求生成 SPEC/CONTRACT/ACCEPTANCE → TASK_MATRIX → 并发执行 → 闭环门禁。
- 默认在完成后自动运行生产闭环门禁。
- `--no-closed-loop` / `--skip-closed-loop` 跳过闭环门禁。
- 在线门禁由环境变量 `CODEX_CHENG_ONLINE=1` 控制。
