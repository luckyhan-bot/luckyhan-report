// 오늘(또는 지정일) 네이버 증권 종목분석 리포트를 모아 work/<날짜>/reports.json 과 PDF 텍스트를 만든다.
// 사용: node scripts/fetch.js [YYYY-MM-DD]
// 공개 모바일 페이지(m.stock.naver.com)를 브라우저로 열어, 페이지가 스스로 불러오는 데이터를 읽는다.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const UA = 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36';
const kstToday = () => new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
const DAY = process.argv[2] || kstToday();
const ROOT = path.resolve(__dirname, '..');
const WORK = path.join(ROOT, 'work', DAY);
fs.mkdirSync(path.join(WORK, 'pdf'), { recursive: true });

const num = s => { if (s == null) return null; const m = String(s).replace(/,/g, '').match(/-?\d+(\.\d+)?/); return m ? Number(m[0]) : null; };
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function withPage(browser, fn) {
  const ctx = await browser.newContext({ userAgent: UA, viewport: { width: 412, height: 900 } });
  const p = await ctx.newPage();
  try { return await fn(p); } finally { await ctx.close(); }
}

// 1) 목록: 리서치 > 국내종목 목록을 스크롤하며 해당 날짜 리포트를 모은다
async function fetchList(browser) {
  return withPage(browser, async p => {
    const rows = new Map();
    p.on('response', async r => {
      if (!r.url().includes('/front-api/research/list')) return;
      try { const j = await r.json(); for (const x of j.result || []) rows.set(x.researchId, x); } catch (e) {}
    });
    await p.goto('https://m.stock.naver.com/investment/research/company', { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
    for (let i = 0; i < 12; i++) {
      const dates = [...rows.values()].map(x => x.writeDate).sort();
      if (dates.length && dates[0] < DAY) break;          // 더 이전 날짜까지 내려왔으면 끝
      const before = rows.size;
      await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await sleep(1500);
      const more = await p.$('button:has-text("더보기")');
      if (more) { await more.click().catch(() => {}); await sleep(1500); }
      if (rows.size === before && i > 2) break;
    }
    return [...rows.values()].filter(x => x.writeDate === DAY && x.itemCode);
  });
}

// 2) 상세: 투자의견·목표주가·현재주가·요약·PDF·같은 종목 과거 리포트
async function fetchDetail(browser, id) {
  return withPage(browser, async p => {
    await p.goto(`https://m.stock.naver.com/research/company/${id}`, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
    await p.waitForSelector('text=원문 보기', { timeout: 15000 }).catch(() => {});
    return p.evaluate(() => {
      const t = document.body.innerText;
      const grab = re => { const m = t.match(re); return m ? m[1].trim() : null; };
      const pdf = [...document.querySelectorAll('a[href*="pdf"]')].map(a => a.href)[0] || null;
      const related = [...document.querySelectorAll('a[href*="/research/company/"]')]
        .map(a => ({ id: Number((a.href.match(/company\/(\d+)/) || [])[1]), text: a.innerText.trim() }))
        .filter(x => x.id && x.text);
      let summary = '';
      const a = t.indexOf('현재주가'), b = t.indexOf('원문 보기', a);
      if (a > 0 && b > a) summary = t.slice(a, b).replace(/^현재주가\s*(도움말)?\s*[\d,]+원?/, '').trim();
      return {
        opinion: grab(/투자의견\s*\n\s*([^\n]+)/),
        target: grab(/목표주가\s*\n\s*([^\n]+)/),
        price: grab(/현재주가\s*\n\s*(?:도움말\s*\n\s*)?([^\n]+)/),
        summary, pdf, related,
      };
    });
  });
}

// 3) 종목: 시가총액·전일 종가 (종목 페이지가 불러오는 실시간 시세)
async function fetchStock(browser, code) {
  return withPage(browser, async p => {
    const out = { code };
    p.on('response', async r => {
      const u = r.url();
      try {
        if (u.includes('/front-api/realTime/unified')) {
          const it = ((await r.json()).result || {}).items || {};
          if (it[code]) out.rt = it[code];
        } else if (u.includes('/front-api/stock/domestic/fundamentals')) out.fund = (await r.json()).result;
        else if (u.includes('/front-api/stock/domestic/consensus')) out.cons = (await r.json()).result;
      } catch (e) {}
    });
    await p.goto(`https://m.stock.naver.com/domestic/stock/${code}/total`, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
    await sleep(800);
    const rt = out.rt || {};
    const cur = num(rt.currentPrice);
    let chg = num(rt.fluctuations);
    if (chg != null && /FALL|LOWER/i.test(rt.fluctuationsType || '') && chg > 0) chg = -chg;
    const mv = num(rt.marketValue);
    // 리포트 날짜 기준 = 전일 종가. 장 마감 후(저녁) 실행이므로 오늘 종가 - 오늘 등락 = 전일 종가
    const tradedDay = (rt.localTradedAt || '').slice(0, 10);
    const prevClose = cur != null && chg != null ? (tradedDay === DAY ? cur - chg : cur) : null;
    return {
      code, market: rt.marketType || null, close: cur, prevClose, tradedAt: rt.localTradedAt || null,
      mcapPrev: mv && cur && prevClose ? Math.round(mv / cur * prevClose) : mv,
      per: num(out.fund && out.fund.per), estPer: num(out.fund && out.fund.estimatedPer), pbr: num(out.fund && out.fund.pbr),
      divYield: num(out.fund && out.fund.dividendYield),
      consTarget: num(out.cons && out.cons.consensusInfo && out.cons.consensusInfo.priceTargetMean),
    };
  });
}

async function pool(items, n, fn) {
  const res = new Array(items.length); let i = 0;
  await Promise.all(Array.from({ length: n }, async () => {
    while (i < items.length) { const k = i++; try { res[k] = await fn(items[k]); } catch (e) { res[k] = { error: String(e) }; } }
  }));
  return res;
}

function pdfText(url, id) {
  const real = (() => { try { return new URL(url).searchParams.get('url') || url; } catch (e) { return url; } })();
  const f = path.join(WORK, 'pdf', `${id}.pdf`), t = path.join(WORK, 'pdf', `${id}.txt`);
  try {
    if (!fs.existsSync(f)) execFileSync('curl', ['-sS', '-L', '-A', 'Mozilla/5.0', '-o', f, real], { timeout: 60000 });
    execFileSync('pdftotext', ['-layout', f, t], { timeout: 60000 });
    return { pdfUrl: real, textFile: path.relative(ROOT, t) };
  } catch (e) { return { pdfUrl: real, textFile: null }; }
}

// 목표주가 변화 신호를 PDF 첫 장에서 찾는다 (예: "목표주가 71,000 유지", "상향", "하향")
function pdfHints(textFile) {
  if (!textFile) return {};
  const head = fs.readFileSync(path.join(ROOT, textFile), 'utf8').split('\n').slice(0, 60).join('\n');
  const near = (kw) => { const i = head.search(kw); return i < 0 ? '' : head.slice(i, i + 160); };
  const tp = near(/목표\s*주가|목표가|Target Price/i), op = near(/투자\s*의견|Rating/i);
  const dir = s => /상향|Up\b/i.test(s) ? 'up' : /하향|Down\b/i.test(s) ? 'down' : /유지|Maintain/i.test(s) ? 'keep' : null;
  return { pdfTargetDir: dir(tp), pdfOpinionDir: /상향|하향|변경|신규|Initiate/i.test(op) ? (op.match(/상향|하향|변경|신규|Initiate/i) || [])[0] : (dir(op) || null) };
}

(async () => {
  const browser = await chromium.launch();
  const list = await fetchList(browser);
  console.log(`[${DAY}] 리포트 ${list.length}건`);
  if (!list.length) { fs.writeFileSync(path.join(WORK, 'reports.json'), JSON.stringify({ date: DAY, reports: [] })); await browser.close(); return; }

  const details = await pool(list, 3, x => fetchDetail(browser, x.researchId));
  const codes = [...new Set(list.map(x => x.itemCode))];
  const stocks = Object.fromEntries((await pool(codes, 3, c => fetchStock(browser, c))).map((s, i) => [codes[i], s]));

  // 같은 증권사의 직전 리포트 → 기존 목표주가·투자의견
  const reports = [];
  for (let i = 0; i < list.length; i++) {
    const x = list[i], d = details[i] || {};
    const prev = (d.related || []).find(r => r.id !== x.researchId && r.id < x.researchId && r.text.includes(x.brokerName));
    let prevInfo = null;
    if (prev) {
      const pd = await fetchDetail(browser, prev.id).catch(() => null);
      const pdate = (prev.text.match(/(\d{4})\.(\d{2})\.(\d{2})/) || []).slice(1).join('-');
      if (pd) prevInfo = { id: prev.id, date: pdate || null, opinion: pd.opinion, target: num(pd.target) };
    }
    const pdf = d.pdf ? pdfText(d.pdf, x.researchId) : { pdfUrl: null, textFile: null };
    reports.push({
      id: x.researchId, code: x.itemCode, name: x.itemName, title: x.title, broker: x.brokerName, date: x.writeDate,
      readCount: num(x.readCount), url: `https://m.stock.naver.com/research/company/${x.researchId}`,
      opinion: d.opinion || null, target: num(d.target), reportPrice: num(d.price), summary: d.summary || '',
      prev: prevInfo, ...pdf, ...pdfHints(pdf.textFile), stock: stocks[x.itemCode] || null,
    });
    process.stdout.write('.');
  }
  await browser.close();
  fs.writeFileSync(path.join(WORK, 'reports.json'), JSON.stringify({ date: DAY, fetchedAt: new Date().toISOString(), reports }, null, 1));
  console.log(`\n저장: work/${DAY}/reports.json`);
})();
