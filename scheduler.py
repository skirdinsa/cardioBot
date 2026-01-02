import os
import logging
import asyncio
import schedule
import time
from datetime import datetime, timedelta
from telegram import Bot
from dotenv import load_dotenv
import pytz
from sheets_manager import SheetsManager

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
        self.sheets_manager = SheetsManager(
            credentials_file='credentials.json',
            spreadsheet_id=os.getenv('GOOGLE_SHEET_ID')
        )

        # Calculate reminder times (main + 30 min + 60 min)
        self.morning_reminder_times = self._calculate_reminder_times(self.morning_time)
        self.evening_reminder_times = self._calculate_reminder_times(self.evening_time)

    def _calculate_reminder_times(self, base_time: str) -> list:
        """
        Calculate three reminder times: base, +30 min, +60 min

        Args:
            base_time: Time in HH:MM format

        Returns:
            List of time strings in HH:MM format
        """
        hour, minute = map(int, base_time.split(':'))
        base_dt = datetime(2000, 1, 1, hour, minute)

        times = [
            base_dt.strftime('%H:%M'),
            (base_dt + timedelta(minutes=30)).strftime('%H:%M'),
            (base_dt + timedelta(minutes=60)).strftime('%H:%M')
        ]
        return times

    async def send_morning_reminder(self):
        """Send morning reminder"""
        try:
            # Check if today's morning measurement exists
            today = datetime.now(self.timezone).strftime('%d.%m.%Y')
            has_measurement = self.sheets_manager.has_morning_measurement(today)

            if not has_measurement:
                await self.bot.send_message(
                    chat_id=self.user_id,
                    text='🌅 Доброе утро!\n\nПора измерить давление.\nИспользуйте команду /morning'
                )
                logger.info('Morning reminder sent')
            else:
                logger.info('Morning measurement already exists, skipping reminder')
        except Exception as e:
            logger.error(f'Error sending morning reminder: {e}')

    async def send_evening_reminder(self):
        """Send evening reminder"""
        try:
            # Check if today's evening measurement exists
            today = datetime.now(self.timezone).strftime('%d.%m.%Y')
            has_measurement = self.sheets_manager.has_evening_measurement(today)

            if not has_measurement:
                await self.bot.send_message(
                    chat_id=self.user_id,
                    text='🌙 Добрый вечер!\n\nПора измерить давление.\nИспользуйте команду /evening'
                )
                logger.info('Evening reminder sent')
            else:
                logger.info('Evening measurement already exists, skipping reminder')
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
        logger.info(f'Starting scheduler with morning reminders at {self.morning_reminder_times}')
        logger.info(f'Evening reminders at {self.evening_reminder_times}')

        # Schedule morning reminders (3 times: 0, +30 min, +60 min)
        for reminder_time in self.morning_reminder_times:
            schedule.every().day.at(reminder_time).do(self.morning_job)
            logger.info(f'Scheduled morning reminder at {reminder_time}')

        # Schedule evening reminders (3 times: 0, +30 min, +60 min)
        for reminder_time in self.evening_reminder_times:
            schedule.every().day.at(reminder_time).do(self.evening_job)
            logger.info(f'Scheduled evening reminder at {reminder_time}')

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
