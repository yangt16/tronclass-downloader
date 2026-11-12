# 课程回放下载器 · 使用文档

把 TronClass 的课堂回放**批量下载成本地文件**，并自动抽出音轨。

> 用途很窄：**拿到文件**。转写、总结、考点提取都不在这个程序里。

---

## 目录

- [能做什么](#能做什么)
- [一次性准备](#一次性准备)
- [三步上手](#三步上手)
- [怎么拿到播放地址](#怎么拿到播放地址)
- [输出规则](#输出规则)
- [命令速查](#命令速查)
- [脚本参数速查](#脚本参数速查)
- [故障排查](#故障排查)
- [维护操作](#维护操作)
- [设计说明](#设计说明)
- [已知限制](#已知限制)
- [目录结构](#目录结构)
- [测试](#测试)

---

## 能做什么

| 能力 | 说明 |
|---|---|
| **一科一个清单** | `lists\计网.txt` → 落到 `media\计网\`，清单名即课程名 |
| **增量下载** | 重跑时本地已有的节**整节跳过**：不联网探测、不重抽音轨 |
| **自动抓取清单** | 浏览器里跑一段脚本，整门课 20+ 节地址一次导出（见下文） |
| **间接地址自动换直链** | 清单里可以直接写 `previewToken` 地址，下载时自动换成签名直链 |
| 批量下载 | 一份清单里放 N 个地址，一次跑完 |
| 断点续传 | 中断后重跑，从断点继续，不重下 |
| 自动抽音轨 | 音频流**直接复制**成 m4a，零重编码、零音质损失 |
| 自动命名 | `<课程>_<日期>.mp4/.m4a`，一天多节时自动带时段 |
| 自动归档 | 跑完的清单存进 `har_archive\`，并重建空模板（`--keep-list` 可关闭） |
| 自动索引 | 每次下完刷新 `lists\<课程>.md`（已下载清单） |
| 下载前预检 | 先验链接是否过期，避免跑到一半才 403 |
| 可搬移 | 整个文件夹搬到任意路径/盘符都能跑 |
| 零第三方依赖 | 只用 Python 标准库 + ffmpeg |



---

## 一次性准备

| 依赖 | 状态 | 说明 |
|---|---|---|
| Python 3.8+ | 需要 | **自动探测**：内置 `python\python.exe` → PATH 的 `python` → `py -3`；每个候选都实际执行校验，避免撞上 Windows Store 的假 python |
| ffmpeg | **已就位** | `bin\ffmpeg.exe` + `bin\ffprobe.exe`（9.0.2） |
| 网络 | 需要 | 能直连校内 `tronclass.wh.bjtu.edu.cn`，**不需要 VPN** |

程序用自身所在目录做根目录（`%~dp0`），所以整个文件夹可以搬到任意位置。

---

## 三步上手

### 1. 在 `lists\` 里建一个清单文件

**文件名 = 课程名**。比如下计算机网络，就建：

```
D:\course-notes\lists\计网.txt
```

不需要先建 `media\计网\` —— 程序会自己建。

### 2. 把播放地址粘进去

一行一个，`#` 开头是注释：

```text
https://ilesson.wh.bjtu.edu.cn/videos/outbound1/bjtu/.../20260921/101000-120500-.../ENCODER-...?ts=...&token=...
https://ilesson.wh.bjtu.edu.cn/videos/outbound1/bjtu/.../20260928/101000-120500-.../ENCODER-...?ts=...&token=...
```

### 3.（建议）先预检

```bat
python D:\course-notes\tools\check_urls.py
```

输出：

```text
[计网.txt]
落点: D:\course-notes\media\计网

状态               大小  落点
--------------------------------------------------------------------
[OK]   1000.2 MB  计网\20260921\计网_20260921.mp4  (ENCODER)
```

有 `[FAIL]` 就重新复制那一条。

### 4. 双击三个入口之一

根目录有三个入口，**区别只在"留什么产物"**：

| 入口 | 产物 | 单节占用 | 适合 |
|---|---|---|---|
| **下视频和音频.cmd** | mp4 + m4a | ~750 MB | 要转写也要看画面（默认） |
| **只要音轨.cmd** | 只留 m4a（下完删 mp4） | ~110 MB | **只做转写，省 6.6 倍空间** |
| **只要视频.cmd** | 只留 mp4（不抽音轨） | ~640 MB | 只要录像，音频另想办法 |

三个入口都支持"双击跑全部清单"和"拖一个 txt 进去只跑它"。

```
[lists] 待下载清单 1 个:
    计网.txt      1 条地址 -> media\计网\
[getlec] LIST D:\course-notes\lists\计网.txt
[mode] 视频 + 音轨
[dest] 落点: D:\course-notes\media\计网

=== 第 1/1 节: 20260921_101000-120500  轨: ['ENCODER'] ===
  [下载] -> ...\计网_20260921.mp4
  [抽音频] -> 计网_20260921.m4a
  [信息]
  上传用这个: ...\计网_20260921.m4a
[archive] 地址清单已归档 -> urls_20260921.txt
[archive] 已重建空清单 lists\计网.txt
[archive] 已刷新下载清单 lists\计网.md
```

产物：

```text
media\计网\20260921\
├─ 计网_20260921.mp4    1000.2 MB   录像
└─ 计网_20260921.m4a     111.5 MB   音轨  ← 传千问用这个
```

---

## 怎么拿到播放地址

这是整套流程里**唯一需要手动操作**的一步，约 15 秒一节。

### 步骤

1. Edge 打开那节回放页
2. `F12` → **Network** 面板
3. 筛选框输入 **`ENCODER`**（或点「媒体」标签）
4. **点播放**，等 10–15 秒
5. 列表里出现 `ENCODER-xxxx…`，状态 **206**、类型 **媒体**
6. **右键那一行 → 复制 → 复制 URL**
7. 粘进 `lists\<科目>.txt`

### 三条轨的区别

播放器右下角有「**音源**」按钮，可切换三个来源：

| 菜单项 | URL 里的 TRACK | 内容 | 体积 |
|---|---|---|---|
| **电脑路** | `ENCODER` | 合成画面 + 课堂音频 | 0.5–1.4 GB |
| 老师路 | `INSTRUCTOR` | 教师机位 + 教师麦克风 | ~1.6 GB |
| 学生路 | `STUDENTS` | 学生机位 + 学生麦克风 | ~1.6 GB |

**默认用 `ENCODER`**：体积最小，实测音轨有正常讲课人声（平均 −19 ~ −32 dB）。
只有转写效果明显很差时才换：

```bat
D:\course-notes\getlec.cmd lists\计网.txt INSTRUCTOR
```

### 常见坑：列表里没有媒体请求

**原因**：视频整段已经缓冲完，播放不再产生新请求。按 6 MB/s 算，600 MB 的课 90 秒就缓冲完。

**解决**：勾 **「禁用缓存」** → `F5` → 再点播放。或者把进度条拖到中间，强制触发新请求。

> ⚠️ 一定要**看到媒体请求再复制**，否则复制不到东西。

---

## 自动化：整门课一次抓取（可选）

手动一节节复制地址，20 节就要点 20 次。这一节讲怎么一次拿完整门课。

### 链路与权限（已实测）

| 步骤 | 接口 | 要登录？ |
|---|---|---|
| 1. 列出课程节次 | `GET /api/courses/<courseId>/live-activities` | ✅ 要 |
| 2. 取每节的回放轨地址 | `GET /api/activities/<activityId>` | ✅ 要 |
| 3. 换成签名直链 | `incast.../preview?previewToken=` → **302** | ❌ 不要 |
| 4. 下载 | `ilesson.../ENCODER-...?ts=&token=` | ❌ 不要 |

**结论：只有前两步需要你的登录态。** 所以在浏览器里跑一小段脚本收集地址，其余全交给本地程序。

接口形状（供以后维护用，实测于 2026-11）：

```text
GET /api/courses/<courseId>/live-activities
    ?status=&types[]=lecture_live&types[]=third_party_live
    &page=<n>&page_size=<n>
→ {"items":[{id,title,start_time,type},...], "total":17, "pages":2, "page":2}
   ⚠️ items 里【没有】replay_videos，必须再逐节查详情

GET /api/activities/<activityId>
→ data.external_live_detail.replay_videos[]
   [{camera_type: encoder|students|instructor,
     url: https://incast.../videos/<cameraId>/preview?previewToken=xxx}]
```

> 未登录访问上面两个接口返回 401 —— 所以脚本只能在已登录的页面里跑。

### 用法

**推荐：装成书签，每门课点一下**

1. 用 Edge 打开 `dist\install.html`（本地文件，双击即可）
2. 按 `Ctrl+Shift+B` 显示书签栏
3. 把页面里那个蓝色按钮**拖到书签栏**（是拖拽，不是点击），可右键改名为「抓取课程清单」
4. 打开某门课的「直播」列表页（地址里有 `/course/<数字>/live-activities`）
5. **点一下书签** → 弹框填课程名 → 选是否导出三条轨（选**取消**=只导 ENCODER）
6. 浏览器下载 `<课程名>.txt`
7. 双击 `getlec.cmd` —— 它会**自动把下载文件夹里的清单收进 `lists\`** 并开始下载

**手动版（不想装书签时）**

1. 打开课程「直播」列表页，等列表加载出来
2. `F12` → **Sources** → 左侧 `>>` → **代码片段** → **新建代码片段**
3. 把 `tools\scrape_course.js` 的内容**全部**粘进去
4. `Ctrl+Enter` 运行
5. 后面的弹框和导出步骤同上

> 书签是编译产物：`tools\scrape_course.js` 是源码，运行
> `node tools\build_bookmarklet.js` 会生成 `dist\bookmarklet.txt`（一行 javascript: 地址）
> 和 `dist\install.html`（拖拽安装页）。**改了源码要重新 build。**

所以完整流程变成：**点一下书签 → 双击一次**，整门课就排队下完了。

### 课程还在进行：每周重跑一次脚本

课程没上完时，列表会逐周变长（例如计网 17 → 19 → 21 条）。**不需要任何特殊操作**，每周重复同一步：

```text
打开课程「直播」页 → 跑一次 scrape_course.js → 双击 getlec.cmd
```

各环节的行为：

| 环节 | 行为 |
|---|---|
| 脚本 | 每次拉**全量**列表（自动翻页） |
| 还没开课的节 | 没有回放文件，脚本跳过并在 Console 打日志 |
| 之后出回放了 | 下次重跑时自动出现在清单里，自动补下 |
| 已下载的节 | 本地按文件判断，**整节跳过**（不联网、不重抽音轨） |

也就是说增量是自动的：**新的一节都不会漏，旧的也不会重下**。

### 清单里存的是什么

`scrape_course.js` 导出的是 `previewToken` 地址（不是最终的签名地址）：

```
# 2026-11-09T02:10:00+00:00 2026-11-09-计算机网络与系统
https://incast.wh.bjtu.edu.cn/api/base/orgs/bjtu/captures/<hash>/videos/280740/preview?previewToken=xxx
```

本地程序在下载前会把它换成签名直链，日志里能看到：

```text
[resolve] 发现间接地址，换成直链（1 条）...
  ...preview?previewToken=bbe5  ->  ...ENCODER-xxx?ts=1794406520&token=d4f2
```

### 已知限制

`scrape_course.js` 现在**纯走接口**（列表接口自动翻页），不依赖页面 DOM，所以不受列表分页影响。

唯一的前提是：必须在**该课程的页面**里运行（地址里要有 `/course/<数字>/`），因为脚本要从 URL 里读课程 id。

如果哪天接口改版，脚本会明确报错（`列表接口失败 HTTP xxx`），而不是静默抓不到。

### 自动收编下载的清单

浏览器导出的 txt 落在「下载」文件夹，`getlec.cmd` 启动时会自动调用：

```bat
python D:\course-notes\tools\import_lists.py
```

它扫描 `%USERPROFILE%\Downloads` 里含 `previewToken` 的 txt，按文件名合并进 `lists\<课程名>.txt`（URL 去重），并把源文件移走。也可以手动指定目录：

```bat
python D:\course-notes\tools\import_lists.py --downloads D:\some\dir --dry-run
```

---

## 输出规则

### 目录结构

```text
media\<清单名>\
└─ <YYYYMMDD>\
   ├─ <清单名>_<YYYYMMDD>.mp4       录像
   ├─ <清单名>_<YYYYMMDD>.m4a       音轨
   ├─ .session                     记录这一节是哪一场（防覆盖用）
   └─ .multi                       仅当这天有多节课时存在
```

### 文件名规则

| 情况 | 文件名 |
|---|---|
| 一天**一节** | `计网_20260921.mp4` |
| 一天**多节** | `软件设计_20261014_150100-160500.mp4`<br>`软件设计_20261014_162000-181500.mp4` |

**为什么一天多节要带时段**：课程表里一天两节真会发生（实测 10-14 有 64 分钟短课 + 115 分钟正常课）。撞名时程序把旧文件改成带时段的名字、并给目录打 `.multi`，之后新文件也带时段。已带时段的名字不会被二次改名。

### 体积参考

| 项 | 规律 |
|---|---|
| 录像 | 约 **4–7 MB/分钟**（实测 530–1640 kbps 都有） |
| 音轨 | 约 **1 MB/分钟**（AAC 固定 ~130 kbps） |

一节 115 分钟的课典型值：录像 0.5–1.4 GB，音轨 106 MB。

---

## 命令速查

### 批量（最常用）

```bat
:: 处理 lists\ 下所有带地址的清单（默认：视频 + 音轨都留）
D:\course-notes\下视频和音频.cmd

:: 只要音轨（省空间，适合转写）
D:\course-notes\只要音轨.cmd

:: 只要视频（不抽音轨）
D:\course-notes\只要视频.cmd

:: 只处理一份清单（把路径拖到 .cmd 上，或直接写）
D:\course-notes\只要音轨.cmd lists\计网.txt

:: 换轨
D:\course-notes\getlec.cmd lists\计网.txt INSTRUCTOR
```

### 单节 / 调试

```bat
:: 只算路径，不联网、不建目录
python D:\course-notes\tools\lectures.py --urls lists\计网.txt --dry-run

:: 只验地址是否有效
python D:\course-notes\tools\check_urls.py

:: 看有哪些待下载清单
python D:\course-notes\tools\lists.py

:: 刷新已下载索引
python D:\course-notes\tools\make_index.py

:: 抽完音轨就删录像（等价于「只要音轨.cmd」）
set GETLEC_DROPVIDEO=1
D:\course-notes\getlec.cmd

:: 只要视频（等价于「只要视频.cmd」）
set GETLEC_NOAUDIO=1
D:\course-notes\getlec.cmd
```

### 环境变量

| 变量 | 作用 |
|---|---|
| `GETLEC_DROPVIDEO=1` | 抽完音轨后删除 mp4（只要音轨） |
| `GETLEC_NOAUDIO=1` | 不抽音轨（只要视频） |
| `GETLEC_DRYRUN=1` | 整条流程走一遍但只打印路径、不下载不写盘 |
| `GETLEC_KEEPLIST=1` | 跑完**不归档、不重建**清单，适合长期维护的增量清单 |
| `GETLEC_FORCE=1` | 已下载的也重做（强制覆盖） |
| `GETLEC_NOPAUSE=1` | 结束时不等按键（脚本内部测试用） |

---

## 脚本参数速查

### `lectures.py` — 主编排

| 参数 | 说明 |
|---|---|
| `--urls <file>` | **必填**，清单路径。落点由文件名决定 |
| `--track <名>` | `ENCODER`（默认）/ `INSTRUCTOR` / `STUDENTS` |
| `--dest <路径>` | 覆盖落点（相对本程序或绝对路径），一般不用 |
| `--drop-video` | 抽完音轨删 mp4（只要音轨） |
| `--no-audio` | 不抽音轨（只要视频） |
| `--dry-run` | 只打印路径，不联网、不建目录 |
| `--force` | 已下载的也重做 |
| `--keep-list` | 跑完不归档/不重建清单 |

### 其他工具

| 脚本 | 作用 |
|---|---|
| `get_media.py` | 下载核心：请求头基线 + Range 分块 + 断点续传 + 探活 |
| `lists.py` | 列出待下载清单；`lists\` 为空时打印操作指引 |
| `check_urls.py [清单]` | **预检**：逐条验链接有效性并预览落点 |
| `make_index.py [--dest]` | 生成已下载清单 `lists\<课程>.md`（不给参数则刷新全部课程） |
| `test_naming.py` | 命名规则测试（8 项） |
| `test_cmd_ascii.py` | `.cmd` 规范校验（纯 ASCII / CRLF / 注释无尖括号） |
| `test_base_headers.py [清单]` | 请求头回归测试（验证不用 Cookie 也能下） |
| `test_scrape.js` | 抓取脚本逻辑测试（需 Node，**仅测试用**） |

---

## 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| `[FAIL] 403` | 链接过期（`ts`/`token` 有时效） | 重新复制那一节的 URL |
| 预检全 `[OK]` 但下载卡住 | 网络拥堵 | 等等，实测出现过 2.0 MB/s（平时 6.2） |
| 中断后出现 0 字节文件 | 刚建文件就被打断 | **直接重跑**，会从 0 继续 |
| `lists\ 里还没有可下载的清单` | 没有清单或清单是空的 | 建 `lists\<科目>.txt` 并粘地址 |
| Network 里没有 `ENCODER` 请求 | 视频已缓冲，播放不走网络 | 勾「禁用缓存」→ `F5` → 再点播放 |
| 转写大量漏字 | 那节音量偏小（低到 −32 dB） | 先 `ffmpeg -af loudnorm=I=-16:TP=-1.5:LRA=11` 标准化 |
| 同一天两节互相覆盖 | 旧版本 bug | 检查日期目录里有没有 `.multi` |
| `'xx' is not recognized` 刷屏 | `.cmd` 里混了中文，或 REM 里有尖括号 | 跑 `test_cmd_ascii.py` |
| `cannot find the batch label` | `.cmd` 是 LF 换行 | 转成 CRLF，再跑 `test_cmd_ascii.py` |

### 中断了怎么办

**什么都不用做，重新双击 `getlec.cmd` 即可。**

- 已完成的节：字节数校验通过 → 跳过下载，只重抽音轨（约 15 秒/节）
- 下了一半的节：从断点续传
- 还没开始的节：正常下载

---

## 维护操作

### 加一门新课

在 `lists\` 里建一个 `<科目名>.txt`，粘地址，双击 `getlec.cmd`。**没有别的步骤**。

### 课程还在进行：每周增量下载

课程没上完时，最简单的做法是**维护一份常驻清单**，每周把新地址追加进去，然后重跑：

```bat
:: 先开增量模式（清单不被归档走）
set GETLEC_KEEPLIST=1
D:\course-notes\getlec.cmd
```

第二次跑时，已经下好的节会**整节跳过**：

```text
=== 第 1/20 节: 20260921_101000-120500 ===
  跳过（已下载）计网_20260921.mp4
=== 第 2/20 节: 20260928_101000-120500 ===
  跳过（已下载）计网_20260928.mp4
...
=== 第 20/20 节: 20261116_101000-120500 ===
  [下载] -> ...\计网_20261116.mp4     ← 只有新的这节真的下
[小结] 新下载 1 节 / 跳过 19 节 / 失败 0 节
```

**跳过是纯文件系统判断**（mp4 + m4a 都存在且非空），所以不联网、不重抽音轨，19 节约 1 秒跳过完。

需要重做某节时：

```bat
set GETLEC_FORCE=1
D:\course-notes\getlec.cmd lists\计网.txt
```

### 刷新已下载清单

```bat
python D:\course-notes\tools\make_index.py
```

扫描 `media\` 下所有课程，重建各自的 `lists\<课程>.md`。**每次下载完会自动调它**。

### 搬家 / 给同学用

**整个文件夹直接复制走就行**，不需要改任何东西：

- 程序用自身所在目录做根目录（`%~dp0`）
- Python 自动探测：不用管对方装在哪
- 对方只需要自己在 `lists\` 里建清单

拷贝时**可以不带** `media\` 和 `har_archive\`，最小可用集合：

```text
getlec.cmd
tools\
bin\            (ffmpeg.exe + ffprobe.exe，约 200 MB)
```

可选：把免安装 Python 解压成 `python\` 目录一起带上，对方就零依赖了。

### 清理

| 可以随便删 | 别删 |
|---|---|
| `har_archive\` 整个目录 | `bin\`（ffmpeg） |
| `tmp\` 里的东西 | `tools\` |
| `lists\` 里跑完的空清单 | `media\`（你的课程文件） |

---

## 设计说明

几处看起来奇怪、但都是有原因的设计。

### 为什么只认 `lists\*.txt`

早期支持过根目录 `urls.txt` 和 HAR 导入，结果是三个入口、两套配置，用户经常粘错地方（粘到根目录却以为会进科目文件夹）。

现在只有一个入口：**`lists\` 下自己建的文件，文件名就是课程名**。落点、课程名、文件名前缀全部由它推导，没有第二处配置。

### 为什么不需要 Cookie

媒体接口 `ilesson.wh.bjtu.edu.cn` **不校验 Cookie**——把浏览器那一次的请求完整抓下来看，媒体请求没带任何 Cookie。

它校验的是**请求头**：

```text
User-Agent, Referer: https://tronclass.wh.bjtu.edu.cn/,
sec-ch-ua, sec-ch-ua-platform, sec-ch-ua-mobile
```

`sec-ch-ua` 三项缺了会 403。程序里写死在 `get_media.BASE_HEADERS`。

> 早期曾误判成"cookie/session 网关"——因为拿站点根 `/` 做探针得到 403。实际上那个路径本来就 `deny all`，不能当探针用。

### 为什么分块下载

`Range` 请求按 8 MB 分块：

1. **断点续传**：中断后从已有字节数继续
2. **失败只重下那一块**（每块最多重试 6 次，指数退避）
3. **进度可见**，不会几分钟没反应

### 为什么文件名带课程名

因为**上传工具（如千问）只显示文件名、不显示路径**。混在一堆 `.m4a` 里，`计网_20260921.m4a` 一眼能认出是哪门课。

### 为什么 `.cmd` 必须纯 ASCII + CRLF

这条踩了**三次**，每次都是刷屏灾难：

| 错误 | 后果 |
|---|---|
| 注释里写中文 | cmd 按 GBK 解码 UTF-8 字节，语法被破坏，变量变空、逻辑错乱 |
| REM 注释里有 `<` `>` | cmd 在 REM 行也解析重定向符，整行被拆成垃圾命令执行 → 刷屏几千行并陷入循环 |
| LF-only 换行 | `goto` / `call` 找不到标签 → `cannot find the batch label specified` |

**规则**：`.cmd` 里只写英文、注释里不出现尖括号、保存成 CRLF。中文提示全部由 Python 打印。

`test_cmd_ascii.py` 会替你检查这三条：

```text
[PASS] getlec.cmd: 纯 ASCII
[PASS] getlec.cmd: CRLF 换行
全部通过
```

### 为什么子程序放在 `.cmd` 文件末尾

`cmd` 的 label 不是函数，执行流会**掉进去**。把 `:trypy` 这种子程序放在主流程中间，`goto` 跳过去后会顺着执行到它的 `exit /b`，后续步骤全被跳过。

### 为什么 `.session` 要用 `utf-8-sig` 读

PowerShell 的 `Set-Content -Encoding UTF8` 可能写入 BOM。Python 用普通 `utf-8` 读会多出一个 `\ufeff` 前缀，字符串比较静默失配——曾因此把同一节课误判成"另一节课"，白重下 607 MB。

---

## 已知限制

| 限制 | 说明 |
|---|---|
| **必须手动拿 URL** | 播放地址由服务端签名（`ts`+`token`），程序无法自己生成 |
| **URL 有时效** | 实测 1 小时以上仍可用，但别放到第二天 |
| **只能 ENCODER 等三轨** | 平台只提供这三条流 |
| **本机 schannel 坏了** | `curl.exe`、PowerShell `Invoke-WebRequest`、`.NET WebClient`、`certutil` 全连不上外网，只有 Python 的 OpenSSL 栈能通。所以下载逻辑全走 Python |
| **不能自动翻课程列表** | 需要浏览器登录态，程序不碰账号 |
| **没有内置 Python** | 依赖系统已有 Python；想零依赖就把免安装版解压到 `python\` |

---

## 目录结构

```text
D:\course-notes\                          ← 整个文件夹可搬到任意位置
├─ 下视频和音频.cmd          ★ 入口：视频 + 音轨（默认）
├─ 只要音轨.cmd              ★ 入口：只留 m4a
├─ 只要视频.cmd              ★ 入口：只留 mp4
├─ getlec.cmd                主脚本（三个入口都调用它）
├─ README.md                 本文档
├─ bin\
│  ├─ ffmpeg.exe             9.0.2
│  └─ ffprobe.exe
├─ tools\                    12 个脚本
│  ├─ get_media.py           请求头基线 + 探活 + 分块下载 + resolve 间接地址
│  ├─ lectures.py            主编排：解析→下载→抽音轨→命名→归档→刷索引
│  ├─ lists.py               列出待下载清单 / 空清单指引
│  ├─ import_lists.py        收编浏览器导出的抓取清单
│  ├─ scrape_course.js       浏览器里跑的整门课抓取脚本（书签源码）
│  ├─ build_bookmarklet.js   把上面那个编译成书签 + 安装页（需 Node）
│  ├─ check_urls.py          下载前预检
│  ├─ make_index.py          生成已下载清单
│  ├─ test_naming.py         命名/分组测试（11 项）
│  ├─ test_modes.py          三种模式判定测试（18 项）
│  ├─ test_cmd_ascii.py      .cmd 规范校验
│  └─ test_base_headers.py   请求头回归
├─ dist\                     ★ 抓取书签（install.html 拖拽安装）
├─ lists\                    ★ 在这里建 <科目>.txt
│  ├─ 计网.txt               待下载队列（粘地址）
│  ├─ 计网.md                已下载索引（自动生成）
│  ├─ 软件设计.txt
│  └─ 软件设计.md
├─ media\
│  ├─ 计网\
│  │  └─ 20260921\  计网_20260921.mp4 + .m4a
│  └─ 软件设计\
│     ├─ 20260918\  软件设计_20260918.mp4 + .m4a
│     └─ 20261014\  软件设计_20261014_150100-160500.mp4 + .m4a
│                    软件设计_20261014_162000-181500.mp4 + .m4a
├─ har_archive\              历史清单归档（urls_<日期>.txt）
├─ python\                   （可选）免安装 Python，放了就优先用它
└─ tmp\                      临时目录（可清空）
```

---

## 测试

```bat
python D:\course-notes\tools\test_naming.py        :: 8 项，不联网
python D:\course-notes\tools\test_cmd_ascii.py     :: .cmd 规范
python D:\course-notes\tools\test_base_headers.py  :: 需联网 + 新鲜清单
```

### `test_naming.py` — 命名规则（8 项）

覆盖一节/两节/三节、旧命名迁移、BOM 容错：

```text
[第一节 命名]     PASS  软件设计_20261014.mp4
[第一节 无.multi] PASS
[第二节 有.multi] PASS
[第二节 旧改名]   PASS  软件设计_20261014_150100-160500.mp4
[第二节 新命名]   PASS  软件设计_20261014_162000-181500.mp4
[第三节 不改旧名] PASS
[第三节 新命名]   PASS  软件设计_20261014_190000-200000.mp4
[BOM 同课时]      PASS
全部通过
```

### `test_scrape.js` — 抓取脚本逻辑（需 Node，7 项，不联网）

用假 fetch 模拟接口和页面环境，验证 `scrape_course.js` 的行为：列表翻页、跳过未开始的活动、只导 ENCODER、文件名与表头。

```bat
node D:\course-notes\tools\test_scrape.js
```

```text
[PASS] 列表接口调用 1 次
[PASS] 只查了已开始的 15 节
[PASS] 文件名是 测试课程.txt
[PASS] 清单里 15 条地址
[PASS] 只导了 ENCODER
[PASS] 未开始的节没被下载
[PASS] 有表头注释
全部通过
```

> 只有测试需要 Node；**运行程序本身不需要**。

### `test_base_headers.py` — 请求头回归

验证「不用 Cookie、只凭自拼请求头就能取到数据」= 「只要有地址就能下」这个前提。

需要**未过期的清单**。三种结果：

| 退出码 | 含义 |
|---|---|
| `0` PASS | 设计前提成立 |
| `3` SKIP | 地址已过期 —— **不是失败**，换新鲜清单再跑 |
| `1` FAIL | 地址没过期却取不到 → 请求头策略可能变了，排查 `BASE_HEADERS` |
