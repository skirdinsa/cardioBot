import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
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

# Conversation states
(MORNING_LEFT_UPPER, MORNING_LEFT_LOWER, MORNING_LEFT_PULSE,
 MORNING_RIGHT_UPPER, MORNING_RIGHT_LOWER, MORNING_RIGHT_PULSE,
 EVENING_LEFT_UPPER, EVENING_LEFT_LOWER, EVENING_LEFT_PULSE,
 EVENING_RIGHT_UPPER, EVENING_RIGHT_LOWER, EVENING_RIGHT_PULSE) = range(12)

# Initialize Sheets Manager
sheets_manager = SheetsManager(
    credentials_file='credentials.json',
    spreadsheet_id=os.getenv('GOOGLE_SHEET_ID')
)


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


# Global storage for current measurement
current_measurement = MeasurementData()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f'Привет, {user.first_name}!\n\n'
        'Я буду напоминать вам измерять давление 2 раза в день.\n\n'
        'Команды:\n'
        '/morning - Утреннее измерение\n'
        '/evening - Вечернее измерение\n'
        '/cancel - Отменить текущее измерение\n'
        '/help - Показать помощь'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        'Команды бота:\n\n'
        '/morning - Начать утреннее измерение давления\n'
        '/evening - Начать вечернее измерение давления\n'
        '/cancel - Отменить текущее измерение\n'
        '/help - Показать эту справку\n\n'
        'Бот будет автоматически напоминать вам о необходимости измерения давления.'
    )


async def morning_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start morning blood pressure measurement"""
    current_measurement.reset()
    current_measurement.date = datetime.now().strftime('%d.%m.%Y')
    current_measurement.time_of_day = 'morning'

    await update.message.reply_text(
        '🌅 Утреннее измерение\n\n'
        'ЛЕВАЯ рука\n'
        'Введите ВЕРХНЕЕ давление:'
    )
    return MORNING_LEFT_UPPER


async def morning_left_upper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store left upper pressure and ask for lower"""
    try:
        value = int(update.message.text)
        current_measurement.left_upper = value
        await update.message.reply_text('ЛЕВАЯ рука\nВведите НИЖНЕЕ давление:')
        return MORNING_LEFT_LOWER
    except ValueError:
        await update.message.reply_text('Пожалуйста, введите число:')
        return MORNING_LEFT_UPPER


