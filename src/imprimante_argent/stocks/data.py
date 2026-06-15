import pandas as pd
import yfinance as yf


def dca_portfolio(ticker: str, start_year: int, monthly: float = 100.0) -> pd.DataFrame:
    """
    Simulate monthly DCA from start_year to today.
    Returns DAILY rows so the animation line has price-level texture like the reference.
    Investments are made on the last trading day of each month; portfolio value
    is tracked every trading day so the red line fluctuates with the market.

    Columns: date, portfolio_value, total_invested
    """
    start = f"{start_year}-01-01"
    stock = yf.Ticker(ticker)

    hist = stock.history(start=start, auto_adjust=True)
    if hist.empty:
        raise ValueError(f"No price data found for {ticker!r}")
    hist.index = hist.index.tz_localize(None)

    closes_daily   = hist["Close"].dropna()
    closes_monthly = closes_daily.resample("ME").last().dropna()

    # Build month-end cumulative share/invested totals
    cum_shares  = 0.0
    cum_invested = 0.0
    monthly_state: dict = {}          # date → (cum_shares, cum_invested)
    for date, price in closes_monthly.items():
        if price > 0:
            cum_shares  += monthly / price
            cum_invested += monthly
            monthly_state[date] = (cum_shares, cum_invested)

    inv_dates = sorted(monthly_state.keys())

    # Walk daily prices, stepping forward the cumulative position as months pass
    rows      = []
    last_s    = 0.0
    last_inv  = 0.0
    inv_idx   = 0

    for date, price in closes_daily.items():
        while inv_idx < len(inv_dates) and inv_dates[inv_idx] <= date:
            last_s, last_inv = monthly_state[inv_dates[inv_idx]]
            inv_idx += 1
        if last_s > 0 and price > 0:
            rows.append({
                "date":            date,
                "portfolio_value": last_s * price,
                "total_invested":  last_inv,
            })

    return pd.DataFrame(rows)


def lump_sum_portfolios(
    tickers: list[str], start_year: int, investment: float = 1000.0
) -> dict[str, pd.DataFrame]:
    """
    Simulate lump-sum investment on the first available trading day of start_year.
    Returns daily portfolio values so the comparison lines also have market texture.

    Returns {ticker: DataFrame(date, portfolio_value)}
    """
    out: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        hist  = stock.history(start=f"{start_year}-01-01", auto_adjust=True)

        if hist.empty:
            raise ValueError(f"No price data found for {ticker!r}")

        hist.index  = hist.index.tz_localize(None)
        first_price = hist["Close"].iloc[0]
        shares      = investment / first_price

        closes_daily = hist["Close"].dropna()
        out[ticker] = pd.DataFrame(
            [{"date": d, "portfolio_value": shares * p}
             for d, p in closes_daily.items()]
        )

    return out
