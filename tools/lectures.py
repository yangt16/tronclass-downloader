"""
lectures.py - 主编排：清单 → 下载 → 抽音轨 → 命名 → 归档 → 刷新索引。

唯一入口是 lists\\<科目>.txt（每行一个播放地址）。
清单名就是课程名：lists\\计网.txt -> media\\计网\\计网_<日期>.mp4 + .m4a

媒体地址不含登录信息，只靠请求头就能下（见 get_media.BASE_HEADERS）。

用法:
    python lectures.py --urls lists\\计网.txt
    python lectures.py --urls lists\\计网.txt --track INSTRUCTOR
    python lectures.py --urls lists\\计网.txt --dest D:\\courses\\db
    python lectures.py --urls lists\\计网.txt --dry-run      # 只打印路径，不写盘
"""
import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from get_media import download, resolve  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ROOT = tools/ 的父目录。整套东西可搬到任意位置而不用改代码。
ROOT = pathlib.Path(__file__).resolve().parent.parent


def _exe(name):
    """优先用 ROOT\\bin 下的，找不到再退回 PATH。"""
    local = ROOT / "bin" / f"{name}.exe"
    if local.exists():
        return local
    found = shutil.which(name)
    return pathlib.Path(found) if found else local


FFMPEG = _exe("ffmpeg")
FFPROBE = _exe("ffprobe")


# ---------------- 落点 ---------------- #

def resolve_outdir(args, urls_file=""):
    """落点完全由清单文件名决定：lists\\计网.txt -> media\\计网\\

    --dest 可以覆盖（相对本程序或绝对路径）；直接调用本脚本且没给 --dest 时，
    也按清单文件名推。
    """
    if getattr(args, "dest", ""):
        return ROOT / args.dest
    if urls_file:
        return ROOT / "media" / pathlib.Path(urls_file).stem
    return ROOT / "media"


def course_name(outdir):
    """课程名 = 落点目录的末级名。落点退化到 media 本身时用通用名。"""
    name = getattr(outdir, "name", "") or ""
    return name if name and name.lower() != "media" else "课程"


LIST_TEMPLATE = """# ============================================================
#  {course} · 待下载清单
#
#  怎么拿地址（每节约 15 秒）:
#     1. 打开那节回放页，F12 开 Network
#     2. 筛选框输入 ENCODER（或点上面的「媒体」标签）
#     3. 点播放，等出现 ENCODER-... 那条（状态 206、类型 媒体）
#        如果列表里没有 -> 勾上「禁用缓存」再按 F5 刷新，然后点播放
#     4. 右键那一行 -> 复制 -> 复制 URL
#     5. 粘到本文件末尾，一行一个
#
#  粘完双击 getlec.cmd 就会下载。
#  产物: media\\{course}\\<日期>\\{course}_<日期>.mp4 + .m4a
#
#  跑完本文件自动归档进 har_archive\\urls_<日期>.txt，并重建一个空的。
#  以 # 开头是注释。文件为空也没关系，批量模式会跳过。
# ============================================================
"""


def template_for(course):
    return LIST_TEMPLATE.format(course=course)


# ---------------- 地址与命名 ---------------- #


def label_of(url):
    """从 .../<日期>/<HHMMSS-HHMMSS-id>/<file> 取出 'YYYYMMDD_HHMMSS-HHMMSS'。"""
    parts = url.split("?")[0].split("/")
    try:
        date = parts[-3]
        span = parts[-2].split("-")
        return f"{date}_{span[0]}-{span[1]}"
    except Exception:
        return "lecture"


def group_by_label(urls):
    """按「日期+时段」分组，而不是按完整目录。

    为什么不能用目录分组：同一节课的三条轨可能被存在**不同目录**里
    （实测：20261111 / 20261023 / 20261106 的 INSTRUCTOR/STUDENTS 就在
    另一个目录下），按目录分会把一节课裂成两组，白白多跑一轮。
    日期+时段是这一节课的稳定标识。
    """
    groups = {}
    for u in urls:
        groups.setdefault(label_of(u), []).append(u)
    return groups


def track_of(url):
    """从 <TRACK>-<b64>?ts=... 认出是哪条轨。"""
    name = url.split("?")[0].rsplit("/", 1)[-1]
    return name.split("-")[0].upper() or "MEDIA"


def labels_parts(label):
    """'20261014_150100-160500' -> ('20261014', '150100-160500')"""
    date, _, span = label.partition("_")
    return date, span


def target_paths(outdir, label):
    """命名规则。

    一天一节:  <课程>_<YYYYMMDD>.mp4 / .m4a
    一天多节:  <课程>_<YYYYMMDD>_<时段>.mp4 / .m4a   （有 .multi 标记时）

    落点:  [dest]\\<YYYYMMDD>\\
    文件名带课程名，因为上传工具只显示文件名、不显示路径。
    """
    date, span = labels_parts(label)
    d = outdir / date
    base = f"{course_name(outdir)}_{date}"
    if (d / ".multi").exists() and span:
        base += f"_{span}"
    return d / f"{base}.mp4", d / f"{base}.m4a"


