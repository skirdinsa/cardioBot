# Изменения в боте

## Что добавлено:

### 1. Настройка таймзоны через бота
- Добавлена команда `/settings` для настройки таймзоны
- Таймзона сохраняется в `context.user_data` с персистентностью
- Таймзона отображается в команде `/start`

### 2. Умные напоминания
- Бот проверяет перед отправкой напоминания, не было ли уже внесено измерение
- Если измерение не внесено, напоминания отправляются 3 раза:
  - В указанное время (например, 09:00)
  - Через 30 минут (09:30)
  - Через 60 минут (10:00)
- Как только измерение внесено, дальнейшие напоминания не отправляются

## Применение изменений:

### Вариант 1: Через worktree (рекомендуется для тестирования)
```bash
cd /Users/skirdinsa/.claude-worktrees/cardioBot/inspiring-satoshi

# Скопируйте .env файл из основного репозитория
cp /Users/skirdinsa/Documents/\!Разработка/cardioBot/.env .

# Запустите бота
docker-compose down
docker-compose up -d --build

# Проверьте логи
docker-compose logs -f
```

### Вариант 2: Применить изменения в основной репозиторий
```bash
cd /Users/skirdinsa/.claude-worktrees/cardioBot/inspiring-satoshi

# Закоммитьте изменения
git add .
git commit -m "Add timezone settings and smart reminders"

# Переключитесь на main ветку
git checkout main

# Слейте изменения
git merge inspiring-satoshi

# Перезапустите бота в основном репозитории
cd /Users/skirdinsa/Documents/\!Разработка/cardioBot
docker-compose down
docker-compose up -d --build
```

## Тестирование команды /settings:

1. Отправьте боту `/settings`
2. Бот должен ответить с текущей таймзоной и предложить ввести новую
3. Введите таймзону, например: `Europe/Moscow` или `Asia/Tokyo`
4. Бот должен подтвердить изменение

## Новые файлы:

- `bot_data.pkl` - файл с персистентными данными бота (создаётся автоматически)
- Этот файл НЕ нужно добавлять в git (уже в .gitignore)
