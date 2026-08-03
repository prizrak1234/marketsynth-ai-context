# Шаг 2: Runtime-структура и исполнительный слой

Создай или адаптируй в проекте такую структуру:

```text
src/image/
  router.ts
  prompt-builder.ts
  provider-kie.ts
  asset-registry.ts
  output.ts

workspace/output/images/
workspace/library/image-assets/
  registry.json
  faces/
  templates/
  styles/
  refs/
```

## Что должен делать каждый файл

### `src/image/router.ts`

- принимает задачу на генерацию
- определяет тип: simple или complex
- решает, идти напрямую или эскалировать в image-agent

### `src/image/prompt-builder.ts`

- принимает короткий запрос пользователя
- достраивает его до production prompt (цель: 300-800 символов, API max 20K)
- добавляет сцену, композицию, стиль, свет, цвет, формат
- переводит итоговый prompt на английский

### `src/image/provider-kie.ts`

- вызывает Kie.ai API
- поддерживает text-to-image и image-to-image
- polling статуса каждые 5 сек с таймаутом 3 мин (36 попыток)
- на успехе возвращает итоговый URL результата

### `src/image/asset-registry.ts`

- читает `workspace/library/image-assets/registry.json`
- выбирает лицо, шаблон, стиль и референсы
- отдает подходящий набор ассетов под тип задачи

### `src/image/output.ts`

- создает имя файла
- скачивает изображение
- сохраняет в `workspace/output/images/`
- проверяет, что файл существует и не пустой

---

## Как добавить API-ключ kie.ai

1. Зарегистрируйся на [kie.ai](https://kie.ai)
2. Личный кабинет → API Keys → создать ключ
3. Добавь в `.env` проекта:

```bash
KIE_AI_KEY=твой_ключ_здесь
```

**ВАЖНО:** переменная называется `KIE_AI_KEY`, не `KIE_API_KEY`. Именно так.

4. Проверить что ключ читается:

```bash
source .env && echo $KIE_AI_KEY
```

Должен вывести твой ключ. Если пусто — проверь имя переменной.

---

## Рабочие curl-команды (проверены на практике)

### Text-to-image (дефолтная модель)

```bash
source .env
TASK=$(curl -s -X POST "https://api.kie.ai/api/v1/jobs/createTask" \
  -H "Authorization: Bearer $KIE_AI_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-image-2-text-to-image","input":{"prompt":"ENHANCED_PROMPT","aspect_ratio":"16:9","resolution":"1K"}}')
TASK_ID=$(echo $TASK | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['taskId'])")
echo "Task ID: $TASK_ID"
```

### Text-to-image быстрый (nano-banana-2)

```bash
source .env
TASK=$(curl -s -X POST "https://api.kie.ai/api/v1/jobs/createTask" \
  -H "Authorization: Bearer $KIE_AI_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"nano-banana-2","input":{"prompt":"ENHANCED_PROMPT","aspect_ratio":"16:9","resolution":"1K","output_format":"jpg"}}')
TASK_ID=$(echo $TASK | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['taskId'])")
```

### Image-to-image (source image → трансформация)

```bash
source .env
TASK=$(curl -s -X POST "https://api.kie.ai/api/v1/jobs/createTask" \
  -H "Authorization: Bearer $KIE_AI_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-image-2-image-to-image","input":{"prompt":"ENHANCED_PROMPT","input_urls":["PUBLIC_URL_OF_IMAGE"],"aspect_ratio":"16:9","resolution":"1K"}}')
TASK_ID=$(echo $TASK | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['taskId'])")
```

### Polling статуса (с таймаутом 3 мин)

```bash
MAX_TRIES=36  # 36 × 5s = 3 min
TRIES=0
while [ $TRIES -lt $MAX_TRIES ]; do
  RESULT=$(curl -s "https://api.kie.ai/api/v1/jobs/recordInfo?taskId=$TASK_ID" \
    -H "Authorization: Bearer $KIE_AI_KEY")
  STATE=$(echo $RESULT | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['state'])")
  if [ "$STATE" = "success" ]; then
    IMG_URL=$(echo $RESULT | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.loads(d['data']['resultJson'])['resultUrls'][0])")
    echo "Done: $IMG_URL"
    break
  elif [ "$STATE" = "failed" ]; then
    echo "Generation failed"
    break
  fi
  TRIES=$((TRIES+1))
  sleep 5
done
[ $TRIES -eq $MAX_TRIES ] && echo "Timeout after 3 min"
```

### Скачать и сохранить

```bash
SLUG=$(echo "PROMPT" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | cut -c1-40)
FILENAME="workspace/output/images/$(date +%Y-%m-%d)-${SLUG}.jpg"
mkdir -p workspace/output/images
curl -sL "$IMG_URL" -o "$FILENAME"
ls -lh "$FILENAME"  # обязательная проверка
```

### Отправить в Telegram

```bash
source .env

# sendPhoto — показывает встроенный превью (для проверки)
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendPhoto" \
  -F "chat_id=${ALLOWED_CHAT_ID}" \
  -F "photo=@${FILENAME}" \
  -F "caption=Готово: ${FILENAME}"

# sendDocument — без сжатия Telegram (для финальных обложек, если важно качество)
# curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendDocument" \
#   -F "chat_id=${ALLOWED_CHAT_ID}" \
#   -F "document=@${FILENAME}" \
#   -F "caption=Готово: ${FILENAME}"
```

Telegram сжимает sendPhoto если файл >~2MB. Для публикации использовать sendDocument.

---

## Лайфхак: локальный файл → публичный URL

`gpt-image-2-image-to-image` требует публичный URL, не локальный путь.
Самый простой способ — загрузить файл через Telegram API:

```bash
source .env

UPLOAD=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendPhoto" \
  -F "chat_id=${ALLOWED_CHAT_ID}" \
  -F "photo=@/путь/к/файлу.jpg" \
  -F "disable_notification=true")

FILE_ID=$(echo "$UPLOAD" | python3 -c "import sys,json; d=json.load(sys.stdin); print(max(d['result']['photo'], key=lambda x: x['file_size'])['file_id'])")

FILE_PATH=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getFile?file_id=${FILE_ID}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['file_path'])")

PUBLIC_URL="https://api.telegram.org/file/bot${TELEGRAM_BOT_TOKEN}/${FILE_PATH}"
echo "$PUBLIC_URL"
```

Этот URL работает как input в `input_urls` для image-to-image.

---

## Ограничения API (из практики)

| Ситуация | Результат |
|---|---|
| `aspect_ratio: "auto"` + `resolution: "2K"` | Ошибка 422 — только `1K` при auto |
| `aspect_ratio: "1:1"` + `resolution: "4K"` | Ошибка 422 — нельзя 4K с 1:1 |
| `gpt-image-2-image-to-image` без `input_urls` | Ошибка 422 — обязательный параметр |
| Локальный путь в `input_urls` | Не работает — нужен публичный URL |

## Время генерации (реальные данные)

| Модель | Время |
|---|---|
| `gpt-image-2-text-to-image` | 60-120 секунд |
| `nano-banana-2` | 25-40 секунд |
| `gpt-image-2-image-to-image` | 60-120 секунд |

Не паниковать если нет ответа 1-2 минуты — это нормально для gpt-image-2.
