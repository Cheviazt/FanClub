from dataclasses import dataclass

SOLVE_ANNOUNCEMENTS = "solve_announcements"
MENTION_ON_SOLVE = "mention_on_solve"
NICKNAME_SYNC = "nickname_sync"


@dataclass(frozen=True)
class SettingDef:
    key: str
    label: str
    description: str
    default: bool = True


SETTINGS: tuple[SettingDef, ...] = (
    SettingDef(
        SOLVE_ANNOUNCEMENTS,
        "Solve announcements",
        "Post a card in the solve channel when you solve a new problem.",
    ),
    SettingDef(
        MENTION_ON_SOLVE,
        "Mention on solve",
        "Ping you in that announcement instead of only naming your handle.",
    ),
    SettingDef(
        NICKNAME_SYNC,
        "Nickname sync",
        "Keep your server nickname in the form 【level】handle.",
    ),
)

SETTINGS_BY_KEY: dict[str, SettingDef] = {setting.key: setting for setting in SETTINGS}


def defaults() -> dict[str, bool]:
    return {setting.key: setting.default for setting in SETTINGS}
