# BotFazer — Tester feedback template

Copy this form for each demo session. One file per session (e.g. `feedback/2026-06-02-tester-name.md`) or paste into your issue tracker.

**Goal:** Capture *confusion, trust, and workflow fit* — not feature wishlists only.

---

## Session metadata

| Field | Value |
|-------|--------|
| **Date** | |
| **Tester name / role** | (e.g. PM, content lead, engineer) |
| **Demo version** | Git commit or tag: |
| **Presenter** | |
| **Duration** | min |
| **Setup** | Fresh seed / existing DB / other: |

---

## 1. First impression (1–5)

| Question | 1 = poor · 5 = excellent | Notes |
|----------|--------------------------|-------|
| Could you follow the story without Swagger? | | |
| Did the UI feel like a coherent product (not a dev panel)? | | |
| Would you trust this for a real campaign (with caveats)? | | |

**One sentence — what is BotFazer ops UI to you?**



---

## 2. Flow clarity (per step)

Rate **clarity** (1–5) and note **first confusion** (one phrase max).

| Step | Clarity 1–5 | First confusion or “aha” |
|------|-------------|-------------------------|
| Dashboard metrics | | |
| Campaigns list | | |
| Campaign detail (overview / workflow) | | |
| Plan draft + generate assets | | |
| Review queue | | |
| Approve / archive | | |
| Asset editor (draft / approved) | | |
| Schedule publication | | |
| Publication calendar (reschedule / cancel) | | |
| Channels settings | | |

**Which step would you drop or reorder?**



---

## 3. Safety & trust

| Statement | Agree? (Y / N / Unsure) | Comment |
|-----------|-------------------------|---------|
| It was clear that **agents do not approve** content | | |
| It was clear that **agents do not publish** | | |
| **Archive** actions felt appropriately guarded (confirm) | | |
| **No accidental publish now** — scheduling requires future time | | |
| **Bot token not in UI** felt correct | | |
| Review queue did not expose full post body unnecessarily | | |

**What would make you nervous using this on a real campaign?**



---

## 4. Gaps vs your job (honest)

**What you expected but did not see:**



**What felt unnecessary or noisy:**



**Top 3 missing capabilities (ranked):**

1.  
2.  
3.  

**Top 3 things to keep unchanged:**

1.  
2.  
3.  

---

## 5. Bugs and friction

| Severity | Screen | What happened | Expected |
|----------|--------|---------------|----------|
| blocker / major / minor | | | |
| | | | |
| | | | |

**Environment issues?** (API key, project id, CORS, blank page)



---

## 6. Comparison & recommendation

**Compared to your current process (spreadsheets, Notion, other tools):**



**Would you run the next campaign step in this UI if we fixed your #1 gap?** (Y / N / Maybe)



**Who else should see this demo?** (role)



---

## 7. Open feedback

Anything else — including ideas we should **not** build:



---

## For presenter (internal only)

| Item | |
|------|---|
| Demo script followed? | Y / N |
| Seed issues? | |
| Deviations from [ui_demo_script.md](./ui_demo_script.md) | |
| Follow-up action | |

---

## Analysis hook (after 10–15 sessions)

Aggregate in a spreadsheet:

- Median clarity per step  
- Count of “trust nervous” themes  
- Blockers vs nice-to-haves  
- Repeat mentions → candidate for UI.13 events or next UI phase  

Do **not** prioritize analytics (UI.13) until at least **5** completed feedback forms exist.
