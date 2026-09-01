# OSP 领域适配评审标准 — 进展报告

*2026-08-30 · issues #4 #5 #6 · fork `a-green-hand-jack/open-scholar-peer@d2a4827`*

> **Corpus update (2026-08-31):** 新增两个含版本对的 benchmark 论文
> `lieb_schultz_mattis_charge_transport`（v1/v2，Zenodo 22081764 / 22140090）和
> `chapoton_q_zeta_numerators`（v1/v2，Zenodo 22099574 / 22171042）；同时移除
> 唯一一份无 tex 源码的 `hidden_arrow_order_escape`（纯 PDF 草稿）。语料现为
> 23 篇论文 / 27 个版本任务（含 erdos973 v1/v2/v3，各版本已补 arXiv 源；
> 2026-08-31 群收集新增的 6 篇已补齐 PDF/tex，全部可评审）。
> 本文下方的 before/after 审核针对的是更新前的 18-version 语料，数字保持
> 不变；`osp_compare.py` 已改为支持任意数量版本的对比（`--versions` /
> `--paper-dir`，见 `OSP_BATCH.md`）。

Open ScholarPeer（OSP）的默认评审标准是照着 ML/NLP/CS 会议评审表写的，但这个项目实际评审的 18 篇论文全部是数学 / 数学物理证明。这份报告记录：为什么要改、改了什么、跑了什么 benchmark、独立审核出了什么结论，以及现在还有哪些已知问题。

## 一眼看结果

| 指标 | 数值 |
|---|---|
| 论文 benchmark 覆盖 | 18/18 |
| improved | 9 |
| no meaningful change | 3 |
| mixed | 6 |
| 发现的 regression | 2 |
| 已修复并重跑验证 | 1 |

## 1. 三个 issue 现在的状态

- **#4 建立 Fork 二次开发与 Benchmark 迭代工作流 — 基本完成。** 建立了 OSP 个人 fork，跑通 sync → parity → installer 全套检查，把 15 篇论文 + erdos973 v1/v2/v3 定为回归 benchmark corpus。本报告的所有改动都遵循这套工作流落地。
- **#5 Revision-aware Reviewer — 仅规划，未实现。** 承接 #3 的 inconclusive 结论：让 reviewer 能区分"已解决/仍未解决/新引入/回归"的问题，而不是三版论文都给出同一个 recommendation。目前只完成设计方案，还没有动手改 fork 代码。erdos973 v1/v2/v3 的 PDF 已经在 benchmark 机器上就绪，可以随时开工。
- **#6 领域适配评审标准 — 已实现 · 已跑 benchmark · 已独立审核。** 本报告的主体，见下文。

## 2. Fork 里实际改了什么

两次提交，都在 `a-green-hand-jack/open-scholar-peer@main`。

### `d8780e0` — Add domain-adaptive review criteria for theoretical/proof papers

- `0-osp-onboarding.md` 新增 step 3.5：判断 `paper.review_mode`（theoretical / empirical / other）和 `paper.field`，写入 session.json —— 两个全新字段，没有复用已有的 `paper.type`（那个字段已经被 batch runner 挪用来存文件扩展名了）。
- 新文件 `defaults/generic_review_guidelines_theoretical.md`：面向证明型论文的 fallback 标准，不出现 baseline/dataset/ablation。
- `osp-summary-agent`：结构化摘要第三段按 review_mode 二选一 —— Evidence(E) 或全新的 Formal Content（引理/定理清单、证明技巧、依赖的已有结果）。
- `osp-baseline-scout-agent`：把"missing baseline/dataset"重新映射为"最接近的已有定理/结果"和"未覆盖的边界情形"。
- `osp-reviewer-agent`：criterion 措辞改成继承 onboarding 已经选好的 guidelines，不再硬编码 ML 用语。
- 全部 14 个工具 adapter 同步，`test_parity.py` 14/14、`test_install.sh` 全部通过。

### `d2a4827` — Fix .gitignore silently excluding new files under extensions/.claude/

- 独立审核过程中发现：`.gitignore` 里裸的 `.claude/` 意外把 `extensions/.claude/`（这个项目实际使用的 Claude Code adapter 产物目录）也忽略掉了，导致新增文件在 14 个工具里唯独 `.claude` 这一个从未被真正提交。
- 改成锚定到仓库根目录的 `/.claude/`，和已有的 `/.agents/` 写法一致；补提交了缺失文件。
- 检查了 `.gitignore` 里其余模式，没有发现类似碰撞——这是一次性 bug，不是系统性问题。

