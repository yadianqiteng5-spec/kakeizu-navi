# -*- coding: utf-8 -*-
import asyncio, traceback
from pathlib import Path
from playwright.async_api import async_playwright

URL = 'https://kakeizu-navi-3joa5l78sjkams2axwbxix.streamlit.app/'
OUT = Path(__file__).parent
LOG = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    LOG.append(s)
    print(s, flush=True)


async def shot(pg, name):
    await pg.screenshot(path=str(OUT / name))
    log('SHOT', name)


async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 1280, 'height': 1000})
        await pg.goto(URL, wait_until='domcontentloaded', timeout=90000)
        await pg.wait_for_timeout(8000)

        # スリープ復帰
        try:
            wake = pg.get_by_text('get this app back up', exact=False)
            if await wake.count() > 0:
                await wake.first.click(timeout=8000)
                log('WOKE app, waiting 50s')
                await pg.wait_for_timeout(50000)
        except Exception as e:
            log('wake check:', repr(e)[:120])

        await pg.wait_for_timeout(5000)
        await shot(pg, '01_landing.png')
        body = await pg.inner_text('body')
        log('BODY_LEN', len(body))
        log('--- TOP TEXT ---')
        log(body[:700])

        await b.close()


try:
    asyncio.run(run())
except Exception:
    LOG.append(traceback.format_exc())
    print(traceback.format_exc(), flush=True)

(OUT / 'log.txt').write_text('\n'.join(LOG), encoding='utf-8')
