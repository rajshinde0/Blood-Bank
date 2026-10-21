# 🩸 LifeLink — Blood Bank Management System

A Flask web application for running a blood bank: donor registry, live inventory,
a priority queue that always surfaces the most critical patient next, and
blood-group compatibility checks.

Built as a Data Structures & Algorithms project at VIT, with a C++ reference
implementation of the underlying structures in [`cpp_Backend/`](cpp_Backend/).

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.3-000000?logo=flask&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00)
![Tests](https://img.shields.io/badge/tests-76%20passing-16794a)

---

## Contents

- [What it does](#what-it-does)
- [The DSA core](#the-dsa-core)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Project layout](#project-layout)
- [API reference](#api-reference)
- [Database schema](#database-schema)
- [Testing](#testing)
- [Docker](#docker)
- [Seeding from the legacy CSV files](#seeding-from-the-legacy-csv-files)
- [Known limitations](#known-limitations)

---

## What it does

| Area | Capability |
|---|---|
| **Dashboard** | Stock totals, waiting-queue size, low-stock alerts, live activity feed |
| **Donors** | Register, search by ID / name / blood group / city, soft-delete, donation counts |
| **Inventory** | Per-type levels against a configurable threshold and capacity, with status chips |
| **Patients** | Priority queue ordered by urgency, then by earliest deadline |
| **Transactions** | Donations in and issues out, with inventory updated atomically |
| **Compatibility** | Single-pair check, "who can donate to this patient", and the full 8×8 matrix |
| **Auth** | Login / registration, PBKDF2-SHA256 hashing |
| **Roles** | Enforced: new accounts are read-only; writes need nurse/doctor, deletes need admin |
| **CSRF** | Every state-changing route protected by Flask-WTF; the token rides on `X-CSRFToken` |
| **Audit** | Every create, delete, login and report written to `audit_logs` with IP and user agent |
| **Real time** | Socket.IO pushes donor, patient, transaction and low-stock events to open tabs |
| **Interface** | Custom design system, light and dark themes, responsive down to 375px |

---

## The DSA core

Two structures do the interesting work, both in [`app.py`](app.py):

**Min-heap priority queue (`PatientQueue`)** — patients are ordered by
`(urgency, deadline, arrival_counter)`, an Earliest-Deadline-First schedule.
`enqueue` and `dequeue` are O(log n); `peek` is O(1) amortised.

The heap lives in memory, so two things keep it honest:

- `refresh()` runs at startup and rebuilds it from the database — the queue
  survives a restart.
- `dequeue()` and `peek()` discard entries whose patient has since been served
  (for example through an *issue* transaction), so a stale heap self-heals.
- A patient with no deadline sorts with a max-datetime sentinel rather than
  `float('inf')`, which would make the heap compare a `datetime` against a
  `float` and raise `TypeError`.

**LRU-cached compatibility lookup (`check_compatibility`)** — the donor →
recipient table is a dictionary; `functools.lru_cache(maxsize=256)` makes repeat
checks O(1) with no recomputation. 64 pairings exist in total, so the cache
saturates almost immediately.

The C++ backend in `cpp_Backend/prog1.cpp` additionally demonstrates hash tables
with separate chaining, an AVL tree, a trie, union-find, a segment tree, and
Kruskal's and Dijkstra's algorithms — see [`docs/design/dsa.txt`](docs/design/dsa.txt).

---

## Quick start

```bash
# 1. Virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate        # macOS / Linux

# 2. Dependencies
pip install -r requirements.txt

# 3. Configuration (optional — sensible defaults apply)
cp .env.example .env

# 4. Run
python app.py
```

Open <http://localhost:5000>.

The database, the eight blood types (100 units each) and an administrator
account are created automatically on first run:

| Username | Password |
|---|---|
| `admin` | `Admin@123` |

> **Change that password before deploying anywhere real.** `FLASK_ENV=production`
> additionally refuses to start while `SECRET_KEY` is the development default.

---

## Configuration

Everything is read from the environment (or a `.env` file). See
[`.env.example`](.env.example).

| Variable | Default | Notes |
|---|---|---|
| `FLASK_ENV` | `development` | `development` \| `testing` \| `production` |
| `SECRET_KEY` | dev default | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | `sqlite:///blood_bank.db` | Any SQLAlchemy URL |
| `SQLALCHEMY_ECHO` | `false` | Accepts `true/false`, `1/0`, `yes/no`, `on/off` |
| `SESSION_TIMEOUT` | `3600` | **Seconds** |
| `LOG_LEVEL` | `INFO` | |
| `LOG_FILE` | `logs/app.log` | Rotates at 10 MB, 10 backups |
| `ITEMS_PER_PAGE` | `20` | Rows per page in every listing |

---

## Project layout

```
.
├── app.py                  # Routes, PatientQueue, compatibility cache
├── models.py               # SQLAlchemy models + enums
├── config.py               # Environment-driven config classes
├── utils.py                # Validation, formatting, blood-group helpers
├── logger.py               # Rotating file + console logging
├── wsgi.py                 # Production entry point
├── migrate_csv_to_db.py    # One-off import from the legacy flat files
├── test_app.py             # 76 tests
│
├── templates/              # Jinja templates, all extending base.html
│   ├── base.html           #   layout: nav, theme toggle, toasts
│   ├── _icons.html         #   inline SVG icon macros
│   └── _pagination.html    #   shared pagination macro
├── static/
│   ├── css/style.css       # Design system: tokens, light + dark, components
│   └── js/main.js          # Theme toggle, toasts, AJAX forms, Socket.IO
│
├── data/                   # Seed CSVs for migrate_csv_to_db.py
├── cpp_Backend/prog1.cpp   # C++ reference implementation of the structures
└── docs/                   # Design notes, team notes, quick start
```

---

## API reference

All routes except `/login`, `/register` and `/healthz` require an authenticated
session. Write endpoints accept `application/x-www-form-urlencoded` and answer
with JSON.

Every `POST` requires a CSRF token, sent either as the `X-CSRFToken` header or
as a `csrf_token` form field — see [Security notes](#security-notes). Calling
these from a script means fetching a page first and reading the token out of its
`<meta name="csrf-token">`.

### Pages

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/` | Dashboard |
| `GET` | `/donors` | Donor registry — `?search=`, `?search_type=all\|id\|name\|blood`, `?page=` |
| `GET` | `/inventory` | Stock levels |
| `GET` | `/patients` | Priority queue — `?urgency=all\|critical\|urgent\|normal`, `?page=` |
| `GET` | `/transactions` | Ledger — `?filter=all\|donation\|issue`, `?page=` |
| `GET` | `/compatibility` | Compatibility tools |

### Actions

| Method | Route | Body | Returns |
|---|---|---|---|
| `POST` | `/login` | `username`, `password` | `{success, redirect}` · 401 on bad credentials |
| `POST` | `/register` | `username`, `email`, `password`, `full_name` | 201 · 400 on duplicate or weak password |
| `POST` | `/logout` | — | Redirect to login (POST so it cannot be forged) |
| `POST` | `/add_donor` | `id`, `name`, `blood_group`, `age`, `phone`, `email?`, `city?` | 201 · 409 if the ID exists |
| `POST` | `/delete_donor/<donor_id>` | — | 200 (soft delete) |
| `POST` | `/add_patient` | `id`, `name`, `age`, `phone`, `blood_group`, `urgency`, `deadline_hours?` | 201 |
| `POST` | `/serve_patient` | — | Highest-priority patient · 404 when the queue is empty |
| `GET` | `/peek_patient` | — | Next patient without dequeuing |
| `POST` | `/add_transaction` | `action`, `donor_id`\|`patient_id`, `blood_group`, `quantity`, `notes?` | 201 · 400 on insufficient stock |
| `POST` | `/check_compatibility` | `donor_blood`, `patient_blood` | `{compatible, message}` |
| `POST` | `/find_compatible_donors` | `patient_blood` | `{donors[], count}` |

### JSON endpoints

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/healthz` | Liveness probe — no auth, used by the container healthcheck |
| `GET` | `/api/inventory/<blood_group>` | One inventory row |
| `GET` | `/api/queue/status` | Queue counts, expired deadlines, next patient |
| `GET` | `/api/reports/inventory` | Inventory report |
| `GET` | `/api/reports/transactions` | Transaction report — `?start_date=`, `?end_date=` (ISO 8601) |

### Socket.IO events

Emitted by the server: `donor_added`, `donor_deleted`, `patient_added`,
`patient_served`, `transaction_created`, `system_alert`, `queue_update`.

---

## Database schema

| Table | Purpose | Notable columns |
|---|---|---|
| `users` | Authentication | `username`, `email`, `password_hash`, `role` |
| `donors` | Registry | `donor_id`, `blood_group`, `donation_count`, `is_active` |
| `patients` | Queue + history | `patient_id`, `urgency`, `deadline`, `served`, `served_time` |
| `inventory` | Stock per type | `blood_group` (unique), `quantity`, `min_threshold`, `max_capacity` |
| `transactions` | Ledger | `transaction_id`, `action`, FKs to donor / patient / user |
| `audit_logs` | Action trail | `action`, `resource_type`, `old_values`, `new_values`, `ip_address` |
| `system_alerts` | Alerts | `alert_type`, `severity`, `acknowledged` |

`blood_group` and `urgency` are SQLAlchemy `Enum` columns, which persist the
member **name** (`O_POSITIVE`), not the display string. Use `utils.blood_enum()`
to convert — a `LIKE '%O+%'` filter against those columns can never match.

---

## Testing

```bash
pytest test_app.py -v                      # 76 tests
pytest test_app.py --cov=. --cov-report=term-missing
```

Tests run against a temporary SQLite file configured before `app` is imported,
so they never touch your development database. Coverage includes authentication,
CSRF (rejection without a token, acceptance with one, and a sweep asserting no
write route is reachable unprotected), authorisation (read-only registrations,
each role's limits, and anonymous socket refusal), timezone awareness (aware round-trips
through SQLite, and a heap holding patients both with and without deadlines),
donor CRUD and search, the priority queue (ordering, restart recovery, no
double-serving), inventory thresholds, transactions in both directions, every
page rendering, and the validation helpers.

---

## Docker

```bash
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
docker compose up -d --build
docker compose logs -f web
```

The image runs gunicorn with a single eventlet worker — Socket.IO needs
WebSocket-capable workers, and multiple workers would split clients across
processes without a shared message queue. The SQLite database lives in a named
volume so it survives `docker compose down`.

---

## Seeding from the legacy CSV files

The project originally stored data in flat files under `data/`. To import them:

```bash
python migrate_csv_to_db.py
```

Duplicate IDs are skipped, so it is safe to re-run.

---

## Security notes

- **CSRF.** `Flask-WTF`'s `CSRFProtect` covers every `POST`. `base.html` renders
  the token into a `<meta name="csrf-token">`, and `static/js/main.js` attaches
  it as `X-CSRFToken` to every request — so no form needs a hidden field, and
  page-level scripts must use `window.LifeLink.post()` rather than calling
  `fetch` directly or they will be refused with a 400.
- A stale or missing token is answered as JSON (`{"status": "csrf_error"}`), not
  Flask-WTF's default HTML page, so the UI can surface it as a readable message.
- `WTF_CSRF_TIME_LIMIT` is `None`: the token lives as long as the session, whose
  own lifetime (`SESSION_TIMEOUT`) is the real bound. A separate expiry would
  silently break a dashboard left open.
- **Signing out is a `POST`** carrying the token — a `GET` logout can be
  triggered by any third-party page.
- `/healthz` is `@csrf.exempt`: it is a liveness probe, not a browser form.

### Roles

Registration is open, so `@login_required` alone is not a guard — without a
role check any stranger could register and then delete records. Permissions
collapse to two gates rather than a per-route matrix:

| Role | May |
|---|---|
| `staff` | **Read only.** What a new registration receives. |
| `nurse`, `doctor` | + register donors and patients, record transactions, serve the queue |
| `admin` | + delete records |

Routes are gated with `@write_required` / `@admin_required`, which answer JSON
for the fetch layer and the themed error page for a navigation. The UI hides
what the current role cannot do, but **the gate is server-side** — bypassing the
hidden form still returns 403.

Grant access from the command line:

```bash
flask list-users
flask set-role alice nurse
```

### Real-time

Socket.IO events carry patient names, blood groups and urgency levels, so
`connect` refuses any session that is not signed in, and `request_queue_update`
re-checks (a session can expire while the socket stays open).

### Datetimes

Every datetime is timezone-aware UTC. `models.utcnow()` replaces the deprecated
`datetime.utcnow()`, and `models.UTCDateTime` is a `TypeDecorator` that keeps
the two directions symmetric:

- SQLite has no native datetime type — SQLAlchemy stores a formatted string and
  **drops any tzinfo**, so an aware value written to the database would come
  back naive. Arithmetic between that and a fresh `utcnow()` raises `TypeError`.
- The decorator stores naive UTC (byte-identical to what the pre-migration code
  wrote, so **existing databases keep working with no migration**) and re-attaches
  `tzinfo=UTC` on load.

If you add a datetime column, use `UTCDateTime`, not `db.DateTime`. `pytest.ini`
turns any new `DeprecationWarning` from `app`, `models` or `utils` into an error
so a naive value cannot creep back in.

## Known limitations

- **Single-process queue.** `PatientQueue` is per-process. Running more than one
  worker needs the heap moved into the database or a shared store.
- **No rate limiting on login.** Passwords can be guessed indefinitely;
  failures are audited but nothing acts on them. `Flask-Limiter` would close it.
- **No license file.** The repository has no `LICENSE`, so default copyright
  applies. Add one if you want others to reuse the code.

---

## Credits

Built by Rajwardhan Shinde, Amey Shirbhate, Roshan Shinde and Anas S.
Team notes are in [`docs/notes/`](docs/notes/).
