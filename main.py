import asyncio
import os
from dotenv import load_dotenv
import ssl
from imap_tools import MailBox
from playwright.async_api import async_playwright
import time
import logging
from datetime import datetime

load_dotenv("config.env")

GELESEN_FOLDER = "Gelesen"
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
CHECK_INTERVAL = 10  # seconds
MINUTES_TO_WAIT = 900 # 900 seconds = 15 minutes
LOG_PATH = os.getenv("LOG_PATH", "netflix-validator.log")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)

SSL_CONTEXT = ssl.create_default_context()

def log_email_moved(msg, reason, success=True):
    """Log details about an email being moved to gelesen folder"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subject = msg.subject or "No Subject"
        sender = msg.from_ or "Unknown Sender"
        date_received = msg.date.strftime("%Y-%m-%d %H:%M:%S") if msg.date else "Unknown Date"
        
        log_message = (
            f"📧 EMAIL MOVED TO GELESEN | "
            f"Timestamp: {timestamp} | "
            f"Subject: {subject} | "
            f"Sender: {sender} | "
            f"Date Received: {date_received} | "
            f"Reason: {reason} | "
            f"Status: {'SUCCESS' if success else 'FAILED'}"
        )
        
        logger.info(log_message)
        print(log_message)
        
    except Exception as e:
        logger.error(f"Error logging email details: {e}")

async def click_confirmation_link(url):
    logger.info(f"🌍 Opening link: {url}")
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
            logger.info("✅ Confirmation link clicked successfully!")
        else:
            logger.warning(f"⚠️ Loading error. Status: {response.status if response else 'No response'}")
            return False
        return True

async def check_emails(mailbox):
    """Check emails using existing mailbox connection"""
    try:
        logger.info(f"📧 Checking for new emails...")
        current_time = datetime.now()
        
        for msg in mailbox.fetch(reverse=True):
            html = msg.html or msg.text
            
            # Check if email is older than 15 minutes AND has been read
            if msg.date:
                time_diff = current_time - msg.date
                if time_diff.total_seconds() > MINUTES_TO_WAIT and msg.flags and '\\Seen' in msg.flags:
                    mailbox.move(msg.uid, GELESEN_FOLDER)
                    logger.info(f"📦 Email '{msg.subject}' moved to Gelesen (older than 15 minutes AND read)")
                    log_email_moved(msg, "Email older than 15 minutes AND read")
                    continue  # Skip further processing for this email
            
            if "update-primary-location" in html:
                start = html.find("https://www.netflix.com/account/update-primary-location")
                end = html.find('"', start)
                url = html[start:end]
                logger.info(f"✅ Found Netflix link!")

                confirmation_successful = await click_confirmation_link(url)
                
                if confirmation_successful:
                    mailbox.move(msg.uid, GELESEN_FOLDER)
                    logger.info("📦 Email moved to Gelesen folder")
                    log_email_moved(msg, "Netflix update link clicked")
                else:
                    logger.warning("❌ Failed to click confirmation link, email not moved")
                    log_email_moved(msg, "Failed to click Netflix update link", success=False)
    except Exception as e:
        logger.error(f"❌ Error checking emails: {e}")
        # Re-raise to trigger reconnection
        raise

async def main():
    logger.info(f"🔄 Starting Netflix Autovalidator - checking every {CHECK_INTERVAL} seconds")
    logger.info(f"📡 Connecting to {IMAP_SERVER}:{IMAP_PORT} as {EMAIL}")
    logger.info(f"📝 Logging to: {LOG_PATH}")
    
    while True:
        try:
            # Establish connection once
            with MailBox(IMAP_SERVER, port=IMAP_PORT, ssl_context=SSL_CONTEXT).login(EMAIL, PASSWORD) as mailbox:
                logger.info(f"✅ Connected to mailbox successfully")
                
                # Keep connection alive and check emails periodically
                while True:
                    try:
                        await check_emails(mailbox)
                        logger.debug(f"💤 Waiting {CHECK_INTERVAL} seconds before next check...")
                        await asyncio.sleep(CHECK_INTERVAL)
                    except Exception as e:
                        logger.error(f"❌ Connection error: {e}")
                        logger.info("🔄 Reconnecting...")
                        break  # Break inner loop to reconnect
                        
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            logger.info(f"🔄 Retrying in {CHECK_INTERVAL} seconds...")
            await asyncio.sleep(CHECK_INTERVAL)

asyncio.run(main())