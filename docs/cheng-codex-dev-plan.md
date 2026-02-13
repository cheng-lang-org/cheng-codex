# Cheng Codex 开发文档

## 目标与范围

- 用 Cheng 语言重写 `codex` CLI（替代 Rust 版 `codex-rs/cli`）
- Cheng IDE 内实现 Codex 的完整可视化体验（侧边栏/面板/任务流）
- 对齐 VSCode Codex 插件（版本 0.4.56）
- 覆盖 CLI、app-server、上下文采集、diff/patch、配置/登录、云端任务

## 对齐基准（VSCode Codex 插件）

- 侧边栏 Codex 面板（聊天/任务/线程列表）
- 新建 Codex Agent 面板（独立任务视图）
- 编辑器右键 “Add to Codex Thread”
- TODO CodeLens “Implement with Codex”
- Chat Sessions：openai-codex 会话入口
- 配置项：CLI 路径、启动聚焦、语言偏好、TODO CodeLens 开关、Windows WSL 模式
- URI 打开与目标跳转
- ChatGPT 桌面应用桥接（可选）

## 兼容边界

- CLI 命令名与主参数对齐（不强制完全一致的提示文本）
- app-server JSON-RPC 方法名与事件名对齐
- 允许阶段性返回简化字段，但保持字段类型不变
- IDE 仅依赖 Cheng CLI，不再连接或依赖 Rust CLI

## 架构方案

- 后端：Cheng 版 `codex app-server`（stdio JSON-RPC）
- 前端：Cheng IDE 读取 JSONL 流并驱动 UI 状态机
- 数据：threads、turns、items、tool outputs、diff blocks
- 资源：workspace roots、文件快照、选区/图片上下文
- 安全：sandbox policy 与 approval policy 对齐

## 模块与目录（建议）

- `codex-cheng/src/main.cheng`：入口与命令分发
- `codex-cheng/src/exec_cmd.cheng`：`exec` 与 CLI 输出
- `codex-cheng/src/app_server.cheng`：JSON-RPC 主循环
- `codex-cheng/src/json_util.cheng`：轻量 JSON 组装/解析
- `codex-cheng/src/config.cheng`：配置读取/写入与路径解析
- `codex-cheng/src/storage.cheng`：线程/turn 持久化（jsonl）
- `codex-cheng/src/tools/*.cheng`：shell/apply_patch 等工具
- `ide/gui/app.cheng`：IDE Codex UI、命令入口与渲染

## 功能拆解

- 会话与任务：thread start/resume/list/archive、turn start/interrupt、review/start
- 模型与配置：model/list、config read/write
- MCP：skills/list、mcpServerStatus/list、oauth login
- 上下文与编辑：当前文件/选区/多文件/图片、修改预览与应用、跳转定位
- UI 结构：侧边栏/面板、任务状态、工具调用输出、审查结果
- CLI 能力：exec/app-server/apply/resume/features、日志与错误码

## 协议与数据

- 线程目录：`~/.codex-cheng/threads/*.jsonl`
- 配置文件：`~/.codex-cheng/config.toml`（先用 key=value 兼容层）
- app-server 事件：`thread/started`、`turn/started`、`item/*`、`turn/completed`
- 线程字段：`id/preview/modelProvider/createdAt`
- Turn 字段：`id/status/items/error`
- Item 字段：`id/type/content`

## 阶段计划

- 阶段 0：CLI 框架与参数解析；IDE Codex 基础入口
- 阶段 1：app-server 核心协议；IDE app-server 连接与输入输出
- 阶段 2：线程/turn 持久化与流式事件；IDE 线程列表与对话流
- 阶段 3：工具调用与 diff/patch；IDE 预览/应用与 TODO CodeLens
- 阶段 4：登录/配置/MCP/云端任务；IDE 设置与模型选择

## 核心优先范围（当前执行）

- app-server 协议完整与线程持久化（thread/turn/item + resume）
- 工具链路：shell/patch/mock + 命令输出事件
- diff/patch 端到端：生成 → 预览 → 应用
- CLI exec/review 与 app-server 对齐（参数/错误格式）
- IDE 基础可视化：线程/消息/工具输出/补丁事件

## 延后项（边缘功能）

