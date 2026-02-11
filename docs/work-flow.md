下面给你一套**“需求 → 正交原子任务矩阵 → 最大化并行 → 集成验证 → 上线监控（生产闭环）”**的可落地实现方案，按你说的“**一口气完成、中间不中断**”去设计：把所有“会让模型停下来问你”的不确定性，提前**固化成契约、规则、技能（Skill）和自动验收门禁**，然后用 Codex 的**非交互执行 + 并行 worker**跑完闭环。

我会以 **GPT‑5.2‑Codex（gpt-5.2-codex）+ Codex（CLI/Cloud/SDK/GitHub Action）**的能力边界来写（这些能力在 OpenAI 官方文档里明确：长时程 agentic coding、compaction、Codex 可读/改/跑代码、Codex Cloud 支持后台并行、非交互模式 codex exec、Skills、AGENTS.md 等）。([OpenAI Platform][1])

---

## 0) 先说结论：要“不中断”，关键不在模型，而在“工作流可执行化”

GPT‑5.2‑Codex 本身就是面向**长时程、复杂真实工程**优化的 coding 模型，并且强调了 compaction、长会话/长任务可靠性、在大仓库持续迭代等点。([OpenAI][2])
但要做到你要的“从需求一路跑到生产闭环”，必须把中间过程改造成：

1. **需求可编译**：用“契约 + 验收测试 + DoD”冻结不确定性
2. **任务可并行**：用“正交原子任务矩阵 + DAG 依赖”生成 worker 队列
3. **执行可自动**：用 `codex exec --full-auto`/SDK + Rules + Sandbox 减少人工批准点 ([OpenAI Developers][3])
4. **结果可闭环**：CI/测试/扫描/发布/监控全部自动回传，失败就自动返工直到门禁全绿

### cheng-codex 一键入口（自动拆解）

在 `cheng-codex` 中使用：

```bash
codex-cheng ship --full-auto "<你的需求>"
```

`ship` 会把需求自动拆解为 `SPEC.md` / `CONTRACT.md` / `ACCEPTANCE.md`，再生成 `TASK_MATRIX.yaml` 并以 orchestrator + 多 worker 并行执行，最后跑完门禁与闭环步骤。

多行需求建议用 stdin：

```bash
cat <<'EOF' | codex-cheng ship --full-auto -
这里是多行需求描述
EOF
```

---

## 1) 把“需求”变成“不会卡住的输入”：三件套

你要模型不停下来，最大杀手是“需求模糊”。解决方式是让输入具备**可执行验收**。

建议你把 PRD 统一变成三个文件（或同一份 JSON 的三个区块）：

### A. SPEC（规格）

* 用户故事/范围（in/out）
* 关键约束（性能、兼容、权限、审计、回滚）
* 风险与降级策略（feature flag / canary / fallback）

### B. CONTRACT（契约）

* API（OpenAPI/JSON Schema）
* 数据（DDL/迁移策略）
* 事件/消息（topic、payload、幂等等）
* UI 合约（props/state、可访问性要求）

### C. ACCEPTANCE（验收）

* BDD 场景（Given/When/Then）
* 关键 E2E 用例
* SLO / 监控指标（上线后怎么判定“成功”）

> 你会发现：**并行**的前提就是“接口先行”。契约先冻结，各模块实现才真正正交。

---

## 2) 正交原子任务矩阵怎么定义（可直接照抄）

把工作拆成矩阵：**行 = 组件/边界上下文（Bounded Context）**，**列 = 交付关注点（Concern）**。

### 推荐列（列就是“天然可并行”的正交维度）

1. `contract`：对外接口/Schema/错误码（只改契约文件）
2. `scaffold`：脚手架/空实现/Mock（只保证编译可跑）
3. `impl`：业务实现
4. `unit_tests`：单测（必须先写失败用例再实现）
5. `integration_tests`：契约测试/集成测试
6. `observability`：日志、指标、trace、告警规则
7. `security`：权限校验、审计、输入校验、依赖扫描配置
8. `docs`：README/Runbook/变更说明
9. `release`：feature flag、迁移、回滚、发布脚本/配置

