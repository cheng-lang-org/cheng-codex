# Closed Loop (cheng-codex)

这份文档描述 `cheng-codex` 的生产闭环执行入口与门禁。

## 当前收口边界

- 本轮锁定为“代码重写 + parity 场景补齐 + 文档同步”，不执行编译/测试/在线门禁。
- 下一轮再执行 `tooling/closed_loop.sh` 全量门禁并产出最终 pass/skip 报告。

## 入口 (原生 Cheng)

闭环由 `codex-cheng ship` 原生执行, 无需脚本:

```bash
cd /Users/lbcheng/.cheng-packages/cheng-codex
./build/codex-cheng ship "你的需求"
```

默认执行离线门禁, 输出报告到 `build/closed-loop/`。如需跳过闭环:

```bash
./build/codex-cheng ship --no-closed-loop "你的需求"
```

## 在线门禁

需要 API key 或可用 OAuth 登录时, 显式开启:

```bash
CODEX_CHENG_ONLINE=1 ./build/codex-cheng ship "你的需求"
```

## 单项检查 (遗留脚本, 可选)

```bash
./tooling/closed_loop.sh --check preflight
./tooling/closed_loop.sh --check build
./tooling/closed_loop.sh --check hard-gate
./tooling/closed_loop.sh --check parity
./tooling/closed_loop.sh --check execpolicy
./tooling/closed_loop.sh --check completion
```

## Parity 输出

- `tooling/parity/parity_manifest.yaml`: codex-rs crate 到 cheng 模块映射与完成度。
- `tooling/parity/behavior_manifest.yaml`: 行为级覆盖（arg0/hooks/plan-mode/...）与场景绑定状态。
- `tooling/parity/coverage_table.md`: crate + behavior 双视角最终覆盖表。
- `build/parity/hard_gate_report.{json,txt}`: 1:1 重写硬门限结果。
- `build/parity/report.{json,txt}`: 双实现差分执行结果与失败归因。
- 硬门限包含 `src/main.cheng` 的 Cheng 入口约束: 使用 `std/cmdline` 参数路径，禁止 `main(argc, argv: str*)` / `__cheng_setCmdLine` 指针入口。
- `tooling/parity/scenarios/app_server.yaml`: 包含 Plan mode 协议面检查 (`collaborationMode`, `item/plan/delta`, `ToolRequestUserInput*`)。
- `tooling/parity/scenarios/arg0_hooks.yaml`: 覆盖 argv0 dispatch、dotenv 过滤、PATH helper、hooks payload 关键语义。
- 当前 crate 映射结果: `total_crates=61`, `implemented=61`, `missing=0`。
- 当前行为映射结果: `implemented=22`, `scenarized=22`, `verification_status=pending_execution`。

## 关联规范

- `SPEC.md`
- `CONTRACT.md`
- `ACCEPTANCE.md`
- `TASK_MATRIX.yaml`
