import asyncio
import os
import shutil
import glob
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/config/.gemini/antigravity/brain/9578031e-2f97-4478-ac4d-d021f0a71e03"
RECORDINGS_DIR = os.path.join(ARTIFACT_DIR, "recordings")

async def record_demo():
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=RECORDINGS_DIR,
            record_video_size={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        
        # Navigate to deployed Cloud Run frontend
        print("Navigating to app URL...")
        await page.goto("https://smart-weather-frontend-24012010193.us-central1.run.app", wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        # Prompt 1: Show main feature (live weather & AQI lookup)
        print("Executing Prompt 1...")
        chip = page.locator(".chip-button").first
        if await chip.is_visible():
            await chip.click()
        else:
            await page.fill("#input", "🌤️ Live weather and AQI for Tokyo")
            await page.click("button[type='submit']")
            
        print("Waiting for Prompt 1 response...")
        # Wait up to 30 seconds for reply
        try:
            await page.wait_for_selector(".msg-row.agent", timeout=30000)
            await page.wait_for_timeout(8000)
        except Exception as e:
            print(f"Timeout waiting for Prompt 1: {e}")
            
        # Prompt 2: Richer prompt showing tool calls, image generation, and database save
        print("Executing Prompt 2...")
        rich_prompt = "Generate a stylish raincoat outfit image for Tokyo and save Tokyo as my favorite city."
        await page.fill("#input", rich_prompt)
        await page.click("button[type='submit']")
        
        print("Waiting for Prompt 2 response...")
        try:
            # Wait extra time for tool execution & image generation
            await page.wait_for_timeout(25000)
        except Exception as e:
            print(f"Timeout waiting for Prompt 2: {e}")

        # Final pause before closing
        await page.wait_for_timeout(3000)
        await context.close()
        await browser.close()
        
    # Find recorded video
    videos = glob.glob(os.path.join(RECORDINGS_DIR, "*.webm"))
    if videos:
        latest_video = max(videos, key=os.path.getmtime)
        target_path = os.path.join(ARTIFACT_DIR, "demo_recording.webm")
        shutil.copy(latest_video, target_path)
        print(f"Demo video saved to: {target_path}")

if __name__ == "__main__":
    asyncio.run(record_demo())
