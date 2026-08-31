# Compression Induced Folding of a Sheet: An Integrable System

## 来源信息

- 群聊：「大代码模型」
- 分享人：么志远（通过 examples.zip 分享）
- 分享时间：2026-08-31 13:48
- 同事评论：examples.zip 里「这两篇写得很好」——本篇与 `transport_in_one_channel_luttinger_liquid` 是写作质量正面示例

## 论文信息

- 标题：Compression Induced Folding of a Sheet: An Integrable System
- 作者：Haim Diamant, Thomas A. Witten
- 单位：Raymond & Beverly Sackler School of Chemistry, Tel Aviv University；University of Chicago
- 年份：2011

## 文件

- `paper.tex`：LaTeX 源码
- `figs/`：fig1.pdf, fig2a.pdf, fig2b.pdf, fig3a.pdf, fig3b.pdf

## 备注

来自么志远发送的 examples.zip（其中「这两篇写得很好」）。作为写作质量正面示例用于 benchmark。
## paper.pdf 的来源

`paper.pdf` 不是原始投稿件，是我们从 `paper.tex` 编译出来的，供 benchmark 作为输入使用
（osp_batch 以 PDF 为 manuscript 入口）。

- 编译：`latexmk -pdf`，4 页
- `\documentclass{revtex4}` 在当前 TeX Live 中已不存在，编译时用一个 shim class 把选项
  转发给 `revtex4-2`。**排版结果因此与 2011 年的原始 revtex4 输出不完全一致**，评审
  Clarity 维度时须知道这一点：行距、图文位置可能有细微差异，但正文、公式、图内容未改动。
- `figs/` 里的图在编译时被复制到源码同级目录，因为 tex 里写的是 `\includegraphics{fig1.pdf}`
  而非 `figs/fig1.pdf`。
