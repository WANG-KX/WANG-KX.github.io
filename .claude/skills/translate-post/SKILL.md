---
name: translate-post
description: 把本博客的一篇中文 Jekyll post 翻译成英文版，生成 _posts/ 下带 lang/ref/permalink 的英文文件，并构建验证。当用户想翻译某篇文章、给文章生成英文版、补翻译时使用。
---

# 翻译博客文章为英文版

把一篇中文 post 翻译成英文版，写入 `_posts/`，与中文版自动配对（语言切换按钮依赖 `ref` 字段）。

## 1. 定位文章

用户会给出文章路径、标题或 slug 之一；都不给时，按日期从新到旧列出中文文章（`_posts/` 下文件名不含 `-en` 的）让用户选。

先检查英文版是否已存在：查找 `*-{slug}-en.*`。已存在时用 AskUserQuestion 问「覆盖更新还是跳过」，不要直接覆盖。

## 2. 生成英文版文件

**文件命名**：在原文件名 slug 后加 `-en`，扩展名不变：
- `2026-09-12-why-phones-fold.md` → `2026-09-12-why-phones-fold-en.md`
- `2026-08-17-ai-inference-chip-research.html` → `2026-08-17-ai-inference-chip-research-en.html`

**front matter**：以原文为基础，做以下调整：

```yaml
lang: en
ref: <中文文件名去掉扩展名>   # 如 2026-09-12-why-phones-fold（与中文版的 ref 一致）
permalink: /en/posts/YYYY/MM/DD/<中文版 slug>/
```

- 中文 post 也带 `ref`（值同上），两侧靠相同的 `ref` 配对
- `date` 与中文版完全一致（关系到语言切换的 URL 推导，必须相同）
- `title`、`excerpt` 翻译成英文；excerpt 压缩为 1–2 句
- `tags` **保留中文原样**（列表页和 AI 总结归档依赖中文 tag 过滤）
- 其余 front matter 字段（cover 等）原样保留

**正文翻译原则**：

- **完整翻译**（不是摘要），语气与原文一致，自然的英文，不要逐字直译
- 保留全部 Markdown 结构（标题层级、列表、表格、粗斜体）
- 代码块、命令、文件路径、图片路径（`/assets/...`）、外链 URL 一律不动
- HTML 型 post（sync.py 产出的 AI 总结、含 Chart.js 的报告）：**只翻译可见文本节点**，标签、属性、内联样式、`<script>`、`<style>` 内容一律不动；表格单元格文本要翻译但结构不变
- 数字、日期、模型名、公司名、人名、论文名保持原样；中文特有说法意译
- 常用术语对照：具身智能→embodied AI、占据栅格→occupancy、稠密建图→dense mapping、周报→weekly notes、端到端→end-to-end、视觉-语言-动作模型→VLA；3DGS、NeRF、SLAM、VLA 等缩写不译

## 3. 构建验证

在仓库根目录：

```bash
bundle exec jekyll build
```

确认无报错，并抽查：

- `_site/en/posts/.../<slug>/index.html` 已生成
- 中文文章页（`_site/posts/.../`）nav 中出现了 `lang-toggle` 的 EN 按钮
- 英文文章页出现「中文」按钮，href 指回中文 URL

## 4. 收尾

- 汇报生成的文件与两个语言的 URL（本地预览加 `http://127.0.0.1:4000` 前缀）
- **询问用户是否提交推送到 GitHub**，不要未经确认自动 commit/push；提交时不要夹带无关的未跟踪文件
