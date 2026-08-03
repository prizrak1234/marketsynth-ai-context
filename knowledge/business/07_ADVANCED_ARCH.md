---
tags: [gemini, subagents, compaction, topic-shift, architecture]
date: 2026-04-18
type: note
---

# Шаг 7: Продвинутая архитектура

Делаем агента умнее: compaction counter, определение смены темы, adversarial self-review, субагенты.

## Prerequisites

- Шаги 4-6 выполнены
- SQLite с таблицей `sessions` (из шага 6)
- `agents/` папка существует

## 1. Compaction counter

Каждый вызов `/compact` увеличивает счётчик. При достижении порога 3 — предупреждение пользователю о том, что лучше начать новую сессию.

Промпт:

```text
Add compaction counter to GeminiClaw.

In the sessions table, compact_count and last_compact_at are already defined.

Implement /compact command in src/bot.ts:
1. Increment sessions.compact_count for this chat_id
2. Set last_compact_at = unixepoch()
3. Run gemini prompt: "Summarize the current session context into 5-7 bullet points. Be concise. Output only the bullets."
4. Save the result to store/geminiclaw.db memories table with scope='session', topic_key='compact_summary', superseding any previous compact_summary
5. Reply to user with the summary
6. If compact_count >= 3: append warning to reply:
   "Сессия сжималась 3+ раза. Качество контекста снижается. Рекомендую /newchat для свежего старта."
```

## 2. Topic shift detection

Определяем смену темы по Jaccard similarity между ключевыми словами текущего сообщения и предыдущих 5 сообщений. При сходстве ниже 15% и 5+ сообщений в сессии — показываем подсказку.

```text
Add topic shift detection to src/bot.ts.

Implement after the message is received, before running gemini:

function extractKeywords(text: string): Set<string>
- Lowercase the text
- Split into words
- Remove stopwords (и, в, на, с, к, по, для, что, как, это, не, я, ты, он, она)
- Remove words shorter than 4 characters
- Return Set of remaining words

function jaccardSimilarity(a: Set<string>, b: Set<string>): number
- Returns |intersection| / |union|
- Return 1.0 if both sets are empty

Store last 5 message keyword sets per chat_id in memory (Map<string, Set<string>[]>).

After extracting keywords from current message:
1. If fewer than 5 previous messages stored: just store and continue
2. Compute average Jaccard similarity against all stored sets
3. If similarity < 0.15:
   - Append hint to the gemini reply (do not interrupt the prompt execution):
     "\n\n---\nНовая тема? Лучше /newchat для чистого контекста."
4. Update stored keyword sets (keep last 5)
```

## 3. Adversarial self-review

Для ответов с глаголами действий (сделаю, запущу, создам, обновлю, удалю, перенесу и т.д.) автоматически перепроверяем:

```text
Add adversarial self-review for action responses.

In the gemini response pipeline:

function hasActionVerbs(text: string): boolean
- Check if text contains any of: сделаю, запущу, создам, обновлю, удалю, перенесу,
  установлю, настрою, добавлю, уберу, перепишу, will do, will create, will run,
  will update, will delete, will install, will configure
- Case-insensitive match

If hasActionVerbs(response) is true AND response length > 200 chars:
1. Run a second gemini call (same session context):
   "Review your previous response for: 1) missing steps, 2) incorrect commands, 3) side effects not mentioned. Reply ONLY with: PASS or ISSUES: [list]"
2. If second call returns ISSUES: prepend to user reply:
   "Review: [ISSUES]\n\n---\n"
3. If second call returns PASS: send original reply unchanged

Keep self-review optional — add env var ENABLE_SELF_REVIEW=true to activate.
Default: disabled (to save API quota).
```

## 4. Субагенты

Субагенты — это отдельные markdown-файлы в `agents/` с инструкциями для специализированных задач.

```text
Create subagent architecture in GeminiClaw.

## Folder structure
agents/
  youtube-analyzer.md
  content-writer.md
  obsidian-librarian.md

## agents/youtube-analyzer.md
```
# YouTube Analyzer Agent

## Role
Analyze YouTube videos: extract key points, create structured notes.

## Workflow
1. Get video URL from user
2. Fetch transcript if available
3. Produce: summary (3-5 sentences), key points, takeaways, action ideas
4. Save note to workspace/output/notes/YouTube/YYYY-MM-DD_title.md
5. Also save to ~/obsidian-vault/YouTube/ if vault exists

## Output Format
Use frontmatter: title, url, channel, date, tags: [youtube]
Include: ## Summary, ## Key Points, ## Takeaways, ## Action Ideas
```

## agents/obsidian-librarian.md
```
# Obsidian Librarian Agent

## Role
Search, cross-link, and organize notes in ~/obsidian-vault/.

## Tools
- grep -ril "QUERY" ~/obsidian-vault/ --include="*.md"
- cat FILE to read note content
- Write/append to create or update notes

## Rules
- Add wikilinks [[note-name]] when referencing other notes
- Use frontmatter with date, tags, type
- Never delete notes — move to Archive/ if outdated
```

## Update GEMINI.md
- **Silent Execution:** Subagents must follow the core Silent Execution rule from GEMINI.md.
Add:
```
## Subagents
- Specialized agents are in agents/ folder
- YouTube URL → use agents/youtube-analyzer.md context
- Obsidian operations → use agents/obsidian-librarian.md context
- Load agent file content into prompt context when task matches agent role
```

Run after files are created:
```bash
npm run build
pm2 restart geminiclaw
```
```

## Troubleshooting

**Topic shift hint появляется слишком часто**
Увеличь порог с 0.15 до 0.10, или увеличь минимальное количество сообщений с 5 до 8.

**Self-review съедает много токенов**
По умолчанию отключён. Включи только если нужна повышенная точность: `ENABLE_SELF_REVIEW=true` в `.env`.

**Субагент не работает**
Субагент — это просто контекстный файл, который читается в промпт. Убедись, что бот загружает `agents/AGENTNAME.md` перед вызовом gemini для соответствующих задач.

## После этого шага

- [ ] /compact увеличивает счётчик и при 3+ показывает предупреждение
- [ ] Смена темы после 5 сообщений вызывает подсказку
- [ ] `agents/youtube-analyzer.md` и `agents/obsidian-librarian.md` созданы
- [ ] ENABLE_SELF_REVIEW=true работает (опционально)

Следующий шаг: [[08_GWS_SEARCH]]
