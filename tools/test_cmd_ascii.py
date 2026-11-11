"""校验所有 .cmd 文件的硬性规则。三条都是真实踩过的坑：

  1. 必须纯 ASCII —— cmd.exe 按 GBK 解码 .cmd，UTF-8 中文会破坏语法
  2. 注释(REM)行里不能有尖括号 —— cmd 在 REM 行上也会解析重定向符，
     会把整行拆成垃圾命令执行（曾经刷屏几千行并陷入循环）
  3. 必须 CRLF 换行 —— goto / call 的标签定位依赖 CRLF 算偏移，
     LF-only 会报 "cannot find the batch label specified"
"""
import pathlib
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
bad = 0


def fail(msg):
    global bad
    bad += 1
    print(f"[FAIL] {msg}")


for p in sorted(ROOT.glob("*.cmd")):
    raw = p.read_bytes()

    non_ascii = [i for i, b in enumerate(raw) if b > 127]
    if non_ascii:
        fail(f"{p.name}: {len(non_ascii)} 个非 ASCII 字节（首个在偏移 {non_ascii[0]}）")
    else:
        print(f"[PASS] {p.name}: 纯 ASCII")

    text = raw.decode("utf-8", errors="replace")
    if "\r\n" not in text:
        fail(f"{p.name}: 缺少 CRLF 换行（goto 会找不到标签）")
    elif "\n" in text.replace("\r\n", ""):
        fail(f"{p.name}: 混用了 LF-only 换行")
    else:
        print(f"[PASS] {p.name}: CRLF 换行")

    for ln, line in enumerate(text.splitlines(), 1):
        if not line.strip().upper().startswith("REM"):
            continue
        if "<" in line or ">" in line:
            fail(f"{p.name}:{ln} REM 行含尖括号: {line.strip()[:66]}")

print()
print("全部通过" if bad == 0 else f"{bad} 项失败")
sys.exit(0 if bad == 0 else 1)
