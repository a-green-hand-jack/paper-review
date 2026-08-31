# Transport in a One-Channel Luttinger Liquid

## 来源信息

- 群聊：「大代码模型」
- 分享人：么志远（通过 examples.zip 分享）
- 分享时间：2026-08-31 13:48
- 同事评论：examples.zip 里「这两篇写得很好」——本篇与 `compression_induced_folding_of_a_sheet` 是写作质量正面示例

## 论文信息

- 标题：Transport in a One-Channel Luttinger Liquid
- 作者：C. L. Kane（University of Pennsylvania），Matthew P. A. Fisher（IBM Research, T. J. Watson Research Center）
- 年份：1992

## 文件

- `paper/main.tex`：LaTeX 源码（2026-08-31 从根目录 `paper.tex` 归一化为 `paper/` 布局；原 pandoc 导出引用 `./images/` 的图路径已改为 `figs/`）
- `paper/figs/fig1.jpg`：图
- `paper/main.pdf`：Ubuntu TeXLive 2026 xelatex 编译产物（7 页，2026-08-31）

## 备注

来自么志远发送的 examples.zip（其中「这两篇写得很好」）。作为写作质量正面示例用于 benchmark。
## paper.pdf 的来源

`paper.pdf` 不是原始投稿件，是我们从 `paper.tex` 编译出来的，供 benchmark 作为输入使用
（osp_batch 以 PDF 为 manuscript 入口）。

- 编译：`latexmk -xelatex`，7 页
- `paper.tex` 本身已是重排版本（`article` + `fontspec`，非 1992 年 PRB 原始排版），
  评审 Clarity 维度时须知道：**看到的排版是转录者的，不是作者的**。正文与公式内容未改动。
- `figs/fig1.jpg` 在编译时被复制到 `images/`，因为 tex 里引用的是 `./images/fig1.jpg`。
