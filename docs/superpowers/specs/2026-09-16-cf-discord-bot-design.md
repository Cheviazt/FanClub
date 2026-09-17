# Codeforces Discord Bot: Design Spec (MVP)

Tanggal: 2026-09-16
Repo: https://github.com/powfulf/FanClub.git
Status: disetujui user, siap dibuat implementation plan.

## 1. Tujuan

Bot Discord untuk komunitas competitive programming yang terhubung ke Codeforces
(API publik `https://codeforces.com/api`). MVP mencakup: register + verifikasi,
level/EXP, money, profile bergambar, leaderboard bergambar, daily problem
per-user, deteksi solve baru, dan notifikasi solve.

Di luar scope MVP: `/store`, `/unregister`, notifikasi lanjutan, multi-guild.

## 2. Konvensi Proyek

- Commit tidak menyertakan baris `Co-Authored-By` atau atribusi AI apa pun.
- Kode tidak memakai komentar. Nama fungsi dan variabel harus menjelaskan diri sendiri.
- Tidak memakai emoji bergaya AI di kode, dokumen, maupun pesan bot.
- Tidak memakai em dash di teks apa pun. Pakai koma, titik dua, atau titik.

## 3. Tech Stack

| Komponen | Pilihan |
|---|---|
| Bahasa | Python 3.12 |
| Discord | discord.py 2.x (app commands, `discord.ui`, `tasks.loop`) |
| HTTP | httpx (async) |
| DB | PostgreSQL 16, SQLAlchemy 2 async (asyncpg), Alembic |
| Render gambar | Pillow, font JetBrains Mono TTF (OFL) di `assets/fonts/` |
| Config | pydantic-settings dari `.env` |
| Test | pytest, pytest-asyncio, respx (mock httpx), aiosqlite (DB test in-memory) |
| Deploy | Docker multi-stage + docker-compose (`bot` + `db`) |

Codeforces API dipakai tanpa API key (endpoint publik cukup).

## 4. Arsitektur

Monolit satu proses, discord.py cogs per fitur, logika bisnis di layer
`services/` yang tidak bergantung pada Discord sehingga bisa di-unit-test.

```
bot/
  __main__.py
  main.py
  config.py
  cf/
    client.py
    models.py
  db/
    models.py
    session.py
    repo/
      users.py, solved.py, daily.py, roles.py, cf_cache.py, problemset.py
  services/
    leveling.py
    rewards.py
    solve_detector.py
    streak.py
    register.py
    daily.py
    leaderboard.py
    roles.py
  render/
    fonts.py
    text.py
    colors.py
    profile.py, leaderboard.py, daily.py
  cogs/
    register.py, profile.py, leaderboard.py, daily.py, poller.py
alembic/
assets/
tests/
Dockerfile, docker-compose.yml, .env.example, pyproject.toml
```

Tanggung jawab tiap modul:

- `main.py`: buat Bot, load cogs, start loops, sync command ke `GUILD_ID`.
- `config.py`: `Settings` (pydantic-settings).
- `cf/client.py`: `CodeforcesClient` untuk `user.info`, `user.status`, `problemset.problems`.
- `cf/models.py`: dataclass `Problem`, `Submission`, `UserInfo`.
- `db/models.py`: model SQLAlchemy. `db/session.py`: engine + session factory.
- `db/repo/*`: query per entitas.
- `services/leveling.py`: exp ke level, level ke rank, threshold.
- `services/rewards.py`: rating ke exp/money.
- `services/solve_detector.py`: submission baru vs `solved_problems`.
- `services/streak.py`: update streak (WIB).
- `services/register.py`: sesi verifikasi 5 menit.
- `services/daily.py`: pilih 3 soal per user per hari.
- `services/leaderboard.py`: query + paginasi.
- `services/roles.py`: sync role + nickname.
- `render/fonts.py`: loader Poppins per weight. `render/text.py`: `fit_text` (auto-size + ellipsis).
- `render/colors.py`: warna rank Discord + rank CF.
- `render/profile.py`, `render/leaderboard.py`, `render/daily.py`: compose gambar.
- `cogs/*`: parse command, panggil service, kirim embed. `cogs/poller.py`: background loops.

