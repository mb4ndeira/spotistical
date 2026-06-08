from __future__ import annotations
import time, requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import clear_output
from style import GREEN, MUTED, _bar

API = 'http://localhost:8000'

FEATURES = [
    'danceability', 'energy', 'key', 'loudness', 'mode',
    'speechiness', 'acousticness', 'instrumentalness',
    'liveness', 'valence', 'tempo', 'time_signature',
]


def run_clustering(include_global: bool = False) -> None:
    s = requests.get(f'{API}/clustering/audio/status', timeout=5).json()
    if s['running']:
        print('Já em execução — monitorando...')
    else:
        r = requests.post(f'{API}/clustering/audio',
                          params={'include_global': str(include_global).lower()}, timeout=5)
        r.raise_for_status()
        print(r.json()['message'])
    while True:
        s = requests.get(f'{API}/clustering/audio/status', timeout=5).json()
        clear_output(wait=True)
        print(f"  etapa     : {s['stage']}")
        print(f"  país      : {s['country_current'] or '—'}")
        print(f"  países    : {_bar(s['countries_done'], s['countries_total'])}")
        if s['countries_skipped']:
            print(f"  pulados   : {s['countries_skipped']}")
        print(f"  k atual   : {s['k_current'] or '—'}")
        print(f"  melhor k  : {s['k_best_this'] or '—'}")
        print(f"  gravados  : {s['tracks_persisted']:,}")
        if not s['running']:
            print('\nConcluído.' if s['stage'] == 'done' else '\nErro.')
            break
        time.sleep(4)


def load_features(engine) -> pd.DataFrame:
    feat_sql = ', '.join(f'AVG({f})::float4 AS {f}' for f in FEATURES)
    not_null = ' AND '.join(f'AVG({f}) IS NOT NULL' for f in FEATURES)
    df = pd.read_sql(f"""
        SELECT spotify_id, {feat_sql}
        FROM   tracks
        GROUP  BY spotify_id
        HAVING {not_null}
    """, engine)
    print(f'{len(df):,} faixas únicas com features completos')
    return df


def plot_feature_distributions(df_all: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 4, figsize=(15, 8))
    for ax, feat in zip(axes.flat, FEATURES):
        ax.hist(df_all[feat].dropna(), bins=40, color=GREEN, alpha=0.85, edgecolor='none')
        ax.set_title(feat, fontsize=8, color=MUTED)
        ax.set_yticks([])
    plt.tight_layout()
    plt.show()


def plot_feature_correlations(df_all: pd.DataFrame) -> None:
    corr = df_all[FEATURES].corr()
    fig, ax = plt.subplots(figsize=(9, 7))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, ax=ax, cmap='RdYlGn', center=0, vmin=-1, vmax=1,
                linewidths=0.3, linecolor='#e5e7eb', annot=True, fmt='.2f', annot_kws={'size': 6})
    ax.set_title('Correlação entre features', fontsize=12)
    plt.tight_layout()
    plt.show()


def load_k_data(engine) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT country,
               max(audio_cluster_id) + 1 AS k,
               count(*)                  AS tracks
        FROM   song_clusters
        WHERE  audio_cluster_id IS NOT NULL AND country <> 'GL'
        GROUP  BY country
        ORDER  BY k DESC, country
    """, engine)


def plot_k_by_market(k_df: pd.DataFrame) -> None:
    if k_df.empty:
        print('Sem dados — execute run_clustering() primeiro.')
        return
    k_min, k_max = k_df.k.min(), k_df.k.max()
    print(f'{len(k_df)} mercados  ·  k {k_min}–{k_max}  ·  mediana {k_df.k.median():.0f}')

    norm_k = [(k - k_min) / (k_max - k_min) for k in k_df.k]
    colors = [plt.cm.RdYlGn(v) for v in norm_k]
    fig, ax = plt.subplots(figsize=(17, 4))
    ax.bar(k_df.country, k_df.k, color=colors, edgecolor='none', width=0.75)
    ax.set_xlabel('Mercado')
    ax.set_ylabel('k')
    ax.set_title('Clusters por mercado  —  verde = mais diverso')
    ax.tick_params(axis='x', labelsize=7, rotation=45)
    ax.set_ylim(0, k_max + 2)
    plt.tight_layout()
    plt.show()

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    top = k_df.head(8)
    bot = k_df.tail(8).sort_values('k')
    axes[0].barh(top.country, top.k, color=GREEN, edgecolor='none')
    axes[0].set_title('Mais diversos')
    axes[0].invert_yaxis()
    axes[1].barh(bot.country, bot.k, color='#d1d5db', edgecolor='none')
    axes[1].set_title('Mais homogêneos')
    axes[1].invert_yaxis()
    plt.tight_layout()
    plt.show()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.scatter(k_df.tracks, k_df.k, color=GREEN, alpha=0.6, s=40, edgecolors='none')
    for _, row in k_df.iterrows():
        ax.annotate(row.country, (row.tracks, row.k), textcoords='offset points',
                    xytext=(3, 2), fontsize=6, color=MUTED)
    ax.set_xlabel('Faixas únicas no mercado')
    ax.set_ylabel('k escolhido')
    ax.set_title('Mais faixas → mais clusters?')
    plt.tight_layout()
    plt.show()

    return k_df.style.background_gradient(subset=['k'], cmap='RdYlGn')


def load_umap_data(engine, pais: str) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT sc.spotify_id, sc.audio_cluster_id, sc.umap_audio_x, sc.umap_audio_y,
               t.name, t.artists
        FROM   song_clusters sc
        JOIN   (SELECT DISTINCT ON (spotify_id) spotify_id, name, artists
                FROM tracks WHERE country = %(c)s) t USING (spotify_id)
        WHERE  sc.country = %(c)s AND sc.audio_cluster_id IS NOT NULL
    """, engine, params={'c': pais})


