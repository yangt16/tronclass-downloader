"""
make_index.py - 生成"已下载清单"（索引），放到 lists\\<课程名>.md

和 lists\\*.txt 的区别（很重要）:
    lists\\<课程>.txt  = 待下载队列，批量模式会去下载里面的地址
    lists\\<课程>.md   = 已下载索引，只是记录；批量模式只认 .txt，不会碰它

用 .md 就是为了让两种东西同一个目录却不打架。
"""
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lectures import FFPROBE, ROOT, course_name  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SPAN_RE = re.compile(r"_(\d{8})_(\d{6}-\d{6})\.mp4$")


def dur_of(path):
    try:
        r = subprocess.run([str(FFPROBE), "-v", "error", "-show_entries",
                            "format=duration", "-of", "default=nw=1:nk=1", str(path)],
                           capture_output=True, text=True, timeout=120)
        return float((r.stdout or "0").strip() or 0)
    except Exception:
        return 0.0


def hhmm(sec):
    s = int(sec)
    return f"{s//3600}:{s%3600//60:02d}:{s%60:02d}"


def build(outdir):
    rows = []
    for day in sorted(p for p in outdir.iterdir() if p.is_dir() and p.name.isdigit()):
        for mp4 in sorted(day.glob("*.mp4")):
            m = SPAN_RE.search(mp4.name)
            span = m.group(2).replace("-", "–") if m else "—"
            m4a = mp4.with_suffix(".m4a")
            rows.append({"date": day.name, "span": span, "mp4": mp4,
                         "m4a": m4a if m4a.exists() else None, "dur": dur_of(mp4)})
    return rows


def rebuild(outdir):
    """重建索引，返回写出的路径（失败返回 None）。供 lec_from_har 下载完自动调用。"""
    try:
        course = course_name(outdir)
        rows = build(outdir)
        if not rows:
            return None

        total = 0
        for r in rows:
            total += r["mp4"].stat().st_size
            if r["m4a"]:
                total += r["m4a"].stat().st_size
        audio_ok = sum(1 for r in rows if r["m4a"])

        lists = ROOT / "lists"
        lists.mkdir(exist_ok=True)
        out = lists / f"{course}.md"

        md = [
            f"# {course} · 已下载清单",
            "",
            f"- 共 **{len(rows)}** 节，合计 **{total/1e9:.2f} GB**",
            f"- 已抽音轨 **{audio_ok}/{len(rows)}** 节",
            f"- 存放目录：`{outdir}`",
            "",
            "> 本文件是**索引**，不是下载队列，批量模式不会执行它。",
            f"> 待下载的地址请粘到 `lists\\{course}.txt`（同目录，扩展名不同）。",
            "",
            "| # | 日期 | 时段 | 时长 | 录像 | 音轨 |",
            "|---:|---|---|---:|---:|---:|",
        ]
        for i, r in enumerate(rows, 1):
            mp4_mb = r["mp4"].stat().st_size / 1e6
            m4a_cell = f"{r['m4a'].stat().st_size/1e6:.1f} MB" if r["m4a"] else "✗ 缺"
            md.append(f"| {i} | {r['date']} | {r['span']} | {hhmm(r['dur'])} "
                      f"| {mp4_mb:.1f} MB | {m4a_cell} |")

        out.write_text("\n".join(md) + "\n", encoding="utf-8")
        return out
    except Exception:
        return None


def main():
    import argparse
    ap = argparse.ArgumentParser(description="生成已下载清单 lists\\<课程>.md")
    ap.add_argument("--dest", default="", help="只刷新这一门（相对本程序或绝对路径）；不给则刷新 media\\ 下所有课程")
    a = ap.parse_args()

    if a.dest:
        targets = [ROOT / a.dest]
    else:
        media = ROOT / "media"
        targets = sorted(p for p in media.iterdir() if p.is_dir()) if media.exists() else []

    done = 0
    for outdir in targets:
        if not outdir.exists():
            print(f"跳过（不存在）{outdir}")
            continue
        out = rebuild(outdir)
        if out:
            print(f"写入 {out}")
            done += 1
    if not done:
        print("没有可刷新的课程")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