### 原子任务（每个 cell）必须满足的“正交”判定

每个 cell 用这一组字段约束（越机械越好）：

* **inputs**：只允许依赖哪些契约/哪些文件
* **outputs**：必须产出哪些文件/哪些测试
* **touch_scope**：允许修改的路径白名单（强制“少而集中”）
* **done_checks**：必须通过哪些命令（lint/test/typecheck）
* **depends_on**：依赖的 cell 列表（形成 DAG）

> 正交不是玄学：你用“允许改哪些路径”就能硬约束正交性；跨组件改动一律拆成“先契约、后实现”的两跳。

---

## 3) 最大化并行：先做“解耦解锁任务”，再开 worker

并行的核心技巧就两条：

### 技巧 1：先跑“解锁型任务”

优先级排序应是：

1. `contract`（接口冻结）
2. `scaffold`（空实现 + mock + 编译通过）
3. 然后所有 `impl / tests / observability / docs` 才能满并行

### 技巧 2：把跨切面工作变成“契约测试”而不是“口头约定”

例如：

* API 的 consumer/provider 用契约测试绑定
* 事件流用 schema + golden file
* UI 用组件 props 合约 + 可访问性检查

这样每个 worker 不需要“问别人现在做到哪了”，只需要“契约文件 + 测试门禁”。

---

## 4) 用 Codex 实现“不中断执行”的三种工程形态（从轻到重）

### 形态 A：单 agent 一口气跑完（最简单）

用 **Codex 非交互模式**直接执行一条“从需求到交付”的指令：

* `codex exec` 是为自动化准备的模式，支持 `--full-auto`、sandbox、输出 schema、以及在 CI 里跑。([OpenAI Developers][3])

示例（你把 SPEC/CONTRACT/ACCEPTANCE 放进仓库，或者作为 prompt 附上）：

```bash
codex exec --full-auto --sandbox workspace-write \
"Read SPEC.md, CONTRACT.md, ACCEPTANCE.md.
1) Generate TASK_MATRIX.yaml with orthogonal atomic tasks + dependencies.
2) Implement all tasks, writing tests first where applicable.
3) Run: lint, typecheck, unit, integration, e2e.
4) Update docs/runbook and add feature flag + rollback notes.
5) Stop only when all checks pass."
```

在 cheng-codex 中，可直接用 `codex-cheng ship` 作为本地封装：默认读取 SPEC/CONTRACT/ACCEPTANCE 并生成 TASK_MATRIX.yaml，然后以 orchestrator + 多 worker 执行；需要最少中断时加 `--full-auto`。

优点：最省事。
缺点：并行度主要靠模型内部（工具并行调用）与它的长时程能力，而不是多 worker。Codex 确实强调可长时程自治与 compaction，但单 agent 仍会比真正并行慢。([OpenAI Developers][4])

---

### 形态 B：正交矩阵 + 多 worker 并行（你要的“最大化并行”）

这才是“矩阵最大化并行”的标准解：**一个 orchestrator + 多个 Codex 会话/任务**。

你有两条官方路径：

1. **Codex Cloud**：能在云端后台跑任务，包含并行（很适合 worker 池）。([OpenAI Developers][5])
2. **Codex SDK**：你自己写 orchestrator，程序化控制多个 Codex agent 并发跑 cell。([OpenAI Developers][6])

Orchestrator 的流程（固定不变，最抗中断）：

1. 读取 SPEC/CONTRACT/ACCEPTANCE
2. 生成 `TASK_MATRIX.yaml`（结构化输出，带 DAG）
3. 按 DAG 拓扑排序，启动 N 个 worker 并行执行“无依赖 cell”
4. 每个 worker：

   * checkout 独立分支
   * 只允许改 `touch_scope`
   * 跑 `done_checks`
   * 产出补丁 + 结果报告（JSON）
5. integrator 合并（或 rebase）到 integration 分支
6. 全量门禁（CI）通过后进入 release（staging → canary → prod）
7. 监控回传：若错误率/延迟超阈值，自动回滚 + 生成修复任务重新进入矩阵