## 3. Benchmark：18 篇论文 before / after

未改动 OSP 的基线（before）本来就已经跑完；改动之后（after）在同一台 Ubuntu 机器上，用完全相同的配置（`openai/gpt-5.6-sol` · `medium` · `opencode` · `arxiv`）重新跑了一遍全部 18 篇。全部 `completed`，全部已归档到私有 Hugging Face 数据集 `Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails`（曾用名 `Jack-Jieke-Wu/osp-trails`）。

审核由三个互不知情、互不共享上下文的独立 agent 完成，每人负责 6 篇，要求带引用原文、不必给面子。完整证据见 `docs/DOMAIN_ADAPTIVE_AUDIT.md`。

| 论文 | 结论 |
|---|---|
| a-proof-of-shors-orthogonal-measurement-conjecture | mixed · 真实 regression |
| erdos973--v1 | improved |
| erdos973--v2 | no meaningful change |
| erdos973--v3 | no meaningful change |
| hidden-arrow-order-escape | mixed，偏 improved |
| on-the-first-and-the-second-borel-cantelli-lemmas | mixed，略有改进 |
| residual-bounds-for-schur-stable-polynomials | improved（modest） |
| solution-p4378 | improved（modest） |
| solution-p4383 | mixed · recommendation 跳变疑似噪声 |
| solution-p4400 | improved（首跑失败，修复后重跑通过） |
| solution-p8534 | improved（抓到真实数学漏洞） |
| solution-p8535 | no meaningful change |
| solution-p8536 | improved |
| solution-p8559 | mixed · 覆盖面平移不算净增益 |
| solution-p8560 | improved（recommendation 跳变疑似噪声） |
| solution-p8607 | improved（modest） |
| solution-p8608 | improved |
| solution-p8610 | mixed · recommendation 跳变疑似噪声 |

**没有发现的问题：** 三个 agent 都没有找到"ML 框架被强行套到证明论文上"这个最初担心的失败模式——未改动版本本身对无实验论文的处理就还算得体（"Datasets: none; this is a self-contained theoretical mathematics paper"）。

**真正挖到的正面发现：**
- **erdos973-v1**：改动后的 baseline-scout 发现 v1 已经被同一篇论文几天后发布的 v3 定量超越，reviewer 据此把结论从"Minor revision"改成"Major revision advised"——理由是版本时效性，不是证明本身有错，这是原版完全没发现的。
- **solution-p8534**：抓到一个原版完全漏掉的真实数学漏洞——Lemma 3.1 的前提条件不足以支撑证明里用到的表达式。
- 多篇论文（solution-p4378、solution-p4383、hidden-arrow-order-escape）挖到了原版遗漏的具体文献比对对象。

## 4. 已知问题

| 问题 | 状态 |
|---|---|
| solution-p4400 首跑失败 | **已修复**——根因是上面的 `.gitignore` bug，已修复并重跑验证通过 |
| 混合"证明+真实数值实验"论文的细节丢失 | **未修复**，留在 #6 checklist。a-proof-of-shors 的 baseline-scout 输出从 5 个具体缺口（2 个高优先级）退化成 1 个低优先级；两篇论文的结构化摘要都丢了部分具体数值。设计里"数值切片保留 ML 框架"这条规则对这个真实案例没生效，需要更细致地改 `osp-baseline-scout-agent`/`osp-summary-agent`，目前语料库只有 2 个样本，暂不着急修 |
| Recommendation 跳变噪声 | 方法论限制，非本次改动的 bug。4 篇论文的 recommendation 出现整档跳变，但支撑事实几乎没变，三个独立 agent 都判断更像模型采样噪声。提示只跑一次 before/after 不足以区分改动效果和噪声，直接关联 #5 的设计，建议未来同配置跑 N>1 次 |
| `04_missing_baselines.md` 标题新旧混用 | cosmetic，未修复。部分文件标题还是旧的 "Missing Baselines & Datasets"，一份文件（solution-p8608）新旧小标题拼在一起 |
| #5 Revision-aware Reviewer 尚未实现 | 规划完成，未开工。erdos973 v1/v2/v3 的 PDF 已就绪，随时可以开始实现和验证 |

---

*fork commits: d8780e0 · d2a4827 · trails: Jack-Jieke-Wu/Paper-Reviewing-Exam-Trails (HF, private) · audit doc: docs/DOMAIN_ADAPTIVE_AUDIT.md*
