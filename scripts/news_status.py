#!/usr/bin/env python3
"""Pretty-print the news backfill status endpoint."""
import json, sys

d   = json.load(sys.stdin)
cov = d.get("db_coverage") or {}

print()
print("  ── Backfill progress ─────────────────────────")
print(f"  Running       : {d['running']}")
if d["running"]:
    done  = d["weeks_done"]
    total = d["weeks_total"]
    pct   = round(done / total * 100) if total else 0
    bar   = ("█" * (pct // 5)).ljust(20)
    print(f"  Current week  : {d['week_current']}")
    print(f"  Progress      : {done}/{total} weeks  [{bar}] {pct}%")
    print(f"  Skipped       : {d['weeks_skipped']} (already had data)")
print(f"  Inserted      : {d['articles_inserted']:,} articles this run")
if d.get("last_error"):
    print(f"  Last error    : {d['last_error']}")

print()
print("  ── DB coverage ───────────────────────────────")
if cov and cov.get("total_articles"):
    print(f"  Total articles: {cov['total_articles']:,}")
    print(f"  Days covered  : {cov['days_covered']}")
    print(f"  Range         : {cov['earliest']} → {cov['latest']}")
else:
    print("  (no articles in DB yet)")
print()
