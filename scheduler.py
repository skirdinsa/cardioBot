import os
import logging
import asyncio
import schedule
import time
from datetime import datetime
from telegram import Bot
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Scheduler for sending reminders"""

    def __init__(self):
        self.bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
        self.user_id = os.getenv('TELEGRAM_USER_ID')
        self.timezone = pytz.timezone(os.getenv('TIMEZONE', 'Europe/Moscow'))
        self.morning_time = os.getenv('MORNING_REMINDER_TIME', '09:00')
        self.evening_time = os.getenv('EVENING_REMINDER_TIME', '21:00')

    async def send_morning_reminder(self):
        """Send morning reminder"""
        try:
            await self.bot.send_message(
                chat_id=self.user_id,
                text='🌅 Доброе утро!\n\nПора измерить давление.\nИспользуйте команду /morning'
            )
            logger.info('Morning reminder sent')
        except Exception as e:
            logger.error(f'Error sending morning reminder: {e}')

    async def send_evening_reminder(self):
        """Send evening reminder"""
        try:
            await self.bot.send_message(
                chat_id=self.user_id,
                text='🌙 Добрый вечер!\n\nПора измерить давление.\nИспользуйте команду /evening'
            )
            logger.info('Evening reminder sent')
        except Exception as e:
            logger.error(f'Error sending evening reminder: {e}')

    def morning_job(self):
        """Wrapper for morning reminder to run in asyncio"""
        asyncio.run(self.send_morning_reminder())

    def evening_job(self):
        """Wrapper for evening reminder to run in asyncio"""
        asyncio.run(self.send_evening_reminder())

    def start(self):
        """Start the scheduler"""
        logger.info(f'Starting scheduler with morning reminder at {self.morning_time} and evening reminder at {self.evening_time}')

        # Schedule reminders
        schedule.every().day.at(self.morning_time).do(self.morning_job)
        schedule.every().day.at(self.evening_time).do(self.evening_job)

        # Run the scheduler
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    scheduler = ReminderScheduler()
    scheduler.start()
