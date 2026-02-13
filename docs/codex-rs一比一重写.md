# cheng-codex 对齐 codex-rs@`ebe359b8` 全量 1:1 一次性交付计划

## 摘要
本计划将 ` /Users/lbcheng/.cheng-packages/cheng-codex ` 作为唯一实施仓库，以 ` /Users/lbcheng/codex-lbcheng ` 的 `main@ebe359b8` 为冻结基线，一次性交付“Rust 工作区语义 1:1”实现。  
完成标准是：三平台（macOS/Linux/Windows）离线门禁全绿 + 双实现差分测试全绿；在线门禁按可选策略执行并单独出具报告。

## 目标与边界
1. 对齐范围包含 `codex-rs` 工作区公开行为：CLI 命令面、参数解析、退出码、配置与状态持久化、exec/review/resume/fork 行为、app-server 协议、MCP 客户端与 server、cloud/proxy/stdio relay、sandbox/execpolicy、TUI 关键行为与输出语义。  
2. 对齐标准为“语义 1:1”：行为、副作用、协议字段、错误类型、退出码一致；非关键空白/排版可容许差异。  
3. `cheng-codex` 专有能力（如 `ship`）保留，但转为实验/隐藏路径，不影响 `codex` 主命令对齐面。  
4. 非目标：逐 crate 源码结构复刻、逐字节帮助文本一致、与基线无关的新功能扩展。

## 实施总策略（一次性交付，内部分层落地）
1. 建立“基线冻结 + 可追溯映射”：新增 parity 清单，逐项映射 `codex-rs` crate/模块到 `cheng-codex` 模块与状态（implemented/partial/missing）。  
2. 先补“公共语义底座”，再补“命令与协议实现”，最后统一“差分门禁与文档收口”；中间不做对外里程碑发布。  
3. 全流程以双实现差分作为主验收，`tooling/closed_loop.sh` 作为汇总门禁入口，离线强制、在线可选。

## 代码与接口变更清单（决策完成版）
1. 新增 `tooling/parity/` 差分框架：场景定义、输入夹具、输出规范化器、结果聚合器、失败归因报告。  
2. 新增 `tooling/parity/scenarios/*.yaml`：按命令族划分场景（exec/review/login/.../mcp-server/app-server）。  
3. 扩展 `src/main.cheng` 与相关命令模块，使根命令与子命令语义完全跟随基线；保留专有命令但从主帮助面隔离。  
4. 扩展 `src/config.cheng`、`src/auth_store.cheng`、`src/storage.cheng`，对齐配置优先级、profile、覆盖规则、状态文件语义与字段。  
5. 扩展 `src/exec_cmd.cheng`、`src/engine.cheng`、`src/interactive.cheng`，对齐 exec/review/resume/fork、JSONL/human 输出、审批与 sandbox 联动。  
6. 扩展 `src/app_server.cheng`、`src/app_server_test_client.cheng`，对齐 app-server v2 JSON-RPC 方法、通知、分页/游标、错误结构。  
7. 扩展 `protocol/` 生成产物流程，保证 TS/JSON schema 与基线协议语义一致（字段名、可空性、枚举、tag 规则）。  
8. 扩展 `src/mcp_cmd.cheng`、`src/mcp_oauth.cheng`、`src/mcp_server_cmd.cheng`，对齐 MCP 生命周期、OAuth、stdio server 初始化与能力声明。  
9. 扩展 `src/cloud_tasks_cmd.cheng`、`src/responses_proxy_cmd.cheng`、`src/stdio_to_uds_cmd.cheng`，对齐 cloud/proxy/relay 的参数与 I/O 语义。  
10. 扩展 `src/sandbox_runner.cheng`、`src/execpolicy_cmd.cheng`、`src/execpolicy_runtime.cheng`，实现三平台策略差异与规则判定一致性。  
11. 更新 `tooling/closed_loop.sh`：接入差分测试步骤、三平台步骤聚合、在线可选步骤显式标记。  
12. 更新 `SPEC.md`、`CONTRACT.md`、`ACCEPTANCE.md`、`TASK_MATRIX.yaml`、`README.md`：将当前目标、门禁、报告字段与一次性交付定义同步。

## 工作流与执行顺序（实现者无需再决策）
1. 先生成基线清单：从 `codex-rs@ebe359b8` 提取命令面、协议面、关键数据结构与行为约束，形成 `parity_manifest`。  
2. 以 `parity_manifest` 驱动代码补齐：先核心底座（config/auth/state/protocol），再命令行为（exec/cli/cloud/mcp），再平台能力（sandbox/execpolicy/tui）。  
3. 每完成一个子域即补对应差分场景；所有场景必须绑定“基线命令 + cheng 命令 + 语义比较规则”。  
4. 所有实现完成后统一跑三平台离线门禁；若任一步失败，按差分报告逆向修正直到全绿。  
5. 最后跑可选在线门禁并单独记录 pass/skip，不阻断离线发布结论。

## 测试与验收场景（必须实现）
1. CLI 解析与退出码差分：`--help/-h/--version`、参数缺失、冲突参数、未知参数、别名、隐藏命令。  
2. Exec/Review 差分：stdin prompt、`--json`、`--output-last-message`、review 参数互斥、颜色与输出模式语义。  
3. Resume/Fork 差分：`SESSION_ID/--last/--all`、picker 触发条件、cwd 过滤语义。  
4. Login/Logout 差分：with-api-key/device-auth/status、脱敏输出、凭据清理副作用。  
5. Features/Config 差分：`--enable/--disable/-c/--profile` 叠加优先级与写回结果。  
6. App-server 差分：`generate-ts`、`generate-json-schema`、运行态 JSON-RPC 请求/响应/通知序列。  
7. MCP/MCP-server 差分：add/list/get/remove/login/logout 生命周期与 initialize 握手。  
8. Sandbox/Execpolicy 差分：三平台命令包装、规则匹配、forbidden/prompt/allow 决策。  
9. Cloud/Apply/Proxy/Stdio relay 差分：参数语义、HTTP/stdio 转发、diff/apply 输出语义。  
10. TUI 关键行为差分：默认进入路径、关键退出信息、resume hint、更新动作触发语义。  
11. 跨平台矩阵：macOS、Linux、Windows 各自离线全量通过。  
12. 在线可选矩阵：登录 smoke、exec smoke、cloud/MCP 在线链路（有凭据时执行）。

## 交付产物
1. 完整 Cheng 实现代码（单次汇总交付）。  
2. `tooling/parity/` 差分框架与场景集。  
3. `build/closed-loop/report.{txt,json}`，含离线必过结果与在线可选结果。  
4. 更新后的规范文档与任务矩阵，状态与实现一致。  
5. 最终“基线覆盖表”：列出 `codex-rs` 工作区各域映射与完成状态，保证无遗漏。

## 假设与默认值（已锁定）
1. 基线固定：`/Users/lbcheng/codex-lbcheng` 的 `main@ebe359b8`。  
2. 交付模式：一次性全量交付，不做阶段性交付。  
3. 对齐范围：Rust 工作区语义 1:1（不是仅 CLI 子集）。  
4. 平台范围：macOS/Linux/Windows 全覆盖。  
5. 严格度：语义 1:1（非关键排版差异可接受）。  
6. 专有命令策略：保留但标记实验/隐藏，不污染主对齐面。  
7. 验收主策略：双实现差分测试。  
8. 门禁策略：离线必过，在线可选。  