## 5. Data Model

Semua waktu disimpan UTC. "Hari" dihitung di zona `Asia/Jakarta` (WIB).

- `users`
  - `discord_id` BIGINT PK
  - `handle` VARCHAR UNIQUE (case-preserving, pencocokan case-insensitive)
  - `exp` INTEGER default 0
  - `money` NUMERIC(12,2) default 0
  - `streak` INTEGER default 0
  - `last_solve_date` DATE nullable (tanggal WIB solve baru terakhir)
  - `registered_at` TIMESTAMPTZ
- `solved_problems`
  - `user_id` BIGINT FK users, `contest_id` INTEGER, `index` VARCHAR, `solved_at` TIMESTAMPTZ
  - PK (`user_id`, `contest_id`, `index`)
  - Diisi baseline saat register (semua AC seumur hidup akun CF), lalu bertambah dari poller.
- `daily_problems`
  - `user_id`, `date` DATE (WIB), `rating` INTEGER, `contest_id`, `index`, `name`, `tags` JSON
  - PK (`user_id`, `date`, `rating`)
- `guild_roles`
  - `guild_id` BIGINT, `rank_name` VARCHAR, `role_id` BIGINT, PK (`guild_id`, `rank_name`)
- `cf_cache` (snapshot `user.info`)
  - `user_id` PK FK, `rating` INTEGER nullable, `max_rating` INTEGER nullable, `rank` VARCHAR nullable,
    `max_rank` VARCHAR nullable, `last_online` TIMESTAMPTZ, `avatar_url` VARCHAR, `updated_at` TIMESTAMPTZ
- `problemset_cache`
  - `contest_id`, `index`, `name`, `rating` INTEGER nullable, `tags` JSON, `fetched_at`, PK (`contest_id`, `index`)
  - Refresh tiap 6 jam dari `problemset.problems`.

Turunan (tidak disimpan): `solved_count = COUNT(solved_problems WHERE user_id)`,
`level = leveling.level_for(exp)`.

## 6. Aturan Bisnis

### 6.1 Level & EXP
- EXP per solve baru = `rating // 10`. Soal tanpa rating: 0 EXP.
- Level dihitung dari total EXP kumulatif. Total EXP minimum untuk level `n` (n >= 1):
  `threshold(n) = 100 * (n-1) * n / 2`, jadi L1=0, L2=100, L3=300, L4=600, L5=1000.
- Kebutuhan EXP di dalam level `n` = `n * 100`. Tampilan: `{exp - threshold(n)}/{n*100}`
  (contoh total 450 berarti L3, tampil `150/300`).
- Rank Discord berdasarkan level:

  | Level | Rank | Warna role |
  |---|---|---|
  | 1-20 | Rookie | `#9E9E9E` |
  | 21-40 | Elite | `#C0C0C0` |
  | 41-80 | Specialist | `#4CAF50` |
  | 81-120 | Expert | `#2196F3` |
  | 121-160 | Master | `#F44336` |
  | 161-200 | Grandmaster | `#FF9800` |
  | 201-300 | Legendary | `#FFEB3B` |
  | 301+ | Legendary Master | `#8B0000` |

- Role dibuat otomatis oleh bot saat startup bila belum ada (nama + warna di atas), ID disimpan di `guild_roles`.
  Saat rank berubah: hapus role rank lama, tambah role baru.
- Nickname anggota: `【{level}】{handle}`. Di-set saat register dan diperbarui setiap level naik.
  Jika Discord menolak (`Forbidden`, misalnya owner server), log warning saja.

### 6.2 Money
- Simbol `$`. Per solve baru: `money += rating / 200` (2 desimal, 900 berarti `$4.50`). Soal tanpa rating: 0.
- Belum ada tempat belanja (`/store` menyusul).

