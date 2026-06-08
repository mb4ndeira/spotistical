from __future__ import annotations
import os, time, requests, pandas as pd
from IPython.display import clear_output
from style import _bar

API = os.environ.get('SPOTISTICAL_API', 'http://localhost:8000')


def check_api() -> None:
    try:
        h = requests.get(f'{API}/health', timeout=5).json()
        print(f"API {h['status']}  ·  DB {h['db']}")
    except Exception as e:
        print(f'API indisponível: {e}')


def ingest_tracks(engine) -> None:
    existing = pd.read_sql('SELECT count(*) AS n FROM tracks', engine).iloc[0]['n']
    if existing > 0:
        print(f'Tracks já carregadas ({existing:,} linhas) — pulando.')
        return
    print('Iniciando ingest...')
    r = requests.post(f'{API}/ingest/tracks', timeout=10)
    r.raise_for_status()
    print(r.json()['message'])
    while True:
        s = requests.get(f'{API}/ingest/tracks/status', timeout=5).json()
        clear_output(wait=True)
        if not s['running']:
            count = pd.read_sql('SELECT count(*) AS n FROM tracks', engine).iloc[0]['n']
            print(f'concluído: {count:,} linhas em tracks')
            break
        time.sleep(8)


def ingest_news(engine, date_from: str, date_to: str) -> None:
    cov = pd.read_sql('SELECT count(*) AS n FROM news_events', engine).iloc[0]['n']
    s   = requests.get(f'{API}/ingest/news/status', timeout=30).json()
    db_cov = s.get('db_coverage') or {}
    full_coverage = (
        db_cov.get('earliest') is not None
        and db_cov.get('earliest', '9999') <= date_from
        and db_cov.get('latest',   '0000') >= date_to
    )
    if full_coverage and not s.get('running'):
        print(f'Notícias já cobertas ({cov:,} artigos) — pulando.')
    elif not s.get('running'):
        print(f'Iniciando backfill {date_from} → {date_to}...')
        r = requests.post(f'{API}/ingest/news',
                          params={'date_from': date_from, 'date_to': date_to}, timeout=10)
        r.raise_for_status()
        print(r.json()['message'])
    else:
        print('Backfill já em execução — monitorando...')


def monitor_news() -> None:
    while True:
        try:
            s   = requests.get(f'{API}/ingest/news/status', timeout=30).json()
            cov = s.get('db_coverage') or {}
            clear_output(wait=True)
            print(f"  rodando    : {s['running']}")
            if s['running']:
                print(f"  progresso  : {_bar(s['weeks_done'], s['weeks_total'])}")
                print(f"  semana     : {s.get('week_current') or '—'}")
            print(f"  inseridos  : {s['articles_inserted_bulk']:,}")
            if cov.get('total_articles'):
                print(f"  total no BD: {cov['total_articles']:,}  ({cov['earliest']} → {cov['latest']})")
            if s.get('last_error'):
                print(f"  erro       : {s['last_error']}")
            if not s['running']:
                break
        except requests.exceptions.Timeout:
            print('  status timeout — api ocupada, tentando em 15s...')
        time.sleep(15)


def lock_sources(engine) -> None:
    trigger_existe = pd.read_sql("""
        SELECT count(*) AS n FROM pg_trigger
        WHERE  tgname = 'trg_prevent_tracks_modification'
    """, engine).iloc[0]['n'] > 0
    if trigger_existe:
        print('Fontes já protegidas — pulando.')
        return
    t_running = requests.get(f'{API}/ingest/tracks/status', timeout=30).json()['running']
    n_running = requests.get(f'{API}/ingest/news/status',   timeout=30).json()['running']
    if t_running or n_running:
        print('Aguarde o ingest terminar antes de fazer o lock.')
    else:
        r = requests.post(f'{API}/ingest/lock-sources', timeout=15)
        r.raise_for_status()
        print(r.json()['message'])


def show_stats(engine) -> None:
    stats = pd.read_sql("""
        SELECT 'tracks'        AS tabela, count(*)::text AS linhas FROM tracks
        UNION ALL SELECT 'news_events',  count(*)::text FROM news_events
        UNION ALL SELECT 'song_clusters',count(*)::text FROM song_clusters
        UNION ALL SELECT 'track_lyrics', count(*)::text FROM track_lyrics
        UNION ALL SELECT 'insights',     count(*)::text FROM insights
    """, engine)
    tracks_range = pd.read_sql("""
        SELECT min(snapshot_date)::text AS primeiro_dia,
               max(snapshot_date)::text AS ultimo_dia,
               count(DISTINCT country)  AS paises
        FROM tracks
    """, engine)
    news_range = pd.read_sql("""
        SELECT min(published_at)::date::text AS primeiro_artigo,
               max(published_at)::date::text AS ultimo_artigo,
               count(DISTINCT published_at::date) AS dias_cobertos
        FROM news_events
    """, engine)
    locked = pd.read_sql("""
        SELECT count(*) AS n FROM pg_trigger WHERE tgname LIKE 'trg_prevent_%'
    """, engine).iloc[0]['n']
    print('Linhas por tabela')
    print(stats.to_string(index=False))
    print()
    print('Cobertura de tracks')
    print(tracks_range.to_string(index=False))
    print()
    print('Cobertura de notícias')
    print(news_range.to_string(index=False))
    print()
    print(f'Proteção de fontes: {locked} trigger(s)  ({"OK" if locked >= 2 else "PENDENTE"})')
