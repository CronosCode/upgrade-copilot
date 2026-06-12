from __future__ import annotations

from upgrade_copilot.index.models import SearchResult


def suggest_follow_up(results: list[SearchResult]) -> str:
    if not results:
        return "Try naming the library and the migration topic, for example: sqlalchemy session changes."

    library = results[0].chunk.library
    return f"Try narrowing the question to a specific {library} migration step or helper tool."
