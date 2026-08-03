---
name: xml-river
description: Collects Yandex Wordstat data via XMLRiver API — keyword frequency, related queries, seasonality, and semantic expansion. Use when the user asks about Wordstat, keyword frequency, search volume, semantic core, частотность, ключевые слова, вордстат, XMLRiver, or how many queries a phrase has.
---

# XMLRiver — сбор данных из Яндекс Wordstat

Скилл для работы с API [XMLRiver Wordstat](https://xmlriver.com/). Все запросы — GET, ответ — JSON.

## Credentials

Ключи хранить в `.env` проекта (не коммитить):

```env
XML_RIVER_USER_ID=your_user_id
XML_RIVER_KEY=your_api_key
```

Получить: зарегистрироваться на xmlriver.com → аккаунт → **Настройки сбора** (без них API недоступен).

## Два API Wordstat

| API | Endpoint | Когда использовать |
|-----|----------|-------------------|
| **Wordstat (старый)** | `http://xmlriver.com/wordstat/json` | Полная выдача «как в Wordstat», пагинация по `page`, до 41 страницы |
| **Wordstat New (новый)** | `http://xmlriver.com/wordstat/new/json` | Новый интерфейс Яндекса, `totalValue` для частоты, `popular` + `associations` |

**Предпочитай Wordstat New** для частоты одной фразы. Старый API — для глубокого сбора семантики с пагинацией.

## Способы сбора

### 1. Топы запросов (семантика)

**New API** — `pagetype=words` (или настройка «топы запросов» в кабинете):

```bash
python3 scripts/wordstat_words.py "gora academy"
python3 scripts/wordstat_words.py "gora academy" --api old --page 2
```

Ответ New: `popular[]` (запросы с вашей фразой) + `associations[]` (похожие).  
Ответ Old: `content.includingPhrases.items[]` (слева) + `content.phrasesAssociations.items[]` (справа).

На одной странице — частота по запросу + до **50 уточняющих фраз**. Цена: ~₽25 за 1000 страниц (базовый тариф).

### 2. Частотность / динамика

**New API** — `pagetype=history`:

```bash
python3 scripts/wordstat_frequency.py "gora academy"
python3 scripts/wordstat_frequency.py "gora academy" --period month --start 01.01.2026 --end 30.07.2026
```

Частота за месяц → поле **`totalValue`**.  
Динамика → `graph.tableData[]` (absoluteValue по периодам).

**Old API** — `pagetype=history`, `period=monthly|weekly`:

```bash
python3 scripts/wordstat_frequency.py "gora academy" --api old --period monthly
```

### 3. Расширение семантики (несколько страниц)

```bash
python3 scripts/wordstat_expand.py "gora academy" --pages 5 --output keywords.csv
```

Собирает все `popular` + `associations` (New) или `includingPhrases` + `phrasesAssociations` (Old) с нескольких страниц, дедуплицирует, сохраняет CSV.

### 4. Режимы доставки ответа

| Режим | Как | Таймаут |
|-------|-----|---------|
| **Realtime** (по умолчанию) | Обычный GET | До **60 сек**, обычно 3–6 сек |
| **Delayed** | `delayed=1` → `req_id` → poll | Не для Wordstat* |

\* Delayed работает для Google/Яндекс SERP, не для Wordstat.

Стандартный аккаунт: **10 потоков**, ~150K запросов/сутки.

### 5. Десктоп-парсер XMLRiver.Parser

Для массового сбора без кода: [xmlriver.com/parser-wordstat-online.html](https://xmlriver.com/parser-wordstat-online.html) — CSV с фразами, частотами всех типов и историей. Поддерживает новый Wordstat.

### 6. Сервисные API

```bash
python3 scripts/xmlriver_api.py balance
python3 scripts/xmlriver_api.py cost wordstat
```

## Параметры GET (приоритет над настройками кабинета)

### Общие

| Параметр | Обяз. | Описание |
|----------|-------|----------|
| `user` | да | ID пользователя |
| `key` | да | API-ключ |
| `query` | да | Фраза Wordstat. **`&` → `%26`** |
| `regions` | нет | ID региона Яндекса (213 = Москва, пусто = все) |
| `device` | нет | Old: `desktop`, `mobile`, `phone`, `tablet`. New: через запятую `desktop,phone,tablet` |

### Old Wordstat

| Параметр | Значения |
|----------|----------|
| `pagetype` | `words` — по словам; `history` — история |
| `page` | Номер страницы (с 1), до 41 |
| `period` | `monthly`, `weekly` (только history) |

### New Wordstat

| Параметр | Значения |
|----------|----------|
| `pagetype` | `words` — топы; `history` — динамика + totalValue |
| `period` | `month`, `week`, `day` |
| `start` | `dd.mm.yyyy` |
| `end` | `dd.mm.yyyy` |

Минимальные периоды: month ≥ 3 мес., week ≥ 3 нед., day ≥ 3 дня (`end` ≠ сегодня).

## Операторы Wordstat в query

Поддерживаются все операторы Wordstat. Подробнее: [references/wordstat-operators.md](references/wordstat-operators.md).

| Оператор | Пример | Частота |
|----------|--------|---------|
| Без операторов | `купить телефон` | Общая (все формы + доп. слова) |
| `"фраза"` | `"gora academy"` | Фразовая |
| `"!gora !academy"` | `"!gora !academy"` | Точная (фикс. словоформы) |
| `[gora academy]` | `[gora academy]` | Прямой порядок слов |
| `+с` | `купить +в москве` | Стоп-слово обязательно |
| `-минус` | `купить -авито` | Исключение |
| `(a\|b)` | `(купить\|заказать) телефон` | Группировка / ИЛИ |

## Workflow агента

### «Сколько запросов по фразе X?»

1. Проверить `.env` (`XML_RIVER_USER_ID`, `XML_RIVER_KEY`).
2. Запустить `wordstat_frequency.py "X"` → взять `totalValue`.
3. Для списка связанных запросов → `wordstat_words.py "X"`.
4. Посчитать: `len(popular) + len(associations)` (New) или items в обеих колонках (Old).
5. При необходимости расширить: `wordstat_expand.py "X" --pages 3`.

### Сбор семантического ядра

1. Seed-фразы от пользователя.
2. `wordstat_expand.py` для каждой seed.
3. Объединить, дедуплицировать, отфильтровать по частоте.
4. Отчёт: таблица фраза → частота → тип (popular/association).

## Обработка ошибок

JSON при ошибке: `{"code": N, "error": "..."}`.

| Код | Действие |
|-----|----------|
| 110, 500 | Повторить запрос (временная ошибка) |
| 115 | HTTP 429, подождать N секунд |
| 200 | Баланс = 0, пополнить |
| 400 | Проверить period/start/end |
| 45 | IP не в whitelist кабинета |

Полный список: [references/errors.md](references/errors.md).

## Формат отчёта

```markdown
## Wordstat: «{query}»

**Частота (totalValue):** {N} показов/мес
**Регион:** {region}
**Связанных запросов на 1-й странице:** {count}

| # | Запрос | Показов | Тип |
|---|--------|---------|-----|
| 1 | ... | ... | popular |

**Источник:** XMLRiver Wordstat New, {date}
```

## Дополнительно

- Полный справочник API: [references/api-reference.md](references/api-reference.md)
- Операторы Wordstat: [references/wordstat-operators.md](references/wordstat-operators.md)
- Коды ошибок: [references/errors.md](references/errors.md)
- Официальная документация: [Wordstat](https://xmlriver.com/apiwordstat/) · [Wordstat New](https://xmlriver.com/apiwordstatnew/)
