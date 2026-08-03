"""
NanoBanana — Dual Modal Endpoint
1. generate_image: KIE AI nano-banana-pro image generation with polling
2. generate_nano_banana: 3-step Claude agentic chain for YouTube content
"""

import modal
from fastapi import Header, HTTPException

app = modal.App("nano-banana")

image = modal.Image.debian_slim().pip_install("anthropic", "fastapi", "httpx")


# ─── Shared auth helper ───


def verify_bearer_token(authorization: str):
    """Validate Bearer token against API_AUTH_TOKEN secret."""
    import os

    expected_token = os.environ.get("API_AUTH_TOKEN")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid authorization header"
        )
    token = authorization.replace("Bearer ", "", 1)
    if token != expected_token:
        raise HTTPException(status_code=403, detail="Invalid authentication token")


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 1: Image Generation (KIE AI nano-banana-pro)
# ═══════════════════════════════════════════════════════════════════════════════

POLL_INTERVAL = 10  # seconds between polls
INITIAL_WAIT = 25  # seconds before first poll (matches n8n workflow)
MAX_POLL_ATTEMPTS = 20  # ~225s total max wait


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("api-auth-token"),
        modal.Secret.from_name("kie-ai-key"),
    ],
    timeout=300,
)
@modal.fastapi_endpoint(method="POST")
def generate_image(data: dict, authorization: str = Header(None)) -> dict:
    """
    Generate an image using KIE AI's nano-banana-pro model.

    Input:  {"prompt": "...", "aspect_ratio": "16:9", "resolution": "4K", "output_format": "png"}
    Output: {"image_url": "https://...", "task_id": "..."}
    """
    import json
    import os
    import time

    import httpx

    verify_bearer_token(authorization)

    prompt = data.get("prompt")
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing 'prompt' in request body")

    aspect_ratio = data.get("aspect_ratio", "16:9")
    resolution = data.get("resolution", "4K")
    output_format = data.get("output_format", "png")

    kie_api_key = os.environ["KIE_AI_API_KEY"]
    headers = {
        "Authorization": f"Bearer {kie_api_key}",
        "Content-Type": "application/json",
    }

    # Step 1: Create image generation task
    create_payload = {
        "model": "nano-banana-pro",
        "input": {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "output_format": output_format,
        },
    }

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                "https://api.kie.ai/api/v1/jobs/createTask",
                json=create_payload,
                headers=headers,
            )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502, detail=f"Failed to reach KIE AI API: {e}"
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"KIE AI createTask failed: {resp.status_code} - {resp.text}",
        )

    resp_json = resp.json()
    task_id = resp_json.get("data", {}).get("taskId")
    if not task_id:
        raise HTTPException(
            status_code=502, detail=f"No taskId in KIE AI response: {resp_json}"
        )

    # Step 2: Wait before first poll
    time.sleep(INITIAL_WAIT)

    # Step 3: Poll for result
    for _ in range(MAX_POLL_ATTEMPTS):
        try:
            with httpx.Client(timeout=30) as client:
                poll_resp = client.get(
                    "https://api.kie.ai/api/v1/jobs/recordInfo",
                    params={"taskId": task_id},
                    headers=headers,
                )
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=502, detail=f"Failed polling KIE AI: {e}"
            )

        if poll_resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"KIE AI poll failed: {poll_resp.status_code} - {poll_resp.text}",
            )

        poll_data = poll_resp.json().get("data", {})
        state = poll_data.get("state", "")

        if state == "success":
            try:
                result_json = json.loads(poll_data.get("resultJson", "{}"))
                image_url = result_json["resultUrls"][0]
            except (json.JSONDecodeError, KeyError, IndexError):
                raise HTTPException(
                    status_code=502,
                    detail=f"Unexpected result format from KIE AI: {poll_data}",
                )
            return {"image_url": image_url, "task_id": task_id}

        elif state == "fail":
            raise HTTPException(
                status_code=502,
                detail=f"Image generation failed at KIE AI. task_id={task_id}",
            )

        # Still generating — wait and retry
        time.sleep(POLL_INTERVAL)

    raise HTTPException(
        status_code=504,
        detail=f"Image generation timed out after polling. task_id={task_id}",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 2: YouTube Content Generator (3-step Claude chain)
# ═══════════════════════════════════════════════════════════════════════════════

# ─── System Prompts ───

TITLE_SYSTEM = (
    "You are a YouTube title optimization expert. You specialize in creating "
    "clickable, high-CTR video titles that are compelling yet accurate. Your "
    "titles balance curiosity, clarity, and searchability. You never use "
    "misleading clickbait. You always output ONLY the title text, with no "
    "quotes, no explanations, no extra formatting."
)

SCRIPT_SYSTEM = (
    "You are a professional YouTube scriptwriter and content strategist. You "
    "write engaging, well-structured video scripts that retain viewers and "
    "deliver value. Your scripts follow proven YouTube storytelling frameworks: "
    "strong hooks, clear sections, and compelling calls to action. You write in "
    "a conversational, energetic tone appropriate for the target audience. You "
    "output the complete script as plain text with clear section markers."
)

SEO_SYSTEM = (
    "You are a YouTube SEO specialist. You create optimized video descriptions "
    "and tag sets that maximize discoverability while remaining natural and "
    "viewer-friendly. You understand YouTube's search algorithm, keyword "
    "placement, and metadata best practices. You always output valid JSON "
    "only — no markdown, no code fences, no extra text."
)

# ─── User Prompt Templates ───

TITLE_USER_TEMPLATE = """Create ONE compelling YouTube video title for the following:

Topic: {topic}
Target Audience: {target_audience}

Requirements:
- Must be under 70 characters
- Must create curiosity or promise clear value
- Must be relevant to the target audience
- Must be SEO-friendly (include natural keywords)
- Do NOT use all caps or excessive punctuation
- Do NOT wrap in quotes

Output ONLY the title text, nothing else."""

SCRIPT_USER_TEMPLATE = """Write a complete YouTube video script for the following:

Title: {title}
Topic: {topic}
Target Audience: {target_audience}

Structure the script with these sections:

1. HOOK (first 15 seconds) - A compelling opening that stops the scroll. Ask a provocative question, share a surprising stat, or make a bold claim related to the topic.

2. INTRO (30 seconds) - Briefly introduce yourself and what the viewer will learn. Set expectations clearly.

3. MAIN CONTENT (3-5 key points) - Break the topic into clear, actionable sections. For each point:
   - State the point clearly
   - Explain WHY it matters
   - Give a specific example or actionable tip
   - Transition smoothly to the next point

4. BONUS TIP - One unexpected insight or advanced tip that adds extra value.

5. CTA + OUTRO - Summarize the key takeaway, ask viewers to like/subscribe, and tease what is coming next.

Guidelines:
- Write in a conversational, engaging tone
- Include specific examples and actionable advice
- Aim for 1500-2500 words (suitable for an 8-12 minute video)
- Add [B-ROLL] or [VISUAL] markers where supporting visuals should appear
- Write for spoken delivery, not reading — use short sentences, rhetorical questions, and direct address ("you")"""

SEO_USER_TEMPLATE = """Generate YouTube SEO metadata for the following video:

Title: {title}
Topic: {topic}
Target Audience: {target_audience}
Script Summary: {script_summary}

Return a JSON object with exactly this structure:
{{"description": "...", "tags": ["tag1", "tag2", ...]}}

Description requirements:
- First 2 lines: compelling summary with primary keywords (these show above the fold)
- Include 3-5 timestamps for key sections (estimate based on the script structure)
- Add a brief "About this video" paragraph
- Include a call to action (subscribe, comment)
- Total length: 800-1500 characters

Tags requirements:
- 15-25 tags
- Mix of: broad tags (1-2 words), specific tags (3-4 words), and long-tail phrases
- Include the exact title as one tag
- Include topic variations and synonyms
- Include audience-relevant tags
- Order from most to least relevant

Output ONLY the JSON object, no other text."""


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("anthropic-api-key"),
        modal.Secret.from_name("api-auth-token"),
    ],
    timeout=120,
)
@modal.fastapi_endpoint(method="POST")
def generate_nano_banana(data: dict, authorization: str = Header(None)) -> dict:
    """
    Generate a complete YouTube content package using a 3-step Claude chain.

    Input:  {"topic": "...", "target_audience": "..."}
    Output: {"title": "...", "script": "...", "description": "...", "tags": [...]}
    """
    import json
    import os
    import re

    import anthropic

    verify_bearer_token(authorization)

    topic = data.get("topic")
    target_audience = data.get("target_audience")
    if not topic:
        raise HTTPException(status_code=400, detail="Missing 'topic' in request body")
    if not target_audience:
        raise HTTPException(
            status_code=400, detail="Missing 'target_audience' in request body"
        )

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = "claude-sonnet-4-5-20250929"

    # ── Step A: Generate Title ──
    title_resp = client.messages.create(
        model=model,
        max_tokens=100,
        system=TITLE_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": TITLE_USER_TEMPLATE.format(
                    topic=topic, target_audience=target_audience
                ),
            }
        ],
    )
    title = title_resp.content[0].text.strip().strip('"').strip("'")

    # ── Step B: Generate Script ──
    script_resp = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SCRIPT_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": SCRIPT_USER_TEMPLATE.format(
                    title=title, topic=topic, target_audience=target_audience
                ),
            }
        ],
    )
    script = script_resp.content[0].text.strip()

    # ── Step C: Generate SEO Metadata ──
    seo_resp = client.messages.create(
        model=model,
        max_tokens=2048,
        system=SEO_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": SEO_USER_TEMPLATE.format(
                    title=title,
                    topic=topic,
                    target_audience=target_audience,
                    script_summary=script[:500],
                ),
            }
        ],
    )

    seo_raw = seo_resp.content[0].text.strip()

    # Clean markdown fences if present
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", seo_raw)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)

    try:
        seo_data = json.loads(cleaned)
    except json.JSONDecodeError:
        seo_data = {"description": seo_raw, "tags": []}

    return {
        "title": title,
        "script": script,
        "description": seo_data.get("description", ""),
        "tags": seo_data.get("tags", []),
    }
