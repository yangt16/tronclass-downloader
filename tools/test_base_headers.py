"""回归测试: 只用自拼的 BASE_HEADERS 能否取到媒体数据。

意义：媒体接口不校验 Cookie，校验的是 UA + Referer + 三个 sec-ch-ua。
这条成立，"只要地址就能下载"这个前提才成立。

⚠️ 需要一份**未过期**的地址清单（ts/token 时效约 1 小时）。
   过期时全部失败是正常的，本测试报 SKIP 而不是 FAIL。

用法:
    python test_base_headers.py [清单路径]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from get_media import probe  # noqa: E402
from lectures import ROOT, load_urls, track_of  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        lists = ROOT / "lists"
        cands = [p for p in sorted(lists.glob("*.txt"))] if lists.exists() else []
        path = str(cands[0]) if cands else ""
    if not path:
        print("lists\\ 下没有清单 —— 这项测试需要一份新鲜清单。")
        print("做法: 建 lists\\<科目>.txt，粘几节播放地址进去，再跑本脚本。")
        return 2

    urls = load_urls(path)
    if not urls:
        print(f"{path} 里没有地址 —— 这项测试需要一份新鲜清单。")
        return 2

    ok = expired = 0
    for u in urls:
        good, total, err = probe(u)
        if good:
            print(f"  [{track_of(u):10s}] OK  {total/1e6:.1f} MB")
            ok += 1
        else:
            print(f"  [{track_of(u):10s}] {err}")
            if "403" in err:
                expired += 1

    print()
    if ok:
        print(f"PASS — {ok} 条仅凭自拼请求头即可取到数据，确认不需要 Cookie")
        return 0
    if expired:
        print("SKIP — 地址已过期（ts/token 有时效），无法判定。")
        print("       这不是失败：换一份新鲜清单再跑即可复验。")
        return 3
    print("FAIL — 地址未过期却取不到，可能请求头策略变了，需排查 BASE_HEADERS")
    return 1


if __name__ == "__main__":
    sys.exit(main())
