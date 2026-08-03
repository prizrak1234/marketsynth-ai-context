# Шаг 3: Шаблон skill для генерации изображений

Добавь эти правила в свой skill или системную инструкцию.

```text
## Skill: image-generator

Triggers:
- сгенерируй картинку
- создай изображение
- сделай обложку
- нарисуй
- generate image
- youtube thumbnail
- /image

## Выбор модели (ВАЖНО — не перепутай)

| Сигнал | Модель |
|---|---|
| Есть прикреплённое фото / файл | gpt-image-2-image-to-image |
| "быстро" / "черновик" / "набросок" / "nano" | nano-banana-2 |
| ВСЁ ОСТАЛЬНОЕ (дефолт) | gpt-image-2-text-to-image |

nano-banana-2 — это НЕ дефолт. Это модель для набросков.
gpt-image-2-text-to-image — дефолт для любого профессионального запроса.

## Выбор aspect_ratio по задаче

| Задача | aspect_ratio |
|---|---|
| YouTube thumbnail / обложка | 16:9 |
| Instagram / Threads пост | 1:1 |
| Instagram / TikTok Stories, Reels | 9:16 |
| Портрет | 3:4 |
| Кинематографичный кадр | 21:9 |

Если не указано явно — ставить 16:9.

## Primary behavior:
1. Определи тип задачи: thumbnail, portrait, illustration, product, ad, social post.
2. Если прикреплено 1+ изображений — это image-to-image (НЕ эскалация к агенту).
3. Расширь сырой промпт до качественного image prompt (молча, не спрашивая разрешения).
4. Если задача подходит под библиотеку ассетов, подключи лицо/шаблон/стиль из registry.
5. Если задача простая — запусти direct flow через runtime.
6. Если задача сложная — эскалируй в image-agent.

## Escalate when:
- нужно 3 и более вариантов
- нужна серия изображений
- пользователь просит итеративные доработки (несколько правок подряд)

## НЕ эскалировать:
- одно изображение + правки — это image-to-image напрямую
- 2+ фото одновременно — это тоже image-to-image напрямую (все в input_urls)

## Output rules:
- верни готовый файл, а не только промпт
- укажи путь сохранения
- если generation failed, скажи точную причину
- не говори "готово" пока файл физически не скачан и не проверен
```

---

## Формула качественного image prompt

Короткий запрос пользователя нужно превращать в полноценный визуальный промпт.
Всегда на английском (API лучше понимает).

**Структура:**
```
[subject + action/pose], [scene/context], [lighting], [style tags], [quality tags]
```

**Для YouTube thumbnail:**
```
[главный объект/персонаж], dramatic tech scene, neon blue accent lighting,
high contrast, vibrant saturated colors, bold text overlay space on [left/right],
youtube thumbnail style, photorealistic, 8K, ultra detailed, sharp focus
```

**Пример — "обложка про лимиты токенов Claude":**
```
a robot AI assistant surrounded by glowing digital token counters and data streams,
futuristic tech environment, dramatic neon blue and orange lighting, high contrast,
bold text space on right side, youtube thumbnail style, photorealistic, 8K,
ultra detailed, sharp focus, vibrant colors
```

**Пример — "обложка про живые навыки AI агентов":**
```
three AI agent icons (Claude, Gemini, Codex) connected by glowing neural network lines,
dynamic skill transfer visualization, deep space background, electric blue and purple tones,
high contrast, bold text space on left, youtube thumbnail composition,
8K, ultra detailed, cinematic lighting
```

---

## Как обрабатывать 2+ прикреплённых изображения

Если пользователь прислал несколько фото — все они идут в input_urls.
Телеграм-файлы сначала нужно превратить в публичные URL через Telegram API.

```bash
source .env

# Получить публичный URL для локального файла
get_telegram_url() {
  local FILE="$1"
  UPLOAD=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendPhoto" \
    -F "chat_id=${ALLOWED_CHAT_ID}" \
    -F "photo=@${FILE}" \
    -F "disable_notification=true")
  FILE_ID=$(echo "$UPLOAD" | python3 -c "import sys,json; d=json.load(sys.stdin); print(max(d['result']['photo'], key=lambda x: x['file_size'])['file_id'])")
  FILE_PATH=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getFile?file_id=${FILE_ID}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['file_path'])")
  echo "https://api.telegram.org/file/bot${TELEGRAM_BOT_TOKEN}/${FILE_PATH}"
}

# Для 2 файлов
URL1=$(get_telegram_url "/path/to/image1.jpg")
URL2=$(get_telegram_url "/path/to/image2.jpg")

# В промпте описать роль каждого изображения явно
PROMPT="first image: person/face to use as subject, second image: style/background reference — combine them into a youtube thumbnail with high contrast and bold text space"

# Запрос к API
curl -s -X POST "https://api.kie.ai/api/v1/jobs/createTask" \
  -H "Authorization: Bearer $KIE_AI_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"gpt-image-2-image-to-image\",\"input\":{\"prompt\":\"${PROMPT}\",\"input_urls\":[\"${URL1}\",\"${URL2}\"],\"aspect_ratio\":\"16:9\",\"resolution\":\"1K\"}}"
```

---

## Дополнительное правило

Если пользователь пишет что-то вроде:

```text
Сделай обложку для видео про Claude Code
```

это нельзя слать в API напрямую. Нужно сначала превратить это в полноценный visual prompt по формуле выше.