def guard_previous(daydir, label, course, date):
    """处理"同一天第二节课"，返回当天是否已有多节。

    - .session 记录的场次和本次不同 -> 判定为多节
    - 把旧的、还不带时段的名字改写成带时段
    - 打 .multi 标记，之后 target_paths() 会给新文件也带时段
    - 已带时段的文件不动，避免二次改名
    """
    tag = daydir / ".session"
    # utf-8-sig 容忍 BOM：PowerShell 写过的文件可能带 BOM
    old = tag.read_text(encoding="utf-8-sig").strip() if tag.exists() else ""
    collided = bool(old) and old != label
    multi = (daydir / ".multi").exists() or collided

    if collided:
        _, oldspan = labels_parts(old)
        oldspan = oldspan or "old"
        for p in sorted(daydir.glob("*.mp4")) + sorted(daydir.glob("*.m4a")):
            if re.search(r"_\d{6}-\d{6}$", p.stem):     # 已带时段，跳过
                continue
            dst = daydir / f"{course}_{date}_{oldspan}{p.suffix}"
            if p != dst and not dst.exists():
                p.replace(dst)
                print(f"  ! 同一天有第二节课，旧文件改名为 {dst.name}")

    daydir.mkdir(parents=True, exist_ok=True)
    if multi:
        (daydir / ".multi").write_text("1", encoding="utf-8")
    tag.write_text(label, encoding="utf-8")
    return multi


def load_urls(path):
    """读清单：一行一个地址，忽略空行和 # 注释。"""
    out = []
    for line in pathlib.Path(path).read_text(encoding="utf-8-sig").splitlines():
        u = line.strip()
        if not u or u.startswith("#"):
            continue
        if not u.lower().startswith("http"):
            print(f"  ! 跳过非 URL 行: {u[:60]}")
            continue
        out.append(u)
    print(f"[urls] {path} 里读到 {len(out)} 条地址")
    return out


# ---------------- 媒体处理 ---------------- #

