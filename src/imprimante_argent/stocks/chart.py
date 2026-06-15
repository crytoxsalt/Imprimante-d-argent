import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.dates as mdates
import pandas as pd
from PIL import Image

_DCA_COLORS = {
    "portfolio": "#e53935",   # red  (like data.dragonn)
    "invested":  "#111111",   # black
}
_COMP_COLORS = ["#c62828", "#111111", "#2e7d32", "#1565c0", "#6a1b9a"]

_FIG_W, _FIG_H, _DPI = 10.8, 15.0, 100


def _dollar_fmt(x, _):
    if x >= 1_000_000:
        return f"${x/1_000_000:.1f}M"
    if x >= 1_000:
        return f"${x:,.0f}"
    return f"${x:.0f}"


def _new_fig():
    fig, ax = plt.subplots(figsize=(_FIG_W, _FIG_H), dpi=_DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    plt.subplots_adjust(left=0.10, right=0.68, top=0.94, bottom=0.07)
    return fig, ax


def _init_axes(ax):
    """Set formatters and style; limits are updated dynamically per frame."""
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(_dollar_fmt))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=13)


def _render(fig) -> Image.Image:
    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    return Image.frombuffer(
        "RGBA", (w, h), fig.canvas.buffer_rgba(), "raw", "RGBA", 0, 1
    ).convert("RGB")


def _mk_ann(ax, color):
    a = ax.annotate(
        "", xy=(0, 0), xytext=(14, 0), textcoords="offset points",
        color=color, fontsize=13, fontweight="bold",
        va="center", ha="left", annotation_clip=False, visible=True,
    )
    return a


def dca_chart_frames(df: pd.DataFrame, ticker_name: str, n_frames: int,
                     fps: int = 24, watermark: str = "@cashroll"):
    """
    Draw the DCA chart progressively across the FULL video duration.
    Each frame reveals a bit more data. Dynamic xlim/ylim expand with data.
    Only unique data slices trigger a matplotlib render (~n_data renders total).
    """
    n_data = len(df)
    x_min  = df["date"].iloc[0]
    x_max  = df["date"].iloc[-1]
    time_span = x_max - x_min

    fig, ax = _new_fig()
    _init_axes(ax)

    # Watermark inside chart
    ax.text(0.25, 0.12, watermark, transform=ax.transAxes,
            fontsize=14, color="#cccccc", ha="center", va="center",
            fontweight="bold")

    lp, = ax.plot([], [], color=_DCA_COLORS["portfolio"], linewidth=3, zorder=3)
    lt, = ax.plot([], [], color=_DCA_COLORS["invested"],  linewidth=3, zorder=2)

    # Moving tip marker on portfolio line
    tip_dot, = ax.plot([], [], "o", color=_DCA_COLORS["portfolio"],
                       markersize=7, zorder=4, clip_on=False)

    ap = _mk_ann(ax, _DCA_COLORS["portfolio"])
    at = _mk_ann(ax, _DCA_COLORS["invested"])

    print("  Pre-rendering chart frames...")
    one_pass = []
    prev_n   = -1
    cached   = None
    try:
        for fi in range(n_frames):
            n = min(n_data, max(2, round((fi + 1) / n_frames * n_data)))
            if n == prev_n:
                one_pass.append(cached)
                continue

            df_s   = df.iloc[:n]
            last_d = df_s["date"].iloc[-1]
            pv     = df_s["portfolio_value"].iloc[-1]
            ti     = df_s["total_invested"].iloc[-1]

            # Dynamic limits — xlim has a 12% lookahead so labels have room
            x_right   = last_d + time_span * 0.12
            cur_y_max = max(pv, ti) * 1.22
            ax.set_xlim(x_min, x_right)
            ax.set_ylim(0, cur_y_max)

            lp.set_data(df_s["date"], df_s["portfolio_value"])
            # Straight diagonal line — no staircase from monthly jumps
            lt.set_data([x_min, last_d], [0, ti])
            tip_dot.set_data([last_d], [pv])

            ap.xy = (last_d, pv)
            ap.set_text(f"{ticker_name}\n$ {pv:,.0f}")
            at.xy = (last_d, ti)
            at.set_text(f"invested\n$ {ti:,.0f}")

            cached = _render(fig)
            prev_n = n
            one_pass.append(cached)
    finally:
        plt.close(fig)

    unique = sum(1 for i, img in enumerate(one_pass) if i == 0 or img is not one_pass[i - 1])
    print(f"  {unique} unique renders, {n_frames} total frames")
    yield from one_pass


def comparison_chart_frames(
    portfolios: dict[str, pd.DataFrame],
    ticker_names: dict[str, str],
    n_frames: int,
    fps: int = 24,
    watermark: str = "@cashroll",
):
    """
    Draw all comparison lines progressively across the full video duration.
    Dynamic xlim/ylim expand with data.
    """
    tickers = list(portfolios.keys())
    min_n   = min(len(df) for df in portfolios.values())

    x_min   = min(df["date"].iloc[0]  for df in portfolios.values())
    x_max   = max(df["date"].iloc[-1] for df in portfolios.values())
    time_span = x_max - x_min

    fig, ax = _new_fig()
    _init_axes(ax)

    ax.text(0.25, 0.12, watermark, transform=ax.transAxes,
            fontsize=14, color="#cccccc", ha="center", va="center",
            fontweight="bold")

    lines = {}
    anns  = {}
    for i, ticker in enumerate(tickers):
        color        = _COMP_COLORS[i % len(_COMP_COLORS)]
        line,        = ax.plot([], [], color=color, linewidth=3)
        lines[ticker] = line
        anns[ticker]  = _mk_ann(ax, color)

    print("  Pre-rendering chart frames...")
    one_pass     = []
    prev_n, cached = -1, None
    try:
        for fi in range(n_frames):
            n = min(min_n, max(2, round((fi + 1) / n_frames * min_n)))
            if n == prev_n:
                one_pass.append(cached)
                continue

            cur_y_max = 0.0
            last_d    = None
            for ticker, df in portfolios.items():
                df_s  = df.iloc[:n]
                final = df_s["portfolio_value"].iloc[-1]
                lines[ticker].set_data(df_s["date"], df_s["portfolio_value"])
                ann = anns[ticker]
                ann.xy = (df_s["date"].iloc[-1], final)
                ann.set_text(f"{ticker_names.get(ticker, ticker)}\n$ {final:,.0f}")
                cur_y_max = max(cur_y_max, final)
                last_d    = df_s["date"].iloc[-1]

            x_right = last_d + time_span * 0.12
            ax.set_xlim(x_min, x_right)
            ax.set_ylim(0, cur_y_max * 1.22)

            cached = _render(fig)
            prev_n = n
            one_pass.append(cached)
    finally:
        plt.close(fig)

    unique = sum(1 for i, img in enumerate(one_pass) if i == 0 or img is not one_pass[i - 1])
    print(f"  {unique} unique renders, {n_frames} total frames")
    yield from one_pass
