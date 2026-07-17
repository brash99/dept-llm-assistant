from __future__ import annotations

from datetime import datetime


class HeaderPanel:
    def render(
        self,
        question: str,
        generated_at: datetime | None = None,
    ) -> str:
        timestamp = generated_at or datetime.now()

        return "\n".join(
            [
                "# Institutional Semantic Observatory",
                "",
                "**Executive Decision Intelligence**",
                "",
                "## Decision",
                "",
                question.strip(),
                "",
                (
                    f"*Generated "
                    f"{timestamp.strftime('%B %d, %Y at %H:%M')}*"
                ),
                "",
                "---",
            ]
        )
