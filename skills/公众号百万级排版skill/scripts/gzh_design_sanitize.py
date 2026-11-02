#!/usr/bin/env python3
"""gzh-design 乱码硬闸：消毒 + 门禁。

历史乱码根因：
  1) 文本节点写成字面量 &quot;（应是真 "）
  2) Markdown 反引号漏进正文
  3) linear-/radial-/conic-gradient 过多触发微信结构/版式乱

sanitize 只改：标签外文本的 &quot;/&amp;quot;/反引号；内联 background(-image) 渐变 → 纯色。
gate 在消毒后仍检出则 ERROR（pack 应拒绝）。

用法:
  python3 gzh_design_sanitize.py <file.html> [--write]
  有 ERROR 时 exit 1；打印 JSON {ok, fixes, errors}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SOLID = "#FCA5A5"  # 红白装饰线约定纯色

# 标签 vs 文本：粗分即可（公众号 HTML 无复杂脚本）
_TAG_OR_TEXT = re.compile(r"(<[^>]+>)", re.S)

# 内联 style 里 background / background-image 的渐变声明
# 捕获 property 名，值用括号平衡扫描
_BG_PROP = re.compile(
    r"(?:^|;)\s*(background(?:-image)?)\s*:\s*",
    re.I,
)
_GRAD_START = re.compile(
    r"(?:repeating-)?(?:linear|radial|conic)-gradient\s*\(",
    re.I,
)


def _balance_paren(s: str, open_idx: int) -> int:
    """open_idx 指向 '('；返回匹配 ')' 的下标，找不到返回 -1。"""
    depth = 0
    i = open_idx
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _sanitize_style_attr(style: str, fixes: list[str]) -> str:
    """把 style 里含 gradient 的 background(-image) 声明改成 background:#FCA5A5。"""
    out = []
    pos = 0
    for m in _BG_PROP.finditer(style):
        prop_end = m.end()  # 值起点
        # 找本声明结束（下一个未转义分号或字符串尾）
        # 但值内可能有 gradient(...) 含分号？通常没有；仍用括号平衡扫到分号
        j = prop_end
        n = len(style)
        # 跳过前导空白
        while j < n and style[j] in " \t":
            j += 1
        chunk = style[j:]
        if not _GRAD_START.match(chunk):
            continue
        # 从 gradient 的 '(' 平衡到 ')'，再吃可选空白与分号
        g = _GRAD_START.match(chunk)
        paren_open = j + g.end() - 1  # 指向 '('
        paren_close = _balance_paren(style, paren_open)
        if paren_close < 0:
            continue
        end = paren_close + 1
        while end < n and style[end] in " \t":
            end += 1
        had_semi = end < n and style[end] == ";"
        if had_semi:
            end += 1
        # m.start() 可能落在 ';' 上；保留前置 ';'
        start = m.start()
        lead = ""
        if style[start:start + 1] == ";":
            lead = ";"
            start += 1
            while start < m.start(1) and style[start] in " \t":
                start += 1
        # 写入未改区间 + 替换
        out.append(style[pos:m.start()])
        out.append(f"{lead}background:{SOLID}" + (";" if had_semi or end >= n else ""))
        # 若原声明后还有内容且我们没吃分号，确保分隔
        fixes.append(f"gradient→{SOLID}")
        pos = end
    out.append(style[pos:])
    return "".join(out)


def _sanitize_tag(tag: str, fixes: list[str]) -> str:
    """处理标签内 style="..." 的渐变。"""
    # 只动 style 属性值
    def repl(m: re.Match) -> str:
        quote = m.group(1)
        style = m.group(2)
        new_style = _sanitize_style_attr(style, fixes)
        return f"style={quote}{new_style}{quote}"

    return re.sub(
        r"""style\s*=\s*(["'])(.*?)\1""",
        repl,
        tag,
        flags=re.I | re.S,
    )


def _sanitize_text(text: str, fixes: list[str]) -> str:
    n_quot = text.count("&quot;") + text.count("&amp;quot;")
    if n_quot:
        text = text.replace("&amp;quot;", '"').replace("&quot;", '"')
        fixes.append(f"text:&quot;→\" ×{n_quot}")
    n_bt = text.count("`")
    if n_bt:
        text = text.replace("`", "")
        fixes.append(f"text:backtick-removed ×{n_bt}")
    return text


def sanitize(html: str) -> tuple[str, list[str]]:
    """消毒：标签外 &quot;/反引号；内联渐变背景→纯色。返回 (html, fixes)。"""
    fixes: list[str] = []
    parts = _TAG_OR_TEXT.split(html)
    out: list[str] = []
    for part in parts:
        if not part:
            continue
        if part.startswith("<") and part.endswith(">"):
            out.append(_sanitize_tag(part, fixes))
        else:
            out.append(_sanitize_text(part, fixes))
    return "".join(out), fixes


def _text_nodes(html: str) -> str:
    parts = _TAG_OR_TEXT.split(html)
    return "".join(p for p in parts if p and not (p.startswith("<") and p.endswith(">")))


def gate(html: str) -> list[str]:
    """消毒后门禁：仍有文本 &quot;、反引号、任何 *-gradient → ERROR 列表。"""
    errors: list[str] = []
    text = _text_nodes(html)
    n_quot = text.count("&quot;") + text.count("&amp;quot;")
    if n_quot:
        errors.append(f"ERROR text still has &quot;/&amp;quot; ×{n_quot}")
    n_bt = text.count("`")
    if n_bt:
        errors.append(f"ERROR text still has backtick ×{n_bt}")
    # 全 HTML（含 style）禁渐变
    n_grad = len(
        re.findall(
            r"(?:repeating-)?(?:linear|radial|conic)-gradient\s*\(",
            html,
            flags=re.I,
        )
    )
    if n_grad:
        errors.append(f"ERROR gradient still present ×{n_grad}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="gzh-design sanitize + gate")
    ap.add_argument("file")
    ap.add_argument("--write", action="store_true", help="写回原文件（消毒后）")
    a = ap.parse_args()
    path = Path(a.file)
    raw = path.read_text(encoding="utf-8")
    cleaned, fixes = sanitize(raw)
    errors = gate(cleaned)
    if a.write and cleaned != raw:
        path.write_text(cleaned, encoding="utf-8")
    ok = not errors
    print(
        json.dumps(
            {"ok": ok, "fixes": fixes, "errors": errors, "file": str(path)},
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
