# -*- coding: utf-8 -*-
import asyncio, traceback
from pathlib import Path
from playwright.async_api import async_playwright

URL = 'https://kakeizu-navi-3joa5l78sjkams2axwbxix.streamlit.app/'
OUT = Path(__file__).parent
LOG = []
def log(*a):
    LOG.append(' '.join(str(x) for x in a)); print(*a, flush=True)

async def has(pg, text):
    try:
        return await pg.get_by_text(text, exact=False).count() > 0
    except Exception:
        return False

async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 1280, 'height': 1100})
        await pg.goto(URL, wait_until='domcontentloaded', timeout=90000)
        await pg.wait_for_timeout(9000)
        try:
            w = pg.get_by_text('get this app back up', exact=False)
            if await w.count() > 0:
                await w.first.click(timeout=8000); log('woke'); await pg.wait_for_timeout(50000)
        except Exception: pass
        await pg.wait_for_timeout(4000)

        # 同意ラベルをクリック（複数手段）
        consent_ok = False
        for attempt in ['label', 'baseweb', 'role']:
            try:
                if attempt == 'label':
                    el = pg.get_by_text('同意した上で利用します', exact=False)
                elif attempt == 'baseweb':
                    el = pg.locator('[data-testid="stCheckbox"]')
                else:
                    el = pg.get_by_role('checkbox')
                if await el.count() > 0:
                    await el.first.click(timeout=6000, force=(attempt!='label'))
                    await pg.wait_for_timeout(5000)
                    if not await has(pg, 'チェックを入れると'):
                        consent_ok = True; log('consent OK via', attempt); break
                    else:
                        log('still gated after', attempt)
            except Exception as e:
                log('consent', attempt, repr(e)[:80])
        log('consent_ok', consent_ok)
        await pg.wait_for_timeout(3000)
        await pg.screenshot(path=str(OUT / '05_input.png'), full_page=True); log('shot 05 full')

        # 入力画面のテキストを確認
        for t in ['質問に答えるだけ', 'まとめてテキスト入力', '典型事例', 'Step 1', '家族構成を入力']:
            log('has', t, await has(pg, t))

        await b.close()

try:
    asyncio.run(run())
except Exception:
    LOG.append(traceback.format_exc()); print(traceback.format_exc(), flush=True)
(OUT / 'log3.txt').write_text('\n'.join(LOG), encoding='utf-8')
