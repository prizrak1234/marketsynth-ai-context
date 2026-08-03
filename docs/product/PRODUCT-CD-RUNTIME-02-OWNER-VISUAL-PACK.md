# PRODUCT-CD-RUNTIME-02 — Owner Visual Pack

**Task:** PRODUCT-CD-RUNTIME-02-OWNER-VISUAL-DELIVERY-RECOVERY  
**Status:** `automated_verified` for contour · `owner_visual_acceptance` / `owner_accepted` = **NOT SET**  
**live_image_provider_verified:** **NOT SET**

## Why this pack exists

Automated pytest / Playwright fixtures proved the Image Golden Path in a test contour.  
They did **not** prove the owner can find Text/Image in the live customer UI. Premature OWNER-ACCEPTED was rolled back.

## Entry URL (no manual guesswork)

Preferred (customer entry):

1. Open Workspace → Projects: `/workspace/projects`
2. Click **«Создать материалы»** on a project row  
   → `/workspace?project={project_id}&view=content_director`

Or with project already open:

1. `/workspace?project={project_id}`
2. Card **«Контент-директор»** → button **«Создать материалы»**

Direct deep link (fallback only):

`/workspace?project={YOUR_PROJECT_ID}&view=content_director`

Optional modes:

- Text: `...&view=content_director&mode=text`
- Image: `...&view=content_director&mode=image`

## What you should see

| Step | Expected |
|------|----------|
| Project with `?project=` | Card «Контент-директор» + CTA «Создать материалы» |
| Content Director home | Title «Контент-директор», actions «Создать текст» / «Создать изображение», recent materials list |
| Text tab | Brief form, variants, edit, approve |
| Image tab | Visual brief, create variants, candidates grid, preview, approve |
| After reload | Same approved material (open Text or Image tab if needed) |

Must **not** see: `owner_preview`, Content Factory as the entry, Launch Visuals, Video.

## Provider honesty

- Live paid OpenAI Images smoke is **not** claimed (`live_image_provider_verified = NOT SET`).
- Do **not** treat deterministic Playwright PNGs as commercial proof.
- If generation fails with provider config, that is an honest error — not a UI delivery failure.

## Owner check steps (5–7)

1. Login to Marketsynth (register/login as needed).
2. Open `/workspace/projects` and pick a real project (or open `/workspace?project=…`).
3. Click **«Создать материалы»** — do not paste `view=content_director` unless the button is missing (FAIL).
4. On Content Director home, confirm **Текст** and **Изображение**.
5. Open Image: fill brief → «Создать варианты» (only if you accept possible provider cost) **or** open an existing draft/approved row if present.
6. If you approved an image earlier: reload and confirm restore on Image tab.
7. Confirm no `owner_preview` / no Video.

## Actions not to click if avoiding paid spend

- Image «Создать варианты» when API is **not** in deterministic demo mode and OpenAI is configured.

## Known limitations

- Backend must expose `/projects/{id}/visual-director/*` (migration `20260802_0068`).
- Stale uvicorn without Image GP code will show Text but fail Image API.
- Mode defaults to Overview home; Text/Image require a click (or `mode=` query).
- Screenshots under `web/e2e-artifacts/content-director-owner-delivery/` support automated entry proof; owner must still confirm live browser.

## Screenshot checklist (live preview)

1. Project Command Center / project page with entry CTA  
2. Content Director home  
3. Text view  
4. Image request form  
5. Image candidates  
6. Approved image  
7. Cold restore  

## Status after automated recovery PASS

```
PRODUCT-CD-RUNTIME-02 = automated_verified
owner_visual_ready = YES   # only after Cursor automated entry E2E + env notes
owner_visual_acceptance = NOT SET
owner_accepted = NOT SET
```

Only the owner sets `owner_accepted` after the template below.