- OAuth/MCP 真实接入、云端任务、ChatGPT 桌面桥接
- 完整审批交互 UI、IDE 结构化面板细节打磨
- 高级配置项与跨平台适配细节

## 详细任务清单

- CLI：命令级参数解析（补齐 `exec/apply/login/logout/config`）
- app-server：线程/turn/事件协议完整字段（覆盖 initialize/thread/turn/review 基线与 list/archive/config）
- storage：jsonl 写入与 resume 读取（已完成）
- config：读取与写入（已完成，支持 unset）
- tools：shell/patch/mock（已完成，patch 使用 git apply/patch）
- apply：补丁应用（已完成）
- review：接入 review prompt 与真实模型输出（已完成）
- IDE：线程列表、对话流、任务状态、消息流式渲染（已完成）
- IDE：diff/patch 预览与应用（已完成）
- IDE：TODO CodeLens、右键追加线程（已完成）

## 当前进度

- `codex-cheng` CLI 已实现 `exec/app-server/apply/config/login/logout/threads/resume`，并对齐 JSON-RPC 事件链路
- 接入 Responses API（`curl` 调用），支持基础/审查提示词文件与工具调用闭环（shell/apply_patch）
- `app-server` 支持 `initialize/thread/start/resume/list/archive/turn/start/review/start/command/exec` 与基础账号/配置接口
- 审批流对齐：按 `approvalPolicy` 触发 `item/*/requestApproval` 请求并等待响应，再继续工具链路
- execpolicy runtime：读取 `~/.codex-cheng/rules`、执行规则判定与 allowlist amendment 写回，统一驱动 shell/command 执行
- sandbox runner：macOS seatbelt/Linux sandbox 执行接入，支持 sandbox 权限绕行、失败重试与审批缓存
- shell 工具对齐：login shell 默认行为与 `timeout_ms` 超时封装支持
- shell snapshot：可选生成环境快照并在后续命令复用（`features.shell_snapshot`）
- config profile：支持 `profiles.<name>.<key>` 读取与 config set/unset 按 profile 写入
- 线程 JSONL 已能回填上下文（user/assistant）与工具输出，支持 resume/threads 列表
- `config` 支持 `auth.token`/`model`/`review_model`/`approval_policy`/`sandbox_mode`，`config/read` 返回运行态配置
- 事件覆盖 `thread/started`、`turn/started/completed`、`item/*`、`turn/diff/updated`，含审批请求 `item/commandExecution|fileChange/requestApproval`
- `update_plan` 工具支持，触发 `turn/plan/updated`，并在 exec JSONL 输出 `todo_list` 项
- Plan mode 已落地：`<proposed_plan>` 解析、`item/plan/delta` 事件、`agentMessage/plan` item 生命周期、`request_user_input` 协议字段与 schema 产物对齐
- parity manifest 已收口：当前 `61/61` crate 映射为 implemented（`tooling/parity/parity_manifest.yaml`）
- arg0 apply_patch 兼容已补齐：支持 `--codex-run-as-apply-patch` 与 `apply_patch` / `applypatch` 入口
- hooks/notify 已落地：支持 `notify=[...]` legacy 外部通知命令与 `agent-turn-complete` JSON payload
- CLI 全局覆盖与特性开关：支持 `-c/--config` 与 `--enable/--disable`，`features list` 输出特性列表
- `exec` 对齐 review/resume 子命令与 `--ask-for-approval`/`--search`，支持 JSON schema 输出与 last-message 文件
- `login status` 子命令已补齐，状态输出区分 ChatGPT/API key（含脱敏）
- `responses-api-proxy` 通过 `curl -i --no-buffer` 管道转发，支持流式响应透传与常规 header 透传
- `app-server generate-ts/json-schema` 默认输出完整协议（来自 `codex-app-server-protocol` 导出），资源缺失时回退最小骨架
- `resume` 支持 `--all` 参数兼容（当前不做 CWD 过滤）
- `resume` 无 prompt 时进入行式交互，并提供会话选择（文本 picker）
- 交互式 CLI 支持可选 `CODEX_UPDATE_CMD` 更新动作（非 TUI）
- web_search：支持 `tools.web_search`/`web_search` 旧键与 `web_search_call` 解析回填（事件与上下文）
- review：仅禁用 web_search/view_image，保留其他工具链路；config/read 回填 tools 配置
- IDE Codex：线程列表/历史回填、流式消息、web_search/patch 状态显示，TODO CodeLens 交互
- IDE 登录：`authUrl` 自动打开 + `auth.json` 检测兜底（缺事件时仍可收敛为已登录）
- 新增 VSCode 外观/交互对齐模板：`doc/cheng-ide-vscode-alignment.md`（待补齐对照清单与差异项）
- 新增 `app-server-test`（Cheng 实现）用于验证 app-server 交互与审批流
- `completion`/`sandbox`/`execpolicy check` 子命令补齐；`apply` 支持 task_id 与 `--patch` 本地补丁
- `cloud`/`responses-api-proxy`/`stdio-to-uds` 子命令已用 Cheng 本地实现（cloud exec/status/diff/apply + 列表兜底与文本交互、auth.json 读取、stdio/HTTP 代理）
- 配置/存储路径：优先 `~/.codex-cheng`，若不存在则回退到 `~/.codex`（兼容读取）
- `responses-api-proxy` 支持 fork 并发处理（非 Windows）
- `cloud`/`interactive` 默认启用 tui2 菜单式交互（threads/task 选择器）
- `interactive`/`cloud` TUI 输出统一 ASCII Header（Codex/Codex Cloud），对齐 Codex CLI 视觉基线
- IDE Codex 面板标题统一为 “Codex”，toolbar 视觉间距与标题样式对齐
- CLI 交互菜单补齐 ANSI 样式（bold/dim/cyan）与 “OpenAI Codex” 头部框，贴近 codex-rs TUI 视觉规范

