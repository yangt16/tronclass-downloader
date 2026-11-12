"""校验三种下载模式的"是否已完成"判定（already_done 的 mode 参数）。

三种模式对"完成"的定义不同：
  both  : mp4 + m4a 都在
  audio : 只要 m4a（音轨模式跑完会删掉 mp4）
  video : 只要 mp4（只要视频模式不抽音轨）
  any   : 任一个在（预检用）
"""
import pathlib
import shutil
import sys
import os

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lectures import already_done  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

bad = 0


def check(name, got, want):
    global bad
    ok = got == want
    print(f"[{'PASS' if ok else 'FAIL'}] {name:34s} got={got} want={want}")
    if not ok:
        bad += 1


def touch(p):
    p.write_bytes(b"x" * 1024)


# 临时目录放工作区里：沙箱不允许写系统 Temp。
# 注意不能用 tempfile.mkdtemp —— 它用 0o700 建目录，会把继承来的
# 沙箱 ACE 去掉，随后写文件报 PermissionError。
BASE = pathlib.Path(__file__).resolve().parent.parent / "tmp" / f"modes_{os.getpid()}"
shutil.rmtree(BASE, ignore_errors=True)
BASE.mkdir(parents=True, exist_ok=True)
try:
    mp4 = BASE / "a.mp4"
    m4a = BASE / "a.m4a"

    # 1) 两个文件都在
    touch(mp4)
    touch(m4a)
    check("both + 都在", already_done(mp4, m4a, "both"), True)
    check("audio + 都在", already_done(mp4, m4a, "audio"), True)
    check("video + 都在", already_done(mp4, m4a, "video"), True)

    # 2) 只有 mp4（音轨模式跑完删了视频的反面；或只要视频模式）
    m4a.unlink()
    check("both + 只有 mp4", already_done(mp4, m4a, "both"), False)
    check("audio + 只有 mp4", already_done(mp4, m4a, "audio"), False)
    check("video + 只有 mp4", already_done(mp4, m4a, "video"), True)
    check("any + 只有 mp4", already_done(mp4, m4a, "any"), True)

    # 3) 只有 m4a（音轨模式跑完的典型状态：mp4 已删）
    mp4.unlink()
    touch(m4a)
    check("both + 只有 m4a", already_done(mp4, m4a, "both"), False)
    check("audio + 只有 m4a", already_done(mp4, m4a, "audio"), True)
    check("video + 只有 m4a", already_done(mp4, m4a, "video"), False)
    check("any + 只有 m4a", already_done(mp4, m4a, "any"), True)

    # 4) 空文件不算完成
    m4a.write_bytes(b"")
    touch(mp4)
    check("both + 空 m4a", already_done(mp4, m4a, "both"), False)
    check("audio + 空 m4a", already_done(mp4, m4a, "audio"), False)
    check("video + 空 m4a(有mp4)", already_done(mp4, m4a, "video"), True)

    # 5) 都不存在
    mp4.unlink()
    m4a.unlink()
    for m in ("both", "audio", "video", "any"):
        check(f"{m} + 都没有", already_done(mp4, m4a, m), False)
finally:
    shutil.rmtree(BASE, ignore_errors=True)

print()
print("全部通过" if bad == 0 else f"{bad} 项失败")
sys.exit(0 if bad == 0 else 1)
