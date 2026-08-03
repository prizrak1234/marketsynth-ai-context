
![[ChatGPT Image 6 апр. 2026 г., 13_20_15.png]]

---

# Бесплатный Claude Code — чек-лист зрителя

> **Главная идея:** Claude Code — это не AI. Это оболочка. Внутрь можно вставить любую модель.

---

## ✅ Чек-лист: Установка Claude Code

- [ ] Установить Claude Code — выбери свой способ:

**macOS / Linux / WSL:**
```bash
curl -fsSL https://claude.ai/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://claude.ai/install.ps1 | iex
```

**Через npm (Node.js 18+):**
```bash
npm install -g @anthropic-ai/claude-code
```

- [ ] Запустить в папке проекта:

```bash
claude
```

- [ ] При первом запуске — авторизоваться через браузер

> **Примечание:** по умолчанию Claude Code использует платный Anthropic API. Дальше в этом чек-листе — как это изменить.

---

## 🧠 Как это устроено (понять один раз)

```
Claude Code (интерфейс + оркестрация)
↓
LLM — Claude / Qwen / Gemma / DeepSeek / Llama
↓
Инструменты — файлы, терминал, API
```

**Claude Code = менеджер. Модели = исполнители.**

Ты платишь не за интерфейс. Ты платишь за интеллект модели внутри.

---

## ⚡ Ключевой инсайт

> **Ты платишь не за качество. Ты платишь за время.**

Frontier модели (Claude, GPT) — интеллект сегодняшнего дня.
Open модели (Qwen, Gemma, DeepSeek) — интеллект ~6 месяцев назад.

Для большинства задач «вчерашнего интеллекта» достаточно.

---

## ✅ Чек-лист: Способ 1 — OpenRouter (облако, быстрый старт)

- [ ] Зарегистрироваться на [openrouter.ai](https://openrouter.ai)
- [ ] Получить API-ключ в разделе Keys
- [ ] Создать файл `.claude/settings.local.json` в папке проекта и вставить:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://openrouter.ai/api",
    "ANTHROPIC_AUTH_TOKEN": "<your-openrouter-api-key>",
    "ANTHROPIC_API_KEY": ""
  }
}
```

- [ ] Или задать через переменные окружения (`~/.zshrc` / `~/.bashrc`):

```bash
export OPENROUTER_API_KEY="<your-openrouter-api-key>"
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_AUTH_TOKEN="$OPENROUTER_API_KEY"
export ANTHROPIC_API_KEY=""
```

- [ ] Выбрать модели (опционально — по умолчанию будет бесплатный роутер):

```bash
export ANTHROPIC_DEFAULT_SONNET_MODEL="qwen/qwen3.6-plus:free"
export ANTHROPIC_DEFAULT_OPUS_MODEL="qwen/qwen3.6-plus:free"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="qwen/qwen3.6-plus:free"
export CLAUDE_CODE_SUBAGENT_MODEL="qwen/qwen3.6-plus:free"
```

- [ ] Убедиться что `ANTHROPIC_API_KEY=""` — иначе Claude Code тихо переключится на платный Anthropic
- [ ] Запустить `claude` и проверить командой `/status` какая модель активна

> **Источник:** [openrouter.ai/docs/guides/coding-agents/claude-code-integration](https://openrouter.ai/docs/guides/coding-agents/claude-code-integration)

![[Снимок экрана 2026-04-06 в 12.30.19.png]]

---

## ⚠️ Главная ловушка OpenRouter

> Если `ANTHROPIC_API_KEY` не пустой — Claude Code начнёт дёргать Anthropic.
> Ты будешь думать «работаю бесплатно», а деньги уже списываются.

**Правило:** всегда логируй, какая модель реально вызвалась. В сессии — команда `/status`.

---

## ✅ Чек-лист: Способ 2 — Ollama (локально, полная приватность)

- [ ] Установить [Ollama](https://ollama.ai)
- [ ] Скачать модель:

```bash
ollama pull llama3
# или
ollama pull qwen
# или
ollama pull mistral
```

- [ ] Запустить локальный сервер:

```bash
ollama serve
# → http://localhost:11434
```

- [ ] Подключить Claude Code через прокси (Ollama не совместим с Anthropic API напрямую — нужен адаптер)

![[Снимок экрана 2026-04-06 в 12.45.20.png]]

---

## 📊 Где работает — где нет

| Задача | Подходит бесплатная модель? |
|---|---|
| Генерация текста | ✅ да |
| Суммаризация | ✅ да |
| Парсинг и форматирование | ✅ да |
| Классификация | ✅ да |
| Простые агентные задачи | ✅ да |
| Сложные multi-step агенты | ❌ нет |
| Tool calling (стабильный) | ❌ ненадёжно |
| Стратегические решения | ❌ нет |

---

## 🏗️ Архитектура (как использовать вместе)

```
Claude (premium)     → критические задачи, агенты
OpenRouter (mid)     → повседневные задачи, генерация
Ollama / Local       → массовые задачи, парсинг, форматирование
```

**Формула:**
```
Cloud (OpenRouter) → платишь деньгами
Local (Ollama)     → платишь железом
```

---

## 🆕 Gemma 4 — свежий сигнал рынка (апрель 2026)

Google выпустила Gemma 4 — open модель, которая:

- Работает **локально** — на ноутбуке и даже смартфоне
- Не требует облака и API
- Построена на той же базе, что Gemini — но бесплатно

| | Gemini | Gemma 4 |
|---|---|---|
| Тип | закрытая | open |
| Где работает | облако | локально |
| Цена | $$$ | бесплатно |
| Контроль | нет | полный |

> Gemini — это SaaS AI. Gemma — это AI, которым ты владеешь.

**Это подтверждение тренда:** open модели догоняют frontier. Медленно, но факт.

---

## 📈 Где смотреть актуальные сравнения моделей

| Ресурс | Что там |
|---|---|
| [lmarena.ai](https://lmarena.ai/leaderboard) | Голосовой лидерборд — люди сравнивают ответы вживую |
| [artificialanalysis.ai](https://artificialanalysis.ai/models) | Цена / скорость / интеллект — лучшие графики |
| [vellum.ai/llm-leaderboard](https://www.vellum.ai/llm-leaderboard) | Фильтр по задачам: coding, reasoning, agents |
| [llm-stats.com](https://llm-stats.com) | Цифры: контекст, стоимость, accuracy |
| [openrouter.ai/rankings](https://openrouter.ai/rankings) | Что реально используют (не лучшие — а выгодные) |

> Все лидерборды дают разные результаты — потому что нет «лучшей» модели. Есть лучшая модель под конкретную задачу.

---

## 💬 Формулировки (можно использовать)

> «Я не гонюсь за самым умным AI. Я использую самый дешёвый, который справляется с задачей.»

> «Ты платишь не за качество — ты платишь за актуальность.»

> «Побеждает не тот, у кого лучший AI. А тот, кто правильно распределяет задачи.»
