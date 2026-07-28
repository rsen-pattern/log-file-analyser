"""Plotly layout theme shared by Flask views."""

PLOTLY_TEMPLATE = {
    "layout": {
        "paper_bgcolor": "#09090b",
        "plot_bgcolor": "#09090b",
        "font": {
            "family": "Inter, system-ui, sans-serif",
            "color": "#b4b4ba",
            "size": 12,
        },
        "title": {"font": {"family": "Space Grotesk, sans-serif", "color": "#f5f5f7"}},
        "colorway": [
            "#b4ff39",
            "#ff6b4a",
            "#4a7bff",
            "#ffd166",
            "#9b8cff",
            "#6affc0",
            "#ff7ad9",
        ],
        "xaxis": {
            "gridcolor": "#1a1a20",
            "zerolinecolor": "#26262d",
            "linecolor": "#26262d",
            "tickfont": {"color": "#707078", "family": "JetBrains Mono, monospace", "size": 11},
            "title": {"font": {"color": "#b4b4ba"}},
        },
        "yaxis": {
            "gridcolor": "#1a1a20",
            "zerolinecolor": "#26262d",
            "linecolor": "#26262d",
            "tickfont": {"color": "#707078", "family": "JetBrains Mono, monospace", "size": 11},
            "title": {"font": {"color": "#b4b4ba"}},
        },
        "legend": {
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"color": "#b4b4ba", "size": 11},
            "bordercolor": "#26262d",
        },
        "hoverlabel": {
            "bgcolor": "#131318",
            "bordercolor": "#26262d",
            "font": {"color": "#f5f5f7", "family": "JetBrains Mono, monospace"},
        },
        "height": 380,
        "margin": {"l": 0, "r": 0, "t": 20, "b": 0},
    }
}


def apply_theme(fig):
    fig.update_layout(**PLOTLY_TEMPLATE["layout"])
    return fig


def fig_to_json(fig):
    return apply_theme(fig).to_json()
