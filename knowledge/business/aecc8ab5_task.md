# Personal AI Assistant Bot

## Tasks

- [x] Search existing n8n workflows via MCP
- [x] Review base workflow structure
- [x] Create implementation plan
- [x] Design workflow architecture (Mermaid diagram)
- [x] Create JSON workflow: `personal_ai_assistant_advanced.json`
  - [x] Telegram Trigger node
  - [x] AI Intent Router (Switch node with OpenAI)
  - [x] Chat branch (Supabase memory + OpenAI)
  - [x] Calendar branch (Google Calendar)
  - [x] Search branch (XMLRiver HTTP + XML parsing)
  - [x] Image branch (DALL-E)
  - [x] Fallback handler
- [x] Embed credentials inline
- [x] Write walkthrough
- [x] File created: personal_ai_assistant_advanced.json (20 nodes, v1.0.0)

## Requires manual n8n setup:
- [ ] Import personal_ai_assistant_advanced.json to n8n
- [ ] Replace OPENAI_API_KEY
- [ ] Replace TELEGRAM_CREDENTIAL_ID (create in n8n Credentials)
- [ ] Replace SUPABASE_PROJECT_URL + SUPABASE_ANON_KEY_PLACEHOLDER
- [ ] Replace GOOGLE_OAUTH_CREDENTIAL_ID
- [ ] Replace XMLRIVER_API_KEY
- [ ] Activate workflow
