# FanClub Bot

A Discord bot for the FanClub competitive programming community at Universitas Brawijaya. It links Discord accounts to Codeforces handles and turns solved problems into levels, ranks, and a shared leaderboard.

## What it does

Once a member links their Codeforces handle, the bot watches their submissions. Every problem the account solves for the first time earns EXP (problem rating divided by 10) and money (problem rating divided by 200). EXP raises the member's level, the level decides their rank role, and the nickname is updated to show the current level. Problems solved before registration count toward the solved total but do not give EXP, and no problem is rewarded twice.

## Features

- Registration by proof of ownership: the member submits a compilation error on a random problem within five minutes.
- Levels, eight rank roles from Rookie to Legendary Master, and automatic nicknames in the form `【level】handle`.
- Daily streaks, tracked in Asia/Jakarta time.
- Rendered profile cards, leaderboards (level, rating, solved, streaks) with pagination, three personal daily problems, and custom practice sets by rating and tags.
- Accepted-solve announcements as image cards in a channel, mentioning the solver.
- Contest announcements for Codeforces, CodeChef and AtCoder up to a week ahead, plus a reminder one hour before the start.
- A daily practice reminder at 09:00 Asia/Jakarta.
- Welcome and registration guides via `/how`, `/howtoregist`, `$how` and `$howtoregist`.

### Commands

| Command | Description |
|---|---|
| `/register handle` | Link a Codeforces handle to your Discord account |
| `/unregister` | Unlink your handle and delete your progress |
| `/profile [@user]` | Profile card with level, money, EXP, rating, recent solves and streak |
| `/leaderboard type` | Top players by `level`, `rating`, `solved` or `streaks` |
| `/daily` | Three problems (900, 1200, 1600) you have not solved, refreshed daily |
| `/grinding count rating [tags]` | One to four unsolved problems at an exact rating, optionally filtered by tags |
| `/refresh [@user]` | Resync Codeforces data, award missed solves, fix role and nickname |
| `/how`, `/howtoregist` | Community introduction and registration guide |
| `/resetall` | Administrators only: strip roles and nicknames from every member |

## Requirements

- Docker and Docker Compose on the host
- A Discord application with a bot user

## Installation

1. Create an application at the Discord Developer Portal, add a bot, and copy its token.
2. Under Bot, enable the **Server Members Intent** and the **Message Content Intent**.
3. Invite the bot with the `bot` and `applications.commands` scopes and these permissions: Manage Roles, Manage Nicknames, Send Messages, Embed Links, Attach Files, Mention Everyone.
4. In the server, move the bot's role above the rank roles. The bot creates the rank roles on first start if they do not exist.
5. Clone the repository and create the environment file:

```bash
git clone https://github.com/powfulf/FanClub.git
cd FanClub
cp .env.example .env
```

6. Fill in `.env`:

| Variable | Required | Description |
|---|---|---|
| `DISCORD_TOKEN` | yes | Bot token |
| `GUILD_ID` | yes | Server ID |
| `NOTIFY_CHANNEL_ID` | yes | Channel for accepted-solve announcements |
| `CONTEST_CHANNEL_ID` | no | Channel for contest announcements; leave empty to disable |
| `REMINDER_CHANNEL_ID` | no | Channel for the daily reminder; leave empty to disable |
| `RESET_KEEP_ROLE_IDS` | no | Comma separated role IDs that `/resetall` must keep |
| `DATABASE_URL` | no | Defaults to the bundled PostgreSQL service |

Enable Developer Mode in Discord (User Settings, Advanced) to copy server and channel IDs.

7. Start the stack:

```bash
docker compose up -d --build
```

The bot container runs database migrations and then connects to Discord. Follow the logs with `docker compose logs -f bot`. PostgreSQL data lives in the `pgdata` volume and cached avatars in the `botdata` volume, so rebuilding the image does not lose anything.

## License

Released under the MIT License. See [LICENSE](LICENSE).
