from __future__ import annotations
import ast, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import text
from style import GREEN, MUTED

API = 'http://localhost:8000'


def compute_embeddings(engine, admin_engine, model_name: str, batch_size: int = 256) -> None:
    from sentence_transformers import SentenceTransformer
    pendentes = pd.read_sql("""
        SELECT id, title FROM news_events
        WHERE  embedding IS NULL
        ORDER  BY published_at
    """, engine)
    if pendentes.empty:
        print('Todos os artigos já têm embedding.')
        return
    print(f'Carregando modelo {model_name}...')
    model = SentenceTransformer(model_name)
    print(f'Computando embeddings para {len(pendentes):,} artigos...')
    ids    = pendentes['id'].tolist()
    titles = pendentes['title'].tolist()
    for i in range(0, len(titles), batch_size):
        batch_ids    = ids[i:i + batch_size]
        batch_titles = titles[i:i + batch_size]
        vecs = model.encode(batch_titles, show_progress_bar=False, normalize_embeddings=True)
        with admin_engine.begin() as conn:
            for article_id, vec in zip(batch_ids, vecs):
                conn.execute(
                    text('UPDATE news_events SET embedding = :v WHERE id = :id'),
                    {'v': str(vec.tolist()), 'id': int(article_id)}
                )
        done = min(i + batch_size, len(titles))
        print(f'  {done:,}/{len(titles):,}  ({done/len(titles)*100:.0f}%)', end='\r')
    print(f'\nEmbeddings salvos para {len(pendentes):,} artigos.')


def load_embeddings(engine) -> tuple[pd.DataFrame, np.ndarray]:
    df = pd.read_sql("""
        SELECT id, title, published_at::date AS data,
               source,
               embedding::text AS emb_text
        FROM   news_events
        WHERE  embedding IS NOT NULL
        ORDER  BY published_at
    """, engine)
    if df.empty:
        print('Sem embeddings — execute compute_embeddings() primeiro.')
        return df, np.array([])
    print(f'{len(df):,} artigos com embedding')
    X = np.array([ast.literal_eval(e) for e in df['emb_text']], dtype=np.float32)
    print(f'Shape: {X.shape}')
    return df, X


def compute_umap(df_emb: pd.DataFrame, X: np.ndarray) -> pd.DataFrame:
    import umap
    print('Calculando UMAP 2D...')
    reducer = umap.UMAP(n_components=2, n_neighbors=15, min_dist=0.1,
                        metric='cosine', random_state=42, low_memory=True)
    coords = reducer.fit_transform(X)
    df_emb = df_emb.copy()
    df_emb['umap_x'] = coords[:, 0]
    df_emb['umap_y'] = coords[:, 1]
    return df_emb


def plot_by_source(df_emb: pd.DataFrame) -> None:
    if df_emb.empty or 'umap_x' not in df_emb.columns:
        print('Execute compute_umap() primeiro.')
        return
    cores_fonte = {'guardian': GREEN, 'gdelt': '#818cf8', None: '#9ca3af'}
    fig, ax = plt.subplots(figsize=(11, 8))
    for fonte, grp in df_emb.groupby('source', dropna=False):
        ax.scatter(grp.umap_x, grp.umap_y, s=8, alpha=0.5,
                   color=cores_fonte.get(fonte, MUTED), label=str(fonte), edgecolors='none')
    ax.set_title('UMAP dos embeddings de notícias — cor = fonte')
    ax.set_xlabel('UMAP 1')
    ax.set_ylabel('UMAP 2')
    ax.legend(markerscale=3, fontsize=8)
    plt.tight_layout()
    plt.show()


def run_bertopic(df_emb: pd.DataFrame, X: np.ndarray, stop_words_lang: str = 'english'):
    from bertopic import BERTopic
    from sklearn.feature_extraction.text import CountVectorizer
    print(f'Rodando BERTopic em {len(df_emb):,} artigos...')
    vectorizer = CountVectorizer(stop_words=stop_words_lang, min_df=3, ngram_range=(1, 2))
    topic_model = BERTopic(
        vectorizer_model=vectorizer,
        nr_topics='auto',
        calculate_probabilities=False,
        verbose=True,
    )
    topics, _ = topic_model.fit_transform(df_emb['title'].tolist(), X)
    df_emb = df_emb.copy()
    df_emb['topic_id'] = topics
    info = topic_model.get_topic_info()
    print(f'\n{len(info) - 1} tópicos encontrados  (excl. outliers -1)')
    print(info[info.Topic != -1].head(10).to_string(index=False))
    return df_emb, topic_model