def extract_audio(mp4, m4a):
    """音频流直接复制，不重编码。"""
    r = subprocess.run(
        [str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(mp4), "-vn", "-c:a", "copy", "-movflags", "+faststart", str(m4a)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(f"  !! ffmpeg 失败: {(r.stderr or '')[:300]}")
        return False
    return True


def info_of(path):
    r = subprocess.run(
        [str(FFPROBE), "-v", "error",
         "-show_entries", "format=duration,size:stream=codec_type,codec_name",
         "-of", "default=noprint_wrappers=1", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip()


# ---------------- 主流程 ---------------- #

def archive_list(urls_file, dates, outdir):
    """归档已跑完的清单，并在**原路径**重建一份空模板（否则用户没地方粘下一批）。"""
    src = pathlib.Path(urls_file)
    arc = ROOT / "har_archive"
    arc.mkdir(exist_ok=True)
    name = "urls_" + "_".join(sorted(set(dates))) + ".txt"
    dest = arc / name
    if dest.exists():
        dest = arc / f"urls_{'_'.join(sorted(set(dates)))}_{int(time.time())}.txt"
    src.replace(dest)
    print(f"\n[archive] 地址清单已归档 -> {dest.name}")
    try:
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(template_for(course_name(outdir)), encoding="utf-8")
        print(f"[archive] 已重建空清单 {src}")
    except Exception as e:
        print(f"[archive] 重建空清单失败: {e}")
    try:
        import make_index
        idx = make_index.rebuild(outdir)     # 必须传本次落点，不能用默认
        if idx:
            print(f"[archive] 已刷新下载清单 {idx}")
    except Exception as e:
        print(f"[archive] 刷新清单失败: {e}")


def already_done(mp4, m4a, mode="both"):
    """本地已有完整产物 —— 只查文件系统，不联网。

    mode 决定"完成"的标准：
      both  : mp4 + m4a 都在（默认）
      audio : 只有 m4a（音轨模式跑完会删掉 mp4）
      video : 只有 mp4（只要视频模式不抽音轨）
      any   : 任一个在（给预检用，判断"这节碰过没"）
    """
    def ok(p):
        try:
            return p.exists() and p.stat().st_size > 0
        except Exception:
            return False

    if mode == "audio":
        return ok(m4a)
    if mode == "video":
        return ok(mp4)
    if mode == "any":
        return ok(m4a) or ok(mp4)
    return ok(mp4) and ok(m4a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", required=True, help="每行一个媒体地址的 txt")
    ap.add_argument("--track", default="ENCODER", help="ENCODER / INSTRUCTOR / STUDENTS")
    ap.add_argument("--dest", default="", help="落点，相对本程序或绝对路径")
    ap.add_argument("--drop-video", action="store_true", help="抽完音轨就删 mp4")
    ap.add_argument("--no-audio", action="store_true", help="只要视频，不抽音轨")
    ap.add_argument("--dry-run", action="store_true", help="只打印路径，不写盘")
    ap.add_argument("--force", action="store_true", help="已下载的也重做")
    ap.add_argument("--keep-list", action="store_true",
                    help="跑完不动清单（不归档、不重建），适合长期维护的增量清单")
    a = ap.parse_args()

    # 落点由清单文件名决定：lists\计网.txt -> media\计网\
    outdir = resolve_outdir(a, a.urls)
    print(f"[dest] 落点: {outdir}")

    urls = load_urls(a.urls)
    if not urls:
        # 空清单是正常状态（比如先建好文件、之后再粘地址），不算失败
        print(f"  {a.urls} 里没有可用地址，跳过")
        return 0

    # 清单里可能是「间接地址」（incast 的 preview?previewToken=...）。
    # 它 302 到真正的签名直链，这个跳转不需要登录态，本地就能换。
    # 换过之后 URL 里才带日期/时段/轨道，才能命名和分组。
    if any("previewToken=" in u for u in urls):
        print(f"[resolve] 发现间接地址，换成直链（{len(urls)} 条）...")
        fixed = []
        for u in urls:
            r = resolve(u)
            if r != u:
                print(f"  {u[-42:]}  ->  {r[-46:]}")
            else:
                print(f"  {u[-42:]}  ->  (未变化，可能已过期)")
            fixed.append(r)
        urls = fixed

    groups = group_by_label(urls)

    # 三种模式：都要 / 只要音轨 / 只要视频
    mode = "video" if a.no_audio else ("audio" if a.drop_video else "both")
    mode_cn = {"both": "视频 + 音轨", "audio": "只要音轨", "video": "只要视频"}[mode]
    print(f"[mode] {mode_cn}")

    done_dates, failed = [], 0
    n_new = n_skip = 0
    for idx, (key, us) in enumerate(groups.items(), 1):
        label = label_of(us[0])
        print(f"\n=== 第 {idx}/{len(groups)} 节: {label}  轨: {[track_of(u) for u in us]} ===")
        want = [u for u in us if track_of(u) == a.track.upper()]
        pick = want[0] if want else us[0]
        if not want and len(us) > 1:
            print(f"  没有 {a.track} 轨，改用 {track_of(pick)}")

        date = labels_parts(label)[0]
        if a.dry_run:
            mp4, m4a = target_paths(outdir, label)
            if mode == "video":
                print(f"  将写入: {mp4}")
            else:
                print(f"  将写入: {mp4}")
                print(f"          {m4a}")
            continue

        outdir.mkdir(parents=True, exist_ok=True)
        guard_previous(outdir / date, label, course_name(outdir), date)
        mp4, m4a = target_paths(outdir, label)

        # 增量下载的核心：本地已有完整产物就整节跳过，不联网、不重抽音轨
        if not a.force and already_done(mp4, m4a, mode):
            print(f"  跳过（已下载）{mp4.name if mode != 'audio' else m4a.name}")
            n_skip += 1
            done_dates.append(date)
            continue

        print(f"  [下载] -> {mp4}")
        try:
            download(pick, mp4)
        except Exception as e:
            print(f"  下载失败: {e}")
            failed += 1
            continue

        if mode == "video":
            # 只要视频：不抽音轨，直接收工
            n_new += 1
            print(f"      视频 {mp4.name}  {mp4.stat().st_size/1e6:.1f} MB")
            print("  [信息]")
            print("      " + info_of(mp4).replace("\n", "\n      "))
            print(f"\n  视频用这个: {mp4}")
            done_dates.append(date)
            continue

        print(f"  [抽音频] -> {m4a.name}")
        if not extract_audio(mp4, m4a):
            failed += 1
            continue
        print(f"      {m4a.name}  {m4a.stat().st_size/1e6:.1f} MB")
        n_new += 1
        if a.drop_video:
            freed = mp4.stat().st_size
            mp4.unlink()
            print(f"      已删除录像 {mp4.name}，省回 {freed/1e6:.1f} MB")

        print("  [信息]")
        print("      " + info_of(m4a).replace("\n", "\n      "))
        print(f"\n  上传用这个: {m4a}")
        done_dates.append(date)

    if not a.dry_run:
        print(f"\n[小结] 新下载 {n_new} 节 / 跳过 {n_skip} 节 / 失败 {failed} 节")

    if a.dry_run or failed or not done_dates:
        return 1 if failed else 0

    if a.keep_list:
        # 增量清单模式：清单原地保留，方便下周把新地址追加进来
        print(f"[list] 保留清单不动: {a.urls}")
        try:
            import make_index
            idx = make_index.rebuild(outdir)
            if idx:
                print(f"[list] 已刷新下载清单 {idx}")
        except Exception:
            pass
        return 0

    archive_list(a.urls, done_dates, outdir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