## 当前执行计划（按建议推进）

- [ ] VSCode 1.108 外观/基础功能对齐，按 `doc/cheng-ide-vscode-alignment.md` 清单推进。
- [ ] Codex 登录授权链路完整跑通（浏览器 OAuth 打开/回调/Token 交换/状态落盘），补齐日志与错误定位。
- [ ] IDE Codex 侧栏 UI 与 VSCode 插件布局/交互对齐（线程/任务/工具输出/补丁应用）。
- [ ] 端到端验证：`codex-cheng login` → app-server → IDE Sign In → 对话/编程交互闭环。

## CLI 对照表（codex-rs/cli -> codex-cheng）

登录基线：默认使用浏览器 OAuth（ChatGPT 登录）。仅当 `--device-auth` 时走设备码，`--with-api-key` 时走 API key。

### 顶层/全局

| 项 | codex-rs/cli | codex-cheng | 差异/备注 |
| --- | --- | --- | --- |
| 无子命令 | 进入交互式 TUI（tui/tui2），支持 resume picker 与 update action | 进入交互式 TUI（`interactive.cheng` + `tui2`），支持会话选择与 update action | 基本对齐（细节视觉持续打磨） |
| 全局配置覆盖 | `-c/--config`、`--enable/--disable` | `-c/--config` + `-c:`/`--config:`、`--enable/--disable` | 基本对齐 |
| 命令名 | `codex` | `codex-cheng` | 发布时需别名或替换为 `codex` |

### 子命令对照

