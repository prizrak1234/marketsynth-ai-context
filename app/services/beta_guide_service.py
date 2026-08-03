"""Static beta tester guide content (Phase AI.97)."""

from __future__ import annotations

from app.schemas.beta_guide import BetaGuideResponse, BetaGuideStep


class BetaGuideService:
    @staticmethod
    def get_guide() -> BetaGuideResponse:
        return BetaGuideResponse(
            current_phase="closed_beta_mvp",
            what_to_test=[
                "First-run onboarding checklist on the dashboard",
                "Agent chat with orchestrator and copywriter on a project",
                "Marketing plan approval and specialist execution run",
                "Content asset approval from copywriter output",
                "Media brief and placeholder media asset",
                "Publication package approval and Telegram dry-run publish job",
            ],
            expected_path=[
                BetaGuideStep(
                    key="onboarding",
                    label="Onboarding",
                    hint="Create project, seed demo (or follow checklist), complete first chat",
                ),
                BetaGuideStep(key="chat", label="Agent chat", hint="Open AI Chat and send one message"),
                BetaGuideStep(
                    key="plan",
                    label="Marketing plan",
                    hint="Approve plan and run execution through copywriter",
                ),
                BetaGuideStep(
                    key="asset",
                    label="Content asset",
                    hint="Approve content asset from copywriter output",
                ),
                BetaGuideStep(
                    key="media",
                    label="Media",
                    hint="Approve media brief and placeholder media asset",
                ),
                BetaGuideStep(
                    key="package",
                    label="Publication package",
                    hint="Create and approve package for Telegram",
                ),
                BetaGuideStep(
                    key="publish",
                    label="Dry-run publish",
                    hint="Create queued job; use dry-run dispatch only (no real Telegram required)",
                ),
            ],
            known_limitations=[
                "No billing or paid plans in this beta",
                "No Instagram or LinkedIn publishing",
                "No background scheduler worker — schedule and dispatch are manual API/UI steps",
                "Media generation uses mock/placeholder providers by default",
                "Real Telegram send requires explicit env flags and bot token",
            ],
            feedback_instructions=(
                "Use Dashboard → Report a beta issue or POST /me/beta-feedback with source, "
                "severity, and a short description. Include error_code from demo-flow status "
                "when a step is blocked. Do not paste API keys or full API responses."
            ),
        )
