r"""
import_lists.py - 把浏览器下载的抓取清单自动搬进 lists\\。

scrape_course.js 在浏览器里导出 <课程名>.txt 到「下载」文件夹，
本脚本负责把它合并进 lists\\<课程名>.txt（已存在则按 URL 去重合并）。

用法:
    python import_lists.py                 # 扫默认下载文件夹
    python import_lists.py --downloads D:\some\dir
    python import_lists.py --dry-run       # 只看会做什么
"""
import argparse
import os
import pathlib
import re
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
LISTS = ROOT / "lists"
DUP_SUFFIX = re.compile(r"\s*\(\d+\)$")     # 浏览器重名会存成 "计网 (1).txt"


def default_downloads():
    return pathlib.Path(os.path.expanduser("~")) / "Downloads"


def is_scraped(path):
    """认得出是我们抓取脚本导出的文件：含 previewToken，或首行带自动抓取标记。"""
    try:
        head = path.read_text(encoding="utf-8-sig", errors="replace")[:4000]
    except Exception:
        return False
    return "previewToken=" in head


def urls_of(text):
    return [ln.strip() for ln in text.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
            and ln.strip().lower().startswith("http")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--downloads", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    dl = pathlib.Path(a.downloads) if a.downloads else default_downloads()
    if not dl.exists():
        return 0
    LISTS.mkdir(exist_ok=True)

    moved = 0
    for src in sorted(dl.glob("*.txt")):
        if not is_scraped(src):
            continue
        name = DUP_SUFFIX.sub("", src.stem).strip() or "course"
        dest = LISTS / f"{name}.txt"
        new_urls = urls_of(src.read_text(encoding="utf-8-sig", errors="replace"))
        if not new_urls:
            continue

        existing = []
        if dest.exists():
            existing = urls_of(dest.read_text(encoding="utf-8-sig", errors="replace"))
        merged = existing + [u for u in new_urls if u not in existing]

        print(f"[import] {src.name} -> {dest.name}"
              f"（新增 {len(merged)-len(existing)} 条，共 {len(merged)} 条）")
        if a.dry_run:
            continue
        header = (f"# {name} · 由 import_lists.py 合并\n"
                  f"# 每行一条地址；previewToken 地址会在下载时自动换成直链\n")
        dest.write_text(header + "\n".join(merged) + "\n", encoding="utf-8")
        try:
            src.unlink()          # 搬走而不是留副本，避免下次重复导入
        except Exception:
            pass
        moved += 1

    if moved:
        print(f"[import] 共导入 {moved} 份清单")
    return 0


if __name__ == "__main__":
    sys.exit(main())
