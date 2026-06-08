from __future__ import annotations
import pathlib
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


# ── Task 2.5 · Lyric Clustering ────────────────────────────────────────────

_CACHE_DIR = pathlib.Path(__file__).parent.parent / 'data'
_EMB_CACHE  = _CACHE_DIR / 'lyric_embeddings.npz'


def compute_lyric_embeddings(engine, model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2',
                              batch_size: int = 256, use_cache: bool = True) -> tuple[pd.DataFrame, 'np.ndarray']:
    import numpy as np
    df = pd.read_sql("""
        SELECT tl.spotify_id, tl.lyrics_raw, tl.language,
               t.name, t.artists
        FROM   track_lyrics tl
        JOIN   (SELECT DISTINCT ON (spotify_id) spotify_id, name, artists
                FROM tracks ORDER BY spotify_id) t USING (spotify_id)
        WHERE  tl.failed = FALSE AND tl.lyrics_raw IS NOT NULL
        ORDER  BY tl.spotify_id
    """, engine)
    if df.empty:
        print('Sem letras disponíveis.')
        return df, np.array([])

    if use_cache and _EMB_CACHE.exists():
        cached = np.load(_EMB_CACHE, allow_pickle=True)
        cached_ids = cached['spotify_ids'].tolist()
        if cached_ids == df['spotify_id'].tolist():
            print(f'Cache carregado — {len(df):,} embeddings  (delete {_EMB_CACHE.name} para recomputar)')
            return df, cached['vecs']
        print('Cache desatualizado — recomputando...')

    from sentence_transformers import SentenceTransformer
    print(f'Carregando modelo {model_name}...')
    model = SentenceTransformer(model_name)
    print(f'Computando embeddings para {len(df):,} letras...')
    texts = df['lyrics_raw'].str[:1000].tolist()
    vecs = model.encode(texts, batch_size=batch_size, show_progress_bar=True,
                        normalize_embeddings=True)
    _CACHE_DIR.mkdir(exist_ok=True)
    np.savez_compressed(_EMB_CACHE, vecs=vecs, spotify_ids=np.array(df['spotify_id'].tolist()))
    print(f'Cache salvo em {_EMB_CACHE}  ·  shape: {vecs.shape}')
    return df, vecs


def find_best_k(X: 'np.ndarray', k_min: int = 5, k_max: int = 40) -> int:
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    rng    = np.random.default_rng(42)
    n      = len(X)
    sample = min(n, 5_000)
    scores: dict[int, float] = {}
    print(f'Testando K de {k_min} a {k_max}...')
    for k in range(k_min, k_max + 1):
        km     = KMeans(n_clusters=k, random_state=42, n_init='auto')
        labels = km.fit_predict(X)
        idx    = rng.choice(n, sample, replace=False) if n > sample else None
        X_s    = X[idx] if idx is not None else X
        L_s    = labels[idx] if idx is not None else labels
        scores[k] = float(silhouette_score(X_s, L_s, metric='cosine'))
        print(f'  K={k:2d}  silhouette={scores[k]:.4f}', end='\r')
    print()
    best_k = max(scores, key=lambda k: scores[k])
    print(f'Melhor K: {best_k}  (silhouette={scores[best_k]:.4f})')

    ks = list(range(k_min, k_max + 1))
    vals = [scores[k] for k in ks]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(ks, vals, color=GREEN, linewidth=2, marker='o', markersize=4)
    ax.axvline(best_k, color=MUTED, linestyle='--', linewidth=1)
    ax.text(best_k + 0.3, max(vals) * 0.99, f'K={best_k}', color=MUTED, fontsize=9)
    ax.set_xlabel('K')
    ax.set_ylabel('Silhouette score')
    ax.set_title('Escolha de K — silhouette score por número de clusters')
    plt.tight_layout()
    plt.show()
    return best_k


def cluster_lyrics(df: pd.DataFrame, X: 'np.ndarray', n_clusters: int = 20,
                   method: str = 'kmeans') -> pd.DataFrame:
    import numpy as np
    if method == 'kmeans':
        from sklearn.cluster import KMeans
        print(f'KMeans com {n_clusters} clusters...')
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = km.fit_predict(X)
    elif method == 'dbscan':
        from sklearn.cluster import DBSCAN
        print('DBSCAN...')
        labels = DBSCAN(eps=0.3, min_samples=5, metric='cosine', n_jobs=-1).fit_predict(X)
    else:
        raise ValueError(f'method deve ser "kmeans" ou "dbscan", não "{method}"')
    df = df.copy()
    df['lyric_cluster_id'] = labels
    n_clusters_found = len(set(labels)) - (1 if -1 in labels else 0)
    print(f'{n_clusters_found} clusters encontrados  ·  '
          f'{(labels == -1).sum():,} outliers (-1)')
    return df


def compute_lyric_umap(df: pd.DataFrame, X: 'np.ndarray') -> pd.DataFrame:
    import umap
    print('Calculando UMAP 2D para letras...')
    reducer = umap.UMAP(n_components=2, n_neighbors=15, min_dist=0.1,
                        metric='cosine', random_state=42)
    coords = reducer.fit_transform(X)
    df = df.copy()
    df['umap_lyric_x'] = coords[:, 0].astype(float)
    df['umap_lyric_y'] = coords[:, 1].astype(float)
    return df