def save_topics(df_emb: pd.DataFrame, topic_model, run_id: str,
                model_name: str, news_lang: str, stop_words_lang: str,
                admin_engine) -> None:
    topic_info = topic_model.get_topic_info()
    run_config = {
        'embedding_model': model_name,
        'news_lang':       news_lang,
        'stop_words':      stop_words_lang,
        'corpus_size':     len(df_emb),
    }
    with admin_engine.begin() as conn:
        for _, row in topic_info.iterrows():
            tid        = int(row.Topic)
            words      = topic_model.get_topic(tid)
            words_json = str([{'word': w, 'score': round(s, 4)} for w, s in (words or [])])
            conn.execute(text("""
                INSERT INTO news_topic_definitions (run_id, topic_id, label, top_words, article_count, config)
                VALUES (:run, :tid, :label, :words::jsonb, :cnt, :cfg::jsonb)
                ON CONFLICT (run_id, topic_id) DO UPDATE SET
                    label = EXCLUDED.label, top_words = EXCLUDED.top_words,
                    article_count = EXCLUDED.article_count, config = EXCLUDED.config
            """), {'run': run_id, 'tid': tid,
                   'label': str(row.get('Name', row.get('Representation', ''))),
                   'words': words_json, 'cnt': int(row.Count),
                   'cfg': json.dumps(run_config)})
        for _, row in df_emb.iterrows():
            conn.execute(text("""
                UPDATE news_events SET topic_id = :tid, topic_run = :run WHERE id = :id
            """), {'tid': int(row.topic_id), 'run': run_id, 'id': int(row.id)})
    print(f'Tópicos salvos  (run_id={run_id}  ·  {news_lang}  ·  stop_words={stop_words_lang})')


def show_topics(engine) -> None:
    topicos = pd.read_sql("""
        SELECT d.topic_id, d.label, d.article_count, d.top_words
        FROM   news_topic_definitions d
        WHERE  d.run_id = (SELECT max(run_id) FROM news_topic_definitions)
          AND  d.topic_id <> -1
        ORDER  BY d.article_count DESC
    """, engine)
    if topicos.empty:
        print('Sem tópicos — execute run_bertopic() e save_topics() primeiro.')
        return
    print(f'{len(topicos)} tópicos')
    fig, ax = plt.subplots(figsize=(12, max(4, len(topicos) * 0.3)))
    ax.barh(topicos['label'].str[:50], topicos['article_count'], color=GREEN, edgecolor='none')
    ax.set_xlabel('Artigos')
    ax.set_title('Tópicos por volume de artigos')
    ax.invert_yaxis()
    plt.tight_layout()
    plt.show()


def plot_umap_by_topic(df_emb: pd.DataFrame) -> None:
    if df_emb.empty or 'topic_id' not in df_emb.columns or 'umap_x' not in df_emb.columns:
        return
    n_t     = df_emb['topic_id'].nunique()
    palette = plt.cm.get_cmap('tab20', n_t)
    tid_map = {t: i for i, t in enumerate(sorted(df_emb['topic_id'].unique()))}
    fig, ax = plt.subplots(figsize=(11, 8))
    for tid, grp in df_emb.groupby('topic_id'):
        label = f't{tid}' if tid != -1 else 'outlier'
        ax.scatter(grp.umap_x, grp.umap_y, s=8, alpha=0.5,
                   color=palette(tid_map[tid]), label=label, edgecolors='none')
    ax.set_title('UMAP dos embeddings — cor = tópico BERTopic')
    ax.set_xlabel('UMAP 1')
    ax.set_ylabel('UMAP 2')
    ax.legend(markerscale=3, fontsize=7, ncol=4, loc='upper right')
    plt.tight_layout()
    plt.show()


def plot_topic_timeline(df_emb: pd.DataFrame) -> None:
    if df_emb.empty or 'topic_id' not in df_emb.columns:
        return
    df_time = df_emb[df_emb['topic_id'] != -1].copy()
    df_time['semana'] = pd.to_datetime(df_time['data']).dt.to_period('W').dt.start_time
    pivot = df_time.groupby(['semana', 'topic_id']).size().unstack(fill_value=0)
    top_topics = df_time['topic_id'].value_counts().head(6).index
    fig, ax = plt.subplots(figsize=(13, 5))
    for tid in top_topics:
        if tid in pivot.columns:
            ax.plot(pivot.index, pivot[tid], linewidth=1.5, label=f't{tid}')
    ax.set_xlabel('Semana')
    ax.set_ylabel('Artigos')
    ax.set_title('Evolução dos top 6 tópicos ao longo do tempo')
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.show()
