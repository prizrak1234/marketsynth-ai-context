---
tags: [gemini, multimodal, vision, audio, media]
date: 2026-04-18
type: note
---

# Шаг 5: Мультимодальность (голос, кружочки, фото, документы)

Gemini CLI поддерживает нативную передачу файлов через синтаксис `@`. Никаких внешних API — Whisper, Vision и т.д. — не нужно.

## Prerequisites

- Шаг 4 выполнен (бот работает и отвечает на текст)
- `workspace/inbox/` создана

## Синтаксис `@` для файлов

```bash
# Анализ изображения
gemini "@workspace/inbox/photo.jpg Что на фото?"

# Транскрипция и анализ аудио
gemini "@workspace/inbox/voice.ogg Транскрибируй и кратко ответь"

# Анализ видео
gemini "@workspace/inbox/video.mp4 Опиши что происходит"

# Документ
gemini "@workspace/inbox/report.pdf Выдели ключевые пункты"
```

Gemini обрабатывает файл нативно — передаёт его напрямую в модель вместе с промптом.

## Промпт для Gemini CLI

Находясь в `~/GeminiClaw`, отправь:

```text
Upgrade the Telegram bot to handle all media types natively using Gemini CLI's @ file syntax.

## Core principle
Gemini CLI handles all media natively — NO external APIs (no Whisper, no Vision API, no OCR tools).
For every media type: download file to workspace/inbox/, then pass to gemini using "@path/to/file PROMPT".

## Update src/bot.ts

### voice messages (message:voice)
1. Download OGG file to workspace/inbox/voice_TIMESTAMP.ogg
2. Run: gemini "@path/to/file [Voice message] — транскрибируй и ответь"
3. Return Gemini's response

### video_note messages (message:video_note) — кружочки
1. Download MP4 to workspace/inbox/vidnote_TIMESTAMP.mp4
2. Run: gemini "@path/to/file [Видео-сообщение] — посмотри и ответь"
3. Return Gemini's response

### photo messages (message:photo)
1. Download highest-resolution photo to workspace/inbox/photo_TIMESTAMP.jpg
2. If caption exists: gemini "@path/to/file [Фото] Caption: USER_CAPTION"
3. If no caption: gemini "@path/to/file [Фото] Опиши что видишь. Если есть текст — прочитай его. Задай один уточняющий вопрос если нужно."

### document messages (message:document)
1. Download to workspace/inbox/ORIGINAL_FILENAME (with collision-safe suffix if file exists)
2. Run: gemini "@path/to/file [Файл: FILENAME] Прочитай если возможно. Продолжи с наиболее вероятной задачей. Задай один короткий вопрос только если необходимо."

### audio messages (message:audio)
Same flow as voice: download, pass with @ prefix.

## File download helper (src/files.ts)
Create helper functions:
- downloadTelegramFile(ctx, fileId: string, filename: string): Promise<string>
  - Use ctx.api.getFile(fileId) to get file path
  - Download binary via fetch to workspace/inbox/
  - Return absolute path to saved file
  - If file already exists, add _1, _2 suffix before extension
- cleanOldInboxFiles(): void
  - Delete files in workspace/inbox/ older than 24 hours
  - Call this once on bot startup and then every hour via setInterval

## Typing indicator
Keep existing typing indicator for all media handlers.
Media processing can take 10-30 seconds for video — the indicator is important.

## Error handling
If gemini fails on a media file (unsupported format, file too large):
- Reply: "Не смог обработать файл: [reason]. Попробуй другой формат."

## Supported formats reference
- Images: jpg, jpeg, png, gif, webp, heic
- Audio: mp3, wav, ogg, flac, aac, m4a
- Video: mp4, mov, avi, mkv, webm
- Documents: pdf, txt, md, csv, json, html, xml, and code files
```

## Очистка inbox

Временные файлы накапливаются. Добавь в инициализацию бота:

```typescript
// Очищать inbox при старте и каждый час
cleanOldInboxFiles()
setInterval(cleanOldInboxFiles, 60 * 60 * 1000)
```

Логика очистки:
```typescript
function cleanOldInboxFiles() {
  const cutoff = Date.now() - 24 * 60 * 60 * 1000
  const files = fs.readdirSync(inboxDir)
  for (const f of files) {
    if (f === '.gitkeep') continue
    const stat = fs.statSync(path.join(inboxDir, f))
    if (stat.mtimeMs < cutoff) {
      fs.unlinkSync(path.join(inboxDir, f))
    }
  }
}
```

## Команды после генерации

```bash
npm run build
pm2 restart geminiclaw
```

## Troubleshooting

**`Error: getFile failed`**
Файл Telegram хранится 24 часа. Если пользователь переслал старое сообщение — файл мог уже не существовать.

**Gemini возвращает ошибку на видео**
Файлы больше 20MB могут не работать с CLI. Для длинного видео лучше передавать только аудио-дорожку. Выведи пользователю понятное сообщение об ограничении.

**Кружочки (video_note) не скачиваются**
`video_note` использует `ctx.message.video_note.file_id`, не `video`. Убедись, что обработчик слушает `message:video_note`.

## После этого шага

- [ ] Голосовое сообщение транскрибируется и получает ответ
- [ ] Кружочек (video_note) обрабатывается
- [ ] Фото с подписью и без подписи работают
- [ ] Документ (PDF, TXT) обрабатывается
- [ ] `workspace/inbox/` не засоряется (очистка работает)

Следующий шаг: [[06_HYBRID_MEMORY]]
