# paper-review-harbor

把论文变成标准的 [Harbor](https://www.harborframework.com/docs/tasks) 任务，用于**收集**同行评审：
稿件已经写完，review agent 读它并写出 `review.md`，这对数据随后归档，留给人类专家评估质量。

这是本项目的主线流水线（`docs/PAPER2HARBOR.md` 是详细文档）。旧的 OSP 顺序批跑 harness
（`tools/`、`docs/OSP_BATCH.md`）已被取代、处于退役状态，等 Harbor 任务跑完整轮后删除。

## 现在支持的功能

| 功能 | 说明 |
|---|---|
| **语料发现** | `papers/<slug>/` 下放任意形状的 TeX 源（目录、`.tar.gz`、`.zip`、裸 `.tex`）即自动成为任务，无需注册步骤 |
| **多版本任务** | 同一论文的每个版本（`v1/v2/v3`）是独立任务；支持显式声明稿件 PDF，自动识别 toplevel TeX |
| **阶段化构建** | `stage` 解包并记录 withheld/净化清单；`show-map` 校验 toplevel 文件与标题提取 |
| **泄露防护** | `emit` 渲染后立即审计、`audit` 独立重审磁盘上的任务；任何把写作期缺陷轨迹（`solution-*/paper/review/`、`plan.md`）或后一版本带进环境的任务会被删除并中断命令 |
| **Harbor 任务生成** | 输出 `schema_version = "1.4"` 任务，`harbor run` 可直接执行；含 `environment/`（TeX Live 子集 + agent 工具链）、`solution/`（占位 oracle）、独立 verifier 容器 |
| **网络模式** | `none` / `agent` / `scholarly` 三档预设，host allowlist 同时作用于 environment 与 agent 两个阶段 |
| **验证** | `verify <label> --agent oracle` 必须 1.0、`--agent nop` 必须 0.0；本机无 Docker 时打印 Linux 箱上的确切命令而非降级为弱检查 |
| **paper-run v0.5.0 review agent** | `pre-harbor verify --agent paper-run` 集成 OpenCode 原生 paper-run 的 `review-report` plan，校验固定 plan、报告必需标题，归档 `.paper-run/` 状态 |
| **Hugging Face 发布** | `publish` 上传到 `Jack-Jieke-Wu/Paper-Reviewing-Exam`，发布前再次审计、默认 dry-run；`harbor run --repo` 可直接跑已发布快照 |
| **opencode 命令** | `/paper2task <label>`（stage → inspect → emit → audit）与 `/verify-task <label>`（oracle + floor） |
| **语料规模** | 当前 **27 篇论文、31 个可审版本** |

## 快速开始

```bash
uv run pre-harbor doctor          # 这台机器能做什么，什么必须交给 Linux 箱
uv run pre-harbor list            # 每个版本及其 spec 状态
uv run pre-harbor emit            # 渲染全部任务；每个任务都审计，泄露即删除
uv run pre-harbor verify <label> --agent oracle    # 在 Linux 箱上运行，必须 1.0
```

## CLI 总览

```
pre-harbor list                 every version and its metadata status
pre-harbor doctor               what this machine can and cannot do
pre-harbor init-spec <label>    write a starter spec (optional overrides)
pre-harbor stage [labels...]    unpack publishable material, write paper_map.json
pre-harbor show-map <label>     print a staged paper's structure
pre-harbor emit [labels...]     render tasks; audits each, deletes on leak
pre-harbor audit                re-audit tasks on disk
pre-harbor verify <label>       harbor run, or the command for a box with Docker
pre-harbor publish --repo O/N   push to Hugging Face; dry run without --execute
```

## 文档导航

- `docs/PAPER2HARBOR.md` — 主文档：add a paper、build、prove、collect、publish、网络细节、私有边界、任务布局、reward
- `docs/OSP_BATCH.md` — 退役中的 OSP 顺序批跑 harness（`tools/osp_batch.py`、`tools/osp_compare.py`）
- `docs/ARTIFACT_CONTRACTS.md` — OSP 会话的 artifact 契约
- `docs/OSP_FORK_WORKFLOW.md` — OSP fork 复现工作流
- `docs/STATUS_REPORT.md` — 早期 issues #4/#5/#6 状态报告
- `papers/README_*.md` — 各批语料收集备忘

## 仓库与数据集的关系

三个位置承载不同角色，发布物互不替代：

| 位置 | 角色 | 内容 | 访问 |
|---|---|---|---|
| `a-green-hand-jack/paper-review` (GitHub) | 源码与语料库 | 本项目代码、`papers/` 语料、文档；是**唯一**可编辑、可重建的来源 | 公开 |
| `Jack-Jieke-Wu/Paper-Reviewing-Exam` (HF dataset) | 可运行任务快照 | `pre-harbor publish` 生成的任务树（`paper-review-exam/<task-id>/`），`harbor run --repo` 直接运行；不含语料全量 | 公开 |
| `Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails` (HF dataset) | review 运行轨迹归档 | OSP/agent 每次运行的 `brain/`、manifest、log（`osp-trails/<paper>/<timestamp>/`） | 公开 |

关系与流：

1. **代码（GitHub）→ 任务（Exam）**：`pre-harbor publish` 把从 `papers/` 生成的 Harbor 任务上传到 Exam；生成的树重新审计后才发布，任务不被「写死」在仓库里，所以 Exam 的快照以它的 git commit/tag 为准。
2. **运行 → 轨迹（Trails）**：`--trail-repo Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails --upload` 把每次 review 的轨迹归档进 Trails；轨迹含审稿内容，是公开数据——**发布前确认你接受这些内容公开**。gitignore 保证本地 `osp-trails/` 不进入 GitHub 仓库。
3. **版本对应**：GitHub 的 `v0.1.0` 是代码版本；Exam 与 Trails 各自是独立数据集，内容随各自 upload 更新，不随 GitHub tag 自动同步。三处都已打 `v0.1.0` tag 标记同一 benchmark 的第一代快照（见 `CHANGELOG.md`）。