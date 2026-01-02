import logging
from datetime import datetime
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

    def add_morning_measurement(self, date: str, left_upper: int, left_lower: int,
                                left_pulse: int, right_upper: int, right_lower: int,
                                right_pulse: int) -> bool:
        """
        Add morning blood pressure measurement

        Args:
            date: Date in format DD.MM.YYYY
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
            # B - Left Upper (Левая Верхнее)
            # C - Left Lower (Левая Нижнее)
            # D - Left Pulse (Левая Пульс)
            # E - Right Upper (Правая Верхнее)
            # F - Right Lower (Правая Нижнее)
            # G - Right Pulse (Правая Пульс)

            # Update cells
            self.sheet.update_cell(row, 2, left_upper)   # B - Left Upper
            self.sheet.update_cell(row, 3, left_lower)   # C - Left Lower
            self.sheet.update_cell(row, 4, left_pulse)   # D - Left Pulse
            self.sheet.update_cell(row, 5, right_upper)  # E - Right Upper
            self.sheet.update_cell(row, 6, right_lower)  # F - Right Lower
            self.sheet.update_cell(row, 7, right_pulse)  # G - Right Pulse

            logger.info(f'Successfully added morning measurement for {date}')
            return True

        except Exception as e:
            logger.error(f'Error adding morning measurement: {e}')
            return False

    def add_evening_measurement(self, date: str, left_upper: int, left_lower: int,
                               left_pulse: int, right_upper: int, right_lower: int,
                               right_pulse: int) -> bool:
        """
        Add evening blood pressure measurement

        Args:
            date: Date in format DD.MM.YYYY
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
            # H - Left Upper (Левая Верхнее)
            # I - Left Lower (Левая Нижнее)
            # J - Left Pulse (Левая Пульс)
            # K - Right Upper (Правая Верхнее)
            # L - Right Lower (Правая Нижнее)
            # M - Right Pulse (Правая Пульс)

            # Update cells
            self.sheet.update_cell(row, 8, left_upper)   # H - Left Upper
            self.sheet.update_cell(row, 9, left_lower)   # I - Left Lower
            self.sheet.update_cell(row, 10, left_pulse)  # J - Left Pulse
            self.sheet.update_cell(row, 11, right_upper) # K - Right Upper
            self.sheet.update_cell(row, 12, right_lower) # L - Right Lower
            self.sheet.update_cell(row, 13, right_pulse) # M - Right Pulse

            logger.info(f'Successfully added evening measurement for {date}')
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
