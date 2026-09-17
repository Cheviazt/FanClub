# FanClub Bot

Discord bot for a competitive programming community, linked to Codeforces.

## Features

- `/register <handle>`: link a Codeforces handle. Verify by submitting a Compilation Error on a random problem within 5 minutes.
- `/profile [@user]`: profile card image with level, money, EXP, Codeforces stats, last solved, streak.
- `/leaderboard <level|rating|solved|streaks>`: paginated image leaderboard, 7 per page.
- `/daily`: three personal daily problems (900, 1200, 1600) that you have never solved.
- Background poller: new accepted solves give EXP (`rating / 10`) and money (`rating / 200`), update level, rank role, nickname, streak, and post a notification.

## Setup

1. Create a Discord application, enable the Server Members intent, invite the bot with `applications.commands`, `Manage Roles`, `Manage Nicknames`, `Send Messages`, `Attach Files`.
2. Copy `.env.example` to `.env` and fill `DISCORD_TOKEN`, `GUILD_ID`, `NOTIFY_CHANNEL_ID`.
3. Run:

```bash
docker compose up -d --build
```

The bot role must be above the rank roles it manages in the server role list.

## Development

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q
```

Run locally against a Postgres instance by setting `DATABASE_URL`, then `alembic upgrade head` and `python -m bot`.

## Deployment (GitHub Actions)

Every push to `main` runs the test suite, then SSHes into the VPS, pulls the latest code, and rebuilds the containers.

One-time VPS setup (Ubuntu, user with Docker access):

```bash
git clone https://github.com/powfulf/FanClub.git ~/fanclub
cd ~/fanclub
cp .env.example .env
docker compose up -d --build
```

Create an SSH key for the workflow on the VPS and add the public half to `~/.ssh/authorized_keys`:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/github_actions -N ""
cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys
```

Repository secrets required: `VPS_HOST`, `VPS_USER`, `VPS_PORT`, `VPS_SSH_KEY` (contents of `~/.ssh/github_actions`).

`.env` lives only on the VPS. Edit it there and run `docker compose up -d` to apply changes.
