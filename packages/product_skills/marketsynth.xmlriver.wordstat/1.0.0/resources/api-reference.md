# XMLRiver Wordstat — полный справочник API

Официальная документация:
- [Wordstat (старый)](https://xmlriver.com/apiwordstat/)
- [Wordstat New](https://xmlriver.com/apiwordstatnew/)
- [Способы сбора](https://xmlriver.com/api/api-alt/)
- [Сервисные методы](https://xmlriver.com/api/api-methods/)

## Endpoints

### Wordstat (старый интерфейс)

```
GET http://xmlriver.com/wordstat/json
    ?user={user_id}
    &key={key}
    &query={query}
    [&page=1]
    [&regions=213]
    [&device=desktop]
    [&pagetype=words|history]
    [&period=monthly|weekly]
```

### Wordstat New (новый интерфейс)

```
GET http://xmlriver.com/wordstat/new/json
    ?user={user_id}
    &key={key}
    &query={query}
    [&regions=213]
    [&device=desktop,phone,tablet]
    [&pagetype=words|history]
    [&period=month|week|day]
    [&start=01.01.2026]
    [&end=30.06.2026]
```

## Способы сбора (6 методов)

| # | Метод | API | pagetype | Что получаем |
|---|-------|-----|----------|--------------|
| 1 | Топы запросов (New) | `/wordstat/new/json` | `words` | `popular[]` + `associations[]` |
| 2 | Динамика + частота (New) | `/wordstat/new/json` | `history` | `totalValue` + `graph.tableData[]` |
| 3 | По словам (Old) | `/wordstat/json` | `words` | `includingPhrases` + `phrasesAssociations` |
| 4 | История (Old) | `/wordstat/json` | `history` | `dataGroups[]`, `graphs[]`, абс./отн. значения |
| 5 | Пагинация (Old) | `/wordstat/json` | `words` + `page=N` | До 41 страницы, `hasNextPage` |
| 6 | Desktop-парсер | XMLRiver.Parser | — | CSV: фразы, частоты, история |

## Структура ответов

### New — words

```json
{
  "popular": [{"text": "фраза", "value": "1234", "isAssociations": false}],
  "associations": [{"text": "похожая", "value": "567", "isAssociations": true}]
}
```

### New — history

```json
{
  "totalValue": 34,
  "graph": {
    "tableData": [{"absoluteValue": "7", "text": "13 мая – 19 мая"}]
  },
  "table": {
    "tableData": {"popular": [...], "associations": [...]}
  }
}
```

**Частота за месяц → `totalValue`.**

### Old — words

```json
{
  "content": {
    "hasNextPage": "yes",
    "currentPage": "1",
    "includingPhrases": {"items": [{"phrase": "...", "number": "123"}]},
    "phrasesAssociations": {"items": [{"phrase": "...", "number": "456"}]}
  }
}
```

### Old — history

```json
{
  "totalValueLabel": "Абсолютное",
  "dataGroups": [{"data": [...], "groupBy": "monthly"}],
  "graphs": [...]
}
```

## Регионы Яндекса (частые)

| ID | Регион |
|----|--------|
| 225 | Россия |
| 213 | Москва |
| 2 | Санкт-Петербург |
| 54 | Екатеринбург |
| 65 | Новосибирск |

Полный список: https://yandex.ru/dev/id/doc/ru/regions

## Сервисные API

```
GET http://xmlriver.com/api/get_balance/?user={id}&key={key}
GET http://xmlriver.com/api/get_cost/wordstat/?user={id}&key={key}
GET http://xmlriver.com/api/get_tarif/?user={id}&key={key}
GET http://xmlriver.com/api/get_tarif_expire/?user={id}&key={key}
```

## Тарификация

- 1 запрос = 1 страница Wordstat
- На странице: частота запроса + до 50 уточняющих фраз
- Базовый тариф: ₽25 / 1000 запросов
- Стандарт: 10 параллельных потоков

## Realtime vs Delayed

| | Realtime | Delayed |
|---|----------|---------|
| Параметр | (по умолчанию) | `delayed=1` |
| Таймаут | до 60 сек | мгновенный req_id |
| Wordstat | ✅ | ❌ |
| Poll | — | `?req_id=N` (хранение >10 мин не гарантировано) |

## Retry-логика

```python
RETRY_CODES = {110, 500}
FATAL_CODES = {2, 31, 42, 45, 200, 400}
WAIT_CODES = {115}  # HTTP 429
```

При 110/500 — повторить до 3 раз с паузой 2–5 сек.
