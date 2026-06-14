# -*- coding: utf-8 -*-
import asyncio, traceback
from pathlib import Path
from playwright.async_api import async_playwright

URL = 'https://kakeizu-navi-3joa5l78sjkams2axwbxix.streamlit.app/'
OUT = Path(__file__).parent
LOG = []
def log(*a):
    LOG.append(' '.join(str(x) for x in a)); print(*a, flush=True)

async def cframe(pg):
    for fr in pg.frames:
        try:
            if await fr.get_by_text('免責', exact=False).count() > 0: return fr
        except Exception: pass
    return pg.main_frame

async def shoot_at(pg, fr, anchor, name):
    try:
        el = fr.get_by_text(anchor, exact=False).first
        await el.scroll_into_view_if_needed(timeout=6000)
        await pg.wait_for_timeout(1500)
        await pg.screenshot(path=str(OUT / name)); log('shot', name, 'at', anchor)
    except Exception as e:
        log('shoot', anchor, repr(e)[:80])

async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 1280, 'height': 1000})
        await pg.goto(URL, wait_until='domcontentloaded', timeout=90000)
        await pg.wait_for_timeout(10000)
        try:
            w = pg.get_by_text('get this app back up', exact=False)
            if await w.count() > 0:
                await w.first.click(timeout=8000); await pg.wait_for_timeout(50000)
        except Exception: pass
        await pg.wait_for_timeout(4000)
        fr = await cframe(pg)
        try:
            el = fr.get_by_text('同意した上で利用します', exact=False)
            if await el.count() > 0: await el.first.click(timeout=8000); await pg.wait_for_timeout(6000)
        except Exception: pass
        # 標準ケース
        btns = fr.get_by_role('button'); n = await btns.count()
        for i in range(n):
            try: t = (await btns.nth(i).inner_text()).strip()
            except Exception: t=''
            if '標準ケース' in t:
                await btns.nth(i).scroll_into_view_if_needed(timeout=5000); await pg.wait_for_timeout(600)
                await btns.nth(i).click(timeout=6000); log('clicked 標準'); await pg.wait_for_timeout(8000); break
        # 各セクションを撮影
        await shoot_at(pg, fr, '相続税', '08_tax.png')
        await shoot_at(pg, fr, '小規模宅地', '09_special.png')
        await shoot_at(pg, fr, '二次相続', '10_secondary.png')
        await shoot_at(pg, fr, 'AI診断', '11_ai.png')
        await shoot_at(pg, fr, 'PDF', '12_pdf.png')
        # サイドバー広告の実態
        for t in ['広告プレースホルダー', 'スポンサー広告', '税理士ドットコム']:
            try: log('sidebar has', t, await fr.get_by_text(t, exact=False).count())
            except Exception: log('sidebar', t, 'ERR')
        await b.close()

try:
    asyncio.run(run())
except Exception:
    LOG.append(traceback.format_exc()); print(traceback.format_exc(), flush=True)
(OUT / 'log6.txt').write_text('\n'.join(LOG), encoding='utf-8')
