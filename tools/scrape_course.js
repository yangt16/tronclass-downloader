/**
 * scrape_course.js (v2) - 在课程「直播」页上运行，导出整门课的回放清单。
 *
 * 纯走接口，不依赖 DOM，不受分页影响。已实测的接口形状：
 *
 *   1) 列表
 *      GET /api/courses/<courseId>/live-activities
 *          ?status=&types[]=lecture_live&types[]=third_party_live
 *          &page=<n>&page_size=<n>
 *      → { items:[{id,title,start_time,type}], total, pages, page, start, end }
 *        注意 items 里【没有】replay_videos
 *
 *   2) 每节详情
 *      GET /api/activities/<activityId>
 *      → data.external_live_detail.replay_videos[]
 *        每条 { camera_type: encoder|students|instructor,
 *               url: https://incast.../videos/<id>/preview?previewToken=xxx }
 *
 *   3) 本地程序拿到这些 url 后自己换签名直链（这步不需要登录）
 *
 * 怎么运行（Edge）：
 *   a) 打开课程「直播」列表页，形如 /course/26384/live-activities
 *   b) F12 → Sources → 左侧 >> → 代码片段 → 新建代码片段
 *   c) 把本文件全部内容粘进编辑器
 *   d) Ctrl+Enter 运行
 *   e) 下载出 <课程名>.txt；双击 getlec.cmd 会自动收编并下载
 */
(async () => {
  const m = location.pathname.match(/course\/(\d+)/);
  if (!m) {
    alert('请在课程页面运行本脚本（地址里要有 /course/<数字>/）');
    return;
  }
  const courseId = m[1];
  console.log(`[scrape] courseId=${courseId}`);

  // ---------- 1. 拉列表（自动翻页） ----------
  const PAGE = 100;                 // 先试一次拉完；服务端若限流，pages 会告诉我们
  const types = 'types[]=lecture_live&types[]=third_party_live';
  const all = [];
  let page = 1, pages = 1, total = 0;
  do {
    const url = `/api/courses/${courseId}/live-activities` +
                `?status=&${types}&page=${page}&page_size=${PAGE}`;
    const r = await fetch(url, { credentials: 'include' });
    if (!r.ok) { alert(`列表接口失败 HTTP ${r.status}`); return; }
    const j = await r.json();
    total = j.total ?? 0;
    pages = j.pages ?? 1;
    (j.items || []).forEach(it => all.push(it));
    console.log(`[scrape] 第 ${page}/${pages} 页，累计 ${all.length}/${total} 条`);
    page++;
  } while (page <= pages && page <= 50);

  const live = all.filter(it => it.type === 'lecture_live');
  if (!live.length) { alert('这门课没有 lecture_live 类型的活动'); return; }
  console.log(`[scrape] lecture_live 共 ${live.length} 条`);

  // 未开始的节没有回放，先按状态过滤掉，省掉无谓的详情请求
  const started = live.filter(it => {
    if (it.is_started === false) {
      console.log(`[scrape] ${it.id} ${it.title} 未开始，跳过（出回放后重跑本脚本即可）`);
      return false;
    }
    return true;
  });
  console.log(`[scrape] 需要查详情的 ${started.length} 条`);

  // ---------- 2. 逐节取回放轨 ----------
  const rows = [];
  for (const it of started) {
    try {
      const r = await fetch(`/api/activities/${it.id}`, { credentials: 'include' });
      if (!r.ok) { console.warn(`[scrape] ${it.id} HTTP ${r.status}`); continue; }
      const j = await r.json();
      const det = (j.data && j.data.external_live_detail) || {};
      const vids = det.replay_videos || [];
      if (!vids.length) { console.warn(`[scrape] ${it.id} 无回放（可能还没下课）`); continue; }
      rows.push({
        id: it.id,
        title: j.title || it.title || '',
        date: (it.start_time || '').slice(0, 10),
        videos: vids,
      });
      console.log(`[scrape] ${it.id} ${it.start_time} -> ${vids.length} 条轨`);
    } catch (e) {
      console.warn(`[scrape] ${it.id} 失败:`, e);
    }
  }
  if (!rows.length) { alert('一条回放都没取到（这门课可能还没出回放）'); return; }

  // ---------- 3. 课程名：从活动标题里去掉日期前缀 ----------
  const guess = (rows[0].title || '').replace(/^\d{4}-\d{2}-\d{2}-?/, '').trim() || `course${courseId}`;
  const course = (prompt(
    `已取到 ${rows.length} 节回放。\n\n清单名（= 课程名，决定 media\\ 下的文件夹名）：`,
    guess) || '').trim();
  if (!course) { alert('已取消'); return; }

  const allTracks = confirm(
    `确定 = 只导出 ENCODER（推荐，每节 0.5-1.4 GB）\n` +
    `取消 = 三条轨全导出（每节约 4.4 GB）`
  );

  // ---------- 4. 生成清单 ----------
  const lines = [
    `# ${course} · 自动抓取于 ${new Date().toLocaleString()}`,
    `# 共 ${rows.length} 节；每行一条 preview 地址，本地程序会换成签名直链`,
  ];
  for (const r of rows) {
    lines.push(`# ${r.date} ${r.title}`);
    const pick = allTracks ? r.videos : r.videos.filter(v => v.camera_type === 'encoder');
    if (!pick.length) { lines.push(`# (无 encoder 轨，已跳过)`); continue; }
    for (const v of pick) lines.push(v.url);
  }

  const blob = new Blob([lines.join('\n') + '\n'], { type: 'text/plain;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${course}.txt`;
  document.body.appendChild(a);
  a.click();
  a.remove();

  console.log(`[scrape] 完成：${rows.length} 节 -> ${course}.txt`);
  alert(`已导出 ${rows.length} 节到「下载」文件夹的 ${course}.txt\n\n接下来双击 getlec.cmd 即可自动开始下载。`);
})();