---

### 形态 C：把闭环搬进 CI/CD（真正“生产闭环”）

用 **Codex GitHub Action**把“失败就自动返工”固化到 CI 里：

* 官方提供 `openai/codex-action@v1`，可在 GitHub Actions 里跑 Codex、打补丁、甚至做 review。([OpenAI Developers][7])
* 非交互模式文档也给了“CI 失败自动修复”的典型模式。([OpenAI Developers][3])

你可以做到：

* PR 合并前：Codex 自动补测试、补文档、补告警
* 主干 CI 红：Codex 自动开修复 PR
* 生产告警：自动回滚 + 自动创建 “hotfix matrix”

---

## 5) 让 Codex “每次都按你要的方式跑”：AGENTS.md + Skills + Rules

这三者是你想“不中断”的底层设施。

### A) AGENTS.md：把团队规范变成“启动即加载”的硬指令

Codex 会在开始工作前读取 `AGENTS.md`，并支持全局与项目分层覆盖。([OpenAI Developers][8])

你可以在仓库根目录放一个强约束版 `AGENTS.md`，核心写：

* 一律先生成/更新 `TASK_MATRIX.yaml`
* 一律 tests-first
* 一律必须跑哪些命令
* 一律禁止哪些危险操作（配合 Rules/Sandbox）

（AGENTS.md 的“强制工作流”是减少中断的关键：模型不会每次都临场发挥。）

---

### B) Skills：把“需求→矩阵→执行”封装成可复用工作流模块

Skills 是 Codex 的“可发现工作流包”，用 `SKILL.md`（YAML front matter + 指令体）定义；只有显式/隐式触发才会注入指令体，天然适合把复杂流程模块化。([OpenAI Developers][9])

官方定义的 skill 格式（你可以直接用）：([OpenAI Developers][10])

* `name`、`description` 必填
* 目录可带脚本/模板/参考资料

你可以做 3 个小 skill（比一个巨型 skill 更稳定，也更符合官方建议“技能要小”）：([OpenAI Developers][10])

1. `req-to-matrix`：把 SPEC/CONTRACT/ACCEPTANCE 变成 `TASK_MATRIX.yaml`
2. `execute-cell`：执行单个 cell（按 touch_scope、done_checks）
3. `ship-closed-loop`：调度矩阵（orchestrator 用），并在 CI/CD 里跑门禁

---

### C) Rules + Sandbox：让 `--full-auto` 也不“失控”

Codex 有 rules 机制：匹配命令前缀，决定 allow/prompt/forbidden，并且“多规则命中取最严格”。([OpenAI Developers][11])
配合 `--sandbox workspace-write` / `read-only`，你就能把自动化跑在安全边界内。([OpenAI Developers][3])

这一步非常关键：否则你为了不中断把 approval 全关了，风险就会跑到生产侧。

---

## 6) “一口气完成”实践模板：TASK_MATRIX.yaml 长这样

给你一个精简示例（你可以扩展列/行）：

```yaml
version: 1
goal: "Add feature X end-to-end"
rows: ["api", "service", "db", "web", "obs", "release"]
cols: ["contract", "scaffold", "impl", "unit_tests", "integration_tests", "docs"]
cells:
  - id: api.contract
    touch_scope: ["contracts/openapi.yaml", "contracts/errors.yaml"]
    depends_on: []
    done_checks: ["make contract-validate"]
    outputs: ["OpenAPI updated", "error codes frozen"]

  - id: service.scaffold
    touch_scope: ["services/x/**"]
    depends_on: ["api.contract"]
    done_checks: ["make build"]
    outputs: ["compiles", "mock endpoints wired"]

  - id: db.impl
    touch_scope: ["migrations/**", "db/**"]
    depends_on: ["api.contract"]
    done_checks: ["make db-migrate", "make db-rollback-test"]
    outputs: ["migration + rollback verified"]

  - id: web.impl
    touch_scope: ["web/**"]
    depends_on: ["api.contract", "service.scaffold"]
    done_checks: ["make web-test"]
    outputs: ["UI wired with feature flag"]

  - id: obs.impl
    touch_scope: ["observability/**", "services/x/**"]
    depends_on: ["service.scaffold"]
    done_checks: ["make lint"]
    outputs: ["metrics + alerts added"]

  - id: release.impl
    touch_scope: ["deploy/**", "runbooks/**"]
    depends_on: ["db.impl", "service.scaffold", "web.impl", "obs.impl"]
    done_checks: ["make staging-deploy", "make smoke"]
    outputs: ["staging verified", "canary plan", "rollback plan"]
```

