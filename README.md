# Real Exchange Rate Calculator (IMF data)

A Streamlit app that computes and plots the **real exchange rate** between any two IMF member countries (or the euro area) from monthly IMF CPI and exchange-rate data, from January 1976 onward where available.

## Data sources

All data come from the IMF SDMX 3.0 REST API (`https://api.imf.org/external/sdmx/3.0`):

| Series | Dataflow | Key |
|---|---|---|
| Monthly CPI index (all items) | `IMF.STA/CPI` | `{ISO3}.CPI._T.IX.M` |
| Exchange rate, period average (local currency units per 1 USD) | `IMF.STA/ER` | `{ISO3}.XDC_USD.PA_RT.M` |

The euro area uses code `G163`.

**Request URL format:**

```
https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/{CPI|ER}/{version}/{key}
```

Example: `https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/CPI/~/GBR.CPI._T.IX.M`

The app requests CSV (`Accept: text/csv`), trying version `~`, then `+`, then a pinned version (CPI 5.0.0, ER 4.0.1). As a last resort it requests SDMX-JSON. It downloads the full history and filters to 1976 onward in pandas. No time filter is sent to the server.

Parsing handles empty responses, missing observations (blank, `NaN`, `NA`, null), non-positive values, and period formats such as `1976-M01`, `1976-01`, `1976M01`, `197601` and `1976-01-31`. Annual or quarterly periods are discarded.

## Formulas

- `S(t) = FX2(t) / FX1(t)`: units of Country 2 currency per one unit of Country 1 currency. FX1 and FX2 are IMF local-currency-per-USD rates. (UK as Country 1 and US as Country 2 gives USD per GBP, roughly 1.2 to 1.4.)
- `RER(t) = S(t) × P1(t) / P2(t)`: P1 and P2 are the monthly CPIs.
- `RER* = mean(RER(t))` over valid months in the selected sample. A valid month has FX1, FX2, P1 and P2 all available.
- `Real Index(t) = 100 × RER(t) / RER*`: averages exactly 100 over the selected sample and is recomputed whenever the dates change.

A rising Real Index means Country 1 is becoming more expensive relative to Country 2 (real appreciation of Country 1's currency). Nominal S(t) is plotted in actual currency units and is not normalised.

## Features

- Two country dropdowns from a hardcoded list (no extra API call).
- Sample start and end month slider (defaults to the full overlap).
- Real, Nominal, or Both (dual y-axis) interactive Plotly charts.
- CSV export of the selected sample with columns `date, FX1, FX2, S, P1, P2, RER, RER_star, Real_Index`.
- Summary of valid months, sample dates, RER* and data-coverage warnings.
- Data cached for 6 hours (`st.cache_data`) and a sidebar button to clear the cache. Failed downloads are never cached.

## Deploy on Streamlit Community Cloud

1. Put `app.py`, `requirements.txt` and `README.md` in the root of a GitHub repository.
2. Go to https://share.streamlit.io, click **Create app**, and select the repository, branch and `app.py` as the main file.
3. Under **Advanced settings**, choose **Python 3.12**.
4. Click **Deploy**.

**Optional API key:** if the IMF gateway ever requires a subscription key, add this in the app's **Settings > Secrets**:

```toml
IMF_SUBSCRIPTION_KEY = "your-key-here"
```

The app sends it as the `Ocp-Apim-Subscription-Key` header. It is not needed otherwise.

## Known limitations

- The IMF migrated to a new SDMX 3.0 portal and has changed dataflow versions and codes before. If a download fails, expand "Data requests used" in the app and check the error messages.
- Many countries have short or patchy CPI or exchange-rate histories. The app uses only months where all four series exist and warns about limited coverage.
- Euro-area members and the euro area itself only have euro data from 1999. For countries that adopted the euro, the IMF may report history in the legacy currency or a converted series. Axis labels use each country's current currency code.
- The United States XDC_USD series is treated as 1.0 if the IMF does not publish it.
- Exchange rates are period averages, and CPI levels are not rebased. The base year does not matter because the Real Index is normalised to its sample mean.
- Currency labels are hardcoded and may not reflect recent currency changes.
- Hyperinflation episodes or currency redenominations can create breaks in the series.
- This is an analytical tool, not investment advice.
