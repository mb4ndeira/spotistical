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

### Idempotência
Cada notebook pode ser re-executado do início ao fim sem destruir ou duplicar dados.  
Ver detalhes em `ROADMAP.md → Notebook conventions`.

## Índice

| Notebook | Tarefa |
|---|---|
| `00_pipeline.ipynb` | Ingest de tracks · backfill de notícias · lock de fontes |
| `01_audio_clustering.ipynb` | K-Means por país · UMAP · exploração de clusters |
| `02_lyrics.ipynb` | Busca de letras · cobertura · detecção de idioma |

## Arquivos compartilhados

| Arquivo | Função |
|---|---|
| `style.py` | Paleta e rcParams do matplotlib |
| `db.py` | Engines SQLAlchemy (`engine` = app user, `admin_engine` = admin) |
| `requirements.txt` | Dependências do ambiente notebooks |
