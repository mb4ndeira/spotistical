from __future__ import annotations
import time, requests
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import text
from IPython.display import clear_output
from style import GREEN, MUTED, _bar

API = 'http://localhost:8000'


def run_lyrics_fetch(engine, retry_failed: bool = False) -> None:
    s = requests.get(f'{API}/lyrics/status', timeout=5).json()
    if s['running']:
        print('Já em execução — monitorando...')
    else:
        cov   = requests.get(f'{API}/lyrics/coverage', timeout=5).json()
        total = pd.read_sql('SELECT count(DISTINCT spotify_id) AS n FROM tracks', engine).iloc[0]['n']
        done  = cov.get('with_lyrics', 0) + (cov.get('without_lyrics', 0) if not retry_failed else 0)
        if done >= total and not retry_failed:
            print(f'Todas as {total:,} faixas já processadas ({cov["coverage_pct"]}% com letras).')
            return
        r = requests.post(f'{API}/lyrics/fetch',
                          params={'retry_failed': str(retry_failed).lower()}, timeout=10)
        r.raise_for_status()
        print(r.json()['message'])

    while True:
        s = requests.get(f'{API}/lyrics/status', timeout=5).json()
        clear_output(wait=True)
        print(f"  etapa     : {s['stage']}")
        if s['tracks_total'] > 0:
            print(f"  progresso : {_bar(s['tracks_done'], s['tracks_total'])}")
        print(f"  com letra : {s['tracks_found']:,}")
        print(f"  sem letra : {s['tracks_failed']:,}")
        print(f"  puladas   : {s['tracks_skipped']:,}")
        if s.get('current_track'):
            print(f"  atual     : {s['current_track']}")
        if not s['running']:
            print('\nConcluído.' if s['stage'] == 'done' else '\nParado.')
            break
        time.sleep(5)


def show_coverage() -> None:
    cov = requests.get(f'{API}/lyrics/coverage', timeout=5).json()
    if 'error' in cov:
        print(f'Erro: {cov["error"]}')
        return
    print(f'  Total em track_lyrics : {cov["total"]:,}')
    print(f'  Com letra             : {cov["with_lyrics"]:,}  ({cov["coverage_pct"]}%)')
    print(f'  Sem letra             : {cov["without_lyrics"]:,}')
    if cov['fail_reasons']:
        print('\n  Motivos de falha:')
        for r in cov['fail_reasons']:
            print(f'    {r["fail_reason"]:30s} {r["n"]:,}')


def plot_coverage_by_popularity(engine) -> None:
    df_cov = pd.read_sql("""
        SELECT t.appearances,
               (tl.failed = FALSE AND tl.lyrics_raw IS NOT NULL) AS tem_letra
        FROM (
            SELECT spotify_id, count(*) AS appearances FROM tracks GROUP BY spotify_id
        ) t
        LEFT JOIN track_lyrics tl USING (spotify_id)
    """, engine)
    if df_cov.empty:
        return
    bins   = [0, 5, 20, 50, 100, 300, 10_000]
    labels = ['1–5', '6–20', '21–50', '51–100', '101–300', '300+']
    df_cov['faixa'] = pd.cut(df_cov['appearances'], bins=bins, labels=labels)
    summary = (df_cov.groupby('faixa', observed=True)
               .agg(total=('tem_letra', 'count'), com_letra=('tem_letra', 'sum'))
               .assign(pct=lambda x: (x.com_letra / x.total * 100).round(1)))
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(summary.index.astype(str), summary.pct, color=GREEN, edgecolor='none', alpha=0.9)
    for i, (_, row) in enumerate(summary.iterrows()):
        ax.text(i, row.pct + 0.5, f'{row.pct}%', ha='center', fontsize=8)
    ax.set_xlabel('Aparições no chart')
    ax.set_ylabel('% com letra')
    ax.set_title('Cobertura de letras por popularidade')
    ax.set_ylim(0, 110)
    plt.tight_layout()
    plt.show()


def load_lyrics(engine) -> pd.DataFrame:
    df = pd.read_sql("""
        SELECT tl.spotify_id, tl.lyrics_raw, tl.language, t.name, t.artists
        FROM   track_lyrics tl
        JOIN   (SELECT DISTINCT ON (spotify_id) spotify_id, name, artists
                FROM tracks ORDER BY spotify_id) t USING (spotify_id)
        WHERE  tl.failed = FALSE AND tl.lyrics_raw IS NOT NULL
    """, engine)
    if df.empty:
        print('Sem letras ainda — execute run_lyrics_fetch() primeiro.')
    else:
        df['palavras'] = df['lyrics_raw'].str.split().str.len()
        print(f'{len(df):,} faixas com letra')
    return df


def plot_lyrics_exploration(df_lyrics: pd.DataFrame) -> None:
    if df_lyrics.empty:
        return
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].hist(df_lyrics['palavras'].clip(upper=800), bins=50,
                 color=GREEN, edgecolor='none', alpha=0.85)
    axes[0].set_xlabel('Número de palavras')
    axes[0].set_title('Tamanho das letras')
    if df_lyrics['language'].notna().any():
        lang = df_lyrics['language'].value_counts().head(12)
        axes[1].barh(lang.index, lang.values, color=GREEN, edgecolor='none')
        axes[1].set_title('Idiomas (top 12)')
        axes[1].invert_yaxis()
    else:
        axes[1].text(0.5, 0.5, 'Execute detect_languages() para ver idiomas',
                     ha='center', va='center', color=MUTED, transform=axes[1].transAxes)
    plt.tight_layout()
    plt.show()


def show_top_lyrics(engine) -> pd.DataFrame:
    sample = pd.read_sql("""
        SELECT t.name, t.artists, count(*) AS aparicoes,
               left(tl.lyrics_raw, 150) AS trecho
        FROM   track_lyrics tl
        JOIN   tracks t USING (spotify_id)
        WHERE  tl.failed = FALSE
        GROUP  BY t.name, t.artists, tl.lyrics_raw
        ORDER  BY aparicoes DESC
        LIMIT  10
    """, engine)
    pd.set_option('display.max_colwidth', 80)
    return sample


def detect_languages(df_lyrics: pd.DataFrame, engine) -> None:
    try:
        from langdetect import detect
    except ImportError:
        print('langdetect não instalado — execute: pip install langdetect')
        return
    if df_lyrics.empty:
        return
    pendentes = df_lyrics[df_lyrics['language'].isna()]
    print(f'{len(pendentes):,} faixas sem idioma detectado')
    detectados = []
    for _, row in pendentes.iterrows():
        try:
            lang = detect(row['lyrics_raw'][:500])
        except Exception:
            lang = 'unknown'
        detectados.append({'spotify_id': row['spotify_id'], 'language': lang})
    if detectados:
        with engine.begin() as conn:
            for r in detectados:
                conn.execute(
                    text('UPDATE track_lyrics SET language = :lang WHERE spotify_id = :sid'),
                    {'lang': r['language'], 'sid': r['spotify_id']}
                )
        import pandas as _pd
        df_det = _pd.DataFrame(detectados)
        print(f'Idioma salvo para {len(detectados):,} faixas')
        print(df_det['language'].value_counts().head(10))
