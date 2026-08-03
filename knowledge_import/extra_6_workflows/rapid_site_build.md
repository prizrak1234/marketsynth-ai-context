---
description: Rapidly build a high-quality website using the Golden Layout and Premium Reset templates.
---

# Rapid Site Build Workflow "The Master Prompt"

Use this workflow to instantly scaffold a professional website project.

## Step 1: Initialize Project Structure
1.  Create a new directory for the project (if not already inside one).
2.  Copy `.agent/skills/premium_web_development/templates/golden-layout.html` to `index.html`.
3.  Copy `.agent/skills/premium_web_development/templates/premium-reset.css` to `style.css`.
4.  Create an empty `script.js` file.

## Step 2: Customize Content
1.  **Read** `rules/03-content-guidelines.md` to understand the tone.
2.  **Replace** placeholders in `index.html` (e.g., `[Page Title]`, `[Headline]`) with specific content relevant to the user's request.
3.  **Ensure** the copy is punchy, specific, and "human".

## Step 3: Apply Aesthetics
1.  **Read** `rules/00-basics.md` to select a font pair.
2.  **Update** `style.css` variables:
    - Set `--font-heading` and `--font-body`.
    - Set `--color-primary`, `--color-secondary`, and `--color-accent` based on the user's preference or a modern palette.

## Step 4: Verification
1.  Open `index.html` in a browser to verify structure and basic styling.
2.  Check for any broken links or missing assets.
