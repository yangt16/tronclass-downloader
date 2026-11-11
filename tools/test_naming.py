"""验证一天多节课的命名规则。

输出目录结构必须模拟真实布局: <root>\\软件设计\\<日期>\\...
course_name() 取落点目录的末级名，所以落点必须是「软件设计」这一层。

不用 tempfile —— 它落在系统 TEMP（工作区外），会被沙箱拒。
"""
import pathlib
import shutil
import sys

sys.path.insert(0, r"D:\course-notes\tools")
from lectures import guard_previous, target_paths  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

COURSE = "软件设计"
BASE = pathlib.Path(r"D:\course-notes\tmp\nametest")
L1 = "20261014_150100-160500"
L2 = "20261014_162000-181500"
L3 = "20261014_190000-200000"
bad = 0


def setup(name):
    """返回 (outdir=软件设计, daydir=20261014)"""
    root = BASE / name
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    out = root / COURSE
    day = out / "20261014"
    day.mkdir(parents=True)
    return out, day


def names(d):
    return sorted(p.name for p in d.iterdir() if p.is_file() and not p.name.startswith("."))


def check(tag, cond, got):
    global bad
    print(f"[{tag}] {'PASS' if cond else 'FAIL'}  {got}")
    if not cond:
        bad += 1


# 1) 一天第一节 -> 不带时段，无 .multi
out, day = setup("one")
guard_previous(day, L1, COURSE, "20261014")
mp4, m4a = target_paths(out, L1)
check("第一节 命名", mp4.name == "软件设计_20261014.mp4", mp4.name)
check("第一节 无.multi", not (day / ".multi").exists(), names(day))

# 2) 同一天第二节 -> 旧文件改成带时段，新文件也带时段，打 .multi
out, day = setup("two")
(day / "软件设计_20261014.mp4").write_bytes(b"x" * 10)
(day / "软件设计_20261014.m4a").write_bytes(b"x" * 10)
guard_previous(day, L1, COURSE, "20261014")          # 第一节记录在案
guard_previous(day, L2, COURSE, "20261014")          # 第二节来了
mp4_2, _ = target_paths(out, L2)
check("第二节 有.multi", (day / ".multi").exists(), names(day))
check("第二节 旧改名", (day / "软件设计_20261014_150100-160500.mp4").exists(), names(day))
check("第二节 新命名", mp4_2.name == "软件设计_20261014_162000-181500.mp4", mp4_2.name)

# 3) 第三节 -> 已带时段的不被二次改名，新节继续带时段
guard_previous(day, L3, COURSE, "20261014")
mp4_3, _ = target_paths(out, L3)
got = names(day)
check("第三节 不改旧名", "软件设计_20261014_150100-160500.mp4" in got, got)
check("第三节 新命名", mp4_3.name == "软件设计_20261014_190000-200000.mp4", mp4_3.name)

# 4) BOM 的同课时不该误判成多节
out, day = setup("bom")
(day / "软件设计_20261014.mp4").write_bytes(b"x" * 10)
(day / ".session").write_bytes(b"\xef\xbb\xbf" + L1.encode())
guard_previous(day, L1, COURSE, "20261014")
check("BOM 同课时", not (day / ".multi").exists(), names(day))

shutil.rmtree(BASE, ignore_errors=True)
print("\n全部通过" if bad == 0 else f"\n{bad} 项失败")
sys.exit(0 if bad == 0 else 1)
