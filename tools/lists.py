"""
lists.py - 确保 lists\\ 目录存在，并报告有哪些待下载清单。

只有一个入口：用户在 lists\\ 下自己建 <科目>.txt。
清单名就是课程名、文件夹名、文件名前缀。
"""
import pathlib
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
LISTS = ROOT / "lists"


def listed():
    """返回 [(路径, 地址数)]，按名字排序。"""
    out = []
    if not LISTS.exists():
        return out
    for p in sorted(LISTS.glob("*.txt")):
        try:
            n = sum(1 for line in p.read_text(encoding="utf-8-sig").splitlines()
                    if line.strip() and not line.strip().startswith("#")
                    and line.strip().lower().startswith("http"))
        except Exception:
            n = 0
        out.append((p, n))
    return out


def main():
    LISTS.mkdir(parents=True, exist_ok=True)
    items = listed()
    todo = [(p, n) for p, n in items if n]
    if not todo:
        print("=" * 56)
        print("  lists\\ 里还没有可下载的清单")
        print("=" * 56)
        print(f"  在 {LISTS} 下新建一个 <科目名>.txt，例如：")
        print("    lists\\计网.txt")
        print("  把每节课的播放地址粘进去（一行一个），再双击 getlec.cmd。")
        print("")
        print("  拿地址: 回放页 F12 -> 筛 ENCODER -> 播放 -> 右键复制 URL")
        if items:
            print("")
            print("  当前已有但为空的清单:")
            for p, _ in items:
                print(f"    {p.name}")
        return 1
    print(f"[lists] 待下载清单 {len(todo)} 个:")
    for p, n in todo:
        print(f"    {p.name:24s} {n} 条地址 -> media\\{p.stem}\\")
    return 0


if __name__ == "__main__":
    sys.exit(main())