你会发现：

* **contract/scaffold**先行，后面实现就能并行铺开
* 每个 cell 都能独立交付并被机器验收
* orchestrator 只需要跑 DAG，不需要“靠聊天推进”

---

## 7) 两个反直觉点：它们决定你能不能“不中断”

### 反直觉 1：别强迫模型“先输出宏大计划”

Codex 官方 prompting guide 明确提到：如果你强行让它做过多“前置计划/中间状态汇报”，反而可能导致任务在 rollout 结束前停下来。([OpenAI Developers][4])
你要的是“一口气跑完”，所以策略应是：

* 计划写到 **TASK_MATRIX.yaml**（结构化产物），不是聊天输出
* 中间进度写到日志/JSON（机器可读），不是让模型停下来“汇报”

### 反直觉 2：真正的“不中断”不是不失败，而是失败自动回路

你要设计的是：

* 失败 → 自动定位 → 自动最小修复 → 重新跑门禁
  这就是闭环。`codex exec` 的自动化模式、以及 CI 失败自动修复范式，天然就是为这个模式准备的。([OpenAI Developers][3])

---

## 你可以直接照这个“落地清单”做（最短路径）

1. 在仓库加：

   * `SPEC.md` `CONTRACT.md` `ACCEPTANCE.md`
   * `AGENTS.md`（强制 tests-first、矩阵输出、必须跑的命令）([OpenAI Developers][8])
2. 加 `.codex/skills/req-to-matrix/SKILL.md` 等技能（按官方 YAML front matter）([OpenAI Developers][10])
3. 把 `make lint test typecheck e2e` 这类门禁做成统一命令
4. 先用 `codex exec --full-auto` 跑形态 A 验证端到端可行 ([OpenAI Developers][3])
5. 再用 Codex Cloud 或 Codex SDK 升级为形态 B 并行 worker ([OpenAI Developers][5])
6. 最后接入 GitHub Action，形成生产闭环（形态 C）([OpenAI Developers][7])

---

如果你愿意把你的需求用 10~20 行写成一段（或贴你现有 PRD/SPEC），我可以直接按上面的规范给你生成一份**可执行的 TASK_MATRIX.yaml + 3 个 SKILL.md 模板 + 一条 codex exec 的“不中断总控指令”**，你复制进仓库就能跑。

---

## 9) cheng-codex 落地闭环 (已对齐文件)

以下文件已在仓库根落地, 直接作为生产闭环输入/门禁:

- `SPEC.md` / `CONTRACT.md` / `ACCEPTANCE.md`
- `TASK_MATRIX.yaml`
- `build/closed-loop/report.*` (原生 Cheng 闭环输出)

推荐最短执行路径:

```bash
cd /Users/lbcheng/cheng-codex
./build/codex-cheng ship "你的需求"
```

如需跳过闭环:

```bash
./build/codex-cheng ship --no-closed-loop "你的需求"
```

如需在线门禁:

```bash
CODEX_CHENG_ONLINE=1 ./build/codex-cheng ship "你的需求"
```

（保留 `tooling/closed_loop.sh` 作为遗留单项门禁脚本）

## 8) IDE 1:1 对齐 VSCode 的生产闭环（排除插件与调试）

这部分是 IDE 对齐 VSCode 的专项闭环：目标是 **功能、布局、交互 1:1**，但**明确排除插件市场与调试/断点**。

### 8.1 对齐范围（in/out）

**in-scope（对齐）**：

