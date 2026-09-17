from bot.cf.models import Problem, Submission
from bot.services.solve_detector import detect_new_solves


def S(id, cid, idx, verdict, t):
    return Submission(id, Problem(cid, idx, "n", 800, ()), verdict, t)


def test_detect_new_solves():
    subs = [
        S(5, 1, "A", "OK", 50),
        S(4, 2, "B", "OK", 40),
        S(3, 2, "B", "OK", 30),
        S(2, 3, "C", "WRONG_ANSWER", 20),
        S(1, 4, "D", "OK", 10),
    ]
    out = detect_new_solves(subs, {(4, "D")})
    assert [(s.problem.key, s.id) for s in out] == [((2, "B"), 3), ((1, "A"), 5)]


def test_detect_ignores_none_verdict():
    assert detect_new_solves([S(1, 1, "A", None, 1)], set()) == []
