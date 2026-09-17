from dataclasses import dataclass


@dataclass(frozen=True)
class Rank:
    name: str
    color: str
    min_level: int
    max_level: int | None


RANKS: tuple[Rank, ...] = (
    Rank("Rookie", "#9E9E9E", 1, 20),
    Rank("Elite", "#C0C0C0", 21, 40),
    Rank("Specialist", "#4CAF50", 41, 80),
    Rank("Expert", "#2196F3", 81, 120),
    Rank("Master", "#F44336", 121, 160),
    Rank("Grandmaster", "#FF9800", 161, 200),
    Rank("Legendary", "#FFEB3B", 201, 300),
    Rank("Legendary Master", "#8B0000", 301, None),
)

RANK_NAMES: tuple[str, ...] = tuple(r.name for r in RANKS)


def threshold(level: int) -> int:
    return 100 * (level - 1) * level // 2


def level_for(exp: int) -> int:
    level = 1
    while exp >= threshold(level + 1):
        level += 1
    return level


def exp_progress(exp: int) -> tuple[int, int]:
    level = level_for(exp)
    return exp - threshold(level), level * 100


def rank_for(level: int) -> Rank:
    for rank in RANKS:
        if rank.max_level is None or level <= rank.max_level:
            return rank
    return RANKS[-1]
