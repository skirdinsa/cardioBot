# Бот для отслеживания артериального давления

Telegram-бот для ежедневного мониторинга артериального давления с автоматической записью данных в Google Sheets.

## Возможности

- Напоминания 2 раза в день (утром и вечером)
- Запись показателей для обеих рук (верхнее/нижнее давление + пульс)
- **Мгновенная обратная связь** - бот анализирует давление и сообщает, в норме ли оно
- Автоматическое сохранение данных в Google Sheets
- Настраиваемые нормы давления через переменные окружения
- Запуск через Docker Compose

## Структура данных в Google Sheets

Бот записывает данные в следующие колонки:

**Утро:**
- B: Левая рука - Верхнее давление
- C: Левая рука - Нижнее давление
- D: Левая рука - Пульс
- E: Правая рука - Верхнее давление
- F: Правая рука - Нижнее давление
- G: Правая рука - Пульс

**Вечер:**
- H: Левая рука - Верхнее давление
- I: Левая рука - Нижнее давление
- J: Левая рука - Пульс
- K: Правая рука - Верхнее давление
- L: Правая рука - Нижнее давление
- M: Правая рука - Пульс

## Настройка

### 1. Создание Telegram бота

1. Откройте [@BotFather](https://t.me/botfather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям и сохраните токен бота
4. Получите ваш User ID от [@userinfobot](https://t.me/userinfobot)

### 2. Настройка Google Sheets API

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите Google Sheets API:
   - Перейдите в "APIs & Services" > "Library"
   - Найдите "Google Sheets API" и включите его
4. Создайте Service Account:
   - Перейдите в "APIs & Services" > "Credentials"
   - Нажмите "Create Credentials" > "Service Account"
   - Заполните форму и создайте аккаунт
5. Создайте ключ:
   - Откройте созданный Service Account
   - Перейдите в "Keys" > "Add Key" > "Create New Key"
   - Выберите JSON формат
   - Сохраните файл как `credentials.json` в корне проекта

### 3. Настройка Google Sheets

1. Откройте вашу таблицу Google Sheets
2. Скопируйте ID таблицы из URL (часть между `/d/` и `/edit`):
   ```
   https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]/edit
   ```
3. Откройте файл `credentials.json` и найдите email Service Account (поле `client_email`)
4. Поделитесь таблицей с этим email (дайте права на редактирование)

### 4. Конфигурация бота

1. Скопируйте файл с примером конфигурации:
   ```bash
   cp .env.example .env
   ```

2. Отредактируйте `.env` файл:
   ```env
   # Токен бота от @BotFather
   TELEGRAM_BOT_TOKEN=your_bot_token_here

   # Ваш Telegram User ID от @userinfobot
   TELEGRAM_USER_ID=your_user_id_here

   # ID Google таблицы
   GOOGLE_SHEET_ID=your_spreadsheet_id_here

   # Часовой пояс
   TIMEZONE=Europe/Moscow

   # Время напоминаний (24-часовой формат)
   MORNING_REMINDER_TIME=09:00
   EVENING_REMINDER_TIME=21:00

   # Нормы артериального давления
   # Оптимальные значения
   OPTIMAL_UPPER=110
   OPTIMAL_LOWER=70

   # Максимальные допустимые значения (до этого - "хорошо")
   GOOD_UPPER=130
   GOOD_LOWER=80
   ```

   **Нормы давления:**
   - Если давление ≤ 110/70 - бот сообщит "Отлично! Давление оптимальное"
   - Если давление ≤ 130/80 - бот сообщит "Хорошо! Давление в норме"
   - Если давление > 130/80 - бот предупредит о повышенном давлении

### 5. Запуск через Docker Compose

1. Убедитесь, что Docker и Docker Compose установлены
2. Убедитесь, что файл `credentials.json` находится в корне проекта
3. Запустите бота:
   ```bash
   docker-compose up -d
   ```

4. Проверьте логи:
   ```bash
   # Логи бота
   docker-compose logs -f bot

   # Логи планировщика
   docker-compose logs -f scheduler
   ```

5. Остановка бота:
   ```bash
   docker-compose down
   ```

## Использование

### Команды бота

- `/start` - Начать работу с ботом
- `/morning` - Начать утреннее измерение
- `/evening` - Начать вечернее измерение
- `/cancel` - Отменить текущее измерение
- `/help` - Показать справку

### Процесс измерения

1. Бот автоматически отправит напоминание в установленное время
2. Или вы можете начать измерение вручную командой `/morning` или `/evening`
3. Бот последовательно запросит:
   - Левая рука: верхнее давление → нижнее давление → пульс
   - Правая рука: верхнее давление → нижнее давление → пульс
4. После ввода всех данных они автоматически сохранятся в Google Sheets
5. Если нужно отменить измерение, используйте `/cancel`

## Обновление бота

Для обновления бота после изменения кода:

```bash
docker-compose down
docker-compose build
docker-compose up -d
```

## Устранение неполадок

### Бот не отвечает
- Проверьте, что контейнер запущен: `docker-compose ps`
- Проверьте логи: `docker-compose logs bot`
- Убедитесь, что токен бота корректный

### Данные не сохраняются в Google Sheets
- Проверьте, что файл `credentials.json` существует
- Убедитесь, что Service Account имеет доступ к таблице
- Проверьте логи: `docker-compose logs bot`
- Проверьте ID таблицы в `.env`

### Напоминания не приходят
- Проверьте логи планировщика: `docker-compose logs scheduler`
- Убедитесь, что TELEGRAM_USER_ID указан корректно
- Проверьте настройки времени в `.env`
- Убедитесь, что часовой пояс указан правильно

## Разработка

Для локальной разработки без Docker:

1. Создайте виртуальное окружение:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # или
   venv\Scripts\activate  # Windows
   ```

2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

3. Запустите бота:
   ```bash
   python bot.py
   ```

4. В отдельном терминале запустите планировщик:
   ```bash
   python scheduler.py
   ```

## Структура проекта

```
cardioBot/
├── bot.py                    # Основной код бота
├── scheduler.py              # Планировщик напоминаний
├── sheets_manager.py         # Интеграция с Google Sheets
├── requirements.txt          # Python зависимости
├── Dockerfile               # Docker образ для бота
├── Dockerfile.scheduler     # Docker образ для планировщика
├── docker-compose.yml       # Docker Compose конфигурация
├── .env                     # Переменные окружения (не в git)
├── .env.example            # Пример переменных окружения
├── credentials.json        # Google Service Account (не в git)
└── README.md              # Документация
```

## Безопасность

- Никогда не коммитьте файлы `.env` и `credentials.json` в git
- Храните токены и ключи в безопасности
- Регулярно обновляйте зависимости
- Ограничьте права Service Account только необходимыми

## Лицензия

MIT
