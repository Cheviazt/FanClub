import io
import random
from datetime import datetime, timezone

import pytest
from PIL import Image

from bot.cf.models import Problem
from bot.cogs.grinding import build_grinding_view
from bot.db.repo import problemset, solved, users
from bot.render.grinding import render_grinding, row_boxes
from bot.services.daily import NotEnoughProblems
from bot.services.grinding import UnknownTags, is_valid_rating, parse_tags, pick_problems

NOW = datetime(2026, 9, 16, tzinfo=timezone.utc)


def P(cid, rating, tags):
    return Problem(cid, "A", f"p{cid}", rating, tuple(tags))


def test_parse_tags():
    assert parse_tags(None) == []
    assert parse_tags(" DP , greedy,dp, ,Binary  Search ") == ["dp", "greedy", "binary search"]


def test_is_valid_rating():
    assert is_valid_rating(800) and is_valid_rating(3500) and is_valid_rating(1200)
    assert not is_valid_rating(1250) and not is_valid_rating(700) and not is_valid_rating(3600)


async def seed(session):
    await users.create_user(session, 1, "a")
    await problemset.replace_problemset(
        session,
        [P(1, 1200, ["dp", "math"]), P(2, 1200, ["dp"]), P(3, 1200, ["greedy"]), P(4, 1300, ["dp"]), P(5, 1200, ["dp", "graphs"])],
        NOW,
    )
    await solved.add_solved(session, 1, 5, "A", NOW)
    await session.commit()


async def test_pick_problems_filters_rating_tags_and_solved(session):
    await seed(session)
    picked = await pick_problems(session, 1, 2, 1200, ["dp"], random.Random(0))
    assert {p.contest_id for p in picked} <= {1, 2} and len(picked) == 2
    picked = await pick_problems(session, 1, 1, 1200, ["dp", "math"])
    assert [p.contest_id for p in picked] == [1]


async def test_pick_problems_errors(session):
    await seed(session)
    with pytest.raises(UnknownTags) as exc:
        await pick_problems(session, 1, 1, 1200, ["dp", "nonsense"])
    assert exc.value.tags == ["nonsense"]
    with pytest.raises(NotEnoughProblems):
        await pick_problems(session, 1, 3, 1200, ["dp"])


def test_row_boxes_split_box_evenly():
    rows = row_boxes(4)
    assert len(rows) == 4
    assert rows[0][1] < rows[1][1] < rows[2][1] < rows[3][1]
    assert rows[3][3] <= 567


@pytest.mark.parametrize("count", [1, 2, 3, 4])
def test_render_grinding(count):
    problems = [P(i, 1200, ["dp", "math"]) for i in range(1, count + 1)]
    im = Image.open(io.BytesIO(render_grinding(problems, {(1, "A")})))
    assert im.size == (974, 650)


async def test_grinding_view_buttons():
    view = build_grinding_view([P(1, 1200, []), P(2, 1200, [])])
    labels = [b.label for b in view.children]
    assert labels == ["Open 1A", "Open 2A"]
