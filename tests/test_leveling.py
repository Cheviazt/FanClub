import pytest

from bot.services.leveling import RANKS, exp_progress, level_for, rank_for, threshold


@pytest.mark.parametrize("level,expected", [(1, 0), (2, 100), (3, 300), (4, 600), (5, 1000)])
def test_threshold(level, expected):
    assert threshold(level) == expected


@pytest.mark.parametrize("exp,level", [(0, 1), (99, 1), (100, 2), (299, 2), (300, 3), (450, 3), (600, 4), (1000, 5)])
def test_level_for(exp, level):
    assert level_for(exp) == level


def test_exp_progress():
    assert exp_progress(450) == (150, 300)
    assert exp_progress(0) == (0, 100)
    assert exp_progress(100) == (0, 200)


@pytest.mark.parametrize(
    "level,name",
    [
        (1, "Rookie"), (20, "Rookie"), (21, "Elite"), (40, "Elite"), (41, "Specialist"),
        (80, "Specialist"), (81, "Expert"), (120, "Expert"), (121, "Master"), (160, "Master"),
        (161, "Grandmaster"), (200, "Grandmaster"), (201, "Legendary"), (300, "Legendary"),
        (301, "Legendary Master"), (999, "Legendary Master"),
    ],
)
def test_rank_for(level, name):
    assert rank_for(level).name == name


def test_rank_colors():
    colors = {r.name: r.color for r in RANKS}
    assert colors["Rookie"] == "#9E9E9E"
    assert colors["Legendary Master"] == "#8B0000"
