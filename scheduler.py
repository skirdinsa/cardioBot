"""
Reminder scheduler for CardioBot.
Checks user settings every minute and sends reminders accordingly.
"""
import os
import logging
import asyncio
import time
from datetime import datetime, timedelta
from telegram import Bot
from telegram.error import NetworkError, TimedOut
from telegram.request import HTTPXRequest
from dotenv import load_dotenv
import pytz
from sheets_manager import SheetsManager
from user_settings import (
    get_all_users_with_settings,
    is_notification_enabled,
    get_notification_time,
    get_user_settings,
)

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """
    Dynamic scheduler for sending reminders.
    Checks user settings every minute and sends reminders at configured times.
    Supports per-user settings including enabled/disabled status and custom times.
    """

    def __init__(self):
        self.default_user_id = os.getenv('TELEGRAM_USER_ID')
        self.sheets_manager = SheetsManager(
            credentials_file='credentials.json',
            spreadsheet_id=os.getenv('GOOGLE_SHEET_ID')
        )
        # Track sent reminders to avoid duplicates: {user_id: {period: [times_sent_today]}}
        self.sent_reminders = {}
        self.last_cleanup_date = None

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

    async def _send_message_with_retry(self, user_id: str, text: str, current_time: str, label: str) -> None:
        """
        Send a message with a fresh bot client; retry once on pool/loop issues.
        """
        for attempt in (1, 2):
            bot = self._build_bot()
            try:
                await bot.send_message(chat_id=user_id, text=text)
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

    def _get_user_timezone(self, user_id: str) -> pytz.timezone:
        """Get timezone for a specific user."""
        settings = get_user_settings(user_id)
        tz_name = settings.get('timezone', os.getenv('TIMEZONE', 'Europe/Moscow'))
        try:
            return pytz.timezone(tz_name)
        except pytz.exceptions.UnknownTimeZoneError:
            return pytz.timezone('Europe/Moscow')

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

    def _cleanup_sent_reminders(self):
        """Clean up sent reminders tracking at midnight."""
        today = datetime.now().date()
        if self.last_cleanup_date != today:
            self.sent_reminders = {}
            self.last_cleanup_date = today
            logger.info('Cleaned up sent reminders tracking for new day')

    def _mark_reminder_sent(self, user_id: str, period: str, time_str: str):
        """Mark a reminder as sent for today."""
        if user_id not in self.sent_reminders:
            self.sent_reminders[user_id] = {'morning': [], 'evening': []}
        if period not in self.sent_reminders[user_id]:
            self.sent_reminders[user_id][period] = []
        self.sent_reminders[user_id][period].append(time_str)

    def _was_reminder_sent(self, user_id: str, period: str, time_str: str) -> bool:
        """Check if a reminder was already sent."""
        if user_id not in self.sent_reminders:
            return False
        if period not in self.sent_reminders[user_id]:
            return False
        return time_str in self.sent_reminders[user_id][period]

    async def send_reminder(self, user_id: str, period: str):
        """
        Send a reminder to a specific user.

        Args:
            user_id: Telegram user ID
            period: 'morning' or 'evening'
        """
        try:
            tz = self._get_user_timezone(user_id)
            now = datetime.now(tz)
            today = now.strftime('%d.%m.%Y')
            current_time = now.strftime('%H:%M:%S')

            logger.info(f'{period.capitalize()} reminder check for user {user_id} at {current_time} (tz: {tz})')

            # Check if measurement already exists
            if period == 'morning':
                has_measurement = self.sheets_manager.has_morning_measurement(today)
                message = '🌅 Доброе утро!\n\nПора измерить давление.\nИспользуйте команду /morning'
                label = 'Morning reminder'
            else:
                has_measurement = self.sheets_manager.has_evening_measurement(today)
                message = '🌙 Добрый вечер!\n\nПора измерить давление.\nИспользуйте команду /evening'
                label = 'Evening reminder'

            if not has_measurement:
                await self._send_message_with_retry(
                    user_id=user_id,
                    text=message,
                    current_time=current_time,
                    label=label
                )
            else:
                logger.info(f'{period.capitalize()} measurement for {today} already exists, skipping')

        except Exception as e:
            logger.error(f'Error sending {period} reminder to user {user_id}: {e}', exc_info=True)

    async def check_and_send_reminders(self):
        """Check all users and send reminders if it's time."""
        self._cleanup_sent_reminders()

        # Get all users with their settings
        users = get_all_users_with_settings()

        # If no users configured, use default from env
        if not users and self.default_user_id:
            users = {self.default_user_id: get_user_settings(self.default_user_id)}

        for user_id, settings in users.items():
            tz = self._get_user_timezone(user_id)
            now = datetime.now(tz)
            current_time = now.strftime('%H:%M')

            # Check morning reminders
            if is_notification_enabled(user_id, 'morning'):
                morning_base = get_notification_time(user_id, 'morning')
                morning_times = self._calculate_reminder_times(morning_base)

                for reminder_time in morning_times:
                    if current_time == reminder_time:
                        if not self._was_reminder_sent(user_id, 'morning', reminder_time):
                            await self.send_reminder(user_id, 'morning')
                            self._mark_reminder_sent(user_id, 'morning', reminder_time)

            # Check evening reminders
            if is_notification_enabled(user_id, 'evening'):
                evening_base = get_notification_time(user_id, 'evening')
                evening_times = self._calculate_reminder_times(evening_base)

                for reminder_time in evening_times:
                    if current_time == reminder_time:
                        if not self._was_reminder_sent(user_id, 'evening', reminder_time):
                            await self.send_reminder(user_id, 'evening')
                            self._mark_reminder_sent(user_id, 'evening', reminder_time)

    def check_job(self):
        """Wrapper to run check in asyncio."""
        asyncio.run(self.check_and_send_reminders())

    def start(self):
        """Start the scheduler."""
        logger.info('Starting dynamic reminder scheduler')
        logger.info(f'Default user ID: {self.default_user_id}')

        # Log initial settings
        users = get_all_users_with_settings()
        if users:
            for user_id, settings in users.items():
                logger.info(
                    f'User {user_id}: '
                    f'morning={settings["notifications"]["morning_enabled"]} at {settings["notifications"]["morning_time"]}, '
                    f'evening={settings["notifications"]["evening_enabled"]} at {settings["notifications"]["evening_time"]}, '
                    f'tz={settings["timezone"]}'
                )
        else:
            logger.info('No users with custom settings, using defaults')

        logger.info('Scheduler started. Checking every minute...')

        # Run check every minute
        while True:
            try:
                self.check_job()
            except Exception as e:
                logger.error(f'Error in scheduler check: {e}', exc_info=True)

            # Sleep until the next minute
            now = datetime.now()
            seconds_until_next_minute = 60 - now.second
            time.sleep(seconds_until_next_minute)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    scheduler = ReminderScheduler()
    scheduler.start()