* 工作台布局：activity bar / side bar / editor / panel / status bar
* 核心体验：命令面板、快速打开、搜索、SCM、终端、问题面板、输出面板
* 编辑器行为：tabs、分屏、breadcrumbs、minimap、peek、diff
* 设置与快捷键：Settings UI / Keybindings UI

**out-of-scope（排除）**：

* 插件市场与插件运行时
* 调试/断点/调试适配器相关能力

### 8.2 规格基线：生成 VSCode 对齐快照

以 VSCode 行为为**单一事实源**，输出可机器读的 spec 快照，作为 SPEC/ACCEPTANCE 的输入。

```bash
cd /Users/lbcheng/cheng-ide
toolchain vscode-spec --format json --output build/ide/spec/vscode_spec.json
toolchain vscode-spec --format text --output build/ide/spec/vscode_spec.txt
```

### 8.3 SPEC / CONTRACT / ACCEPTANCE 专项结构

**SPEC.md（对齐规格）**：

* UI 布局图（区域 + 视图清单）
* 关键交互流程（打开/搜索/切换/拆分/关闭）
* 统一命令清单（command id + 行为）
* 快捷键矩阵（默认键位 + 上下文 when）
* 性能预算（启动、搜索、切换的目标阈值）

**CONTRACT.md（稳定契约）**：

* 视图状态机（focus/selection/dirty/readonly）
* 事件与消息（command id、菜单、快捷键触发）
* 关键数据模型（workspace、files、problems、output）
* UI 组件 props/state 约束（可访问性要求）

**ACCEPTANCE.md（验收与闭环门禁）**：

* VSCode 1:1 对齐清单（逐项勾选）
* 关键路径 E2E（打开工程、搜索替换、SCM 提交、终端交互）
* 视觉与交互一致性检查
* 破坏性重建记录（允许的偏离项 + 审批说明）

### 8.4 正交原子任务矩阵（IDE 专用）

行是区域，列是关注点，确保每个 cell 都能并行执行且可自动验收。

```yaml
rows: ["workbench", "activity_bar", "side_bar", "editor", "panel", "status_bar", "terminal", "search", "scm", "settings", "commands", "keybindings", "a11y", "perf", "docs"]
cols: ["contract", "impl", "ui_snapshot", "interaction_tests", "perf_budget"]
cells:
  - id: editor.contract
    touch_scope: ["ide/gui/editor/**", "docs/CONTRACT.md"]
    depends_on: []
    done_checks: ["make lint"]
    outputs: ["editor contract frozen"]

  - id: editor.impl
    touch_scope: ["ide/gui/editor/**"]
    depends_on: ["editor.contract"]
    done_checks: ["make gui-test"]
    outputs: ["editor behavior aligned"]

  - id: editor.ui_snapshot
    touch_scope: ["ide/gui/editor/**", "snapshots/**"]
    depends_on: ["editor.impl"]
    done_checks: ["make gui-snapshot"]
    outputs: ["visual diff passed"]
```

### 8.5 门禁与自动回路

**硬门禁（必须全绿）**：

* VSCode spec 对齐差异为 0（或已记录为允许偏离）
* UI snapshot diff 全绿
* 命令/快捷键覆盖率达标
* 核心路径 E2E 全绿
* 性能预算满足（启动、搜索、切换）

**自动回路**：

* 任一门禁失败 → 自动生成修复 cell → 重新跑矩阵
* 破坏性重建必须同步更新 SPEC/CONTRACT/ACCEPTANCE，并记录在 ACCEPTANCE 偏离清单

### 8.6 一口气执行指令（面向 IDE 对齐）

```bash
codex exec --full-auto --sandbox workspace-write \
"Generate SPEC/CONTRACT/ACCEPTANCE from vscode_spec.json.
Build TASK_MATRIX.yaml with orthogonal IDE cells.
Execute all cells with tests and snapshots.
Regenerate parity report until gates pass."
```

这样就能把 IDE 1:1 对齐 VSCode 的闭环流程变成可执行产物：**先冻结规格，再并行实现，再自动回路到全绿**。
