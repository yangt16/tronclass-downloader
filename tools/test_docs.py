"""检查 README 与使用说明的交叉链接、锚点、关键内容、以及是否残留真实课名。

用法: python tools/test_docs.py
"""
import pathlib
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
readme = (ROOT / "README.md").read_text(encoding="utf-8")
usage_p = ROOT / "docs" / "使用说明.md"
usage = usage_p.read_text(encoding="utf-8")

bad = 0


def fail(msg):
    global bad
    bad += 1
    print(f"[FAIL] {msg}")


def slugs(text):
    """GitHub 风格锚点：小写、去标点、空格转 -"""
    out = set()
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if not m:
            continue
        t = m.group(2).strip().lower()
        t = re.sub(r"[：:，,。.、（）()「」【】\-_/\\`*\"'!?？!]", "", t)
        t = t.replace(" ", "-")
        out.add(t)
    return out


usage_slugs = slugs(usage)
readme_slugs = slugs(readme)


def check_links(text, base_slugs, other_file, other_slugs, label):
    for m in re.finditer(r"\]\(([^)\s]+)\)", text):
        target = m.group(1)
        if target.startswith("http") or target.startswith("#"):
            continue
        if "#" in target:
            f, anchor = target.split("#", 1)
        else:
            f, anchor = target, None
        # 文件存在？
        if f.startswith("docs/") or f == "docs/使用说明.md":
            p = ROOT / f
        elif f == "../README.md":
            p = ROOT / "README.md"
        else:
            p = ROOT / f
        if not p.exists():
            fail(f"{label}: 链接指向的文件不存在 -> {target}")
            continue
        if anchor:
            pool = usage_slugs if p == usage_p else readme_slugs
            if anchor.lower() not in pool:
                fail(f"{label}: 锚点不存在 -> {target}")


check_links(readme, readme_slugs, None, None, "README")
check_links(usage, usage_slugs, None, None, "使用说明")

# 课程名残留
for name, text in (("README", readme), ("使用说明", usage)):
    for kw in ("计网", "计算机网络", "软件设计", "操作系统"):
        if kw in text:
            fail(f"{name}: 出现课程名 {kw}")

# 关键内容是否都还在
must_in_usage = [
    "手动版", "书签", "只要音轨", "只要视频", "环境变量", "故障排查",
    "test_naming", "test_modes", "sec-ch", "断点续传",
]
must_in_readme = [
    "docs/使用说明.md", "下视频和音频.cmd", "只要音轨.cmd", "只要视频.cmd",
    "免责声明", "增量下载",
]
for kw in must_in_usage:
    if kw not in usage:
        fail(f"使用说明: 缺少关键内容 {kw}")
for kw in must_in_readme:
    if kw not in readme:
        fail(f"README: 缺少关键内容 {kw}")

print(f"\nREADME {len(readme.splitlines())} 行 / 使用说明 {len(usage.splitlines())} 行")
print("全部通过" if bad == 0 else f"{bad} 项失败")
sys.exit(0 if bad == 0 else 1)
