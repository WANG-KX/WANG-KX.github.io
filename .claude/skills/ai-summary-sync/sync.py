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

STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S)
# 部分文档（如深度调研报告）样式集中在 <head><style>、正文靠 class；
# 嵌入博客后需把样式限定在一个包裹层内，避免 html/body/h2 等全局选择器污染整站。
DOC_SCOPE = "wd-doc"


def scope_css(css: str, scope: str) -> str:
    """把 CSS 的所有选择器限定到 scope 下（:root/html/body 映射到 scope 本身）。

    支持嵌套的 @media/@supports；@keyframes 等其他 at-rule 原样保留。
    """
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

    def prefix_sel(sel: str) -> str:
        s = sel.strip()
        if not s:
            return ""
        if s in (":root", "html", "body"):
            return scope
        if s == "*":
            return f"{scope}, {scope} *"
        return f"{scope} {s}"

    def prefix_rules(block: str) -> str:
        def repl(m: re.Match) -> str:
            sels = ", ".join(
                p for p in (prefix_sel(x) for x in m.group(1).split(",")) if p
            )
            return f"{sels}{{{m.group(2)}}}"

        return re.sub(r"([^{}]+)\{([^{}]*)\}", repl, block)

    out, i, n = [], 0, len(css)
    while i < n:
        m = re.compile(r"@([\w-]+)[^{]*\{").search(css, i)
        if not m:
            out.append(prefix_rules(css[i:]))
            break
        if m.start() > i:
            out.append(prefix_rules(css[i : m.start()]))
        depth, j = 1, m.end()
        while j < n and depth:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
            j += 1
        inner = css[m.end() : j - 1]
        if m.group(1) in ("media", "supports"):  # 内容仍是规则集，递归处理
            head = re.match(r"@[\w-]+[^{]*", m.group(0)).group(0)
            out.append(f"{head}{{{scope_css(inner, scope)}}}")
        else:  # @keyframes 等：内部不是选择器，原样保留
            out.append(css[i:j])
        i = j
    return "".join(out)


def extract_styled_body(html: str) -> str:
    """带头部样式的文档：返回「作用域 <style> + 包裹层正文」，正文仍走通用清洗。"""
    css = STYLE_RE.search(html)
    body = extract_body(html)
    scoped = scope_css(css.group(1), f".{DOC_SCOPE}")
    return f'<style scoped>\n{scoped}\n</style>\n\n<div class="{DOC_SCOPE}">\n{body}\n</div>'


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
        "lang: zh\n"
        f"ref: {date}-{slug}\n"
        "layout: post\n"
        f'title: "{yq(title)}"\n'
        f"date: {date}\n"
        f"tags: [{TAG}]\n"
        f'excerpt: "{yq(excerpt)}"\n'
        "---\n\n"
    )

    content = extract_styled_body(html) if STYLE_RE.search(html) else extract_body(html)
    if args.assets:
        src_dir, url_base = args.assets.split(":", 1)
        src_dir = Path(src_dir)
        if not src_dir.is_absolute():  # 相对路径基于源文件所在目录
            src_dir = f.parent / src_dir
        content = copy_assets(content, src_dir, url_base)
    dst.write_text(fm + content + "\n", encoding="utf-8")
    print(f"已写入 {dst}")


def copy_assets(content: str, src_dir: Path, url_base: str) -> str:
    """把正文里引用的本地资源复制到博客 assets/，并改写引用路径。

    url_base 形如 /assets/posts/2026-09-19-<slug>（站点根相对路径）。
    """
    if not src_dir.is_dir():
        sys.exit(f"错误：资源目录不存在：{src_dir}")
    dst_root = POSTS.parent / url_base.strip("/")
    n = 0
    for f in sorted(src_dir.iterdir()):
        if not f.is_file():
            continue
        ref = f'"{src_dir.name}/{f.name}"'
        if ref not in content:
            continue
        dst_root.mkdir(parents=True, exist_ok=True)
        (dst_root / f.name).write_bytes(f.read_bytes())
        content = content.replace(ref, f'"{url_base.rstrip("/")}/{f.name}"')
        n += 1
    print(f"已复制 {n} 个资源文件到 {dst_root}")
    return content


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
    add.add_argument(
        "--assets",
        help="本地资源映射 <源目录>:<站点URL前缀>（如 gifs:/assets/posts/2026-09-19-<slug>），"
        "会把正文引用的文件复制到博客 assets/ 并改写路径",
    )
    args = parser.parse_args()
    cmd_list() if args.cmd == "list" else cmd_add(args)


if __name__ == "__main__":
    main()
