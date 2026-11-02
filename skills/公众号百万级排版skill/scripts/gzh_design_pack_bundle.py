#!/usr/bin/env python3
"""Pack gzh-design HTML + cover + local images into a publish_remote-compatible bundle.

Usage:
  python3 gzh_design_pack_bundle.py <ws> --html <ws>/build_gzh_design/article_排版_….html \
      [--cover <ws>/build/cover/cover_900x383.jpg] [--out <ws>/build_gzh_design/bundle]

- Rewrites local img src (assets/… or relative) to bundle filenames.
- Keeps title/author/digest from article.md frontmatter when present.
- Does NOT call the network; publish_remote still uploads.
"""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

# 乱码硬闸：pack 强制 sanitize + gate（见 gzh_design_sanitize.py / 排版-乱码硬闸.md）
_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
from gzh_design_sanitize import sanitize, gate  # noqa: E402

IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

def frontmatter(md: Path):
    text = md.read_text(encoding="utf-8")
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            block = text[3:end].strip()
            if yaml:
                meta = yaml.safe_load(block) or {}
            else:
                for line in block.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip().strip('"').strip("'")
            body = text[end + 4:].lstrip("\n")
            return meta, body
    return {}, text

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ws")
    ap.add_argument("--html", required=True)
    ap.add_argument("--cover")
    ap.add_argument("--out")
    ap.add_argument("--title"); ap.add_argument("--author", default="袁六伟"); ap.add_argument("--digest")
    a = ap.parse_args()
    ws = Path(a.ws).resolve()
    html_path = Path(a.html).resolve()
    html = html_path.read_text(encoding="utf-8")
    # strip preview wrapper if any
    if "<!DOCTYPE" in html or "<html" in html.lower():
        m = re.search(r"(<section[\s\S]*</section>)", html, re.I)
        if not m:
            sys.exit("HTML 不是干净 section 片段，且抽不出 section")
        html = m.group(1)

    # 强制消毒 + 门禁（拒绝带 &quot;/反引号/gradient 的稿进 bundle）
    html, san_fixes = sanitize(html)
    san_errors = gate(html)
    if san_errors:
        print(json.dumps({"ok": False, "stage": "sanitize_gate", "fixes": san_fixes, "errors": san_errors}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    # 旁路落盘，便于对照；article.json 用消毒后 html
    side = html_path.with_name(html_path.stem + ".sanitized.html")
    side.write_text(html, encoding="utf-8")
    if san_fixes:
        print(json.dumps({"sanitize_fixes": san_fixes, "sanitized": str(side)}, ensure_ascii=False), file=sys.stderr)

    meta, _ = frontmatter(ws / "article.md") if (ws / "article.md").exists() else ({}, "")
    title = a.title or meta.get("title") or ws.name
    author = a.author or meta.get("author") or "袁六伟"
    digest = a.digest or meta.get("digest") or ""

    out = Path(a.out).resolve() if a.out else (ws / "build_gzh_design" / "bundle")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # map local images
    srcs = re.findall(r'(?:src|data-src)=["\']([^"\']+)["\']', html, flags=re.I)
    images = {}
    for src in srcs:
        if src.startswith("http://") or src.startswith("https://") or src.startswith("data:"):
            continue
        # resolve relative to ws or html dir
        cand = (ws / src).resolve() if not Path(src).is_absolute() else Path(src)
        if not cand.exists():
            cand = (html_path.parent / src).resolve()
        if not cand.exists():
            # try assets basename
            cand = ws / "assets" / Path(src).name
        if not cand.exists() or cand.suffix.lower() not in IMG_EXTS:
            print(f"WARN missing image: {src}", file=sys.stderr)
            continue
        h = hashlib.sha1(cand.read_bytes()).hexdigest()[:10]
        name = f"img_{h}{cand.suffix.lower().replace('.jpeg','.jpg')}"
        if src not in images:
            shutil.copy2(cand, out / name)
            # wechat_draft looks up content src in images.json keys; after rewrite keys must be new names
            images[name] = name
            html = html.replace(src, name)

    cover = Path(a.cover).resolve() if a.cover else (ws / "build" / "cover" / "cover_900x383.jpg")
    if not cover.exists():
        # fallback any jpg in cover dir
        cdir = ws / "build" / "cover"
        alts = sorted(cdir.glob("cover_900x383.*")) if cdir.exists() else []
        if not alts:
            sys.exit(f"缺少封面: {cover}")
        cover = alts[0]
    shutil.copy2(cover, out / "cover.jpg")

    art = {
        "article_type": "news",
        "title": title,
        "author": author,
        "digest": digest[:120],
        "content": html,
        "content_source_url": "",
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
        "pic_crop_235_1": "0_0_1_1",
        "pic_crop_1_1": "0.574468_0_1_1",
    }
    (out / "article.json").write_text(json.dumps(art, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "images.json").write_text(json.dumps(images, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "bundle": str(out), "title": title, "images": len(images)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
