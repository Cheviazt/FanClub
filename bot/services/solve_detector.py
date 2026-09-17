from bot.cf.models import Submission


def detect_new_solves(submissions: list[Submission], solved: set[tuple[int, str]]) -> list[Submission]:
    earliest: dict[tuple[int, str], Submission] = {}
    for sub in submissions:
        if sub.verdict != "OK":
            continue
        key = sub.problem.key
        if key in solved:
            continue
        current = earliest.get(key)
        if current is None or sub.created_at < current.created_at:
            earliest[key] = sub
    return sorted(earliest.values(), key=lambda s: (s.created_at, s.id))
