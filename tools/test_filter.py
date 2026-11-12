"""校验 --only / --exclude 的解析与筛选逻辑（不联网）。

覆盖用户最常写的几种格式：
  20261030               一天
  20261030,20261104      多天（英文逗号）
  20261030，20261104     多天（中文逗号）
  20261030_101000-120500 完整标签
  20261030_10            前缀
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lectures import filter_groups, match_label, parse_specs  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

bad = 0


def check(name, got, want):
    global bad
    ok = got == want
    print(f"[{'PASS' if ok else 'FAIL'}] {name:38s} got={got!r} want={want!r}")
    if not ok:
        bad += 1


# ---------- parse_specs ----------
check("单值", parse_specs(["20261030"]), ["20261030"])
check("英文逗号", parse_specs(["20261030,20261104"]), ["20261030", "20261104"])
check("中文逗号", parse_specs(["20261030，20261104"]), ["20261030", "20261104"])
check("重复传参合并", parse_specs(["20261030", "20261104"]), ["20261030", "20261104"])
check("去重", parse_specs(["20261030,20261030"]), ["20261030"])
check("去空格/空项", parse_specs([" 20261030 , ,20261104 "]), ["20261030", "20261104"])
check("空列表", parse_specs([]), [])

# ---------- match_label ----------
L = "20261030_101000-120500"
check("日期命中", match_label(L, ["20261030"]), True)
check("完整标签命中", match_label(L, ["20261030_101000-120500"]), True)
check("前缀命中", match_label(L, ["20261030_10"]), True)
check("别的日期不命中", match_label(L, ["20261104"]), False)
check("日期不能部分匹配", match_label(L, ["20261003"]), False)
check("多值任一命中", match_label(L, ["20261104", "20261030"]), True)
不命中 = match_label(L, ["20261104", "20261111"])
check("多值都不命中", 不命中, False)

# ---------- filter_groups ----------
groups = {
    "20261030_101000-120500": ["a", "b"],
    "20261104_080000-095500": ["c"],
    "20261106_162000-181500": ["d"],
}

g, note = filter_groups(dict(groups), ["20261030"], [])
check("--only 一天", sorted(g), ["20261030_101000-120500"])
check("--only 说明带节数", "3 节 -> 1 节" in note, True)

g, _ = filter_groups(dict(groups), ["20261030", "20261104"], [])
check("--only 多天", len(g), 2)

g, _ = filter_groups(dict(groups), [], ["20261030"])
check("--exclude 排除一天", sorted(g), ["20261104_080000-095500", "20261106_162000-181500"])

g, _ = filter_groups(dict(groups), ["2026"], [])   # 宽松前缀：全命中
check("前缀 2026 命中全部", len(g), 3)

g, _ = filter_groups(dict(groups), ["20991231"], [])
check("不存在的日期 -> 空", len(g), 0)

g, _ = filter_groups(dict(groups), ["20261030"], ["20261030"])
check("only+exclude 同时命中 -> 空", len(g), 0)

g, _ = filter_groups(dict(groups), [], [])
check("不过滤 -> 原样", len(g), 3)

print()
print("全部通过" if bad == 0 else f"{bad} 项失败")
sys.exit(0 if bad == 0 else 1)
