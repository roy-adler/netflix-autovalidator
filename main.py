import asyncio
import os
from dotenv import load_dotenv
import ssl
from imap_tools import MailBox
from playwright.async_api import async_playwright
import time

load_dotenv("config.env")

GELESEN_FOLDER = "Gelesen"
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
CHECK_INTERVAL = 10  # seconds

SSL_CONTEXT = ssl.create_default_context()

async def click_confirmation_link(url):
    print(f"🌍 Opening link: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_selector('[data-uia="set-primary-location-action"]', timeout=5000)
        await page.click('[data-uia="set-primary-location-action"]')
        # Wait for a confirmation message or page change to verify success
        response = await page.goto(url)
        await browser.close()
        if response and response.status == 200:
            print("✅ Confirmation link clicked successfully!")
        else:
            print(f"⚠️ Loading error. Status: {response.status if response else 'No response'}")
            return False
        return True

async def check_emails():
    print(f"📡 Connecting to {IMAP_SERVER}:{IMAP_PORT} as {EMAIL}")
    with MailBox(IMAP_SERVER, port=IMAP_PORT, ssl_context=SSL_CONTEXT).login(EMAIL, PASSWORD) as mailbox:
        print(f"I'm in the mailbox")
        for msg in mailbox.fetch(reverse=True):
            html = msg.html or msg.text
            if "update-primary-location" in html:
                start = html.find("https://www.netflix.com/account/update-primary-location")
                end = html.find('"', start)
                url = html[start:end]
                print(f"✅ Found Netflix link!")

                confirmation_successful = await click_confirmation_link(url)
                
                if confirmation_successful:
                    mailbox.move(msg.uid, GELESEN_FOLDER)
                    print("📦 Email moved to Gelesen folder")
                else:
                    print("❌ Failed to click confirmation link, email not moved")
            elif msg.from_ and "netflix" in msg.from_.lower():
                 mailbox.move(msg.uid, GELESEN_FOLDER)
                 print(f"📦 Email with subject {msg.subject} moved to Gelesen folder")

async def main():
    print(f"🔄 Starting Netflix Autovalidator - checking every {CHECK_INTERVAL} seconds")
    while True:
        try:
            await check_emails()
        except Exception as e:
            print(f"❌ Error occurred: {e}")
        print(f"💤 Waiting {CHECK_INTERVAL} seconds before next check...")
        await asyncio.sleep(CHECK_INTERVAL)

asyncio.run(main())