def plot_umap(engine, pais: str) -> pd.DataFrame:
    df_c = load_umap_data(engine, pais)
    if df_c.empty:
        print(f'Sem clusters para {pais}.')
        return df_c
    n_c = df_c.audio_cluster_id.nunique()
    palette = plt.cm.get_cmap('tab20', n_c)
    fig, ax = plt.subplots(figsize=(10, 7))
    for cid in sorted(df_c.audio_cluster_id.unique()):
        sub = df_c[df_c.audio_cluster_id == cid]
        ax.scatter(sub.umap_audio_x, sub.umap_audio_y,
                   s=16, alpha=0.6, color=palette(cid), label=f'c{cid}', edgecolors='none')
    ax.set_title(f'UMAP — {pais}  (k={n_c})')
    ax.set_xlabel('UMAP 1')
    ax.set_ylabel('UMAP 2')
    ax.legend(markerscale=2, fontsize=7, ncol=4)
    plt.tight_layout()
    plt.show()
    return df_c


def show_popular_tracks(engine) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT t.spotify_id, t.name, t.artists, count(DISTINCT t.country) AS mercados
        FROM   tracks t
        GROUP  BY t.spotify_id, t.name, t.artists
        ORDER  BY mercados DESC
        LIMIT  15
    """, engine)


def plot_cross_market(engine, track_id: str, track_name: str) -> pd.DataFrame:
    cross = pd.read_sql("""
        SELECT country, audio_cluster_id
        FROM   song_clusters
        WHERE  spotify_id = %(tid)s
          AND  audio_cluster_id IS NOT NULL AND country <> 'GL'
        ORDER  BY country
    """, engine, params={'tid': track_id})
    print(f'"{track_name}"  —  {len(cross)} mercados  ·  {cross.audio_cluster_id.nunique()} cluster IDs distintos')
    return cross


def plot_cluster_profiles(engine, df_c: pd.DataFrame, pais: str) -> None:
    if df_c.empty:
        return
    feat_avgs = ', '.join(f'AVG(t.{f})::float4 AS {f}' for f in FEATURES)
    profiles = pd.read_sql(f"""
        SELECT sc.audio_cluster_id, count(DISTINCT t.spotify_id) AS faixas, {feat_avgs}
        FROM   song_clusters sc
        JOIN   tracks t ON sc.spotify_id = t.spotify_id AND t.country = %(c)s
        WHERE  sc.country = %(c)s AND sc.audio_cluster_id IS NOT NULL
        GROUP  BY sc.audio_cluster_id ORDER BY sc.audio_cluster_id
    """, engine, params={'c': pais})

    norm = profiles[FEATURES].copy()
    for col in FEATURES:
        mn, mx = norm[col].min(), norm[col].max()
        norm[col] = (norm[col] - mn) / (mx - mn + 1e-9)

    fig, ax = plt.subplots(figsize=(13, max(4, len(profiles) * 0.35)))
    sns.heatmap(norm.values, ax=ax, xticklabels=FEATURES,
                yticklabels=[f'c{int(r)} ({int(n)})' for r, n in zip(profiles.audio_cluster_id, profiles.faixas)],
                cmap='YlGn', linewidths=0.2, linecolor='#e5e7eb',
                cbar_kws={'label': 'valor normalizado'})
    ax.set_title(f'{pais} — centroides dos clusters')
    plt.xticks(rotation=30, ha='right', fontsize=7)
    plt.yticks(rotation=0, fontsize=7)
    plt.tight_layout()
    plt.show()


def show_cluster_tracks(engine, df_c: pd.DataFrame, pais: str) -> pd.DataFrame:
    if df_c.empty:
        return df_c
    samples = pd.read_sql("""
        SELECT sc.audio_cluster_id, t.name, t.artists, count(*) AS aparicoes
        FROM   song_clusters sc
        JOIN   tracks t ON sc.spotify_id = t.spotify_id AND t.country = %(c)s
        WHERE  sc.country = %(c)s AND sc.audio_cluster_id IS NOT NULL
        GROUP  BY sc.audio_cluster_id, t.name, t.artists
        ORDER  BY sc.audio_cluster_id, aparicoes DESC
    """, engine, params={'c': pais})
    pd.set_option('display.max_colwidth', 50)
    return (
        samples.groupby('audio_cluster_id', group_keys=False)
        .apply(lambda g: g.head(5))
        .reset_index(drop=True)
    )
