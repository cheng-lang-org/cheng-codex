# ACCEPTANCE: cheng-codex 生产闭环验收

> 分为离线门禁 (必过) 与在线门禁 (可选, 需要 API key/网络)。

## 离线门禁 (必须全绿)
1) 规格文件齐全
- SPEC.md / CONTRACT.md / ACCEPTANCE.md / TASK_MATRIX.yaml 存在且非空。

2) 构建可用
- `./build.sh` 成功产出 `build/codex-cheng`。

3) execpolicy 可用
- `codex-cheng execpolicy check --rules <file> git push origin main` 返回 JSON。

4) completion 参数对齐
- `codex-cheng completion --shell bash` 成功输出脚本。

5) app-server 代码生成可用
- `codex-cheng app-server generate-ts --out <dir>` 产出 `.ts` 文件。
- `codex-cheng app-server generate-json-schema --out <dir>` 产出 `.json` 文件。

6) app 命令面可用
- `codex-cheng app --help` 返回 0。

7) debug 命令面可用
- `codex-cheng debug --help` 返回 0。

8) mcp 命令面可用
- `codex-cheng mcp add/list/get/remove` 在隔离 HOME 下可完成生命周期操作。
- `mcp list/get --json` 返回 transport/auth/status 等字段。

9) mcp-server 协议面可用
- 向 `codex-cheng mcp-server` 写入 initialize 请求，返回 JSON-RPC initialize response。

10) TUI 命令面可用 (纯 Cheng)
- `codex-cheng --help` 可正常返回，且源码门禁包含：
  - `src/interactive.cheng` 含 `interactiveMenuChoiceTui`
  - `src/exec_cmd.cheng` 含 `selectThreadIdTui`
  - `src/main.cheng` 默认无子命令进入 `runInteractive`

## 在线门禁 (需要显式开启)
11) 登录 + 执行 smoke
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

## 门禁工具
- `codex-cheng ship "<需求>"` (原生 Cheng 闭环入口)
- `--no-closed-loop` 可跳过闭环
- 设置 `CODEX_CHENG_ONLINE=1` 开启在线门禁
- `tooling/closed_loop.sh` 仅作为遗留脚本
