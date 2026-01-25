import asyncio
import pandas as pd
from playwright.async_api import async_playwright

async def fetch_tpex_cb_master():
    url = "https://www.tpex.org.tw/zh-tw/bond/issue/cbond/listed.html"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_selector("table")
        rows = await page.query_selector_all("table tr")
        data = []
        for row in rows[1:]:
            cols = await row.query_selector_all("td")
            # 列印所有欄位內容，供人工判斷
            col_texts = [await c.inner_text() for c in cols]
            print(col_texts)
            # 暫不寫入資料
        await browser.close()

if __name__ == "__main__":
    asyncio.run(fetch_tpex_cb_master())