# spotistical — notebooks

Interface humana para o pipeline de dados.

## Convenções

### Idioma
Todo texto dos notebooks — títulos, markdown, comentários explicativos — em **português**.  
Nomes de variáveis, funções e código permanecem em inglês.

### Markdown
**Mínimo.** Cada seção tem um título e no máximo duas linhas de contexto.  
Sem tabelas decorativas, sem blocos longos de explicação, sem `---` entre cada célula.

### Estilo visual
```python
from style import GREEN, MUTED, setup_style
setup_style()
```

- Fundo branco — funciona em qualquer tema de IDE
- `GREEN = "#1db954"` como cor primária em todos os gráficos
- `MUTED = "#6b7280"` para eixos e texto auxiliar
- Sem `plt.style.use('dark_background')`

### Idempotência e isolamento de runs
Cada notebook pode ser re-executado do início ao fim sem destruir ou duplicar dados.

Além disso, tabelas derivadas usam `run_id` para que re-rodar clustering ou BERTopic
nunca deixe dados de runs diferentes misturados em `insights`:

- `song_clusters.clustering_run_id` — identifica o run de K-Means
- `news_topic_definitions.run_id` — identifica o run BERTopic  
- `insights.clustering_run_id` + `insights.topic_run` — vinculam cada insight ao esquema exato que o gerou

Re-rodar clustering invalida automaticamente insights do run anterior.
Ver detalhes em `ROADMAP.md → Run isolation`.

## Índice

| Notebook | Tarefa |
|---|---|
| `00_pipeline.ipynb` | Ingest de tracks · backfill de notícias · lock de fontes |
| `01_audio_clustering.ipynb` | K-Means por país · UMAP · exploração de clusters |
| `02_lyrics.ipynb` | Busca de letras · cobertura · detecção de idioma |
| `03_news_topics.ipynb` | Embeddings de notícias · UMAP · BERTopic · evolução temporal |

## Limitações conhecidas

### Corpus de notícias — idioma e cobertura

A fonte de notícias é o **GDELT DOC API 2.0** (gratuito, sem API key, sem limite publicado de requests). GDELT indexa notícias em 65+ idiomas de 100+ países, o que significa que artigos chegam na língua original da fonte.

**Consequência no BERTopic:** o `CountVectorizer` usa `stop_words='english'` porque o corpus coletado até agora (out–dez/2023, queries temáticas globais) retornou predominantemente artigos em inglês. Isso pode mudar com o corpus maior.

**O código está preparado para a transição.** Cada run BERTopic grava um campo `config` em `news_topic_definitions` com os parâmetros usados:

```json
{
  "embedding_model": "paraphrase-multilingual-mpnet-base-v2",
  "news_lang": "en",
  "stop_words": "english",
  "corpus_size": 7788
}
```

Quando o corpus for predominantemente multilingual, basta alterar `STOP_WORDS_LANG` e `NEWS_LANG` no topo do notebook — o novo run fica diferenciado dos anteriores pelo `config`.

O modelo de embedding (`paraphrase-multilingual-mpnet-base-v2`) já é multilingual e não precisa mudar.

## Arquivos compartilhados

| Arquivo | Função |
|---|---|
| `style.py` | Paleta e rcParams do matplotlib |
| `db.py` | Engines SQLAlchemy (`engine` = app user, `admin_engine` = admin) |
| `requirements.txt` | Dependências do ambiente notebooks |
