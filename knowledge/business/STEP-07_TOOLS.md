# Step 7 - External Tools

Paste this prompt into Codex inside the `CodexClaw/` project.

## Goal

Connect practical external tools without hardcoding broken or unstable installers.

Base stack in this step:

1. Web search through Codex when available
2. n8n webhooks
3. Firecrawl via HTTP API
4. GitHub CLI
5. Optional Google Workspace integration through your own scripts or MCP tooling

## 1. Web search

If your Codex setup supports web search, enable it in the way your environment expects.

Do not claim "latest" information without search enabled.

Add this rule to `AGENTS.md`:

```markdown
## Web Search
- For latest news, prices, APIs, or unstable facts, use web search first when available
- If web search is not enabled, say that directly instead of guessing
```

## 2. n8n webhooks

Add webhook instructions to `AGENTS.md`:

```markdown
## n8n Webhooks
- Use webhook calls for background automations when an endpoint is configured
- Keep webhook URLs in `.env`, not in hardcoded prompts
```

Add these optional env vars:

```env
N8N_YOUTUBE_WEBHOOK=
N8N_CONTENT_WEBHOOK=
```

If present, the bot can call:

```bash
curl -X POST "$N8N_YOUTUBE_WEBHOOK" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://youtube.com/watch?v=..."}'
```

## 3. Firecrawl

Do not install a fake CLI. Use the API directly.

Add:

```env
FIRECRAWL_API_KEY=
```

Add helper logic or instructions to call:

```bash
curl -X POST https://api.firecrawl.dev/v1/scrape \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"PAGE_URL","formats":["markdown"]}'
```

Add to `AGENTS.md`:

```markdown
## Web Scraping
- Use Firecrawl API when `FIRECRAWL_API_KEY` is configured
- Save scraped outputs under `workspace/output/`
```

## 4. GitHub CLI

Install:

```bash
apt install -y gh
gh auth login
```

Add to `AGENTS.md`:

```markdown
## GitHub
- Use `gh` for repo, issue, and PR operations when authenticated
```

## 5. Google Workspace

Do not hardcode a specific npm package name here.

Instead:

- if you already use a working `gws` CLI or MCP server, document that exact tool
- otherwise skip Google Workspace in the base video and cover it in a separate advanced lesson

Add to `AGENTS.md`:

```markdown
## Google Workspace
- Use project-specific scripts or MCP tooling only when configured
- Do not assume a package name without verifying it in the current environment
```

## After Implementation

Verify:

1. GitHub CLI auth if configured
2. n8n webhook call if configured
3. Firecrawl API call if configured
4. `AGENTS.md` contains tool rules

Then restart:

```bash
npm run build
pm2 restart codexclaw
```

## Tell The User

```text
Tools are connected.

Configured:
- web search rules
- n8n hooks
- Firecrawl API
- GitHub CLI
- optional Google Workspace layer

Next step: STEP-08_SUPERVISOR.md
```
