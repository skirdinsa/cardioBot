"""
User settings management module for CardioBot.
Stores and retrieves user settings from a JSON file.
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Path to settings file
SETTINGS_FILE = Path(os.getenv('SETTINGS_FILE', 'data/user_settings.json'))


def get_default_settings() -> dict:
    """Get default settings from environment variables."""
    return {
        'notifications': {
            'morning_enabled': True,
            'evening_enabled': True,
            'morning_time': os.getenv('MORNING_REMINDER_TIME', '09:00'),
            'evening_time': os.getenv('EVENING_REMINDER_TIME', '21:00'),
        },
        'thresholds': {
            'good_upper': int(os.getenv('GOOD_UPPER', 130)),
            'good_lower': int(os.getenv('GOOD_LOWER', 70)),
            'warning_upper': int(os.getenv('WARNING_UPPER', 140)),
            'warning_lower': int(os.getenv('WARNING_LOWER', 90)),
        },
        'timezone': os.getenv('TIMEZONE', 'Europe/Moscow'),
    }


def _ensure_settings_file() -> None:
    """Ensure settings file and directory exist."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text('{}', encoding='utf-8')


def _load_all_settings() -> dict:
    """Load all user settings from file."""
    _ensure_settings_file()
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f'Error loading settings: {e}')
        return {}


def _save_all_settings(settings: dict) -> bool:
    """Save all user settings to file."""
    _ensure_settings_file()
    try:
        SETTINGS_FILE.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        return True
    except OSError as e:
        logger.error(f'Error saving settings: {e}')
        return False


def get_user_settings(user_id: str) -> dict:
    """
    Get settings for a specific user.
    Returns default settings merged with user's custom settings.

    Args:
        user_id: Telegram user ID as string

    Returns:
        User settings dictionary
    """
    all_settings = _load_all_settings()
    default = get_default_settings()

    if user_id not in all_settings:
        return default

    user_settings = all_settings[user_id]

    # Merge with defaults (user settings override defaults)
    result = {
        'notifications': {
            **default['notifications'],
            **user_settings.get('notifications', {})
        },
        'thresholds': {
            **default['thresholds'],
            **user_settings.get('thresholds', {})
        },
        'timezone': user_settings.get('timezone', default['timezone']),
    }

    return result


def save_user_settings(user_id: str, settings: dict) -> bool:
    """
    Save settings for a specific user.

    Args:
        user_id: Telegram user ID as string
        settings: Settings dictionary to save

    Returns:
        True if saved successfully, False otherwise
    """
    all_settings = _load_all_settings()
    all_settings[user_id] = settings
    return _save_all_settings(all_settings)


def update_user_settings(user_id: str, updates: dict) -> bool:
    """
    Update specific settings for a user (partial update).

    Args:
        user_id: Telegram user ID as string
        updates: Dictionary with settings to update

    Returns:
        True if saved successfully, False otherwise
    """
    current = get_user_settings(user_id)

    # Deep merge updates
    if 'notifications' in updates:
        current['notifications'].update(updates['notifications'])
    if 'thresholds' in updates:
        current['thresholds'].update(updates['thresholds'])
    if 'timezone' in updates:
        current['timezone'] = updates['timezone']

    return save_user_settings(user_id, current)


def get_all_users_with_settings() -> dict:
    """
    Get all users and their settings.
    Useful for scheduler to iterate over users.

    Returns:
        Dictionary with user_id as keys and settings as values
    """
    all_settings = _load_all_settings()
    default = get_default_settings()

    # If no users saved, return default user from env
    if not all_settings:
        default_user_id = os.getenv('TELEGRAM_USER_ID')
        if default_user_id:
            return {default_user_id: default}
        return {}

    # Merge each user's settings with defaults
    result = {}
    for user_id, user_settings in all_settings.items():
        result[user_id] = {
            'notifications': {
                **default['notifications'],
                **user_settings.get('notifications', {})
            },
            'thresholds': {
                **default['thresholds'],
                **user_settings.get('thresholds', {})
            },
            'timezone': user_settings.get('timezone', default['timezone']),
        }

    return result


def is_notification_enabled(user_id: str, period: str) -> bool:
    """
    Check if notification is enabled for a user and period.

    Args:
        user_id: Telegram user ID as string
        period: 'morning' or 'evening'

    Returns:
        True if enabled, False otherwise
    """
    settings = get_user_settings(user_id)
    key = f'{period}_enabled'
    return settings['notifications'].get(key, True)


def get_notification_time(user_id: str, period: str) -> str:
    """
    Get notification time for a user and period.

    Args:
        user_id: Telegram user ID as string
        period: 'morning' or 'evening'

    Returns:
        Time string in HH:MM format
    """
    settings = get_user_settings(user_id)
    key = f'{period}_time'
    default_times = {
        'morning_time': os.getenv('MORNING_REMINDER_TIME', '09:00'),
        'evening_time': os.getenv('EVENING_REMINDER_TIME', '21:00'),
    }
    return settings['notifications'].get(key, default_times[key])


def get_thresholds(user_id: str) -> dict:
    """
    Get blood pressure thresholds for a user.

    Args:
        user_id: Telegram user ID as string

    Returns:
        Dictionary with threshold values
    """
    settings = get_user_settings(user_id)
    return settings['thresholds']
