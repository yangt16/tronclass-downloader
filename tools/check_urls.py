"""
check_urls.py - 下载前预检：逐条验证地址是否还有效，并预览落点。

链接带 ts/token 签名，时效有限，所以"先预检再下载"能避免跑到一半才 403。

用法:
    python check_urls.py                # 预检 lists\\ 下所有清单
    python check_urls.py lists\\计网.txt  # 只预检这一份
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from get_media import probe  # noqa: E402
from lectures import (ROOT, labels_parts, load_urls,  # noqa: E402
                      label_of, session_key, track_of)


def check_list(path):
    urls = load_urls(path)
    if not urls:
        print(f"  （{pathlib.Path(path).name} 没有地址，跳过）\n")
        return 0

    course = pathlib.Path(path).stem
    outdir = ROOT / "media" / course
    print(f"落点: {outdir}\n")

    groups = {}
    for u in urls:
        groups.setdefault(session_key(u), []).append(u)

    bad = 0
    print(f"{'状态':<8} {'大小':>10}  {'落点'}")
    print("-" * 68)
    for key, us in groups.items():
        label = label_of(us[0])
        date, span = labels_parts(label)
        multi = (outdir / date / ".multi").exists()
        base = f"{course}_{date}" + (f"_{span}" if multi and span else "")
        for u in us:
            ok, total, err = probe(u)
            if not ok:
                bad += 1
            size = f"{total/1e6:.1f} MB" if total else "-"
            print(f"[{'OK' if ok else 'FAIL'}] {size:>10}  "
                  f"{course}\\{date}\\{base}.mp4  ({track_of(u)})")
            if err:
                print(f"        !! {err}")
        print()
    print(f"  {len(groups)} 节 / 无效 {bad} 条\n")
    return bad


def main():
    if len(sys.argv) > 1:
        paths = [pathlib.Path(sys.argv[1])]
    else:
        lists = ROOT / "lists"
        paths = sorted(lists.glob("*.txt")) if lists.exists() else []
        if not paths:
            print(f"{lists} 下还没有清单。先建 <科目>.txt 并粘入地址。")
            return 1

    total_bad = 0
    for p in paths:
        print("=" * 68)
        print(f"[{p.name}]")
        total_bad += check_list(p)

    print("=" * 68)
    if total_bad:
        print(f"!! 共 {total_bad} 条无效。常见原因：链接已过期，重新复制一次。")
        return 1
    print("全部有效，可以下。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
