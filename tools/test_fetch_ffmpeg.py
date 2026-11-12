"""校验 fetch_ffmpeg.py 的解压与检测逻辑（不联网）。

真实下载要 100+ MB，太慢；这里用合成 zip 覆盖真正容易出错的路径匹配：
zip 里 ffmpeg.exe 在 <版本>/bin/ 下，还混着 ffplay.exe 和 README 要忽略。
"""
import os
import pathlib
import shutil
import sys
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fetch_ffmpeg as ff  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

bad = 0


def check(name, ok, detail=""):
    global bad
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail and not ok else ""))
    if not ok:
        bad += 1


BASE = pathlib.Path(__file__).resolve().parent.parent / "tmp" / f"fftest_{os.getpid()}"
shutil.rmtree(BASE, ignore_errors=True)
BASE.mkdir(parents=True, exist_ok=True)

# 把 MIN_SIZE 调小，避免测试里造 100 MB 假文件
ff.MIN_SIZE = 1024

try:
    zpath = BASE / "fake.zip"
    members = {
        "ffmpeg-9.0-essentials_build/bin/ffmpeg.exe": b"F" * 4096,
        "ffmpeg-9.0-essentials_build/bin/ffprobe.exe": b"P" * 4096,
        "ffmpeg-9.0-essentials_build/bin/ffplay.exe": b"L" * 4096,   # 不该被抽出
        "ffmpeg-9.0-essentials_build/README.txt": b"readme",         # 不该被抽出
    }
    with zipfile.ZipFile(zpath, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)

    dest = BASE / "bin"
    picked = ff.extract(zpath, dest)
    check("只抽 ffmpeg + ffprobe", sorted(picked) == ["ffmpeg.exe", "ffprobe.exe"], picked)
    check("ffmpeg.exe 已落盘", (dest / "ffmpeg.exe").exists())
    check("ffprobe.exe 已落盘", (dest / "ffprobe.exe").exists())
    check("ffplay.exe 没被抽", not (dest / "ffplay.exe").exists())
    check("内容正确", (dest / "ffmpeg.exe").read_bytes() == b"F" * 4096)

    got = ff.have(dest)
    check("have() 认两个文件", sorted(got) == ["ffmpeg.exe", "ffprobe.exe"], sorted(got))

    # 体积异常（小于 MIN_SIZE）不算就绪
    (dest / "ffprobe.exe").write_bytes(b"x" * 10)
    got = ff.have(dest)
    check("体积过小被排除", sorted(got) == ["ffmpeg.exe"], sorted(got))

    # 缺失一个也不算就绪
    (dest / "ffprobe.exe").write_bytes(b"x" * 4096)
    (dest / "ffmpeg.exe").unlink()
    check("缺文件不算就绪", sorted(ff.have(dest)) == ["ffprobe.exe"], sorted(ff.have(dest)))

    # version_of 对假 exe 不应抛异常
    v = ff.version_of(dest / "ffprobe.exe")
    check("version_of 不抛异常", isinstance(v, str) and len(v) > 0, v)
finally:
    shutil.rmtree(BASE, ignore_errors=True)

print()
print("全部通过" if bad == 0 else f"{bad} 项失败")
sys.exit(0 if bad == 0 else 1)