### 6.3 Register (`/register handle`)
1. Tolak bila: handle tidak ada di CF, handle sudah terhubung ke Discord lain, atau pemanggil sudah register.
   Balas embed error ephemeral.
2. Pilih 1 soal acak dari `problemset_cache` (rating apa saja). Simpan sesi pending in-memory
   `{discord_id: PendingRegistration(handle, contest_id, index, started_at)}`. Satu sesi aktif per user.
3. Balas embed instruksi: link soal, "submit apa saja dengan verdict Compilation Error", deadline `<t:{ts}:R>`.
4. Setiap 10 detik selama maksimal 5 menit: `user.status?handle=X&from=1&count=10`. Sukses jika ada
   submission dengan `verdict == "COMPILATION_ERROR"`, `problem.contestId/index` sama, dan
   `creationTimeSeconds >= started_at`.
5. Sukses: insert `users` (exp 0, money 0, streak 0). Tarik seluruh submission (`user.status` paginasi
   `count=1000`), simpan semua `verdict == "OK"` unik ke `solved_problems`. Isi `cf_cache`. Beri role Rookie.
   Set nickname `【1】{handle}`. Edit embed menjadi sukses. Timeout: edit embed menjadi gagal, hapus sesi.

### 6.4 Smart Problem Detect (poller)
- `tasks.loop(seconds=60)`. Iterasi semua `users`. Klien CF menjaga jeda >= 2 detik antar request
  (`asyncio.Lock` global). Sekitar 100 user berarti kira-kira 3,5 menit per putaran. Putaran berikut mulai
  setelah putaran sebelumnya selesai (tidak overlap).
- Per user: `user.status?handle=X&from=1&count=30`. Untuk tiap submission `verdict == "OK"` yang
  `(contest_id, index)` belum ada di `solved_problems`, urut dari yang paling lama:
  1. insert `solved_problems` (PK mencegah duplikasi bila crash di tengah)
  2. `exp += rating // 10`, `money += rating / 200`
  3. hitung level lama/baru. Naik: update nickname. Rank berubah: swap role.
  4. update streak (6.5)
  5. kirim notifikasi (6.8)
- Setiap 10 menit: refresh `cf_cache` untuk semua user via `user.info?handles=a;b;c` (maksimal 100 handle per request).
- Setiap 6 jam: refresh `problemset_cache`.
- Solve ulang soal yang sudah ada di `solved_problems` tidak dihitung, tidak dinotifikasi.

### 6.5 Streak
- Hari = tanggal WIB. Saat solve baru terdeteksi:
  - `last_solve_date == hari ini`: streak tetap
  - `last_solve_date == kemarin`: `streak += 1`
  - lainnya (null atau lebih lama): `streak = 1`
  - set `last_solve_date = hari ini`
- Loop harian 00:05 WIB: user dengan `last_solve_date < kemarin` mendapat `streak = 0`.
- Solve daily problem tidak memberi bonus. Reward sama seperti solve biasa.

### 6.6 Daily Problem (`/daily`)
- Wajib register. Per user, per hari WIB, 3 soal dengan rating tepat 900, 1200, 1600.
- Bila `daily_problems` untuk (user, hari ini) belum ada: pilih acak dari `problemset_cache` dengan rating
  tersebut, exclude soal di `solved_problems` user dan soal yang pernah jadi daily user tersebut. Simpan.
  Panggilan ulang di hari yang sama mengembalikan soal yang sama.
- Balas embed berisi gambar render (7.3) + 3 link button berlabel `900`, `1200`, `1600` ke
  `https://codeforces.com/problemset/problem/{contestId}/{index}`.

### 6.7 Profile (`/profile [user]`)
- Default = pemanggil. Target belum register: embed error ephemeral.
- Data: handle, avatar (`cf_cache.avatar_url`, tambahkan prefix `https:` bila diawali `//`), level, money,
  EXP dalam level, rating, rank CF, rank Discord, max rating, last seen, 3 last solved (dari `solved_problems`
  order by `solved_at` desc), solved count, streak.
