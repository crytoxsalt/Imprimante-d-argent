import multiprocessing as mp

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.dates as mdates
import pandas as pd
from PIL import Image

_DCA_COLORS = {
    "portfolio": "#e53935",
    "invested":  "#111111",
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
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(_dollar_fmt))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=13)


def _render_bytes(fig) -> bytes:
    fig.canvas.draw()
    w, h = fig.canvas.get_width_height()
    return Image.frombuffer(
        "RGBA", (w, h), fig.canvas.buffer_rgba(), "raw", "RGBA", 0, 1
    ).convert("RGB").tobytes()


def _mk_ann(ax, color):
    return ax.annotate(
        "", xy=(0, 0), xytext=(14, 0), textcoords="offset points",
        color=color, fontsize=13, fontweight="bold",
        va="center", ha="left", annotation_clip=False, visible=True,
    )


# ── Parallel worker functions (module-level so they're picklable on Windows) ──

def _dca_batch_worker(args):
    """Render a batch of DCA frames in a worker process. Returns {fi: bytes}."""
    indices, ns, df, ticker_name, x_min, time_span, watermark = args

    matplotlib.use('Agg')
    fig, ax = _new_fig()
    _init_axes(ax)
    ax.text(0.25, 0.12, watermark, transform=ax.transAxes,
            fontsize=14, color="#cccccc", ha="center", va="center", fontweight="bold")

    lp,      = ax.plot([], [], color=_DCA_COLORS["portfolio"], linewidth=3, zorder=3)
    lt,      = ax.plot([], [], color=_DCA_COLORS["invested"],  linewidth=3, zorder=2)
    tip_dot, = ax.plot([], [], "o", color=_DCA_COLORS["portfolio"],
                       markersize=7, zorder=4, clip_on=False)
    ap = _mk_ann(ax, _DCA_COLORS["portfolio"])
    at = _mk_ann(ax, _DCA_COLORS["invested"])

    results  = {}
    prev_n   = -1
    cached   = None

    for fi, n in zip(indices, ns):
        if n == prev_n:
            results[fi] = cached
            continue

        df_s   = df.iloc[:n]
        last_d = df_s["date"].iloc[-1]
        pv     = df_s["portfolio_value"].iloc[-1]
        ti     = df_s["total_invested"].iloc[-1]

        ax.set_xlim(x_min, last_d + time_span * 0.12)
        ax.set_ylim(0, max(pv, ti) * 1.22)

        lp.set_data(df_s["date"], df_s["portfolio_value"])
        lt.set_data([x_min, last_d], [0, ti])
        tip_dot.set_data([last_d], [pv])
        ap.xy = (last_d, pv);  ap.set_text(f"{ticker_name}\n$ {pv:,.0f}")
        at.xy = (last_d, ti);  at.set_text(f"invested\n$ {ti:,.0f}")

        cached = _render_bytes(fig)
        prev_n = n
        results[fi] = cached

    plt.close(fig)
    return results


def _comp_batch_worker(args):
    """Render a batch of comparison frames in a worker process. Returns {fi: bytes}."""
    indices, ns, portfolios, ticker_names, colors, x_min, time_span, watermark = args

    matplotlib.use('Agg')
    fig, ax = _new_fig()
    _init_axes(ax)
    ax.text(0.25, 0.12, watermark, transform=ax.transAxes,
            fontsize=14, color="#cccccc", ha="center", va="center", fontweight="bold")

    tickers = list(portfolios.keys())
    lines   = {}
    anns    = {}
    for i, ticker in enumerate(tickers):
        color         = colors[i % len(colors)]
        line,         = ax.plot([], [], color=color, linewidth=3)
        lines[ticker] = line
        anns[ticker]  = _mk_ann(ax, color)

    results = {}
    prev_n  = -1
    cached  = None

    for fi, n in zip(indices, ns):
        if n == prev_n:
            results[fi] = cached
            continue

        cur_y_max = 0.0
        last_d    = None
        for ticker, df in portfolios.items():
            df_s  = df.iloc[:n]
            final = df_s["portfolio_value"].iloc[-1]
            lines[ticker].set_data(df_s["date"], df_s["portfolio_value"])
            anns[ticker].xy = (df_s["date"].iloc[-1], final)
            anns[ticker].set_text(f"{ticker_names.get(ticker, ticker)}\n$ {final:,.0f}")
            cur_y_max = max(cur_y_max, final)
            last_d    = df_s["date"].iloc[-1]

        ax.set_xlim(x_min, last_d + time_span * 0.12)
        ax.set_ylim(0, cur_y_max * 1.22)

        cached = _render_bytes(fig)
        prev_n = n
        results[fi] = cached

    plt.close(fig)
    return results


