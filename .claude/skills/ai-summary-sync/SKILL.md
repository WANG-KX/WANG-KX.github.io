---
name: ai-summary-sync
description: 扫描 /Users/wang/WorkBuddy/播客-视频-总结文档 下的播客/视频总结（*_公众号版.html），逐个向用户确认后同步到本博客的「AI 总结」tag。当用户想更新 AI 总结、检查有没有新的总结文章、同步总结文档时使用。
---

# 同步 AI 总结到个人博客

把 WorkBuddy 里的播客/视频总结（公众号版 HTML）逐篇确认后转成本仓库 `_posts/ai-summaries/` 下的 Jekyll post（AI 总结单独放这个子目录，与 `_posts/` 根目录的手工博客隔离开）。
所有转换规则已封装在脚本 `sync.py`（与本 skill 同目录）中，不要手写 HTML 转换逻辑。

## 1. 扫描

```bash
python3 /Users/wang/Documents/code/WANG-KX.github.io/.claude/skills/ai-summary-sync/sync.py list
```

输出 JSON 数组，每项包含：

- `path` / `dir`：源文件路径与其所在目录名
- `title`：文章标题（已自动去掉「深度报告」字样）
- `date`：日期，取文档内「生成于」日期
- `draft_excerpt`：「顶层结论」段落纯文本，作为摘要草稿
- `synced`：`true` 表示该标题的文章已收录在 `_posts/ai-summaries/`，**直接跳过**

若没有 `synced == false` 的项，告诉用户"没有新文章"并结束。
若目录里根本没有 `*_公众号版.html`，同样如实告知。

## 2. 逐个确认

对每篇新文章（按 `date` 从新到旧），**一次一篇**用 AskUserQuestion 询问：

- question：`把《<title>》放进个人主页的"AI 总结"？`
- options：
  1. `放入`（推荐）—— 按现有流程转成 Jekyll post 并进入 AI 总结列表
  2. `跳过` —— 本次不同步

用户选「跳过」就不再提这篇，继续问下一篇；全部问完后汇总。

## 3. 放入（仅对用户确认的）

每篇执行：

1. **拟 slug**：从标题提炼简洁的英文 kebab-case（参考已有命名：`figure-jed-yang`、`tesla-cybercab`、`dyna-york-yang`、`generalist-gen1`）。
2. **润色 excerpt**：以 `draft_excerpt` 为基础，压缩成 1–2 句中文摘要（保留原意，注意把双引号转成「」以免破坏 YAML）。
3. **转换**：
   ```bash
   python3 <skill目录>/sync.py add "<path>" --slug <slug> --excerpt "<润色后的摘要>"
   ```
   `title`/`date` 默认自动提取，一般不用传；脚本会拒绝重复 slug 和空 slug。
4. **构建验证**：在博客仓库根目录跑 `bundle exec jekyll build`，确认无报错。

## 4. 收尾

- 汇报本次「放入 / 跳过」清单及文章 URL（`/posts/YYYY/MM/DD/<slug>/`，本地预览加 `http://127.0.0.1:4000` 前缀）
- 列表页（`/ai-summary/`）与导航是按 tag 自动收录的，**无需改动任何页面**
- **询问用户是否提交推送到 GitHub**，不要未经确认自动 commit/push；提交时不要夹带无关的未跟踪文件

## 约定

- 只处理 `*_公众号版.html`；同一目录下其他文件忽略
- post 一律 `tags: [AI 总结]`、`layout: post`，文件名 `YYYY-MM-DD-<slug>.html`
- 脚本已自动处理：抽取 `<body>` 内容（源文件均为纯内联样式）、去掉「深度报告」、去掉文末「生成于 … 公众号适配版」脚注