| 子命令 | codex-rs/cli | codex-cheng | 差异/备注 |
| --- | --- | --- | --- |
| `exec` | `codex exec [PROMPT]`<br>参数：`--image/-i`、`--model/-m`、`--oss`、`--local-provider`、`--sandbox/-s`、`--profile/-p`、`--full-auto`、`--dangerously-bypass-approvals-and-sandbox`/`--yolo`、`--cd/-C`、`--add-dir`、`--output-schema`、`--color`、`--json`、`--output-last-message/-o` | `codex-cheng exec [prompt]`<br>同名参数全覆盖，新增 `--ask-for-approval/--approval-policy`、`--search`、`--prompt` | Rust 的 `exec` 无 `--ask-for-approval/--search`（仅 TUI 有）；`-` 读 stdin 行为未对齐 |
| `review` | `codex review` + `--uncommitted` / `--base <branch>` / `--commit <sha>` / `--title <title>` / `[PROMPT|-]` | `codex-cheng review` 同名参数 + `--prompt` | `-` 读 stdin 细节与 Rust 不完全一致 |
| `resume` | `codex resume [SESSION_ID] [--last] [--all]` + TUI 旗标 | `codex-cheng resume <session_id> [prompt]` 或 `--last/--all`，支持 TUI 会话选择器 | `--all` 仍不做 CWD 过滤 |
| `login` | 默认浏览器 OAuth；`--device-auth`、`--with-api-key`；`login status` 子命令；隐藏 `--experimental_issuer`/`--experimental_client-id` | 默认浏览器 OAuth；`--device-auth`、`--with-api-key`、`--token`；`login status`；`--experimental_issuer`/`--experimental_client-id` | 新增 `--token`（直写 token） |
| `logout` | `codex logout` | `codex-cheng logout` | 提示文案不同 |
| `app-server` | `codex app-server` / `generate-ts --out --prettier` / `generate-json-schema --out` | `codex-cheng app-server` / `generate-ts --out --prettier` / `generate-json-schema --out` | 默认输出完整协议（`codex-app-server-protocol`），资源缺失时回退最小骨架 |
| `mcp` | `list/get/add/remove/login/logout` + OAuth（streamable_http） | `mcp` Cheng 原生实现 | 已实现（含 lifecycle 与 OAuth） |
| `mcp-server` | 运行 MCP server（stdio） | `mcp-server` Cheng 原生实现 | 已实现（含 initialize 握手） |
| `completion` | `codex completion --shell <bash|zsh|fish|...>` | `codex-cheng completion <bash|zsh|fish|powershell>` | 参数形式不同 |
| `sandbox` | `codex sandbox <macos|linux|windows> [--full-auto] [--log-denials] -- <cmd>` | 同名用法 | 基本对齐 |
| `execpolicy` | `codex execpolicy check`（隐藏） | `codex-cheng execpolicy check` | 语法/输出仍需对齐 |
| `apply` | `codex apply <task_id>`（从 Codex Cloud 拉取 diff） | `codex-cheng apply <task_id>` 或 `--patch <file|diff>` | 任务来源与拉取逻辑未对齐 |
| `cloud` | `codex cloud` TUI + `exec/status/diff/apply` | `codex-cheng cloud exec/status/diff/apply` + 列表/TUI 交互 | 基本对齐（云端接口细节持续对齐） |
| `responses-api-proxy` | `--port`、`--server-info`、`--http-shutdown`、`--upstream-url` | 同名参数 | Cheng 使用 curl 管道流式转发；支持 fork 并发（非 Windows） |
| `stdio-to-uds` | `codex stdio-to-uds <socket>` | `codex-cheng stdio-to-uds <socket>` | 基本对齐 |
| `features` | `codex features list`（基于 codex_core 特性表） | `codex-cheng features list`（静态特性表） | 特性集合与 stage 需对齐 |
| `app-server-test` | 无 | `codex-cheng app-server-test` | Cheng 内置 app-server 交互测试客户端 |

### Cheng 专有命令（Rust 无对应）

- `config`（get/set/unset 与 `config/read`）
- `threads`（本地线程列表）

## 差异清单（需对齐/补齐）

- MCP：`mcp`/`mcp-server` 全量缺失（含 OAuth、HTTP headers、env/cwd/timeout 配置）。
- `resume`：`--all` 已兼容参数，但无 CWD 过滤。
- `exec` 旗标差异：Rust `exec` 无 `--ask-for-approval/--search`；Cheng 已提供但行为需对齐 TUI。

## 推进计划（排除 MCP）

- [x] 交互式 TUI（tui/tui2）与 update action，对齐 `codex resume` 的会话选择器与快捷入口
- [x] `app-server` 协议全字段对齐（TS/JSON schema）
- [x] `cloud` TUI 与交互流程
- [x] `responses-api-proxy` 线程化/并发处理（保持流式透传）
- [x] 配置与凭据路径兼容（`~/.codex` ↔ `~/.codex-cheng`）

## 验收清单

- 功能：与 VSCode Codex 插件功能点对齐
- 体验：热键、操作路径、错误提示一致
- 稳定性：断线重连、崩溃恢复、数据不丢
