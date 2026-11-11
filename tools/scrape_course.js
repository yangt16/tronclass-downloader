/**
 * scrape_course.js - 在「课程直播回放列表页」上运行，导出整门课的抓取清单。
 *
 * 原理（已实测）：
 *   1. GET /api/activities/<activityId>   ← 需要登录态（在页面里跑就自带）
 *        返回 JSON: data.external_live_detail.replay_videos[].url
 *        这些 url 形如 incast.../videos/<cameraId>/preview?previewToken=xxx
 *   2. 本地程序再拿这些 url 去换签名直链（这一步不需要登录）
 *
 * 怎么运行（Edge）：
 *   a) 打开课程页，例如 /course/26384/live-activities
 *   b) F12 → Sources（源代码）→ 左侧 >> → 代码片段 → 新建代码片段
 *   c) 把本文件全部内容粘进编辑器
 *   d) Ctrl+Enter 运行
 *   e) 会下载一个 <课程名>.txt，把它放进 D:\course-notes\lists\
 *
 * 也可以在 Console 里跑（前提是已输入过 allow pasting）。
 */
(async () => {
  // ---------- 1. 收集本页出现过的 activityId ----------
  const html = document.documentElement.innerHTML;
  const ids = [...new Set(
    [...html.matchAll(/live-activities#?\/(\d+)\/detail/g)].map(m => m[1])
  )];
  if (!ids.length) {
    alert('没找到节次。请先打开这门课的「直播」回放列表页，让列表加载出来。');
    return;
  }
  console.log(`[scrape] 找到 ${ids.length} 个 activityId:`, ids);

  // ---------- 2. 逐个查详情，取三条轨的 preview 地址 ----------
  const rows = [];
  for (const id of ids) {
    try {
      const r = await fetch(`/api/activities/${id}`, { credentials: 'include' });
      if (!r.ok) { console.warn(`[scrape] ${id} HTTP ${r.status}`); continue; }
      const j = await r.json();
      const det = (j.data && j.data.external_live_detail) || {};
      const vids = det.replay_videos || [];
      if (!vids.length) { console.warn(`[scrape] ${id} 没有回放视频`); continue; }
      rows.push({
        id,
        title: j.title || '',
        start: det.start_time || '',
        videos: vids
          .filter(v => v.camera_type === 'encoder' || v.camera_type === 'instructor' || v.camera_type === 'students')
          .map(v => ({ type: v.camera_type, url: v.url })),
      });
    } catch (e) {
      console.warn(`[scrape] ${id} 失败:`, e);
    }
  }
  if (!rows.length) {
    alert('一条回放地址都没取到。可能是这门课还没出回放。');
    return;
  }

  // ---------- 3. 选文件名（课程名） ----------
  const guess = (document.title || '').split(/[-–|]/)[0].trim() || 'course';
  const course = (prompt('清单名（= 课程名，决定 media\\ 下的文件夹名）', guess) || '').trim();
  if (!course) { alert('已取消'); return; }

  // ---------- 4. 只导出 ENCODER（体积最小、含课堂音频）；可选全部 ----------
  const all = confirm(
    `已取到 ${rows.length} 节课的地址。\n\n` +
    `确定 = 只导出 ENCODER（推荐，每节 0.5-1.4 GB）\n` +
    `取消 = 三条轨全导出（每节约 4.4 GB）`
  );

  const lines = [];
  lines.push(`# ${course} · 自动抓取于 ${new Date().toLocaleString()}`);
  lines.push(`# 共 ${rows.length} 节；每行一条 preview 地址（本地程序会自动换成直链）`);
  for (const r of rows) {
    lines.push(`# ${r.start} ${r.title}`);
    const pick = all ? r.videos : r.videos.filter(v => v.type === 'encoder');
    for (const v of pick) lines.push(v.url);
    if (!pick.length) lines.push(`# (该节没有 encoder 轨)`);
  }

  const blob = new Blob([lines.join('\n') + '\n'], { type: 'text/plain;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${course}.txt`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  console.log(`[scrape] 已导出 ${rows.length} 节 -> ${course}.txt（在下载文件夹）`);
  console.log('[scrape] 把它放到 D:\\course-notes\\lists\\ 下，然后双击 getlec.cmd');
})();
