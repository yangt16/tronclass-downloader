"""
fetch_ffmpeg.py - 下载 ffmpeg 的 Windows 构建，抽出 ffmpeg.exe / ffprobe.exe 放进 bin\\。

为什么需要它：ffmpeg.exe 单文件就 100 MB，超过 GitHub 单文件 100 MB 的限制，
所以仓库里不含它。新机器 clone 下来先跑一次本脚本（或双击根目录 setup.cmd）。

用法:
    python tools\\fetch_ffmpeg.py            下载并安装到 bin\\
    python tools\\fetch_ffmpeg.py --check    只检查是否已就绪
    python tools\\fetch_ffmpeg.py --force    已存在也重新下载
    python tools\\fetch_ffmpeg.py --dest D:\\some\\dir   换安装位置（测试用）
    python tools\\fetch_ffmpeg.py --mirror <url>        指定下载地址
"""
import argparse
import pathlib
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
CTX = ssl._create_unverified_context()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36 Edg/157.0.4341.42"}

# 按优先级尝试。都是官方/长期维护的 Windows 构建源。
# 每项是 (url, 说明)，顺序不能反。
# 实测（2026-11，本机）：BtbN 约 1.6 MB/s，gyan 约 0.04 MB/s，
# 所以 BtbN 放第一位；gyan 留作备用（别的网络下可能更快）。
MIRRORS = [
    ("https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
     "ffmpeg-master-latest-win64-gpl.zip",
     "BtbN 完整版（GitHub）"),
    ("https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
     "gyan.dev 精简版"),
]

SLOW_AFTER = 20 * 1024 * 1024        # 至少下到 20 MB 才判断速度
SLOW_SPEED = 0.15                     # MB/s，低于这个算"这个源不行"
SLOW_ABORT = 600                      # 秒，单源最长 10 分钟

NEEDED = ("ffmpeg.exe", "ffprobe.exe")
MIN_SIZE = 20 * 1024 * 1024       # 小于 20 MB 说明文件不对


def have(dest):
    """返回 {名字: 路径}，只包含存在且体积正常的。"""
    got = {}
    for name in NEEDED:
        p = dest / name
        if p.exists() and p.stat().st_size >= MIN_SIZE:
            got[name] = p
    return got


def version_of(exe):
    try:
        r = subprocess.run([str(exe), "-hide_banner", "-version"],
                           capture_output=True, text=True, timeout=20)
        line = (r.stdout or r.stderr or "").splitlines()
        return line[0].strip() if line else "?"
    except Exception as e:
        return f"(无法执行: {type(e).__name__})"


def download(url, out_path, label):
    """流式下载，每 8 MB 打一行进度。

    太慢的源会主动放弃：下到 20 MB 后若平均速度低于 SLOW_SPEED，
    或者单源超过 SLOW_ABORT 秒，就抛异常让上层换下一个源。
    """
    req = urllib.request.Request(url, headers=UA)
    t0 = time.time()
    done = 0
    last = -8 * 1024 * 1024
    with urllib.request.urlopen(req, timeout=60, context=CTX) as r, open(out_path, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        total_mb = total / 1e6 if total else 0
        print(f"  源: {label}")
        print(f"  大小: {total_mb:.1f} MB" if total else "  大小: 未知")
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            dt = time.time() - t0
            if done - last >= 8 * 1024 * 1024:
                last = done
                speed = done / dt / 1e6
                pct = f"{done/total*100:5.1f}%" if total else "  ?  "
                print(f"    {done/1e6:7.1f}/{total_mb:7.1f} MB  {pct}  {speed:5.2f} MB/s",
                      flush=True)
            if dt > SLOW_ABORT:
                raise TimeoutError(f"单源超过 {SLOW_ABORT} 秒，放弃")
            if done >= SLOW_AFTER and done / dt / 1e6 < SLOW_SPEED:
                raise TimeoutError(f"速度过慢（{done/dt/1e6:.2f} MB/s），放弃此源")
    return done


def extract(zip_path, dest):
    """从 zip 里只抽 bin/ffmpeg.exe 和 bin/ffprobe.exe。"""
    dest.mkdir(parents=True, exist_ok=True)
    picked = []
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            name = info.filename.replace("\\", "/")
            base = name.rsplit("/", 1)[-1].lower()
            if base not in NEEDED:
                continue
            if "/bin/" not in ("/" + name) and not name.lower().startswith("bin/"):
                continue
            target = dest / base
            print(f"  解出 {base}  ({info.file_size/1e6:.1f} MB)")
            with z.open(info) as src, open(target, "wb") as out:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
            picked.append(base)
    return picked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default="", help="安装目录，默认 bin\\")
    ap.add_argument("--check", action="store_true", help="只检查")
    ap.add_argument("--force", action="store_true", help="已存在也重新下载")
    ap.add_argument("--mirror", default="", help="指定下载地址")
    a = ap.parse_args()

    dest = pathlib.Path(a.dest) if a.dest else ROOT / "bin"
    got = have(dest)

    print(f"[ffmpeg] 目标目录: {dest}")
    if len(got) == len(NEEDED):
        for name in NEEDED:
            print(f"  {name:12s} {got[name].stat().st_size/1e6:6.1f} MB  {version_of(got[name])}")
        if not a.force:
            print("[ffmpeg] 已就绪，无需下载（--force 可强制重下）")
            return 0
        print("[ffmpeg] --force: 重新下载")

    if a.check:
        missing = [n for n in NEEDED if n not in got]
        print(f"[ffmpeg] 缺少: {', '.join(missing)}")
        return 1

    tmpdir = ROOT / "tmp"
    tmpdir.mkdir(parents=True, exist_ok=True)
    zip_path = tmpdir / "ffmpeg_download.zip"

    sources = [(a.mirror, "自定义") ] if a.mirror else MIRRORS
    last_err = ""
    for url, label in sources:
        try:
            print(f"\n[ffmpeg] 开始下载（{label}）")
            size = download(url, zip_path, label)
            if size < MIN_SIZE:
                last_err = f"下载不完整（{size/1e6:.1f} MB）"
                continue
            print(f"\n[ffmpeg] 解压到 {dest}")
            picked = extract(zip_path, dest)
            if len(picked) < 2:
                last_err = f"压缩包里只找到 {picked}"
                continue
            got = have(dest)
            if len(got) < 2:
                last_err = "解出的文件体积异常"
                continue

            print("\n[ffmpeg] 校验")
            for name in NEEDED:
                print(f"  {name:12s} {got[name].stat().st_size/1e6:6.1f} MB  {version_of(got[name])}")
            print("\n[ffmpeg] 安装完成")
            return 0
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            print(f"  失败: HTTP {e.code}，换下一个源")
        except Exception as e:
            last_err = f"{type(e).__name__}: {str(e)[:80]}"
            print(f"  失败: {last_err}，换下一个源")
        finally:
            if zip_path.exists():
                try:
                    zip_path.unlink()
                except Exception:
                    pass

    print(f"\n[ffmpeg] 全部源都失败（最后一次: {last_err}）")
    print("  手动安装：下载 ffmpeg Windows 版，把 ffmpeg.exe / ffprobe.exe 放进")
    print(f"  {dest}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