def label_lyric_clusters(df: pd.DataFrame, X: 'np.ndarray',
                          stop_words_lang: str = 'english') -> tuple[pd.DataFrame, dict]:
    from bertopic import BERTopic
    from sklearn.feature_extraction.text import CountVectorizer
    texts = df['lyrics_raw'].str[:500].fillna('').tolist()
    vectorizer = CountVectorizer(stop_words=stop_words_lang, min_df=2, ngram_range=(1, 2))
    topic_model = BERTopic(
        vectorizer_model=vectorizer,
        nr_topics='auto',
        calculate_probabilities=False,
        verbose=False,
    )
    topics, _ = topic_model.fit_transform(texts, X)
    info = topic_model.get_topic_info()
    cluster_labels: dict[int, str] = {}
    for _, row in info.iterrows():
        tid = int(row.Topic)
        cluster_labels[tid] = str(row.get('Name', row.get('Representation', f'cluster_{tid}')))
    df = df.copy()
    df['lyric_cluster_label'] = df['lyric_cluster_id'].map(cluster_labels)
    print(f'{len(info) - 1} rótulos de cluster gerados via BERTopic')
    return df, cluster_labels


def save_lyric_clusters(df: pd.DataFrame, run_id: str, admin_engine) -> None:
    required = {'spotify_id', 'lyric_cluster_id', 'umap_lyric_x', 'umap_lyric_y'}
    if not required.issubset(df.columns):
        print(f'Faltam colunas: {required - set(df.columns)}')
        return
    written = 0
    with admin_engine.begin() as conn:
        for _, row in df.iterrows():
            result = conn.execute(text("""
                UPDATE song_clusters SET
                    lyric_cluster_id    = :cid,
                    lyric_cluster_label = :clabel,
                    umap_lyric_x        = :ux,
                    umap_lyric_y        = :uy,
                    clustering_run_id   = :run
                WHERE spotify_id = :sid
            """), {
                'sid':    row['spotify_id'],
                'cid':    int(row['lyric_cluster_id']),
                'clabel': row.get('lyric_cluster_label'),
                'ux':     float(row['umap_lyric_x']),
                'uy':     float(row['umap_lyric_y']),
                'run':    run_id,
            })
            written += result.rowcount
    print(f'{written:,} linhas atualizadas em song_clusters  (run_id={run_id})')


def plot_lyric_umap(df: pd.DataFrame) -> None:
    import numpy as np
    if 'umap_lyric_x' not in df.columns:
        print('Execute compute_lyric_umap() primeiro.')
        return
    n_clusters = df['lyric_cluster_id'].nunique()
    palette = plt.cm.get_cmap('tab20', n_clusters)
    cid_map = {c: i for i, c in enumerate(sorted(df['lyric_cluster_id'].unique()))}
    fig, ax = plt.subplots(figsize=(11, 8))
    for cid, grp in df.groupby('lyric_cluster_id'):
        label = str(grp['lyric_cluster_label'].iloc[0]) if 'lyric_cluster_label' in df.columns else f'c{cid}'
        ax.scatter(grp['umap_lyric_x'], grp['umap_lyric_y'], s=8, alpha=0.5,
                   color=palette(cid_map[cid]), label=label[:30], edgecolors='none')
    ax.set_title('UMAP de letras — cor = cluster lírico')
    ax.set_xlabel('UMAP 1')
    ax.set_ylabel('UMAP 2')
    ax.legend(markerscale=3, fontsize=7, ncol=3, loc='upper right')
    plt.tight_layout()
    plt.show()


def plot_cluster_sizes(df: pd.DataFrame) -> None:
    agg = {'n': ('spotify_id', 'count')}
    if 'lyric_cluster_label' in df.columns:
        agg['label'] = ('lyric_cluster_label', 'first')
    counts = df.groupby('lyric_cluster_id').agg(**agg).sort_values('n', ascending=True)
    fig, ax = plt.subplots(figsize=(9, max(4, len(counts) * 0.35)))
    labels = counts['label'].astype(str).str[:40] if 'label' in counts.columns else counts.index.astype(str)
    ax.barh(labels, counts['n'], color=GREEN, edgecolor='none')
    ax.set_xlabel('Faixas')
    ax.set_title('Tamanho dos clusters líricos')
    plt.tight_layout()
    plt.show()


def plot_audio_lyric_cross(engine) -> None:
    df = pd.read_sql("""
        SELECT audio_cluster_id, lyric_cluster_id, count(*) AS n
        FROM   song_clusters
        WHERE  audio_cluster_id IS NOT NULL AND lyric_cluster_id IS NOT NULL
        GROUP  BY audio_cluster_id, lyric_cluster_id
    """, engine)
    if df.empty:
        print('Sem dados de cross-referência ainda.')
        return
    pivot = df.pivot(index='audio_cluster_id', columns='lyric_cluster_id', values='n').fillna(0)
    import numpy as np
    fig, ax = plt.subplots(figsize=(14, 8))
    im = ax.imshow(pivot.values, aspect='auto', cmap='YlGn', interpolation='nearest')
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([f'L{c}' for c in pivot.columns], fontsize=7, rotation=90)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([f'A{r}' for r in pivot.index], fontsize=7)
    ax.set_xlabel('Cluster lírico')
    ax.set_ylabel('Cluster de áudio')
    ax.set_title('Cross-referência: áudio × lírica')
    plt.colorbar(im, ax=ax, label='Faixas')
    plt.tight_layout()
    plt.show()


def show_cluster_sample(df: pd.DataFrame, cluster_id: int, n: int = 8) -> None:
    sample = df[df['lyric_cluster_id'] == cluster_id][['name', 'artists', 'lyrics_raw']].head(n)
    sample = sample.copy()
    sample['trecho'] = sample['lyrics_raw'].str[:120]
    pd.set_option('display.max_colwidth', 90)
    print(sample[['name', 'artists', 'trecho']].to_string(index=False))