# ── Public frame generators ───────────────────────────────────────────────────

def _batches(n_frames, n_workers):
    size = (n_frames + n_workers - 1) // n_workers
    for w in range(n_workers):
        start = w * size
        end   = min(start + size, n_frames)
        if start < n_frames:
            yield list(range(start, end))


def _collect(results_list, n_frames):
    """Merge worker dicts and yield PIL Images in frame order."""
    merged = {}
    for d in results_list:
        merged.update(d)
    img_w = int(_FIG_W * _DPI)
    img_h = int(_FIG_H * _DPI)
    prev  = None
    for fi in range(n_frames):
        raw = merged[fi]
        if raw is prev:
            yield _last_img
        else:
            img = Image.frombuffer("RGB", (img_w, img_h), raw, "raw", "RGB", 0, 1)
            prev = raw
            _last_img = img
            yield img


def dca_chart_frames(df: pd.DataFrame, ticker_name: str, n_frames: int,
                     fps: int = 24, watermark: str = "@geldmaker"):
    n_data    = len(df)
    x_min     = df["date"].iloc[0]
    x_max     = df["date"].iloc[-1]
    time_span = x_max - x_min

    frame_ns = [min(n_data, max(2, round((fi + 1) / n_frames * n_data)))
                for fi in range(n_frames)]

    n_workers = mp.cpu_count()
    print(f"  Pre-rendering {n_frames} frames across {n_workers} cores...")

    batch_args = [
        (batch, [frame_ns[i] for i in batch], df, ticker_name, x_min, time_span, watermark)
        for batch in _batches(n_frames, n_workers)
    ]

    with mp.Pool(n_workers) as pool:
        results_list = pool.map(_dca_batch_worker, batch_args)

    unique = len({v for d in results_list for v in d.values()})
    print(f"  {unique} unique renders, {n_frames} total frames")
    yield from _collect(results_list, n_frames)


def comparison_chart_frames(
    portfolios: dict[str, pd.DataFrame],
    ticker_names: dict[str, str],
    n_frames: int,
    fps: int = 24,
    watermark: str = "@geldmaker",
):
    tickers   = list(portfolios.keys())
    min_n     = min(len(df) for df in portfolios.values())
    x_min     = min(df["date"].iloc[0]  for df in portfolios.values())
    x_max     = max(df["date"].iloc[-1] for df in portfolios.values())
    time_span = x_max - x_min

    frame_ns  = [min(min_n, max(2, round((fi + 1) / n_frames * min_n)))
                 for fi in range(n_frames)]

    n_workers = mp.cpu_count()
    print(f"  Pre-rendering {n_frames} frames across {n_workers} cores...")

    batch_args = [
        (batch, [frame_ns[i] for i in batch],
         portfolios, ticker_names, _COMP_COLORS, x_min, time_span, watermark)
        for batch in _batches(n_frames, n_workers)
    ]

    with mp.Pool(n_workers) as pool:
        results_list = pool.map(_comp_batch_worker, batch_args)

    unique = len({v for d in results_list for v in d.values()})
    print(f"  {unique} unique renders, {n_frames} total frames")
    yield from _collect(results_list, n_frames)
