"""
get_media.py - 分块下载 + 请求头基线。

媒体接口 ilesson.wh.bjtu.edu.cn 不校验 Cookie，只校验请求头：
    User-Agent, Referer, sec-ch-ua, sec-ch-ua-platform, sec-ch-ua-mobile
缺 sec-ch-ua 三项会 403。所以地址本身即可下载，无需登录态。

分块用 HTTP Range：
  * 断点续传（中断后从已有字节继续）
  * 失败只重下那一块（指数退避，最多 6 次）
  * 进度可见
"""
import re
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36 Edg/157.0.4341.42"),
    "Referer": "https://tronclass.wh.bjtu.edu.cn/",
    "Accept": "*/*",
    "sec-ch-ua": '"Not-A.Brand";v="99", "Microsoft Edge";v="157", "Chromium";v="157"',
    "sec-ch-ua-platform": '"Windows"',
    "sec-ch-ua-mobile": "?0",
}
CTX = ssl._create_unverified_context()
CHUNK = 8 * 1024 * 1024


def probe(url, timeout=60):
    """取 1 字节探活。返回 (是否可用, 总字节数, 错误说明)。"""
    h = dict(BASE_HEADERS, Range="bytes=0-0")
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=h),
                                   timeout=timeout, context=CTX)
        cr = r.headers.get("Content-Range") or ""
        r.close()
        m = re.search(r"/(\d+)", cr)
        total = int(m.group(1)) if m else 0
        if not total:
            return False, 0, "服务器未返回文件长度"
        return True, total, ""
    except urllib.error.HTTPError as e:
        return False, 0, f"HTTP {e.code}" + ("（链接可能已过期）" if e.code == 403 else "")
    except Exception as e:
        return False, 0, f"{type(e).__name__} {str(e)[:60]}"


def download(url, out_path):
    """按块下载到 out_path，已存在的部分会续传。"""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    ok, total, err = probe(url)
    if not ok:
        raise RuntimeError(f"无法访问媒体地址: {err}")
    have = out.stat().st_size if out.exists() else 0
    if have > total:
        out.unlink()
        have = 0
    print(f"总长 {total/1e6:.1f} MB  已有 {have/1e6:.1f} MB")
    if have == total:
        print("已经下完，跳过")
        return out

    t0 = time.time()
    with open(out, "ab" if have else "wb") as fh:
        while have < total:
            end = min(have + CHUNK - 1, total - 1)
            h = dict(BASE_HEADERS, Range=f"bytes={have}-{end}")
            for attempt in range(6):
                try:
                    r = urllib.request.urlopen(urllib.request.Request(url, headers=h),
                                               timeout=120, context=CTX)
                    fh.write(r.read())
                    fh.flush()
                    break
                except Exception as ex:
                    if attempt == 5:
                        raise RuntimeError(f"第 {have} 字节处连续失败: {ex}")
                    print(f"  重试 {attempt+1}/5: {type(ex).__name__} {str(ex)[:60]}")
                    time.sleep(2 * (attempt + 1))
            have = out.stat().st_size
            el = time.time() - t0
            print(f"  {have/1e6:8.1f}/{total/1e6:.1f} MB  {have/total*100:5.1f}%"
                  f"  {have/el/1e6 if el else 0:5.1f} MB/s", end="\r", flush=True)
    print()
    print(f"完成 {out}  {out.stat().st_size/1e6:.1f} MB  用时 {time.time()-t0:.0f}s")
    return out
