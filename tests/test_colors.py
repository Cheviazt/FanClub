from bot.render.colors import DISCORD_RANK_COLORS, cf_rank_color, cf_rating_color


def test_discord_rank_colors_match_leveling():
    from bot.services.leveling import RANKS
    for r in RANKS:
        assert DISCORD_RANK_COLORS[r.name] == r.color


def test_cf_rank_color():
    assert cf_rank_color("pupil") == "#008000"
    assert cf_rank_color("international grandmaster") == "#FF0000"
    assert cf_rank_color(None) == "#808080"


def test_cf_rating_color():
    assert cf_rating_color(900) == "#808080"
    assert cf_rating_color(1200) == "#008000"
    assert cf_rating_color(1600) == "#5C7CFF"
    assert cf_rating_color(None) == "#808080"
