# Step 3 - Formatting and Media Support

Paste this prompt into Codex inside the `CodexClaw/` project.

## Goal

Upgrade the Telegram bot to support:

1. Safe Telegram HTML formatting
2. Voice message transcription with Whisper
3. Photos with captions
4. Video notes
5. Document upload to `workspace/inbox/`

## Ask The User First

Collect:

1. `OPENAI_API_KEY`

Add it to `.env`.

## Important Rules

- Keep the queue from Step 2. Media handling must still run one Codex task at a time.
- Do not split Telegram messages after generating raw HTML. Create an HTML-safe chunker.
- Save every incoming file under `workspace/inbox/`
- Use current `openai` package, not an old pinned major

## Package Changes

Add:

```json
"openai": "^6.34.0"
```

Then run:

```bash
npm install
```

## Files To Add

Create:

- `src/format.ts`
- `src/files.ts`
- `src/whisper.ts`

Update:

- `src/bot.ts`
- `.env`

## Implementation Requirements

### 1. Telegram HTML formatting

Create `formatTelegramHTML(text: string): string` in `src/format.ts`.

Requirements:

- Escape plain text safely
- Support:
  - `**bold**`
  - `` `inline code` ``
  - fenced code blocks
- If formatting is ambiguous, prefer plain escaped text over broken HTML
- Create `splitTelegramHTML(text: string, maxLen = 4000): string[]`
- Never cut inside `<pre>`, `<code>`, or another HTML tag

### 2. Telegram file download helper

Create `src/files.ts` with helpers that:

- resolve Telegram file path via `ctx.getFile()`
- download the binary to disk
- save to `workspace/inbox/`
- generate safe filenames
- preserve original file extension when possible
- avoid overwriting existing files

### 3. Whisper transcription

Create `src/whisper.ts` with:

```ts
transcribeAudio(filePath: string): Promise<string>
```

Requirements:

- Use `openai` package
- Read `OPENAI_API_KEY` from `.env`
- Use Whisper transcription API
- Return plain transcript text
- Throw a readable error if transcription fails

### 4. Text replies

Update `src/bot.ts` so text replies:

- run through `formatTelegramHTML`
- use `parse_mode: 'HTML'`
- send with HTML-safe chunking

### 5. Voice and audio

Handle:

- `message:voice`
- `message:audio`

Flow:

1. Download the file to `workspace/inbox/`
2. Transcribe it
3. Send this to Codex as user input:

```text
[Voice transcribed]: <transcript>
```

4. Return formatted Telegram HTML

### 6. Photos

Handle `message:photo`.

Flow:

1. Download the highest resolution photo
2. Save it to `workspace/inbox/`
3. If a caption exists, send Codex:

```text
User sent an image saved at: <path>
Caption: <caption>
```

4. If no caption exists, send Codex:

```text
User sent an image saved at: <path>
Describe what is visible, extract any text, then ask one short clarifying question if needed.
```

### 7. Video notes

Handle `message:video_note`.

Flow:

1. Download to `workspace/inbox/`
2. Send Codex:

```text
User sent a video note saved at: <path>
Describe the next best action.
```

### 8. Documents

Handle `message:document`.

Flow:

1. Download to `workspace/inbox/`
2. Save with a collision-safe filename
3. Send Codex:

```text
User sent a file saved at: <path>
Read it if possible and continue with the likely task. Ask one short clarifying question only if needed.
```

## After Implementation

Run:

```bash
npm run build
pm2 restart codexclaw
```

Test:

1. Plain text
2. Voice message
3. Photo with caption
4. Video note
5. Document

## Tell The User

```text
Media support added.

Test in Telegram:
1. Text
2. Voice
3. Photo
4. File

Next step: STEP-04_MEMORY.md
```
