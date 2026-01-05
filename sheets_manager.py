import logging
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)


class SheetsManager:
    """Manager for Google Sheets integration"""

    def __init__(self, credentials_file: str, spreadsheet_id: str):
        """
        Initialize the Sheets Manager

        Args:
            credentials_file: Path to the Google service account credentials JSON file
            spreadsheet_id: Google Spreadsheet ID
        """
        self.spreadsheet_id = spreadsheet_id
        self.credentials_file = credentials_file
        self.client = None
        self.sheet = None
        self._authorize()

    def _authorize(self):
        """Authorize with Google Sheets API"""
        try:
            # Define the scope
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]

            # Authorize with credentials
            creds = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=scope
            )
            self.client = gspread.authorize(creds)

            # Open the spreadsheet
            self.sheet = self.client.open_by_key(self.spreadsheet_id).sheet1

            logger.info('Successfully authorized with Google Sheets')
        except Exception as e:
            logger.error(f'Error authorizing with Google Sheets: {e}')
            raise

    def _find_or_create_row(self, date: str) -> int:
        """
        Find the row for a specific date or create a new one

        Args:
            date: Date in format DD.MM.YYYY

        Returns:
            Row number (1-indexed)
        """
        try:
            # Get all dates from column A
            dates_column = self.sheet.col_values(1)

            # Find the row with the matching date
            for idx, cell_date in enumerate(dates_column):
                if cell_date == date:
                    return idx + 1

            # If date not found, find the next empty row
            # Start from row 4 (after headers)
            row_num = len(dates_column) + 1
            if row_num < 4:
                row_num = 4

            # Write the date
            self.sheet.update_cell(row_num, 1, date)
            logger.info(f'Created new row {row_num} for date {date}')

            return row_num

        except Exception as e:
            logger.error(f'Error finding/creating row: {e}')
            raise

    def add_morning_measurement(self, date: str, time: str, left_upper: int, left_lower: int,
                                left_pulse: int, right_upper: int, right_lower: int,
                                right_pulse: int) -> bool:
        """
        Add morning blood pressure measurement

        Args:
            date: Date in format DD.MM.YYYY
            time: Time in format HH:MM
            left_upper: Left arm upper pressure
            left_lower: Left arm lower pressure
            left_pulse: Left arm pulse
            right_upper: Right arm upper pressure
            right_lower: Right arm lower pressure
            right_pulse: Right arm pulse

        Returns:
            True if successful, False otherwise
        """
        try:
            row = self._find_or_create_row(date)

            # Column mapping for morning measurements (Утро):
            # B - Time (Время)
            # C - Left Upper (Левая Верхнее)
            # D - Left Lower (Левая Нижнее)
            # E - Left Pulse (Левая Пульс)
            # F - Right Upper (Правая Верхнее)
            # G - Right Lower (Правая Нижнее)
            # H - Right Pulse (Правая Пульс)

            # Update cells
            self.sheet.update_cell(row, 2, time)         # B - Time
            self.sheet.update_cell(row, 3, left_upper)   # C - Left Upper
            self.sheet.update_cell(row, 4, left_lower)   # D - Left Lower
            self.sheet.update_cell(row, 5, left_pulse)   # E - Left Pulse
            self.sheet.update_cell(row, 6, right_upper)  # F - Right Upper
            self.sheet.update_cell(row, 7, right_lower)  # G - Right Lower
            self.sheet.update_cell(row, 8, right_pulse)  # H - Right Pulse

            logger.info(f'Successfully added morning measurement for {date} at {time}')
            return True

        except Exception as e:
            logger.error(f'Error adding morning measurement: {e}')
            return False

    def add_evening_measurement(self, date: str, time: str, left_upper: int, left_lower: int,
                               left_pulse: int, right_upper: int, right_lower: int,
                               right_pulse: int) -> bool:
        """
        Add evening blood pressure measurement

        Args:
            date: Date in format DD.MM.YYYY
            time: Time in format HH:MM
            left_upper: Left arm upper pressure
            left_lower: Left arm lower pressure
            left_pulse: Left arm pulse
            right_upper: Right arm upper pressure
            right_lower: Right arm lower pressure
            right_pulse: Right arm pulse

        Returns:
            True if successful, False otherwise
        """
        try:
            row = self._find_or_create_row(date)

            # Column mapping for evening measurements (Вечер):
            # I - Time (Время)
            # J - Left Upper (Левая Верхнее)
            # K - Left Lower (Левая Нижнее)
            # L - Left Pulse (Левая Пульс)
            # M - Right Upper (Правая Верхнее)
            # N - Right Lower (Правая Нижнее)
            # O - Right Pulse (Правая Пульс)

            # Update cells
            self.sheet.update_cell(row, 9, time)         # I - Time
            self.sheet.update_cell(row, 10, left_upper)  # J - Left Upper
            self.sheet.update_cell(row, 11, left_lower)  # K - Left Lower
            self.sheet.update_cell(row, 12, left_pulse)  # L - Left Pulse
            self.sheet.update_cell(row, 13, right_upper) # M - Right Upper
            self.sheet.update_cell(row, 14, right_lower) # N - Right Lower
            self.sheet.update_cell(row, 15, right_pulse) # O - Right Pulse

            logger.info(f'Successfully added evening measurement for {date} at {time}')
            return True

        except Exception as e:
            logger.error(f'Error adding evening measurement: {e}')
            return False

    def get_measurement(self, date: str) -> dict:
        """
        Get measurements for a specific date

        Args:
            date: Date in format DD.MM.YYYY

        Returns:
            Dictionary with measurement data or None if not found
        """
        try:
            dates_column = self.sheet.col_values(1)

            for idx, cell_date in enumerate(dates_column):
                if cell_date == date:
                    row = idx + 1
                    row_data = self.sheet.row_values(row)

                    return {
                        'date': date,
                        'morning': {
                            'left': {
                                'upper': row_data[1] if len(row_data) > 1 else '',
                                'lower': row_data[2] if len(row_data) > 2 else '',
                                'pulse': row_data[3] if len(row_data) > 3 else '',
                            },
                            'right': {
                                'upper': row_data[4] if len(row_data) > 4 else '',
                                'lower': row_data[5] if len(row_data) > 5 else '',
                                'pulse': row_data[6] if len(row_data) > 6 else '',
                            }
                        },
                        'evening': {
                            'left': {
                                'upper': row_data[7] if len(row_data) > 7 else '',
                                'lower': row_data[8] if len(row_data) > 8 else '',
                                'pulse': row_data[9] if len(row_data) > 9 else '',
                            },
                            'right': {
                                'upper': row_data[10] if len(row_data) > 10 else '',
                                'lower': row_data[11] if len(row_data) > 11 else '',
                                'pulse': row_data[12] if len(row_data) > 12 else '',
                            }
                        }
                    }

            return None

        except Exception as e:
            logger.error(f'Error getting measurement: {e}')
            return None

    def has_morning_measurement(self, date: str) -> bool:
        """
        Check if morning measurement exists for a specific date

        Args:
            date: Date in format DD.MM.YYYY

        Returns:
            True if morning measurement exists, False otherwise
        """
        try:
            measurement = self.get_measurement(date)
            if measurement is None:
                return False

            # Check if at least one morning value is filled
            morning = measurement['morning']
            return bool(
                morning['left']['upper'] or
                morning['left']['lower'] or
                morning['left']['pulse'] or
                morning['right']['upper'] or
                morning['right']['lower'] or
                morning['right']['pulse']
            )
        except Exception as e:
            logger.error(f'Error checking morning measurement: {e}')
            return False

    def has_evening_measurement(self, date: str) -> bool:
        """
        Check if evening measurement exists for a specific date

        Args:
            date: Date in format DD.MM.YYYY

        Returns:
            True if evening measurement exists, False otherwise
        """
        try:
            measurement = self.get_measurement(date)
            if measurement is None:
                return False

            # Check if at least one evening value is filled
            evening = measurement['evening']
            return bool(
                evening['left']['upper'] or
                evening['left']['lower'] or
                evening['left']['pulse'] or
                evening['right']['upper'] or
                evening['right']['lower'] or
                evening['right']['pulse']
            )
        except Exception as e:
            logger.error(f'Error checking evening measurement: {e}')
            return False

    def get_moving_average(self, end_date: str, period: str = 'morning', days: int = 7) -> dict:
        """
        Calculate moving average for the last N days for a specific period (morning or evening)

        Args:
            end_date: End date in format DD.MM.YYYY
            period: 'morning' or 'evening'
            days: Number of days to calculate average (default: 7)

        Returns:
            Dictionary with average values for left and right arm measurements
        """
        try:
            # Parse end date
            end_dt = datetime.strptime(end_date, '%d.%m.%Y')

            # Collect measurements for the last N days
            measurements = []
            for i in range(days):
                date_to_check = (end_dt - timedelta(days=i)).strftime('%d.%m.%Y')
                measurement = self.get_measurement(date_to_check)

                if measurement:
                    period_data = measurement.get(period, {})
                    if period_data:
                        measurements.append(period_data)

            if not measurements:
                return None

            # Calculate averages
            left_upper_sum = 0
            left_lower_sum = 0
            left_pulse_sum = 0
            right_upper_sum = 0
            right_lower_sum = 0
            right_pulse_sum = 0
            count = 0

            for m in measurements:
                left = m.get('left', {})
                right = m.get('right', {})

                # Only count if we have valid numeric values
                try:
                    if left.get('upper') and left.get('lower') and left.get('pulse'):
                        left_upper_sum += int(left['upper'])
                        left_lower_sum += int(left['lower'])
                        left_pulse_sum += int(left['pulse'])
                        right_upper_sum += int(right['upper'])
                        right_lower_sum += int(right['lower'])
                        right_pulse_sum += int(right['pulse'])
                        count += 1
                except (ValueError, TypeError):
                    continue

            if count == 0:
                return None

            return {
                'count': count,
                'left': {
                    'upper': round(left_upper_sum / count, 1),
                    'lower': round(left_lower_sum / count, 1),
                    'pulse': round(left_pulse_sum / count, 1)
                },
                'right': {
                    'upper': round(right_upper_sum / count, 1),
                    'lower': round(right_lower_sum / count, 1),
                    'pulse': round(right_pulse_sum / count, 1)
                }
            }

        except Exception as e:
            logger.error(f'Error calculating moving average: {e}')
            return None
