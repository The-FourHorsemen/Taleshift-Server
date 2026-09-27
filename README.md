# Taleshift Server

Backend for Taleshift — adaptive read-aloud practice with ASR, analysis, and Supabase persistence.

## Prerequisites

- Python 3.12+
- A [Supabase](https://supabase.com) project (URL + `service_role` key)
- Optional: working microphone if you use local audio capture (`app/helper/recorder.py`)

## Setup

```bash
# from the repo root
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## Configure Supabase

1. In the [Supabase dashboard](https://supabase.com/dashboard) open your project → **Project Settings → API**.
2. Copy the **Project URL** and the **`service_role`** key (server-only; never put this in a browser client).
3. Create a local env file:

```bash
cp .env.example .env
```

4. Edit `.env`:

```env
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_KEY=YOUR_SERVICE_ROLE_KEY
```

5. Apply the starter schema. In the dashboard open **SQL → New query**, paste the contents of `supabase/migrations/20260927000000_init_taleshift.sql`, and run it.

This creates `learners`, `sessions`, `activities`, and `results` with RLS enabled.

## Verify the database connection

```bash
source .venv/bin/activate
python scripts/verify_supabase.py
```

You should see `Connected to Supabase.` If `learners` was created, the script also confirms that table is reachable.

## Run the API

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000/docs` for the interactive OpenAPI UI (once routes are registered in `app/main.py`).

## Project layout

| Path | Purpose |
|------|---------|
| `app/main.py` | FastAPI entrypoint |
| `app/config.py` | Loads `.env` (`SUPABASE_URL`, `SUPABASE_KEY`) |
| `app/db/` | Shared Supabase client + repositories |
| `app/api/routes/` | HTTP routes (sessions, activities, audio, adapt) |
| `app/asr/` | ASR / alignment helpers |
| `app/analysis/` | Reading-signal analysis |
| `supabase/migrations/` | SQL schema for Supabase |
| `scripts/verify_supabase.py` | Connection smoke test |

## Common issues

- **`ValidationError` for `SUPABASE_URL` / `SUPABASE_KEY`** — `.env` is missing or incomplete; copy from `.env.example` and fill in real values.
- **`learners table not ready`** — schema not applied yet; run the migration SQL in the Supabase SQL editor.
- **Import errors after clone** — activate the venv and re-run `pip install -r requirements.txt`.
