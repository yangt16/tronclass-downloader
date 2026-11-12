"""
build_release.py - 打一个"下载解压就能用"的 Windows 发布包。

包含：
  * 仓库里所有跟踪文件（源码 + 文档 + 书签）
  * bin\\ffmpeg.exe + bin\\ffprobe.exe（约 340 MB 解压后，压缩后约 200 MB）
  * START-HERE.txt / LICENSE-ffmpeg.txt / COPYING.GPLv3.txt
  * 空的 lists\\

为什么不含 media\\ 和 har_archive\\：那是用户数据，且含签名地址。

用法:
    python tools\\build_release.py                 # 版本号取 git describe
    python tools\\build_release.py --version v3    # 指定版本
    python tools\\build_release.py --no-gpl-text   # 不发 GPL 全文（不推荐）

产物: release\\tronclass-downloader-<版本>-win64.zip
"""
import argparse
import pathlib
import shutil
import subprocess
import sys
import urllib.request
import zipfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
RELEASE = ROOT / "release"
ASSETS = RELEASE / "assets"
# GPL 全文：官方站偶尔 403，备一个镜像
GPL_URLS = [
    "https://www.gnu.org/licenses/gpl-3.0.txt",
    "https://raw.githubusercontent.com/gcc-mirror/gcc/master/COPYING3",
]

START_HERE = """\
课程回放下载器 · Windows 版
================================

这是一份已经装好 ffmpeg 的完整包，解压后即可使用。

第一步（一次性）
---------------
双击 setup.cmd
  它会检测 Python、确认 ffmpeg 就绪、建好 lists\\ 文件夹。
  本包已含 ffmpeg，所以这一步只需几秒。

第二步：拿到课程地址
-------------------
方式 A（推荐）：装书签
   1. 用 Edge 打开 dist\\install.html
   2. 把页面里的蓝色按钮拖到书签栏
   3. 打开课程的「直播」列表页，点一下书签，会下载一个 <课程名>.txt

方式 B（手动）：自己复制播放地址
   见 docs\\使用说明.md 的「手动版」一节。

第三步：下载
-----------
双击以下任一个：
   下视频和音频.cmd     视频 + 音轨都留（默认）
   只要音轨.cmd         只留音轨，省空间（只做转写用这个）
   只要视频.cmd         只留视频
   只下某一天.cmd       只下指定的某一天

产物在 media\\<课程名>\\<日期>\\ 下。

详细文档
--------
README.md              项目简介
docs\\使用说明.md       完整手册（含故障排查）
"""
LICENSE_FFMPEG = """\
这个发布包内含 FFmpeg 可执行文件（ffmpeg.exe / ffprobe.exe）。

FFmpeg 来源与版本
-----------------
    项目：FFmpeg (https://ffmpeg.org/)
    版本：见 bin\\ffmpeg.exe -version 的输出
    构建：gyan.dev 的 release-essentials Windows 构建
          (https://www.gyan.dev/ffmpeg/builds/)
    许可证：GPL v3（该构建启用了 GPL 组件）

本发行包未修改 FFmpeg 二进制，仅原样打包分发。完整许可证文本见
COPYING.GPLv3.txt；FFmpeg 源码可从 https://ffmpeg.org/download.html
或其镜像获取。

FFmpeg 是独立的第三方程序，本项目的 MIT/学习用途声明不覆盖它。
"""


def git(*args, **kw):
    r = subprocess.run(["git", "-C", str(ROOT)] + list(args),
                       capture_output=True, **kw)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} 失败: {r.stderr.decode('utf-8', 'replace')}")
    return r.stdout


def tracked_files():
    out = git("-c", "core.quotepath=false", "ls-files", "-z")
    return [p for p in out.decode("utf-8").split("\0") if p]


def version_of(arg):
    if arg:
        return arg
    try:
        return git("describe", "--tags", "--always", "--dirty").decode().strip()
    except SystemExit:
        return "dev"


def ensure_assets(no_gpl):
    ASSETS.mkdir(parents=True, exist_ok=True)
    sh = ASSETS / "START-HERE.txt"
    lf = ASSETS / "LICENSE-ffmpeg.txt"
    sh.write_text(START_HERE, encoding="utf-8")
    lf.write_text(LICENSE_FFMPEG, encoding="utf-8")

    gpl = ASSETS / "COPYING.GPLv3.txt"
    if no_gpl:
        return sh, lf, None
    if not gpl.exists() or gpl.stat().st_size < 1000:
        for url in GPL_URLS:
            print(f"[release] 下载 GPL 全文: {url}")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=40) as r:
                    data = r.read()
                if len(data) > 10000:
                    gpl.write_bytes(data)
                    break
            except Exception as e:
                print(f"[release]   失败（{type(e).__name__}），换下一个")
        if not (gpl.exists() and gpl.stat().st_size > 10000):
            print("[release] GPL 全文拿不到，包里不放；LICENSE-ffmpeg.txt 里已给出链接")
            return sh, lf, None
    if gpl.stat().st_size < 1000:
        return sh, lf, None
    return sh, lf, gpl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="")
    ap.add_argument("--no-gpl-text", action="store_true")
    a = ap.parse_args()

    ver = version_of(a.version)
    name = f"tronclass-downloader-{ver}-win64"
    out_zip = RELEASE / f"{name}.zip"
    RELEASE.mkdir(parents=True, exist_ok=True)

    # 必须有 ffmpeg 才能打完整包
    ff = [ROOT / "bin" / n for n in ("ffmpeg.exe", "ffprobe.exe")]
    missing = [p.name for p in ff if not p.exists()]
    if missing:
        raise SystemExit(f"缺少 {missing}；先跑一次 setup.cmd 再打包")

    sh, lf, gpl = ensure_assets(a.no_gpl_text)

    if out_zip.exists():
        out_zip.unlink()

    files = tracked_files()
    cmd_files = [f for f in files if f.lower().endswith(".cmd")]
    # .cmd 必须是 CRLF，否则解压出来的入口会坏
    for f in cmd_files:
        raw = (ROOT / f).read_bytes()
        if b"\r\n" not in raw:
            raise SystemExit(f"{f} 不是 CRLF，先在仓库里修好再打包")

    total = 0
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in files:
            src = ROOT / f
            if not src.exists():
                print(f"[release] 跳过不存在的跟踪文件: {f}")
                continue
            z.write(src, f"{name}/{f}")
            total += 1
        for p in ff:
            z.write(p, f"{name}/bin/{p.name}")
            total += 1
        for extra in (sh, lf, gpl):
            if extra and extra.exists():
                z.write(extra, f"{name}/{extra.name}")
                total += 1
        # 空中目录：解压后就有 lists\，省得用户自己建
        z.writestr(f"{name}/lists/", "")

    size = out_zip.stat().st_size / 1e6
    print(f"\n[release] {out_zip}")
    print(f"[release] {size:.1f} MB，{total} 个文件，版本 {ver}")
    if size > 1900:
        print("[release] 警告：超过 GitHub Releases 单文件 2 GB 上限")
    return 0


if __name__ == "__main__":
    sys.exit(main())
