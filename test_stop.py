import asyncio
from playwright.async_api import async_playwright
import os
import time
import subprocess

async def verify_stop_button():
    # Start Streamlit in background
    process = subprocess.Popen(["python", "hotel_reservation_app.py"], env={**os.environ, "STREAMLIT_SERVER_PORT": "8505"})
    time.sleep(12) # Wait for it to start

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto("http://localhost:8505")

            # 1. Fill URL and Start
            await page.fill("input[placeholder='https://example.com/reserve']", "http://localhost:8000")

            # Set start time to 1 minute from now to enter "Waiting" state
            # Find the time input. It's usually the second time_input if there are multiple,
            # but let's just find the button and click it.
            # The current time in the app is 00:00 by default (datetime.time(0, 0)).
            # If we just click "Start", it will likely start immediately or wait if the date is today.

            await page.click("text=🚀 上記の内容で実行予約（待機開始）")
            await asyncio.sleep(3)

            # Check if Stop button is visible
            stop_btn = await page.query_selector("text=🛑 実行を強制中断（ブラウザを閉じる）")
            if stop_btn:
                print("Stop button is visible during execution.")
                await stop_btn.click()
                print("Stop button clicked.")
                await asyncio.sleep(3)

                # Check if it returned to "Start" state
                start_btn = await page.query_selector("text=🚀 上記の内容で実行予約（待機開始）")
                if start_btn:
                    print("Successfully returned to Start state after Stop.")
                else:
                    print("Failed to return to Start state.")
            else:
                print("Stop button not found.")

            await page.screenshot(path="/home/jules/verification/stop_button_check.png")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            process.terminate()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_stop_button())
