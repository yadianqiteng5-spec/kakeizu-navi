# -*- coding: utf-8 -*-
import asyncio, traceback
from pathlib import Path
from playwright.async_api import async_playwright

URL = 'https://kakeizu-navi-3joa5l78sjkams2axwbxix.streamlit.app/'
OUT = Path(__file__).parent
LOG = []
def log(*a):
    LOG.append(' '.join(str(x) for x in a)); print(*a, flush=True)

async def content_frame(pg):
    for fr in pg.frames:
        try:
            if await fr.get_by_text('免責', exact=False).count() > 0:
                return fr
        except Exception: pass
    return pg.main_frame

async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 1280, 'height': 1100})
        await pg.goto(URL, wait_until='domcontentloaded', timeout=90000)
        await pg.wait_for_timeout(10000)
        try:
            w = pg.get_by_text('get this app back up', exact=False)
            if await w.count() > 0:
                await w.first.click(timeout=8000); await pg.wait_for_timeout(50000)
        except Exception: pass
        await pg.wait_for_timeout(4000)
        fr = await content_frame(pg)
        # consent
        try:
            el = fr.get_by_text('同意した上で利用します', exact=False)
            if await el.count() > 0:
                await el.first.click(timeout=8000); await pg.wait_for_timeout(6000)
        except Exception as e: log('consent', repr(e)[:80])

        # 全ボタンのラベルを列挙
        btns = fr.get_by_role('button')
        n = await btns.count()
        labels = []
        for i in range(n):
            try:
                t = (await btns.nth(i).inner_text()).strip().replace('\n',' ')
                if t: labels.append(t)
            except Exception: pass
        log('BUTTONS(', n, '):', ' | '.join(labels[:40]))

        # 典型事例のボタンを優先的にクリック（ラベルにシナリオ語を含むもの）
        target = None
        for i in range(n):
            try:
                t = (await btns.nth(i).inner_text()).strip()
            except Exception:
                t = ''
            if any(k in t for k in ['配偶者と子', '標準', '配偶者＋子', '子あり', '事例']):
                target = (i, t); break
        if target:
            i, t = target
            await btns.nth(i).scroll_into_view_if_needed(timeout=5000)
            await pg.wait_for_timeout(800)
            await btns.nth(i).click(timeout=6000)
            log('clicked scenario:', t)
            await pg.wait_for_timeout(7000)
        else:
            log('no scenario button matched')

        await pg.screenshot(path=str(OUT / '07_demo_result.png'), full_page=True); log('shot 07')
        # 結果テキスト確認
        for t in ['法定相続分', '遺留分', '相続税', '家系図', 'AI診断', 'PDF']:
            try: log('result has', t, await fr.get_by_text(t, exact=False).count())
            except Exception: log('result has', t, 'ERR')
        await b.close()

try:
    asyncio.run(run())
except Exception:
    LOG.append(traceback.format_exc()); print(traceback.format_exc(), flush=True)
(OUT / 'log5.txt').write_text('\n'.join(LOG), encoding='utf-8')