- Unrated (`rating` null): rating tampil `Unrated` abu-abu, rank CF `Unrated`, max `-`.
- Last seen relatif: `just now`, `{n}m ago`, `{n}h ago`, `{n}d ago`.
- Embed berisi gambar + `discord.ui.Button(style=ButtonStyle.link, label="See Profile", url="https://codeforces.com/profile/{handle}")`.
  Link button Discord tidak bisa berwarna hijau. Keputusan user: tetap link button.

### 6.8 Notifikasi
- Channel dari `NOTIFY_CHANNEL_ID`. Hanya untuk solve baru (6.4). Format:
  `**{handle}** solved [{contestId}{index} - {name}]({url}) (rating {rating}) | +{exp} EXP | +${money}`
  Soal tanpa rating: `(unrated)`, `+0 EXP | +$0.00`.

### 6.9 Leaderboard (`/leaderboard type`)
- `type` choices: `level`, `rating`, `solved`, `streaks`. 7 user per halaman.
- Urutan:
  - level: `exp` desc
  - rating: `cf_cache.rating` desc (null = 0), tie `max_rating` desc
  - solved: `solved_count` desc, tie `exp` desc
  - streaks: `streak` desc, tie `exp` desc
- Username = handle CF, warna mengikuti rank Discord user tersebut.
- View dengan tombol `Back` / `Next`. Disabled di ujung. Hanya pemanggil yang bisa klik
  (lainnya dapat balasan ephemeral). Timeout 300 detik lalu tombol dinonaktifkan.
- Baris kosong (user < 7) dibiarkan blank. Pill bawah: `{page}/{total_pages}`.

## 7. Render Gambar

Semua template 974x650 RGB. Font JetBrains Mono: Regular, Medium, SemiBold, Bold.
`fit_text(draw, text, box, weight, max_size, min_size, align)`: turunkan ukuran font dari `max_size`
sampai muat lebar box. Bila di `min_size` masih terlalu lebar, potong karakter dan tambahkan `…`.
Berlaku untuk semua teks dinamis (judul soal, handle, tags).

Warna rank CF: Newbie `#808080`, Pupil `#008000`, Specialist `#03A89E`, Expert `#0000FF`,
Candidate Master `#AA00AA`, Master dan International Master `#FF8C00`,
Grandmaster, International Grandmaster, Legendary Grandmaster `#FF0000`, Unrated `#808080`.

### 7.1 Profile (`assets/profile.png`)

| Slot | Box (x0,y0,x1,y1) | Isi | Font (max ke min) |
|---|---|---|---|
| A | 167,158,386,377 | avatar CF, resize 219x219, rounded 12px | - |
| B | 167,415,386,492 | 3 last solved, 3 baris `{contestId}{index} · {name}` | Regular 16 ke 12 |
| C | 411,158,485,207 | `Lv {level}` | Bold 22 |
| D | 509,158,807,207 | handle, warna rank CF | Bold 30 ke 18 |
| E | 411,226,525,267 | rank Discord, warna rank | SemiBold 18 ke 12 |
| F | 551,226,666,267 | `{exp_in_level}/{need}` | SemiBold 18 ke 12 |
| G | 692,226,807,267 | `${money}` | SemiBold 18 ke 12 |
| H | 430,366,530,392 | rating, warna rank CF | SemiBold 20 |
| I | 563,366,663,392 | rank CF, warna rank CF | SemiBold 16 ke 11 |
| J | 696,366,796,392 | max rating | SemiBold 20 |
| K | 430,434,530,460 | last seen | Medium 16 |
| L | 563,434,663,460 | solved count | SemiBold 20 |
| M | 696,434,796,460 | streak | SemiBold 20 |

Teks slot C sampai M rata tengah. Slot B rata kiri.

