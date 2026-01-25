import os
import logging
import asyncio
import schedule
import time
from datetime import datetime, timedelta
from telegram import Bot
from telegram.error import NetworkError, TimedOut
from telegram.request import HTTPXRequest
from dotenv import load_dotenv
import pytz
from sheets_manager import SheetsManager

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Scheduler for sending reminders"""

    def __init__(self):
        self.user_id = os.getenv('TELEGRAM_USER_ID')
        self.timezone = pytz.timezone(os.getenv('TIMEZONE', 'Europe/Moscow'))
        self._apply_timezone()
        self.morning_time = os.getenv('MORNING_REMINDER_TIME', '09:00')
        self.evening_time = os.getenv('EVENING_REMINDER_TIME', '21:00')
        self.sheets_manager = SheetsManager(
            credentials_file='credentials.json',
            spreadsheet_id=os.getenv('GOOGLE_SHEET_ID')
        )

        # Calculate reminder times (main + 30 min + 60 min)
        self.morning_reminder_times = self._calculate_reminder_times(self.morning_time)
        self.evening_reminder_times = self._calculate_reminder_times(self.evening_time)

    def _build_bot(self) -> Bot:
        """Create bot with a slightly larger connection pool to avoid pool exhaustion."""
        request = HTTPXRequest(
            connection_pool_size=5,
            read_timeout=10.0,
            write_timeout=10.0,
            connect_timeout=10.0,
            pool_timeout=10.0,
        )
        return Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'), request=request)

    async def _send_message_with_retry(self, text: str, current_time: str, label: str) -> None:
        """
        Send a message with a fresh bot client; retry once on pool/loop issues.
        """
        for attempt in (1, 2):
            bot = self._build_bot()
            try:
                await bot.send_message(chat_id=self.user_id, text=text)
                logger.info(f'{label} sent successfully{" on retry" if attempt == 2 else ""} at {current_time}')
                return
            except (TimedOut, NetworkError) as e:
                # Close and retry once with a new client
                logger.warning(f'{label} send failed (attempt {attempt}) with network/timeout: {e}')
                try:
                    await bot.shutdown()
                except Exception:
                    pass
                if attempt == 2:
                    raise
            except Exception:
                # Unknown error, rethrow
                try:
                    await bot.shutdown()
                except Exception:
                    pass
                raise
            else:
                try:
                    await bot.shutdown()
                except Exception:
                    pass
    def _apply_timezone(self) -> None:
        """Apply TZ for schedule library which uses local time."""
        tz_name = os.getenv('TIMEZONE', 'Europe/Moscow')
        os.environ['TZ'] = tz_name
        try:
            time.tzset()
            logger.info(f'Applied timezone for scheduler: {tz_name}')
        except AttributeError:
            logger.info('time.tzset is not available; using system timezone')

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
            now = datetime.now(self.timezone)
            today = now.strftime('%d.%m.%Y')
            current_time = now.strftime('%H:%M:%S')

            logger.info(f'Morning reminder triggered at {current_time} (timezone: {self.timezone})')
            has_measurement = self.sheets_manager.has_morning_measurement(today)

            if not has_measurement:
                await self._send_message_with_retry(
                    text='🌅 Доброе утро!\n\nПора измерить давление.\nИспользуйте команду /morning',
                    current_time=current_time,
                    label='Morning reminder'
                )
            else:
                logger.info(f'Morning measurement for {today} already exists, skipping reminder')
        except Exception as e:
            logger.error(f'Error sending morning reminder: {e}', exc_info=True)

    async def send_evening_reminder(self):
        """Send evening reminder"""
        try:
            # Check if today's evening measurement exists
            now = datetime.now(self.timezone)
            today = now.strftime('%d.%m.%Y')
            current_time = now.strftime('%H:%M:%S')

            logger.info(f'Evening reminder triggered at {current_time} (timezone: {self.timezone})')
            has_measurement = self.sheets_manager.has_evening_measurement(today)

            if not has_measurement:
                await self._send_message_with_retry(
                    text='🌙 Добрый вечер!\n\nПора измерить давление.\nИспользуйте команду /evening',
                    current_time=current_time,
                    label='Evening reminder'
                )
            else:
                logger.info(f'Evening measurement for {today} already exists, skipping reminder')
        except Exception as e:
            logger.error(f'Error sending evening reminder: {e}', exc_info=True)

    def morning_job(self):
        """Wrapper for morning reminder to run in asyncio"""
        asyncio.run(self.send_morning_reminder())

    def evening_job(self):
        """Wrapper for evening reminder to run in asyncio"""
        asyncio.run(self.send_evening_reminder())

    def start(self):
        """Start the scheduler"""
        logger.info(f'Starting scheduler with timezone: {self.timezone}')
        logger.info(f'Morning reminders at {self.morning_reminder_times}')
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
        logger.info('Scheduler started. Checking every 10 seconds...')
        while True:
            schedule.run_pending()
            time.sleep(10)  # Check every 10 seconds for better precision


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    scheduler = ReminderScheduler()
    scheduler.start()
