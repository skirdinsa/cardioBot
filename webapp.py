"""
Flask web server for CardioBot Mini App.
Provides API endpoints and serves static files.
"""
import os
import hmac
import hashlib
import json
import logging
from urllib.parse import parse_qsl, unquote
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from user_settings import (
    get_user_settings,
    save_user_settings,
    get_default_settings,
)

load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')
app.secret_key = os.getenv('WEBAPP_SECRET_KEY', 'dev-secret-key')

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')


def validate_init_data(init_data: str) -> dict | None:
    """
    Validate Telegram Mini App initData.

    Args:
        init_data: Raw initData string from Telegram WebApp

    Returns:
        Parsed user data if valid, None otherwise
    """
    if not init_data or not BOT_TOKEN:
        return None

    try:
        # Parse init data
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))

        # Get hash and remove it from data
        received_hash = parsed.pop('hash', '')
        if not received_hash:
            return None

        # Sort and create data check string
        data_check_arr = sorted(
            [f'{k}={v}' for k, v in parsed.items()]
        )
        data_check_string = '\n'.join(data_check_arr)

        # Create secret key
        secret_key = hmac.new(
            b'WebAppData',
            BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Validate hash
        if not hmac.compare_digest(calculated_hash, received_hash):
            logger.warning('Invalid initData hash')
            return None

        # Parse user data
        user_data = parsed.get('user')
        if user_data:
            return json.loads(unquote(user_data))

        return None

    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logger.error(f'Error validating initData: {e}')
        return None


def get_user_from_request() -> dict | None:
    """
    Extract and validate user from request.

    Returns:
        User data dict if valid, None otherwise
    """
    init_data = request.headers.get('X-Telegram-Init-Data', '')

    # For development/testing, allow mock user
    if os.getenv('WEBAPP_DEBUG') == 'true' and not init_data:
        test_user_id = os.getenv('TELEGRAM_USER_ID')
        if test_user_id:
            return {'id': int(test_user_id)}

    return validate_init_data(init_data)


@app.route('/')
def index():
    """Serve the Mini App HTML."""
    return send_from_directory('static', 'index.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory('static', filename)


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get user settings."""
    user = get_user_from_request()

    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = str(user['id'])
    settings = get_user_settings(user_id)

    return jsonify({
        'success': True,
        'settings': settings,
    })


@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update user settings."""
    user = get_user_from_request()

    if not user:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = str(user['id'])

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON'}), 400

        # Validate settings structure
        settings = {}

        if 'notifications' in data:
            notifications = data['notifications']
            settings['notifications'] = {}

            if 'morning_enabled' in notifications:
                settings['notifications']['morning_enabled'] = bool(
                    notifications['morning_enabled']
                )
            if 'evening_enabled' in notifications:
                settings['notifications']['evening_enabled'] = bool(
                    notifications['evening_enabled']
                )
            if 'morning_time' in notifications:
                time_str = notifications['morning_time']
                if _validate_time(time_str):
                    settings['notifications']['morning_time'] = time_str
            if 'evening_time' in notifications:
                time_str = notifications['evening_time']
                if _validate_time(time_str):
                    settings['notifications']['evening_time'] = time_str

        if 'thresholds' in data:
            thresholds = data['thresholds']
            settings['thresholds'] = {}

            for key in ['good_upper', 'good_lower', 'warning_upper', 'warning_lower']:
                if key in thresholds:
                    value = int(thresholds[key])
                    if 40 <= value <= 250:  # Reasonable BP range
                        settings['thresholds'][key] = value

        if 'timezone' in data:
            settings['timezone'] = str(data['timezone'])

        # Merge with existing settings
        current = get_user_settings(user_id)
        if 'notifications' in settings:
            current['notifications'].update(settings['notifications'])
        if 'thresholds' in settings:
            current['thresholds'].update(settings['thresholds'])
        if 'timezone' in settings:
            current['timezone'] = settings['timezone']

        # Save
        success = save_user_settings(user_id, current)

        if success:
            return jsonify({
                'success': True,
                'settings': current,
            })
        else:
            return jsonify({'error': 'Failed to save settings'}), 500

    except (ValueError, TypeError) as e:
        logger.error(f'Error updating settings: {e}')
        return jsonify({'error': str(e)}), 400


@app.route('/api/defaults', methods=['GET'])
def get_defaults():
    """Get default settings."""
    return jsonify({
        'success': True,
        'defaults': get_default_settings(),
    })


def _validate_time(time_str: str) -> bool:
    """Validate time string in HH:MM format."""
    try:
        parts = time_str.split(':')
        if len(parts) != 2:
            return False
        hour, minute = int(parts[0]), int(parts[1])
        return 0 <= hour <= 23 and 0 <= minute <= 59
    except (ValueError, AttributeError):
        return False


if __name__ == '__main__':
    port = int(os.getenv('WEBAPP_PORT', 8080))
    debug = os.getenv('WEBAPP_DEBUG', 'false').lower() == 'true'

    logger.info(f'Starting webapp on port {port}')
    app.run(host='0.0.0.0', port=port, debug=debug)
