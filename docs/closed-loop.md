# Closed Loop (cheng-codex)

这份文档描述 `cheng-codex` 的生产闭环执行入口与门禁。

## 入口 (原生 Cheng)

闭环由 `codex-cheng ship` 原生执行, 无需脚本:

```bash
cd /Users/lbcheng/cheng-codex
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
./tooling/closed_loop.sh --check execpolicy
./tooling/closed_loop.sh --check completion
```

## 关联规范

- `SPEC.md`
- `CONTRACT.md`
- `ACCEPTANCE.md`
- `TASK_MATRIX.yaml`
