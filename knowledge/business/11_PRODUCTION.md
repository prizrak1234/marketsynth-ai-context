---
tags: [gemini, production, pm2, deployment, checklist]
date: 2026-04-18
type: note
---

# Шаг 11: Продакшн чеклист

Финальные шаги перед тем как отойти от компьютера и доверить бота серверу.

## Prerequisites

- Все шаги 1-10 выполнены
- Бот отвечает на сообщения в Telegram
- `/selfaudit` возвращает OK по основным компонентам

## 1. PM2: автозапуск после перезагрузки

```bash
# Сохранить текущий список процессов PM2
pm2 save

# Зарегистрировать PM2 в systemd (выполнить один раз)
pm2 startup
# Скопируй и выполни команду, которую вернёт pm2 startup
# Обычно выглядит так:
# sudo env PATH=$PATH:/usr/local/bin pm2 startup systemd -u root --hp /root

# Ещё раз сохранить (после выполнения startup команды)
pm2 save
```

Проверка: перезагрузи сервер (`reboot`) и через минуту проверь что бот снова отвечает.

## 2. Настройка dream.sh для регулярной консолидации памяти

```bash
# Проверить что скрипт существует (если есть)
ls ~/GeminiClaw/scripts/dream.sh

# Добавить в crontab (2 раза в день: в 3:00 и 15:00)
crontab -e
```

Добавь строки:

```cron
0 3 * * * /bin/bash ~/GeminiClaw/scripts/dream.sh >> ~/GeminiClaw/workspace/tmp/dream.log 2>&1
0 15 * * * /bin/bash ~/GeminiClaw/scripts/dream.sh >> ~/GeminiClaw/workspace/tmp/dream.log 2>&1
```

Если `dream.sh` не создан — консолидацию памяти можно запускать вручную через команду `/dream` в Telegram.

## 3. Проверка логов

```bash
# Последние 50 строк логов бота
pm2 logs geminiclaw --lines 50

# Логи в реальном времени
pm2 logs geminiclaw

# Лог dream.sh
tail -20 ~/GeminiClaw/workspace/tmp/dream.log
```

На что смотреть в логах:
- `ERROR` или `WARN` — требуют внимания
- `spawn gemini ENOENT` — Gemini CLI не найден, проверь PATH
- `429 Too Many Requests` — превышены лимиты квоты

## 4. PM2 мониторинг

```bash
# Интерактивный дашборд
pm2 monit

# Краткий статус
pm2 list

# Статистика по процессу
pm2 show geminiclaw
```

В `pm2 monit` видно: CPU, RAM, количество рестартов, uptime.

## 5. Полезные команды обслуживания

```bash
# Перезапустить бота (без downtime)
pm2 reload geminiclaw

# Полный рестарт
pm2 restart geminiclaw

# Остановить
pm2 stop geminiclaw

# Запустить снова
pm2 start geminiclaw

# Обновить после изменений кода
npm run build && pm2 reload geminiclaw
```

## 6. Ротация логов PM2

По умолчанию логи PM2 растут бесконечно. Установи ротацию:

```bash
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
```

## 7. Мониторинг дискового пространства

```bash
# Общее использование диска
df -h

# Размер папки проекта
du -sh ~/GeminiClaw/

# Самые большие файлы в workspace
find ~/GeminiClaw/workspace -type f -size +1M | xargs ls -lh
```

SQLite база (`store/geminiclaw.db`) растёт со временем. Раз в месяц можно запустить VACUUM:

```bash
sqlite3 ~/GeminiClaw/store/geminiclaw.db "VACUUM;"
```

## Финальный verify

Отправь эти сообщения в Telegram по очереди и убедись что всё работает:

1. Отправь: "привет" — должен ответить
2. Отправь: `/status` — должен показать статистику
3. Отправь: `/selfaudit` — все компоненты OK
4. Отправь голосовое — должен транскрибировать
5. Отправь фото — должен описать
6. Отправь: `/schedule list` — должен работать
7. Перезагрузи сервер (`reboot`), подожди минуту, отправь "привет" снова

## Troubleshooting

**После перезагрузки бот не поднимается**
Проверь что `pm2 startup` был выполнён и его вывод скопирован и запущен. Затем `pm2 save` должен был сохранить список процессов.

**pm2 monit показывает постоянные рестарты**
Смотри логи: `pm2 logs geminiclaw --lines 100`. Скорее всего ошибка в коде или `.env` не загружается.

**Диск заканчивается**
Проверь `~/GeminiClaw/workspace/inbox/` — там могут копиться медиафайлы. Очистка inbox старше 24 часов должна работать автоматически (Шаг 5), но проверь что обработчик запущен.

## После этого шага

- [ ] `pm2 startup && pm2 save` выполнены
- [ ] Перезагрузка сервера не убивает бота
- [ ] `pm2 logs geminiclaw --lines 50` не показывает критических ошибок
- [ ] `pm2 monit` показывает стабильный процесс без частых рестартов
- [ ] Бот отвечает на "привет" в Telegram
- [ ] Логи PM2 ротируются (pm2-logrotate установлен)

GeminiClaw собран и запущен в продакшне.

---

*Начало: [[00_INDEX]] | Быстрый старт: [[00_QUICK_START]]*
