# -*- coding: utf-8 -*-
import asyncio, traceback
from pathlib import Path
from playwright.async_api import async_playwright

URL = 'https://kakeizu-navi-3joa5l78sjkams2axwbxix.streamlit.app/'
OUT = Path(__file__).parent
LOG = []
def log(*a):
    LOG.append(' '.join(str(x) for x in a)); print(*a, flush=True)

async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 1280, 'height': 1100})
        await pg.goto(URL, wait_until='domcontentloaded', timeout=90000)
        await pg.wait_for_timeout(9000)
        # wake
        try:
            w = pg.get_by_text('get this app back up', exact=False)
            if await w.count() > 0:
                await w.first.click(timeout=8000); log('woke'); await pg.wait_for_timeout(50000)
        except Exception: pass
        await pg.wait_for_timeout(4000)

        # 1) 同意チェック
        try:
            cb = pg.get_by_role('checkbox')
            if await cb.count() > 0:
                await cb.first.click(timeout=8000); log('consent clicked')
                await pg.wait_for_timeout(4000)
        except Exception as e:
            log('consent err', repr(e)[:100])
        await pg.screenshot(path=str(OUT / '02_after_consent.png')); log('shot 02')

        # 2) 入力画面のタブ群を撮影（スクロール下げて入力エリア）
        await pg.mouse.wheel(0, 500); await pg.wait_for_timeout(1500)
        await pg.screenshot(path=str(OUT / '03_input_tabs.png')); log('shot 03')

        # 3) 典型事例集（デモ）を探してクリック→結果へ
        # 「典型事例」「デモ」「標準」等のボタン候補
        clicked = False
        for kw in ['標準', '配偶者と子', '典型事例', 'デモ', '事例で体験', '事例']:
            try:
                el = pg.get_by_role('button', name=lambda n: kw in n) if False else pg.get_by_text(kw, exact=False)
                if await el.count() > 0:
                    await el.first.scroll_into_view_if_needed(timeout=4000)
                    await pg.wait_for_timeout(800)
                    await el.first.click(timeout=5000)
                    log('clicked demo kw=', kw); clicked = True
                    await pg.wait_for_timeout(6000)
                    break
            except Exception as e:
                log('demo try', kw, repr(e)[:80])
        await pg.screenshot(path=str(OUT / '04_after_demo.png'), full_page=True); log('shot 04 full', 'clicked=', clicked)

        await b.close()

try:
    asyncio.run(run())
except Exception:
    LOG.append(traceback.format_exc()); print(traceback.format_exc(), flush=True)
(OUT / 'log2.txt').write_text('\n'.join(LOG), encoding='utf-8')
