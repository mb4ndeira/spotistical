set dotenv-load
set shell := ["bash", "-c"]

# ── Config ─────────────────────────────────────────────────────────────────────
compose := "docker compose -f " + justfile_directory() + "/docker-compose.yml"

# ── Default ────────────────────────────────────────────────────────────────────
default:
    @just --list

# ── Imports ────────────────────────────────────────────────────────────────────
import 'just/setup.just'
import 'just/services.just'
import 'just/db.just'
