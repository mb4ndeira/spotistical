# spotistical — notebooks

Human interface to the data pipeline. Each notebook triggers the corresponding
API use case, streams live progress, and visualises the results.

## Idempotency contract

**Every notebook is safe to re-run from top to bottom at any time.**

Each step checks whether its work is already done before touching anything:

| Step type | Guard |
|---|---|
| DB ingest | `SELECT count(*) FROM table` → skip if rows present |
| Date-range backfill | compare `min/max` in DB to target range → skip if covered |
| DB object (trigger, index…) | query `pg_trigger` / `pg_class` → skip if exists |
| Background job | `GET /…/status` → attach to running job, don't start a duplicate |

The API endpoints are also idempotent (`ON CONFLICT DO NOTHING` / `DO UPDATE`),
so even an accidental double-run won't corrupt data.

## Running

```bash
just notebooks          # launches Jupyter Lab on port 8888
```

Requires the `spotistical` pyenv environment (created by `pyenv virtualenv 3.12.2 spotistical`)
with `notebooks/requirements.txt` installed.

## Index

| Notebook | What it does |
|---|---|
| `00_pipeline.ipynb` | Tracks ingest · news backfill · lock source tables · verify |
| `01_audio_clustering.ipynb` | K-Means sweep · UMAP · per-country cluster exploration |

## Shared helpers

| File | Purpose |
|---|---|
| `db.py` | Sync SQLAlchemy engines (`engine` = app user, `admin_engine` = admin user) |
| `requirements.txt` | Notebook-only deps (jupyterlab, seaborn, plotly, psycopg2…) |
