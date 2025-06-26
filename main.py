import asyncio
import os
from dotenv import load_dotenv
import ssl
from imap_tools import MailBox, AND
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

load_dotenv("config.env")

GELESEN_FOLDER = "Gelesen"
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))

SSL_CONTEXT = ssl.create_default_context()

def get_confirmation_link():
    print(f"📡 Connecting to {IMAP_SERVER}:{IMAP_PORT} as {EMAIL}")
    with MailBox(IMAP_SERVER, port=IMAP_PORT, ssl_context=SSL_CONTEXT).login(EMAIL, PASSWORD) as mailbox:
        print(f"I'm in the mailbox")
        for msg in mailbox.fetch(reverse=True):
            html = msg.html or msg.text
            if "update-primary-location" in html:
                start = html.find("https://www.netflix.com/account/update-primary-location")
                end = html.find('"', start)  # assumes the link ends with a quote
                url = html[start:end]
                print(f"✅ Found Netflix link!")

                # ✅ Move the email after processing
                mailbox.move(msg.uid, GELESEN_FOLDER)
                print("📦 Email moved to Gelesen folder")
                return url
    return None

async def click_confirmation_link2(url):
    print(f"🌍 Opening link: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_selector('[data-uia="set-primary-location-action"]', timeout=5000)
        await page.click('[data-uia="set-primary-location-action"]')
        await browser.close()
        print("✅ Button clicked: Aktualisierung bestätigen")

async def click_confirmation_link(url):
    print(f"🌍 Besuche Link: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(3000)  # Optional: kurze Pause
        await browser.close()
        print("✅ Bestätigt.")

async def main():
    link = get_confirmation_link()
    if link:
        await click_confirmation_link2(link)
    else:
        print("❌ Kein passender Link gefunden.")

asyncio.run(main())