async def morning_left_lower(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store left lower pressure and ask for pulse"""
    try:
        value = int(update.message.text)
        current_measurement.left_lower = value
        await update.message.reply_text('ЛЕВАЯ рука\nВведите ПУЛЬС:')
        return MORNING_LEFT_PULSE
    except ValueError:
        await update.message.reply_text('Пожалуйста, введите число:')
        return MORNING_LEFT_LOWER


async def morning_left_pulse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store left pulse and ask for right upper pressure"""
    try:
        value = int(update.message.text)
        current_measurement.left_pulse = value
        await update.message.reply_text('ПРАВАЯ рука\nВведите ВЕРХНЕЕ давление:')
        return MORNING_RIGHT_UPPER
    except ValueError:
        await update.message.reply_text('Пожалуйста, введите число:')
        return MORNING_LEFT_PULSE


async def morning_right_upper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store right upper pressure and ask for lower"""
    try:
        value = int(update.message.text)
        current_measurement.right_upper = value
        await update.message.reply_text('ПРАВАЯ рука\nВведите НИЖНЕЕ давление:')
        return MORNING_RIGHT_LOWER
    except ValueError:
        await update.message.reply_text('Пожалуйста, введите число:')
        return MORNING_RIGHT_UPPER


async def morning_right_lower(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store right lower pressure and ask for pulse"""
    try:
        value = int(update.message.text)
        current_measurement.right_lower = value
        await update.message.reply_text('ПРАВАЯ рука\nВведите ПУЛЬС:')
        return MORNING_RIGHT_PULSE
    except ValueError:
        await update.message.reply_text('Пожалуйста, введите число:')
        return MORNING_RIGHT_LOWER


async def morning_right_pulse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store right pulse and save to Google Sheets"""
    try:
        value = int(update.message.text)
        current_measurement.right_pulse = value

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
            await update.message.reply_text(
                '✅ Утреннее измерение сохранено!\n\n'
                f'Дата: {current_measurement.date}\n'
                f'Левая рука: {current_measurement.left_upper}/{current_measurement.left_lower}, пульс {current_measurement.left_pulse}\n'
                f'Правая рука: {current_measurement.right_upper}/{current_measurement.right_lower}, пульс {current_measurement.right_pulse}'
            )
        else:
            await update.message.reply_text(
                '❌ Ошибка при сохранении данных. Пожалуйста, попробуйте позже.'
            )

        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text('Пожалуйста, введите число:')
        return MORNING_RIGHT_PULSE


async def evening_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start evening blood pressure measurement"""
    current_measurement.reset()
    current_measurement.date = datetime.now().strftime('%d.%m.%Y')
    current_measurement.time_of_day = 'evening'

    await update.message.reply_text(
        '🌙 Вечернее измерение\n\n'
        'ЛЕВАЯ рука\n'
        'Введите ВЕРХНЕЕ давление:'
    )
    return EVENING_LEFT_UPPER


async def evening_left_upper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store left upper pressure and ask for lower"""
    try:
        value = int(update.message.text)
        current_measurement.left_upper = value
        await update.message.reply_text('ЛЕВАЯ рука\nВведите НИЖНЕЕ давление:')
        return EVENING_LEFT_LOWER
    except ValueError:
        await update.message.reply_text('Пожалуйста, введите число:')
        return EVENING_LEFT_UPPER


async def evening_left_lower(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store left lower pressure and ask for pulse"""
    try:
        value = int(update.message.text)
        current_measurement.left_lower = value
        await update.message.reply_text('ЛЕВАЯ рука\nВведите ПУЛЬС:')
        return EVENING_LEFT_PULSE
    except ValueError:
        await update.message.reply_text('Пожалуйста, введите число:')
        return EVENING_LEFT_LOWER


async def evening_left_pulse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store left pulse and ask for right upper pressure"""
    try:
        value = int(update.message.text)
        current_measurement.left_pulse = value
        await update.message.reply_text('ПРАВАЯ рука\nВведите ВЕРХНЕЕ давление:')
        return EVENING_RIGHT_UPPER
    except ValueError:
        await update.message.reply_text('Пожалуйста, введите число:')
        return EVENING_LEFT_PULSE


async def evening_right_upper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store right upper pressure and ask for lower"""
    try:
        value = int(update.message.text)
        current_measurement.right_upper = value
        await update.message.reply_text('ПРАВАЯ рука\nВведите НИЖНЕЕ давление:')
        return EVENING_RIGHT_LOWER
    except ValueError:
        await update.message.reply_text('Пожалуйста, введите число:')
        return EVENING_RIGHT_UPPER


async def evening_right_lower(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store right lower pressure and ask for pulse"""
    try:
        value = int(update.message.text)
        current_measurement.right_lower = value
        await update.message.reply_text('ПРАВАЯ рука\nВведите ПУЛЬС:')
        return EVENING_RIGHT_PULSE
    except ValueError:
        await update.message.reply_text('Пожалуйста, введите число:')
        return EVENING_RIGHT_LOWER


async def evening_right_pulse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store right pulse and save to Google Sheets"""
    try:
        value = int(update.message.text)
        current_measurement.right_pulse = value

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
            await update.message.reply_text(
                '✅ Вечернее измерение сохранено!\n\n'
                f'Дата: {current_measurement.date}\n'
                f'Левая рука: {current_measurement.left_upper}/{current_measurement.left_lower}, пульс {current_measurement.left_pulse}\n'
                f'Правая рука: {current_measurement.right_upper}/{current_measurement.right_lower}, пульс {current_measurement.right_pulse}'
            )
        else:
            await update.message.reply_text(
                '❌ Ошибка при сохранении данных. Пожалуйста, попробуйте позже.'
            )

        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text('Пожалуйста, введите число:')
        return EVENING_RIGHT_PULSE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation"""
    current_measurement.reset()
    await update.message.reply_text(
        'Измерение отменено. Используйте /morning или /evening для нового измерения.'
    )
    return ConversationHandler.END


def main() -> None:
    """Start the bot"""
    # Create the Application
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

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
    )

    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(morning_conv_handler)
    application.add_handler(evening_conv_handler)

    # Run the bot
    logger.info('Starting bot...')
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
