"""
style.py — estilo visual compartilhado para todos os notebooks do spotistical.

Regras:
  - Fundo branco / neutro: funciona em qualquer tema de IDE
  - Verde Spotify como cor primária em gráficos
  - Cinza para elementos secundários (eixos, grades, texto auxiliar)
  - Sem dark_background — os outputs de célula sempre têm fundo claro
  - Markdown dos notebooks: mínimo, direto, em português

Uso em todo notebook:
    from style import GREEN, MUTED, setup_style
    setup_style()
"""
import matplotlib as mpl
import matplotlib.pyplot as plt

GREEN  = "#1db954"   # verde Spotify — cor primária
MUTED  = "#6b7280"   # cinza — eixos, rótulos secundários
BG     = "#ffffff"   # fundo das figuras
GRID   = "#f0f0f0"   # cor da grade
ACCENT = "#0a7a38"   # verde escuro — destaques


def setup_style() -> None:
    """Aplica o estilo padrão do spotistical ao matplotlib."""
    mpl.rcParams.update({
        # figura
        "figure.facecolor":  BG,
        "figure.dpi":        120,
        # eixos
        "axes.facecolor":    BG,
        "axes.edgecolor":    "#e5e7eb",
        "axes.linewidth":    0.8,
        "axes.spines.top":   False,
        "axes.spines.right": False,
        "axes.grid":         True,
        "grid.color":        GRID,
        "grid.linewidth":    0.5,
        "grid.alpha":        1.0,
        # texto
        "text.color":        "#111827",
        "axes.labelcolor":   MUTED,
        "axes.titlecolor":   "#111827",
        "axes.titlesize":    12,
        "axes.labelsize":    10,
        "xtick.color":       MUTED,
        "ytick.color":       MUTED,
        "xtick.labelsize":   8,
        "ytick.labelsize":   8,
        # legenda
        "legend.framealpha": 0.9,
        "legend.edgecolor":  "#e5e7eb",
        "legend.fontsize":   8,
        # fonte
        "font.family":       "sans-serif",
    })
