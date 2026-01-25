import asyncio
from playwright.async_api import async_playwright

async def download_tpex_csv(download_url, out_path):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        # 監聽下載事件
        async with page.expect_download() as download_info:
            await page.goto(download_url)
        download = await download_info.value
        await download.save_as(out_path)
        print(f"Downloaded to {out_path}")
        await browser.close()

if __name__ == "__main__":
    url = "https://www.tpex.org.tw/storage/bond_zone/tradeinfo/cb/2026/202601/RSta0113.20260123-C.csv"
    out_path = "data/raw/daily_samples/test_quote_playwright.csv"
    asyncio.run(download_tpex_csv(url, out_path))