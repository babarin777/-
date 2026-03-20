import asyncio
from playwright.async_api import async_playwright
import os
import time

async def verify_v6_ui():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Start Streamlit in background
        import subprocess
        process = subprocess.Popen(["python", "hotel_reservation_app.py"], env={**os.environ, "STREAMLIT_SERVER_PORT": "8503"})
        time.sleep(10)

        try:
            await page.goto("http://localhost:8503")
            await page.wait_for_selector("h3", text="⚠ 予約内容の確認", timeout=20000)

            # Fill something to see reflection
            # Find the number input for "3. 利用人数"
            # It's an input with type number
            inputs = await page.query_selector_all("input[type='number']")
            if inputs:
                await inputs[0].fill("5")
                await inputs[0].press("Enter")
                await asyncio.sleep(2) # wait for reflection

            await page.screenshot(path="/home/jules/verification/v6_ui_final.png")
            print("Screenshot saved to /home/jules/verification/v6_ui_final.png")

        except Exception as e:
            print(f"Error during verification: {e}")
        finally:
            process.terminate()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_v6_ui())
