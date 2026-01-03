import os
import logging
from datetime import datetime
import pytz
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
    PicklePersistence,
)
from dotenv import load_dotenv
from sheets_manager import SheetsManager

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_version() -> str:
    """Load bot version from version file."""
    try:
        with open('version', 'r', encoding='utf-8') as version_file:
            return version_file.read().strip()
    except OSError:
        return '0.1.0'


VERSION = load_version()


def get_current_date(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Get current date based on user or env timezone."""
    tz_name = context.user_data.get('timezone', os.getenv('TIMEZONE', 'Europe/Moscow'))
    try:
        tz = pytz.timezone(tz_name)
    except pytz.exceptions.UnknownTimeZoneError:
        tz = pytz.timezone(os.getenv('TIMEZONE', 'Europe/Moscow'))
    return datetime.now(tz).strftime('%d.%m.%Y')

# Conversation states
(MORNING_LEFT_UPPER, MORNING_LEFT_LOWER, MORNING_LEFT_PULSE,
 MORNING_RIGHT_UPPER, MORNING_RIGHT_LOWER, MORNING_RIGHT_PULSE,
 EVENING_LEFT_UPPER, EVENING_LEFT_LOWER, EVENING_LEFT_PULSE,
 EVENING_RIGHT_UPPER, EVENING_RIGHT_LOWER, EVENING_RIGHT_PULSE,
 SETTINGS_TIMEZONE) = range(13)

# Initialize Sheets Manager
sheets_manager = SheetsManager(
    credentials_file='credentials.json',
    spreadsheet_id=os.getenv('GOOGLE_SHEET_ID')
)


def analyze_blood_pressure(upper: int, lower: int) -> str:
    """
    Analyze blood pressure values and return feedback

    Args:
        upper: Upper (systolic) blood pressure
        lower: Lower (diastolic) blood pressure

    Returns:
        Feedback message with emoji
    """
    # Thresholds for blood pressure
    good_upper = int(os.getenv('GOOD_UPPER', 130))
    warning_upper = int(os.getenv('WARNING_UPPER', 140))
    good_lower = int(os.getenv('GOOD_LOWER', 70))
    warning_lower = int(os.getenv('WARNING_LOWER', 90))

    # Determine status for upper (systolic) pressure
    if upper <= good_upper:
        upper_status = "good"
        upper_emoji = "🟢"
    elif upper <= warning_upper:
        upper_status = "warning"
        upper_emoji = "🟡"
    else:
        upper_status = "bad"
        upper_emoji = "🔴"

    # Determine status for lower (diastolic) pressure
    if lower <= good_lower:
        lower_status = "good"
        lower_emoji = "🟢"
    elif lower <= warning_lower:
        lower_status = "warning"
        lower_emoji = "🟡"
    else:
        lower_status = "bad"
        lower_emoji = "🔴"

    # Generate feedback message
    if upper_status == "good" and lower_status == "good":
        return f"{upper_emoji}{lower_emoji} Отлично! Давление в норме."
    elif upper_status == "bad" or lower_status == "bad":
        message = f"{upper_emoji}{lower_emoji} ⚠️ Внимание! Повышенное давление."
        if upper_status == "bad" and lower_status == "bad":
            message += f" Оба показателя требуют внимания."
        elif upper_status == "bad":
            message += f" Верхнее давление слишком высокое (>{warning_upper})."
        else:
            message += f" Нижнее давление слишком высокое (>{warning_lower})."
        return message
    else:
        # At least one is in warning zone
        message = f"{upper_emoji}{lower_emoji} Давление умеренно повышено."
        details = []
        if upper_status == "warning":
            details.append(f"верхнее {upper}")
        if lower_status == "warning":
            details.append(f"нижнее {lower}")
        if details:
            message += f" ({', '.join(details)})"
        return message


class MeasurementData:
    """Temporary storage for measurement data during conversation"""
    def __init__(self):
        self.reset()

    def reset(self):
        self.date = None
        self.time_of_day = None  # 'morning' or 'evening'
        self.left_upper = None
        self.left_lower = None
        self.left_pulse = None
        self.right_upper = None
        self.right_lower = None
        self.right_pulse = None
        self.message_ids = []  # Store message IDs to delete later


# Global storage for current measurement
current_measurement = MeasurementData()


async def send_and_track(update: Update, text: str) -> None:
    """Send a message and track its ID for later deletion"""
    # Store user's message ID
    current_measurement.message_ids.append(update.message.message_id)

    # Send bot's message and store its ID
    msg = await update.message.reply_text(text)
    current_measurement.message_ids.append(msg.message_id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user

    # Get current timezone from environment or user data
    current_tz = context.user_data.get('timezone', os.getenv('TIMEZONE', 'Europe/Moscow'))

    await update.message.reply_text(
        f'Привет, {user.first_name}!\n\n'
        'Я буду напоминать вам измерять давление 2 раза в день.\n\n'
        'Команды:\n'
        '/morning - Утреннее измерение\n'
        '/evening - Вечернее измерение\n'
        '/settings - Настройки (таймзона, время напоминаний)\n'
        '/version - Версия бота\n'
        '/cancel - Отменить текущее измерение\n'
        '/help - Показать помощь\n\n'
        f'Текущая таймзона: {current_tz}'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        'Команды бота:\n\n'
        '/morning - Начать утреннее измерение давления\n'
        '/evening - Начать вечернее измерение давления\n'
        '/settings - Настройки (таймзона, время напоминаний)\n'
        '/version - Показать версию бота\n'
        '/cancel - Отменить текущее измерение\n'
        '/help - Показать эту справку\n\n'
        'Бот будет автоматически напоминать вам о необходимости измерения давления.'
    )


async def settings_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start settings configuration"""
    current_tz = context.user_data.get('timezone', os.getenv('TIMEZONE', 'Europe/Moscow'))

    await update.message.reply_text(
        f'⚙️ Настройки\n\n'
        f'Текущая таймзона: {current_tz}\n\n'
        'Введите новую таймзону (например: Europe/Moscow, Asia/Tokyo, America/New_York)\n'
        'Или отправьте /cancel для отмены'
    )
    return SETTINGS_TIMEZONE


async def version_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /version is issued."""
    await update.message.reply_text(f'Версия бота: {VERSION}')


async def settings_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save timezone setting"""
    timezone_str = update.message.text.strip()

    try:
        # Validate timezone
        pytz.timezone(timezone_str)

        # Save to user data
        context.user_data['timezone'] = timezone_str

        await update.message.reply_text(
            f'✅ Таймзона обновлена: {timezone_str}\n\n'
            'Примечание: для применения изменений в расписании напоминаний требуется перезапуск scheduler.'
        )
        return ConversationHandler.END
    except pytz.exceptions.UnknownTimeZoneError:
        await update.message.reply_text(
            f'❌ Неизвестная таймзона: {timezone_str}\n\n'
            'Примеры правильных таймзон:\n'
            '- Europe/Moscow\n'
            '- Asia/Tokyo\n'
            '- America/New_York\n'
            '- UTC\n\n'
            'Попробуйте снова или отправьте /cancel'
        )
        return SETTINGS_TIMEZONE


async def morning_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start morning blood pressure measurement"""
    current_measurement.reset()
    current_measurement.date = get_current_date(context)
    current_measurement.time_of_day = 'morning'

    # Store user's command message ID
    current_measurement.message_ids.append(update.message.message_id)

    msg = await update.message.reply_text(
        '🌅 Утреннее измерение\n\n'
        'ЛЕВАЯ рука\n'
        'Введите ВЕРХНЕЕ давление:'
    )
    current_measurement.message_ids.append(msg.message_id)
    return MORNING_LEFT_UPPER


async def morning_left_upper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store left upper pressure and ask for lower"""
    text = update.message.text

    try:
        value = int(text)
        current_measurement.left_upper = value
        await send_and_track(update, 'ЛЕВАЯ рука\nВведите НИЖНЕЕ давление:')
        return MORNING_LEFT_LOWER
    except ValueError:
        await send_and_track(update, 'Пожалуйста, введите число:')
        return MORNING_LEFT_UPPER


async def morning_left_lower(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store left lower pressure and ask for pulse"""
    text = update.message.text

    try:
        value = int(text)
        current_measurement.left_lower = value
        await send_and_track(update, 'ЛЕВАЯ рука\nВведите ПУЛЬС:')
        return MORNING_LEFT_PULSE
    except ValueError:
        await send_and_track(update, 'Пожалуйста, введите число:')
        return MORNING_LEFT_LOWER


async def morning_left_pulse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store left pulse and ask for right upper pressure"""
    text = update.message.text

    try:
        value = int(text)
        current_measurement.left_pulse = value
        await send_and_track(update, 'ПРАВАЯ рука\nВведите ВЕРХНЕЕ давление:')
        return MORNING_RIGHT_UPPER
    except ValueError:
        await send_and_track(update, 'Пожалуйста, введите число:')
        return MORNING_LEFT_PULSE


async def morning_right_upper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store right upper pressure and ask for lower"""
    text = update.message.text

    try:
        value = int(text)
        current_measurement.right_upper = value
        await send_and_track(update, 'ПРАВАЯ рука\nВведите НИЖНЕЕ давление:')
        return MORNING_RIGHT_LOWER
    except ValueError:
        await send_and_track(update, 'Пожалуйста, введите число:')
        return MORNING_RIGHT_UPPER


async def morning_right_lower(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store right lower pressure and ask for pulse"""
    text = update.message.text

    try:
        value = int(text)
        current_measurement.right_lower = value
        await send_and_track(update, 'ПРАВАЯ рука\nВведите ПУЛЬС:')
        return MORNING_RIGHT_PULSE
    except ValueError:
        await send_and_track(update, 'Пожалуйста, введите число:')
        return MORNING_RIGHT_LOWER


async def morning_right_pulse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store right pulse and save to Google Sheets"""
    text = update.message.text

    try:
        value = int(text)
        current_measurement.right_pulse = value

        # Add user's last message to deletion list
        current_measurement.message_ids.append(update.message.message_id)

        # Save to Google Sheets
        success = sheets_manager.add_morning_measurement(
            date=current_measurement.date,
            left_upper=current_measurement.left_upper,
            left_lower=current_measurement.left_lower,
            left_pulse=current_measurement.left_pulse,
            right_upper=current_measurement.right_upper,
            right_lower=current_measurement.right_lower,
            right_pulse=current_measurement.right_pulse
        )

        if success:
            # Analyze blood pressure for both arms
            left_analysis = analyze_blood_pressure(
                current_measurement.left_upper,
                current_measurement.left_lower
            )
            right_analysis = analyze_blood_pressure(
                current_measurement.right_upper,
                current_measurement.right_lower
            )

            # Get Google Sheets link
            sheet_url = f"https://docs.google.com/spreadsheets/d/{os.getenv('GOOGLE_SHEET_ID')}"

            result_msg = await update.message.reply_text(
                '✅ Утреннее измерение сохранено!\n\n'
                f'Дата: {current_measurement.date}\n\n'
                f'📍 Левая рука: {current_measurement.left_upper}/{current_measurement.left_lower}, пульс {current_measurement.left_pulse}\n'
                f'{left_analysis}\n\n'
                f'📍 Правая рука: {current_measurement.right_upper}/{current_measurement.right_lower}, пульс {current_measurement.right_pulse}\n'
                f'{right_analysis}\n\n'
                f'📊 <a href="{sheet_url}">Открыть таблицу</a>',
                reply_markup=ReplyKeyboardRemove(),
                parse_mode='HTML'
            )

            # Delete all intermediate messages AFTER showing result
            for msg_id in current_measurement.message_ids:
                try:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
                except Exception as e:
                    logger.warning(f'Could not delete message {msg_id}: {e}')
        else:
            await update.message.reply_text(
                '❌ Ошибка при сохранении данных. Пожалуйста, попробуйте позже.',
                reply_markup=ReplyKeyboardRemove()
            )

        return ConversationHandler.END
    except ValueError:
        await send_and_track(update, 'Пожалуйста, введите число:')
        return MORNING_RIGHT_PULSE


async def evening_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start evening blood pressure measurement"""
    current_measurement.reset()
    current_measurement.date = get_current_date(context)
    current_measurement.time_of_day = 'evening'

    # Store user's command message ID
    current_measurement.message_ids.append(update.message.message_id)

    msg = await update.message.reply_text(
        '🌙 Вечернее измерение\n\n'
        'ЛЕВАЯ рука\n'
        'Введите ВЕРХНЕЕ давление:'
    )
    current_measurement.message_ids.append(msg.message_id)
    return EVENING_LEFT_UPPER


async def evening_left_upper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store left upper pressure and ask for lower"""
    text = update.message.text

    try:
        value = int(text)
        current_measurement.left_upper = value
        await send_and_track(update, 'ЛЕВАЯ рука\nВведите НИЖНЕЕ давление:')
        return EVENING_LEFT_LOWER
    except ValueError:
        await send_and_track(update, 'Пожалуйста, введите число:')
        return EVENING_LEFT_UPPER


async def evening_left_lower(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store left lower pressure and ask for pulse"""
    text = update.message.text

    try:
        value = int(text)
        current_measurement.left_lower = value
        await send_and_track(update, 'ЛЕВАЯ рука\nВведите ПУЛЬС:')
        return EVENING_LEFT_PULSE
    except ValueError:
        await send_and_track(update, 'Пожалуйста, введите число:')
        return EVENING_LEFT_LOWER


async def evening_left_pulse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store left pulse and ask for right upper pressure"""
    text = update.message.text

    try:
        value = int(text)
        current_measurement.left_pulse = value
        await send_and_track(update, 'ПРАВАЯ рука\nВведите ВЕРХНЕЕ давление:')
        return EVENING_RIGHT_UPPER
    except ValueError:
        await send_and_track(update, 'Пожалуйста, введите число:')
        return EVENING_LEFT_PULSE


async def evening_right_upper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store right upper pressure and ask for lower"""
    text = update.message.text

    try:
        value = int(text)
        current_measurement.right_upper = value
        await send_and_track(update, 'ПРАВАЯ рука\nВведите НИЖНЕЕ давление:')
        return EVENING_RIGHT_LOWER
    except ValueError:
        await send_and_track(update, 'Пожалуйста, введите число:')
        return EVENING_RIGHT_UPPER


async def evening_right_lower(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store right lower pressure and ask for pulse"""
    text = update.message.text

    try:
        value = int(text)
        current_measurement.right_lower = value
        await send_and_track(update, 'ПРАВАЯ рука\nВведите ПУЛЬС:')
        return EVENING_RIGHT_PULSE
    except ValueError:
        await send_and_track(update, 'Пожалуйста, введите число:')
        return EVENING_RIGHT_LOWER


async def evening_right_pulse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store right pulse and save to Google Sheets"""
    text = update.message.text

    try:
        value = int(text)
        current_measurement.right_pulse = value

        # Add user's last message to deletion list
        current_measurement.message_ids.append(update.message.message_id)

        # Save to Google Sheets
        success = sheets_manager.add_evening_measurement(
            date=current_measurement.date,
            left_upper=current_measurement.left_upper,
            left_lower=current_measurement.left_lower,
            left_pulse=current_measurement.left_pulse,
            right_upper=current_measurement.right_upper,
            right_lower=current_measurement.right_lower,
            right_pulse=current_measurement.right_pulse
        )

        if success:
            # Analyze blood pressure for both arms
            left_analysis = analyze_blood_pressure(
                current_measurement.left_upper,
                current_measurement.left_lower
            )
            right_analysis = analyze_blood_pressure(
                current_measurement.right_upper,
                current_measurement.right_lower
            )

            # Get Google Sheets link
            sheet_url = f"https://docs.google.com/spreadsheets/d/{os.getenv('GOOGLE_SHEET_ID')}"

            result_msg = await update.message.reply_text(
                '✅ Вечернее измерение сохранено!\n\n'
                f'Дата: {current_measurement.date}\n\n'
                f'📍 Левая рука: {current_measurement.left_upper}/{current_measurement.left_lower}, пульс {current_measurement.left_pulse}\n'
                f'{left_analysis}\n\n'
                f'📍 Правая рука: {current_measurement.right_upper}/{current_measurement.right_lower}, пульс {current_measurement.right_pulse}\n'
                f'{right_analysis}\n\n'
                f'📊 <a href="{sheet_url}">Открыть таблицу</a>',
                reply_markup=ReplyKeyboardRemove(),
                parse_mode='HTML'
            )

            # Delete all intermediate messages AFTER showing result
            for msg_id in current_measurement.message_ids:
                try:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
                except Exception as e:
                    logger.warning(f'Could not delete message {msg_id}: {e}')
        else:
            await update.message.reply_text(
                '❌ Ошибка при сохранении данных. Пожалуйста, попробуйте позже.',
                reply_markup=ReplyKeyboardRemove()
            )

        return ConversationHandler.END
    except ValueError:
        await send_and_track(update, 'Пожалуйста, введите число:')
        return EVENING_RIGHT_PULSE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation"""
    current_measurement.reset()
    await update.message.reply_text(
        'Измерение отменено. Используйте /morning или /evening для нового измерения.',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def main() -> None:
    """Start the bot"""
    # Create persistence
    persistence = PicklePersistence(filepath='bot_data.pkl')

    # Create the Application
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).persistence(persistence).build()

    # Morning conversation handler
    morning_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('morning', morning_start)],
        states={
            MORNING_LEFT_UPPER: [MessageHandler(filters.TEXT & ~filters.COMMAND, morning_left_upper)],
            MORNING_LEFT_LOWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, morning_left_lower)],
            MORNING_LEFT_PULSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, morning_left_pulse)],
            MORNING_RIGHT_UPPER: [MessageHandler(filters.TEXT & ~filters.COMMAND, morning_right_upper)],
            MORNING_RIGHT_LOWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, morning_right_lower)],
            MORNING_RIGHT_PULSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, morning_right_pulse)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name='morning_conversation',
        persistent=True,
    )

    # Evening conversation handler
    evening_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('evening', evening_start)],
        states={
            EVENING_LEFT_UPPER: [MessageHandler(filters.TEXT & ~filters.COMMAND, evening_left_upper)],
            EVENING_LEFT_LOWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, evening_left_lower)],
            EVENING_LEFT_PULSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, evening_left_pulse)],
            EVENING_RIGHT_UPPER: [MessageHandler(filters.TEXT & ~filters.COMMAND, evening_right_upper)],
            EVENING_RIGHT_LOWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, evening_right_lower)],
            EVENING_RIGHT_PULSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, evening_right_pulse)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name='evening_conversation',
        persistent=True,
    )

    # Settings conversation handler
    settings_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('settings', settings_start)],
        states={
            SETTINGS_TIMEZONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, settings_timezone)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        name='settings_conversation',
        persistent=True,
    )

    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('version', version_command))
    application.add_handler(settings_conv_handler)
    application.add_handler(morning_conv_handler)
    application.add_handler(evening_conv_handler)

    # Run the bot
    logger.info('Starting bot...')
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