### 7.2 Leaderboard (`assets/lb_{type}.png`)
- Baris (x 173 sampai 801): y `204-244, 249-288, 293-332, 337-377, 381-421, 426-465, 470-509`.
- Kolom: `no` tengah x=215. `username` kiri x=324, lebar maks 300. `value` tengah x=700.
- Font Medium 20 (username fit 20 ke 14). Value: level `{level}`, rating angka atau `0`, solved angka, streaks angka.
- Pill halaman: box 448,581,526,621, teks `{page}/{total}` Medium 16 tengah.

### 7.3 Daily (`assets/daily.png`)
- Box (x 250 sampai 724): y `157-256`, `294-393`, `431-531`. Padding dalam 16px.
- Baris 1 (y+18): kiri `{contestId}{index} · {name}` SemiBold 22 ke 14, putih. Kanan `{rating}` Bold 22,
  warna rank CF untuk rating tersebut. Judul dipotong dengan `…` agar tidak menabrak rating.
- Baris 2 (y+58): tags dipisah ` · `, Regular 15, abu `#B0BEC5`, `…` bila panjang.

### 7.4 Pengiriman
Render ke `BytesIO` PNG, bungkus `discord.File(fp, filename="x.png")`, embed `set_image(url="attachment://x.png")`.

## 8. Konfigurasi (`.env`)

```
DISCORD_TOKEN=
GUILD_ID=
NOTIFY_CHANNEL_ID=
DATABASE_URL=postgresql+asyncpg://bot:bot@db:5432/bot
TZ=Asia/Jakarta
LOG_LEVEL=INFO
```

## 9. Error Handling

- CF client: timeout 15 detik, retry 3x exponential backoff untuk 5xx/network error. `status != "OK"`
  dilempar sebagai `CodeforcesError(comment)`.
- Poller: exception per user ditangkap dan di-log, lanjut ke user berikut.
- Discord `Forbidden`/`HTTPException` saat role/nickname: log warning.
- Command: semua error ke user berupa embed merah ephemeral. Exception tak terduga di-log dengan traceback.
- Poller idempotent via PK `solved_problems`.

## 10. Testing

- Unit (tanpa I/O): `leveling` (threshold, level_for, rank batas 20/21, 40/41, 200/201, 300/301),
  `rewards` (900 ke 90 EXP dan 4.50, None ke 0), `streak` (hari ini, kemarin, lewat, null),
  `solve_detector` (skip yang sudah solved, urutan lama ke baru), `render.text.fit_text` (auto-size, ellipsis).
- DB: repo tests dengan SQLite in-memory (aiosqlite) memakai model yang sama.
- CF client: `respx` mock. Test retry dan error `status != OK`.
- Render: generate PNG untuk profile/leaderboard/daily dengan data dummy, assert ukuran 974x650 dan tidak exception.
- Tidak ada test terhadap Discord live.

## 11. Deploy

- `Dockerfile`: multi-stage `python:3.12-slim`, install deps ke venv, runtime image non-root, copy `bot/`, `assets/`, `alembic/`.
- `docker-compose.yml`: service `db` (postgres:16-alpine, volume `pgdata`, healthcheck), service `bot`
  (`depends_on: db: condition: service_healthy`, `env_file: .env`, command `alembic upgrade head && python -m bot`).
- Perintah: `docker compose up -d --build`.

## 12. Keputusan yang Sudah Disepakati

- Batas rank: Grandmaster 161-200, Legendary 201-300, Legendary Master 301+.
- Money desimal 2 digit. Soal tanpa rating: dihitung solved + notif, EXP/money 0.
- Solved count = seumur hidup akun CF (baseline saat register). Reward hanya untuk solve setelah register.
- Sekitar 100 user. Poll 60 detik, jeda 2 detik per request.
- Timezone WIB. Streak +1 per hari ada solve baru. Daily tanpa bonus.
- Verifikasi register: soal acak rating apa saja, poll 10 detik, 5 menit.
- Role dibuat otomatis. Single guild. Nickname owner gagal: warning.
- Daily per-user, exclude soal yang sudah di-solve dan daily lama user.
- Ellipsis `…` untuk semua teks yang melebihi box.
- See Profile = link button (abu-abu, langsung ke CF).
