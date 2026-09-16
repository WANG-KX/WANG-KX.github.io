#!/usr/bin/env python3
"""扫描播客/视频总结目录，并把确认过的文档转成博客的 Jekyll post。

配合 ai-summary-sync skill 使用：

  python3 sync.py list
      列出所有 *_公众号版.html，输出 JSON（title/date/draft_excerpt/synced 等），
      synced=true 表示该标题的文章已在 _posts 里。

  python3 sync.py add <源文件路径> --slug <english-kebab-slug> [--excerpt ...] [--title ...] [--date ...]
      把源 HTML 转成 _posts/YYYY-MM-DD-<slug>.html（tags: [AI 总结]）。
      title/date 默认自动提取（<title> 去掉「深度报告」；日期取「生成于」）。
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

SRC_ROOT = Path("/Users/wang/WorkBuddy/播客-视频-总结文档")
POSTS = Path(os.environ.get("BLOG_POSTS_DIR", "/Users/wang/Documents/code/WANG-KX.github.io/_posts"))
TAG = "AI 总结"

FOOTER_RE = re.compile(
    r'\s*<p style="text-align:center;font-size:12\.5px;color:#9aa0a8;[^>]*>生成于[^<]*</p>\s*'
)


def extract_title(html: str) -> str | None:
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    if not m:
        return None
    return re.sub(r"\s*深度报告\s*", "", m.group(1)).strip()


def extract_body(html: str) -> str:
    """抽取 <body> 内容，去掉「深度报告」字样与文末生成脚注。"""
    m = re.search(r"<body[^>]*>\s*(.*?)\s*</body>", html, re.S)
    if not m:
        sys.exit(f"错误：{html[:0]}文档中找不到 <body>")
    body = m.group(1)
    body = body.replace("深度报告", "")
    return FOOTER_RE.sub("\n", body).strip()


def gen_date(html: str, path: Path) -> str:
    m = re.search(r"生成于 (\d{4}-\d{2}-\d{2})", html)
    if m:
        return m.group(1)
    return datetime.date.fromtimestamp(path.stat().st_mtime).isoformat()


def draft_excerpt(html: str) -> str:
    """取「顶层结论」一段作为摘要草稿，交给上层润色。"""
    m = re.search(r"顶层结论[^<]*</p>(.*?)</section>", html, re.S)
    if not m:
        return ""
    txt = re.sub(r"<[^>]+>", "", m.group(1))
    return re.sub(r"\s+", " ", txt).strip()


def existing_titles() -> set[str]:
    out = set()
    for p in POSTS.glob("*.html"):
        m = re.search(r'^title: "(.*)"$', p.read_text(encoding="utf-8", errors="ignore"), re.M)
        if m:
            out.add(m.group(1))
    return out


def yq(s: str) -> str:
    """YAML 双引号字符串转义。"""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def cmd_list() -> None:
    synced = existing_titles()
    items = []
    for f in sorted(SRC_ROOT.rglob("*_公众号版.html")):
        html = f.read_text(encoding="utf-8")
        title = extract_title(html)
        items.append(
            {
                "path": str(f),
                "dir": f.parent.name,
                "title": title,
                "date": gen_date(html, f),
                "draft_excerpt": draft_excerpt(html),
                "synced": title in synced,
            }
        )
    items.sort(key=lambda x: x["date"], reverse=True)
    print(json.dumps(items, ensure_ascii=False, indent=2))


def cmd_add(args: argparse.Namespace) -> None:
    slug = args.slug.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        sys.exit(f"错误：slug 非法（只允许小写字母/数字/连字符）：{slug!r}")

    f = Path(args.path)
    if not f.is_file():
        sys.exit(f"错误：源文件不存在：{f}")
    html = f.read_text(encoding="utf-8")

    title = args.title or extract_title(html)
    date = args.date or gen_date(html, f)
    excerpt = args.excerpt or draft_excerpt(html)
    if not title:
        sys.exit("错误：无法提取标题，请用 --title 指定")

    dst = POSTS / f"{date}-{slug}.html"
    if dst.exists():
        sys.exit(f"错误：目标文件已存在：{dst}")

    fm = (
        "---\n"
        "layout: post\n"
        f'title: "{yq(title)}"\n'
        f"date: {date}\n"
        f"tags: [{TAG}]\n"
        f'excerpt: "{yq(excerpt)}"\n'
        "---\n\n"
    )
    dst.write_text(fm + extract_body(html) + "\n", encoding="utf-8")
    print(f"已写入 {dst}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="列出所有源文档及收录状态（JSON）")
    add = sub.add_parser("add", help="把一篇源文档转成 Jekyll post")
    add.add_argument("path", help="源 HTML 文件路径")
    add.add_argument("--slug", required=True, help="文章 slug（英文 kebab-case，用于 URL 与文件名）")
    add.add_argument("--title", help="覆盖自动提取的标题")
    add.add_argument("--date", help="覆盖自动提取的日期 (YYYY-MM-DD)")
    add.add_argument("--excerpt", help="摘要；缺省用「顶层结论」草稿")
    args = parser.parse_args()
    cmd_list() if args.cmd == "list" else cmd_add(args)


if __name__ == "__main__":
    main()
