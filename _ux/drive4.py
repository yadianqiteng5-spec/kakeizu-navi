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
    # 「免責」を含むフレームを探す
    for fr in pg.frames:
        try:
            if await fr.get_by_text('免責', exact=False).count() > 0:
                return fr
        except Exception:
            pass
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
                await w.first.click(timeout=8000); log('woke'); await pg.wait_for_timeout(50000)
        except Exception: pass
        await pg.wait_for_timeout(4000)

        log('frames:', len(pg.frames))
        fr = await content_frame(pg)
        log('content frame url:', (fr.url or '')[:60])

        # 同意（フレーム内のラベルをクリック）
        try:
            el = fr.get_by_text('同意した上で利用します', exact=False)
            log('consent label count', await el.count())
            if await el.count() > 0:
                await el.first.click(timeout=8000)
                await pg.wait_for_timeout(6000)
                log('gated still?', await fr.get_by_text('チェックを入れると', exact=False).count())
        except Exception as e:
            log('consent err', repr(e)[:120])

        await pg.screenshot(path=str(OUT / '06_input_full.png'), full_page=True); log('shot 06')

        # 入力画面の主要テキスト確認（フレーム内）
        for t in ['質問に答えるだけ', 'まとめてテキスト入力', '画像アップロード', '音声入力', '典型事例', 'Step 1', 'AIで解析']:
            try: log('has', t, await fr.get_by_text(t, exact=False).count())
            except Exception: log('has', t, 'ERR')
        await b.close()

try:
    asyncio.run(run())
except Exception:
    LOG.append(traceback.format_exc()); print(traceback.format_exc(), flush=True)
(OUT / 'log4.txt').write_text('\n'.join(LOG), encoding='utf-8')
