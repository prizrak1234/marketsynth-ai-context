# Step 1 - Install Codex CLI on VDS

Paste commands into your server terminal over SSH.

## Prerequisites

You need:
1. Ubuntu 22.04+ or Debian 12+ on a VPS/VDS
2. SSH access
3. An active OpenAI/Codex-compatible login method:
   - ChatGPT account supported by Codex login flow, or
   - `OPENAI_API_KEY`

## Commands

### 1. Update the server
```bash
apt update && apt upgrade -y
```

### 2. Install Node.js 22
```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs
node -v
npm -v
```

### 3. Install Codex CLI and PM2
```bash
npm install -g @openai/codex pm2
codex --version
pm2 -v
```

### 4. Login to Codex

Option A - login with ChatGPT/OpenAI account:
```bash
codex login
```

Option B - login with API key:
```bash
printenv OPENAI_API_KEY | codex login --with-api-key
```

### 5. Verify non-interactive execution
```bash
mkdir -p ~/codex-smoke-test
cd ~/codex-smoke-test
printf '# Test\n\nAlways answer in one short line.\n' > AGENTS.md
codex exec --skip-git-repo-check --full-auto "Say hello in one word"
```

If you get a short answer back, Codex is installed and working.

## Notes

- `codex exec` is the reliable check for a server tutorial. It avoids dropping into the interactive UI.
- `AGENTS.md` is the standard project instruction file. We will use it in the next steps.

## Troubleshooting

- `codex: command not found` -> run `npm install -g @openai/codex` again, then open a new shell
- Login fails -> try `codex login` again or use `OPENAI_API_KEY`
- Node version is not `v22.x` -> reinstall Node from NodeSource
- The verify command hangs -> confirm the server has outbound internet access

## Next Step

Proceed to `STEP-02_TELEGRAM_BRIDGE.md`.
