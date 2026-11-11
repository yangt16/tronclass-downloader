/**
 * 离线验证 scrape_course.js（或编译后的书签）的逻辑：用假 fetch/假页面环境跑一遍，
 * 检查它拉了几页、跳过了几节、生成的清单内容对不对。
 *
 * 用法:
 *   node tools/test_scrape.js                       测试 tools/scrape_course.js
 *   node tools/test_scrape.js dist/bookmarklet.txt  测试编译好的书签
 */
const fs = require('fs');
const path = require('path');

const SRC = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.join(__dirname, 'scrape_course.js');

let code = fs.readFileSync(SRC, 'utf8');
if (code.startsWith('javascript:')) {
  code = decodeURIComponent(code.slice('javascript:'.length));
  console.log(`[test] 从书签地址解码：${SRC}`);
} else {
  console.log(`[test] 从源码读取：${SRC}`);
}

// ---------- 假数据：17 条，其中 2 条未开始 ----------
const items = [];
for (let i = 0; i < 17; i++) {
  const started = i >= 2;                       // 前两条未开始
  items.push({
    id: 270000 + i,
    type: 'lecture_live',
    title: `2026-11-${String(17 - i).padStart(2, '0')}-计算机网络与系统`,
    start_time: `2026-11-${String(17 - i).padStart(2, '0')}T02:10:00Z`,
    is_started: started,
  });
}

const requests = [];
let downloadedName = null;
let downloadedText = null;
let alerts = [];

global.location = { pathname: '/course/26384/live-activities' };
global.fetch = async (url) => {
  requests.push(url);
  if (url.includes('/live-activities')) {
    return {
      ok: true,
      json: async () => ({ items, total: 17, pages: 1, page: 1, page_size: 100 }),
    };
  }
  const m = url.match(/activities\/(\d+)/);
  const id = Number(m[1]);
  const it = items.find(x => x.id === id);
  const started = it && it.is_started;
  return {
    ok: true,
    json: async () => ({
      title: it ? it.title : '',
      data: {
        external_live_detail: {
          replay_videos: started
            ? [
                { camera_type: 'encoder', url: `https://incast/x/videos/${id}0/preview?previewToken=enc${id}` },
                { camera_type: 'students', url: `https://incast/x/videos/${id}1/preview?previewToken=stu${id}` },
                { camera_type: 'instructor', url: `https://incast/x/videos/${id}2/preview?previewToken=ins${id}` },
              ]
            : [],
        },
      },
    }),
  };
};
global.prompt = () => '测试课程';
global.confirm = () => false;                     // false = 只导 ENCODER
global.alert = (m) => alerts.push(m);

const blobParts = [];
global.Blob = class {
  constructor(parts) { blobParts.push(parts.join('')); }
};
global.URL = { createObjectURL: () => 'blob:fake' };
global.document = {
  body: { appendChild() {} },
  createElement: () => ({
    set href(v) {}, get href() { return ''; },
    set download(v) { downloadedName = v; },
    get download() { return downloadedName; },
    click() { downloadedText = blobParts[blobParts.length - 1]; },
    remove() {},
  }),
};

(async () => {
  const logs = [];
  const origLog = console.log;
  console.log = (...a) => { logs.push(a.join(' ')); origLog(...a); };
  const origWarn = console.warn;
  console.warn = (...a) => { logs.push('WARN ' + a.join(' ')); origWarn(...a); };

  await eval(code);

  console.log('\n================ 诊断 ================');
  console.log('  downloadedText 类型:', typeof downloadedText);
  console.log('  blobParts 数量:', blobParts.length);
  console.log('  downloadedName:', downloadedName);
  console.log('  alerts:', alerts.length);

  console.log('\n================ 验证 ================');
  const text = downloadedText || '';
  const listCalls = requests.filter(u => u.includes('/live-activities'));
  const detailCalls = requests.filter(u => u.includes('/activities/'));
  const lines = text.split('\n').filter(l => l && !l.startsWith('#'));
  const comments = text.split('\n').filter(l => l.startsWith('#'));

  const checks = [
    ['列表接口调用 1 次', listCalls.length === 1],
    ['只查了已开始的 15 节', detailCalls.length === 15],
    ['文件名是 测试课程.txt', downloadedName === '测试课程.txt'],
    ['清单里 15 条地址', lines.length === 15],
    ['只导了 ENCODER', lines.length > 0 && lines.every(u => u.includes('previewToken=enc'))],
    ['未开始的节没被下载', !lines.some(u => u.includes('270000') || u.includes('270001'))],
    ['有表头注释', comments.length > 0 && comments[0].startsWith('# 测试课程')],
  ];
  let bad = 0;
  for (const [name, ok] of checks) {
    console.log(`  [${ok ? 'PASS' : 'FAIL'}] ${name}`);
    if (!ok) bad++;
  }
  console.log(bad ? `\n${bad} 项失败` : '\n全部通过');
  process.exit(bad ? 1 : 0);
})();
