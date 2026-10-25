"""
Real exchange rate calculator and plotter using IMF SDMX 3.0 data.

Economics (all derived from IMF data, local currency units per USD):
    S(t)   = FX2(t) / FX1(t)          units of Country 2 currency per 1 unit of Country 1 currency
    RER(t) = S(t) * P1(t) / P2(t)     real exchange rate (level)
    RER*   = mean of RER(t) over valid months in the selected sample
    Real Index(t) = 100 * RER(t) / RER*   (averages exactly 100 over the sample)
"""

import io
import json
import re
import unicodedata

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------
BASE_URL = "https://api.imf.org/external/sdmx/3.0"
AGENCY = "IMF.STA"
# Dataflow -> versions to try, in order. "~" / "+" mean "latest"; the last entry is a pinned fallback.
DATAFLOW_VERSIONS = {
    "CPI": ["~", "+", "5.0.0"],
    "ER": ["~", "+", "4.0.1"],
}
ACCEPT_CSV = "text/csv"
ACCEPT_JSON = "application/vnd.sdmx.data+json;version=2.0.0"
START_DATE = pd.Timestamp("1976-01-01")  # data are used from January 1976 onward
REQUEST_TIMEOUT = (10, 45)  # (connect, read) seconds
CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours

# Name | IMF code (ISO3, or G163 for the euro area) | currency code (for axis labels)
COUNTRY_TABLE = """
Afghanistan|AFG|AFN
Albania|ALB|ALL
Algeria|DZA|DZD
Angola|AGO|AOA
Antigua and Barbuda|ATG|XCD
Argentina|ARG|ARS
Armenia|ARM|AMD
Aruba|ABW|AWG
Australia|AUS|AUD
Austria|AUT|EUR
Azerbaijan|AZE|AZN
Bahamas, The|BHS|BSD
Bahrain|BHR|BHD
Bangladesh|BGD|BDT
Barbados|BRB|BBD
Belarus|BLR|BYN
Belgium|BEL|EUR
Belize|BLZ|BZD
Benin|BEN|XOF
Bhutan|BTN|BTN
Bolivia|BOL|BOB
Bosnia and Herzegovina|BIH|BAM
Botswana|BWA|BWP
Brazil|BRA|BRL
Brunei Darussalam|BRN|BND
Bulgaria|BGR|EUR
Burkina Faso|BFA|XOF
Burundi|BDI|BIF
Cabo Verde|CPV|CVE
Cambodia|KHM|KHR
Cameroon|CMR|XAF
Canada|CAN|CAD
Central African Republic|CAF|XAF
Chad|TCD|XAF
Chile|CHL|CLP
China (Mainland)|CHN|CNY
Colombia|COL|COP
Comoros|COM|KMF
Congo, Democratic Republic of the|COD|CDF
Congo, Republic of|COG|XAF
Costa Rica|CRI|CRC
Côte d'Ivoire|CIV|XOF
Croatia|HRV|EUR
Cyprus|CYP|EUR
Czech Republic|CZE|CZK
Denmark|DNK|DKK
Djibouti|DJI|DJF
Dominica|DMA|XCD
Dominican Republic|DOM|DOP
Ecuador|ECU|USD
Egypt|EGY|EGP
El Salvador|SLV|USD
Equatorial Guinea|GNQ|XAF
Eritrea|ERI|ERN
Estonia|EST|EUR
Eswatini|SWZ|SZL
Ethiopia|ETH|ETB
Euro area (G163)|G163|EUR
Fiji|FJI|FJD
Finland|FIN|EUR
France|FRA|EUR
Gabon|GAB|XAF
Gambia, The|GMB|GMD
Georgia|GEO|GEL
Germany|DEU|EUR
Ghana|GHA|GHS
Greece|GRC|EUR
Grenada|GRD|XCD
Guatemala|GTM|GTQ
Guinea|GIN|GNF
Guinea-Bissau|GNB|XOF
Guyana|GUY|GYD
Haiti|HTI|HTG
Honduras|HND|HNL
Hong Kong SAR, China|HKG|HKD
Hungary|HUN|HUF
Iceland|ISL|ISK
India|IND|INR
Indonesia|IDN|IDR
Iran|IRN|IRR
Iraq|IRQ|IQD
Ireland|IRL|EUR
Israel|ISR|ILS
Italy|ITA|EUR
Jamaica|JAM|JMD
Japan|JPN|JPY
Jordan|JOR|JOD
Kazakhstan|KAZ|KZT
Kenya|KEN|KES
Kiribati|KIR|AUD
Korea, Republic of|KOR|KRW
Kosovo|XKX|EUR
Kuwait|KWT|KWD
Kyrgyz Republic|KGZ|KGS
Lao P.D.R.|LAO|LAK
Latvia|LVA|EUR
Lebanon|LBN|LBP
Lesotho|LSO|LSL
Liberia|LBR|LRD
Libya|LBY|LYD
Lithuania|LTU|EUR
Luxembourg|LUX|EUR
Macao SAR, China|MAC|MOP
Madagascar|MDG|MGA
Malawi|MWI|MWK
Malaysia|MYS|MYR
Maldives|MDV|MVR
Mali|MLI|XOF
Malta|MLT|EUR
Marshall Islands|MHL|USD
Mauritania|MRT|MRU
Mauritius|MUS|MUR
Mexico|MEX|MXN
Micronesia|FSM|USD
Moldova|MDA|MDL
Mongolia|MNG|MNT
Montenegro|MNE|EUR
Morocco|MAR|MAD
Mozambique|MOZ|MZN
Myanmar|MMR|MMK
Namibia|NAM|NAD
Nepal|NPL|NPR
Netherlands|NLD|EUR
New Zealand|NZL|NZD
Nicaragua|NIC|NIO
Niger|NER|XOF
Nigeria|NGA|NGN
North Macedonia|MKD|MKD
Norway|NOR|NOK
Oman|OMN|OMR
Pakistan|PAK|PKR
Palau|PLW|USD
Panama|PAN|PAB
Papua New Guinea|PNG|PGK
Paraguay|PRY|PYG
Peru|PER|PEN
Philippines|PHL|PHP
Poland|POL|PLN
Portugal|PRT|EUR
Qatar|QAT|QAR
Romania|ROU|RON
Russian Federation|RUS|RUB
Rwanda|RWA|RWF
Samoa|WSM|WST
San Marino|SMR|EUR
São Tomé and Príncipe|STP|STN
Saudi Arabia|SAU|SAR
Senegal|SEN|XOF
Serbia|SRB|RSD
Seychelles|SYC|SCR
Sierra Leone|SLE|SLE
Singapore|SGP|SGD
Slovak Republic|SVK|EUR
Slovenia|SVN|EUR
Solomon Islands|SLB|SBD
Somalia|SOM|SOS
South Africa|ZAF|ZAR
South Sudan|SSD|SSP
Spain|ESP|EUR
Sri Lanka|LKA|LKR
St. Kitts and Nevis|KNA|XCD
St. Lucia|LCA|XCD
St. Vincent and the Grenadines|VCT|XCD
Sudan|SDN|SDG
Suriname|SUR|SRD
Sweden|SWE|SEK
Switzerland|CHE|CHF
Syrian Arab Republic|SYR|SYP
Taiwan Province of China|TWN|TWD
Tajikistan|TJK|TJS
Tanzania|TZA|TZS
Thailand|THA|THB
Timor-Leste|TLS|USD
Togo|TGO|XOF
Tonga|TON|TOP
Trinidad and Tobago|TTO|TTD
Tunisia|TUN|TND
Türkiye|TUR|TRY
Turkmenistan|TKM|TMT
Tuvalu|TUV|AUD
Uganda|UGA|UGX
Ukraine|UKR|UAH
United Arab Emirates|ARE|AED
United Kingdom|GBR|GBP
United States|USA|USD
Uruguay|URY|UYU
Uzbekistan|UZB|UZS
Vanuatu|VUT|VUV
Venezuela|VEN|VES
Vietnam|VNM|VND
West Bank and Gaza|PSE|ILS
Yemen|YEM|YER
Zambia|ZMB|ZMW
Zimbabwe|ZWE|ZWG
"""

# Hardcoded name -> (code, currency); no second API call is needed.
COUNTRIES = {}
for _line in COUNTRY_TABLE.strip().splitlines():
    _name, _code, _ccy = _line.split("|")
    COUNTRIES[_name] = (_code, _ccy)


def _sort_key(text):
    """Sort names ignoring accents and case."""
    return unicodedata.normalize("NFKD", text).casefold()


# --------------------------------------------------------------------------------------
# Parsing helpers (robust to missing values and different period formats)
# --------------------------------------------------------------------------------------
# Accepts "1976-M01", "1976-01", "1976M01", "197601", "1976-01-31", "1976-1".
_PERIOD_RE = re.compile(r"^(\d{4})-?M?(\d{1,2})(?:-\d{1,2})?$", re.IGNORECASE)


def empty_series():
    """An empty float series with a DatetimeIndex."""
    return pd.Series(dtype="float64", index=pd.DatetimeIndex([]))


def parse_periods(values):
    """Convert period strings to month-start Timestamps. Unparseable values become NaT."""
    out = []
    for v in values:
        m = _PERIOD_RE.match(str(v).strip())
        if m and 1 <= int(m.group(2)) <= 12:
            out.append(pd.Timestamp(int(m.group(1)), int(m.group(2)), 1))
        else:
            out.append(pd.NaT)  # annual/quarterly/garbage periods are dropped
    return out


def to_series(periods, values):
    """Build a clean monthly series: drop NaT dates, missing / non-positive values, pre-1976 data."""
    periods, values = list(periods), list(values)
    if not periods:
        return empty_series()
    df = pd.DataFrame(
        {
            "date": parse_periods(periods),
            "value": pd.to_numeric(pd.Series(values, dtype="object"), errors="coerce").to_numpy(),
        }
    )
    df = df.dropna()  # missing observations ("", "NaN", "NA", null)
    df = df[df["value"] > 0]  # CPI and FX levels must be positive
    df = df[df["date"] >= START_DATE]
    if df.empty:
        return empty_series()
    # If duplicates exist (e.g. several series returned), keep the last one per month.
    return df.groupby("date")["value"].last().sort_index().astype("float64")


def parse_csv(text):
    """Parse an SDMX CSV response. Returns a Series, or None if the text is not recognisable."""
    if not text.strip():
        return empty_series()  # an empty body is a legitimate "no data" answer
    if text.lstrip().startswith(("<", "{")):
        return None  # HTML or JSON error page
    try:
        df = pd.read_csv(io.StringIO(text), dtype=str)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, ValueError):
        return None
    # Column names may carry labels, e.g. "TIME_PERIOD:Time period"; keep the part before ':'.
    cols = {c.split(":")[0].strip().upper(): c for c in df.columns}
    if "TIME_PERIOD" not in cols or "OBS_VALUE" not in cols:
        return None
    return to_series(df[cols["TIME_PERIOD"]].tolist(), df[cols["OBS_VALUE"]].tolist())


def parse_sdmx_json(text):
    """Parse an SDMX-JSON (1.0 / 2.0) response with series-oriented layout. None if unrecognisable."""
    try:
        obj = json.loads(text)
    except ValueError:
        return None
    root = obj.get("data", obj) if isinstance(obj, dict) else None
    if not isinstance(root, dict) or "dataSets" not in root:
        return None
    datasets = root.get("dataSets") or []
    if not datasets:
        return empty_series()
    structs = root.get("structures") or ([root["structure"]] if root.get("structure") else [])
    try:
        obs_dims = structs[0]["dimensions"]["observation"]
        time_dim = next(d for d in obs_dims if d.get("id") == "TIME_PERIOD")
        time_ids = [v.get("id") or v.get("value") or v.get("name") for v in time_dim["values"]]
        periods, values = [], []
        for series in (datasets[0].get("series") or {}).values():
            for idx, obs in (series.get("observations") or {}).items():
                periods.append(time_ids[int(idx)])
                values.append(obs[0] if obs else None)
    except (KeyError, IndexError, StopIteration, TypeError, ValueError):
        return None
    return to_series(periods, values)


# --------------------------------------------------------------------------------------
# Download
# --------------------------------------------------------------------------------------
class ImfError(Exception):
    """Raised for download problems. Exceptions are never cached by st.cache_data."""


def _subscription_key():
    """Optional API key from Streamlit secrets (not needed unless the IMF gateway demands it)."""
    try:
        return st.secrets.get("IMF_SUBSCRIPTION_KEY")
    except Exception:  # no secrets file configured
        return None


def build_url(flow, version, key):
    """SDMX 3.0 data URL: {base}/data/dataflow/{agency}/{flow}/{version}/{key}"""
    return f"{BASE_URL}/data/dataflow/{AGENCY}/{flow}/{version}/{key}"


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_series(flow, key):
    """Download one monthly series. Returns (clean Series, URL used). Raises ImfError on failure.

    Tries CSV with several dataflow-version spellings, then SDMX-JSON as a last resort.
    A 200 response with no observations returns an empty Series (country has no data).
    """
    versions = DATAFLOW_VERSIONS[flow]
    variants = [(v, ACCEPT_CSV) for v in versions] + [(versions[0], ACCEPT_JSON)]
    headers_base = {"User-Agent": "streamlit-rer-app/1.0"}
    api_key = _subscription_key()
    if api_key:
        headers_base["Ocp-Apim-Subscription-Key"] = api_key

    attempts = []
    for version, accept in variants:
        url = build_url(flow, version, key)
        try:
            resp = requests.get(url, headers={**headers_base, "Accept": accept}, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.Timeout:
            raise ImfError(f"Request timed out after {REQUEST_TIMEOUT[1]} s ({url}).")
        except requests.exceptions.RequestException as exc:
            raise ImfError(f"Network error: {exc}")

        if resp.status_code in (401, 403):
            raise ImfError(
                f"Access denied (HTTP {resp.status_code}). If the IMF gateway now requires a key, "
                "add IMF_SUBSCRIPTION_KEY to the app's Streamlit secrets."
            )
        if resp.status_code == 429:
            raise ImfError("The IMF API rate limit was hit (HTTP 429). Please retry in a minute.")
        if resp.status_code >= 500:
            raise ImfError(f"IMF server error (HTTP {resp.status_code}).")
        if resp.status_code != 200:
            attempts.append(f"HTTP {resp.status_code} for {url} ({accept})")
            continue  # often 404 = wrong version spelling or no such series; try the next variant

        parsed = parse_csv(resp.text) if accept == ACCEPT_CSV else parse_sdmx_json(resp.text)
        if parsed is None:
            attempts.append(f"Unrecognised response body for {url} ({accept})")
            continue
        return parsed, url

    raise ImfError(
        "No usable response (the series may not exist for this country, or the endpoint changed). "
        "Attempts: " + "; ".join(attempts)
    )


def load_country(name, code):
    """Load CPI and FX for one country. Returns (dict of series, list of (level, message), list of URLs)."""
    result = {"CPI": None, "FX": None}
    notes, urls = [], []
    pending_fx_note = None
    specs = (
        ("CPI", "CPI", f"{code}.CPI._T.IX.M", "monthly CPI"),
        ("FX", "ER", f"{code}.XDC_USD.PA_RT.M", "exchange rate (local units per USD)"),
    )
    for label, flow, key, desc in specs:
        note = None
        try:
            series, url = fetch_series(flow, key)
            urls.append(url)
            if series.empty:
                note = ("warning", f"{name}: the IMF returned no usable {desc} observations (key {key}).")
            else:
                result[label] = series
        except ImfError as exc:
            note = ("error", f"{name}: could not download {desc} (key {key}). {exc}")
        if note:
            if label == "FX" and code == "USA":
                pending_fx_note = note  # handled below: USD per USD is 1 by definition
            else:
                notes.append(note)

    # The US exchange rate vs USD is identically 1; synthesise it if the IMF has no such series.
    if code == "USA" and result["FX"] is None:
        if result["CPI"] is not None:
            result["FX"] = pd.Series(1.0, index=result["CPI"].index)
            notes.append(("info", "United States: XDC_USD is identically 1, so a constant 1.0 series was used."))
        elif pending_fx_note:
            notes.append(pending_fx_note)
    return result, notes, urls


# --------------------------------------------------------------------------------------
# Calculation
# --------------------------------------------------------------------------------------
def build_frame(fx1, fx2, p1, p2):
    """Align the four series on valid months and compute S(t) and RER(t)."""
    df = pd.concat({"FX1": fx1, "FX2": fx2, "P1": p1, "P2": p2}, axis=1, join="inner").dropna()
    df["S"] = df["FX2"] / df["FX1"]  # Step 1: units of currency 2 per 1 unit of currency 1
    df["RER"] = df["S"] * df["P1"] / df["P2"]  # Step 2: RER = S * P1 / P2
    return df


def add_real_index(sample):
    """Step 3: normalise on the selected sample so the Real Index averages exactly 100."""
    sample = sample.copy()
    rer_star = sample["RER"].mean()  # RER* = sample average of RER(t)
    sample["RER_star"] = rer_star
    sample["Real_Index"] = 100.0 * sample["RER"] / rer_star
    return sample, rer_star


# --------------------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------------------
def make_chart(plot_df, mode, n1, n2, ccy1, ccy2):
    """Plotly figure for 'Real', 'Nominal' or 'Both' (two y-axes)."""
    nominal_label = f"{ccy2} per {ccy1}"
    real_label = "Real Index (sample average = 100)"
    both = mode == "Both"
    fig = make_subplots(specs=[[{"secondary_y": True}]]) if both else go.Figure()
    primary = {"secondary_y": False} if both else {}
    secondary = {"secondary_y": True} if both else {}

    if mode in ("Real", "Both"):
        fig.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df["Real_Index"], mode="lines", name=real_label,
                       line=dict(width=2)),
            **primary,
        )
        # Horizontal reference line at 100 (drawn as a trace so it works with any axis layout).
        fig.add_trace(
            go.Scatter(x=[plot_df.index.min(), plot_df.index.max()], y=[100, 100], mode="lines",
                       name="Index = 100", line=dict(color="gray", dash="dash", width=1)),
            **primary,
        )
    if mode in ("Nominal", "Both"):
        fig.add_trace(
            go.Scatter(x=plot_df.index, y=plot_df["S"], mode="lines", name=f"Nominal S(t): {nominal_label}",
                       line=dict(width=2, color="#d62728" if both else None)),
            **secondary,
        )

    if both:
        fig.update_yaxes(title_text=real_label, secondary_y=False)
        fig.update_yaxes(title_text=nominal_label, secondary_y=True, showgrid=False)
        title = f"Real index and nominal rate: {n2} vs {n1}"
    elif mode == "Real":
        fig.update_yaxes(title_text=real_label)
        title = f"Real exchange rate index: {n2} vs {n1}"
    else:
        fig.update_yaxes(title_text=nominal_label)
        title = f"Nominal exchange rate: {nominal_label}"

    fig.update_xaxes(title_text="Month")
    fig.update_layout(
        title=title,
        hovermode="x unified",
        height=520,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=10, r=10, t=90, b=10),
    )
    return fig


# --------------------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------------------
def month_span(first, last):
    """Number of calendar months from first to last inclusive."""
    return (last.year - first.year) * 12 + (last.month - first.month) + 1


def main():
    st.set_page_config(page_title="Real exchange rates (IMF data)", page_icon="💱", layout="wide")
    st.title("Real exchange rate calculator")
    st.caption("Monthly CPI and exchange-rate data from the IMF SDMX 3.0 API, January 1976 onward where available.")

    with st.sidebar:
        st.header("Options")
        if st.button("Clear cache and re-download"):
            st.cache_data.clear()
            st.rerun()
        st.caption(f"Downloads are cached for {CACHE_TTL_SECONDS // 3600} hours.")

    names = sorted(COUNTRIES, key=_sort_key)
    col_a, col_b = st.columns(2)
    n1 = col_a.selectbox("Country 1 (base currency)", names, index=names.index("United Kingdom"))
    n2 = col_b.selectbox("Country 2 (quote currency)", names, index=names.index("United States"))
    code1, ccy1 = COUNTRIES[n1]
    code2, ccy2 = COUNTRIES[n2]

    if code1 == code2:
        st.info("Please choose two different countries.")
        st.stop()

    # ---- Download (cached) ----
    with st.spinner("Downloading IMF data..."):
        d1, notes1, urls1 = load_country(n1, code1)
        d2, notes2, urls2 = load_country(n2, code2)
    for level, msg in notes1 + notes2:
        getattr(st, level)(msg)

    missing = [f"{nm} {kind}" for nm, d in ((n1, d1), (n2, d2)) for kind in ("CPI", "FX") if d[kind] is None]
    if missing:
        st.error("Cannot compute the real exchange rate because data are missing for: " + ", ".join(missing) + ".")
        st.stop()

    with st.expander("Data requests used"):
        st.write("URL format: `{base}/data/dataflow/{agency}/{dataflow}/{version}/{key}`")
        for u in urls1 + urls2:
            st.code(u, language=None)

    # ---- Calculation on valid months ----
    df = build_frame(d1["FX"], d2["FX"], d1["CPI"], d2["CPI"])
    if len(df) < 2:
        st.error(
            "These two countries have fewer than two months in common where CPI and exchange rates are all "
            "available, so no real exchange rate can be computed."
        )
        st.stop()

    with st.expander("Series coverage"):
        cov = pd.DataFrame(
            [
                {"Series": f"{nm} {kind}", "First month": s.index.min().strftime("%Y-%m"),
                 "Last month": s.index.max().strftime("%Y-%m"), "Observations": len(s)}
                for nm, d in ((n1, d1), (n2, d2)) for kind, s in d.items()
            ]
        )
        st.dataframe(cov, hide_index=True)

    # ---- Sample selection (default = full overlap) ----
    month_labels = df.index.strftime("%Y-%m").tolist()
    start_label, end_label = st.select_slider(
        "Sample period (start month to end month)",
        options=month_labels,
        value=(month_labels[0], month_labels[-1]),
    )
    sample = df.loc[pd.Timestamp(start_label + "-01"): pd.Timestamp(end_label + "-01")]
    if len(sample) < 1:
        st.error("The selected sample contains no valid months.")
        st.stop()

    # RER* and Real Index are recomputed on every change of the sample dates.
    sample, rer_star = add_real_index(sample)

    # ---- Summary ----
    n_valid = len(sample)
    span = month_span(sample.index.min(), sample.index.max())
    gaps = span - n_valid
    m1, m2, m3 = st.columns(3)
    m1.metric("Valid months", f"{n_valid}")
    m2.metric("Sample", f"{start_label} to {end_label}")
    m3.metric("RER* (sample average)", f"{rer_star:.4f}")
    if n_valid < 120 or gaps > 0:
        parts = []
        if n_valid < 120:
            parts.append(f"only {n_valid} valid months")
        if gaps > 0:
            parts.append(f"{gaps} month(s) inside the sample have missing data")
        st.warning("Limited data coverage: " + " and ".join(parts) + ". Interpret results with care.")

    # ---- Chart ----
    mode = st.radio("Chart", ["Real", "Nominal", "Both"], horizontal=True)
    plot_df = sample.asfreq("MS")  # insert NaN rows for missing months so lines show gaps
    st.plotly_chart(make_chart(plot_df, mode, n1, n2, ccy1, ccy2))
    st.caption(
        f"S(t) = {ccy2} per 1 {ccy1} = FX2 / FX1. RER(t) = S(t) × P1(t) / P2(t). "
        f"A rising Real Index means {n1} becomes relatively more expensive (real appreciation of its currency)."
    )

    # ---- Export ----
    export = sample.reset_index().rename(columns={"index": "date"})
    export.index.name = None
    export = export.rename(columns={sample.index.name or "index": "date"}) if "date" not in export.columns else export
    export["date"] = pd.to_datetime(export["date"]).dt.strftime("%Y-%m-%d")
    export = export[["date", "FX1", "FX2", "S", "P1", "P2", "RER", "RER_star", "Real_Index"]]
    st.download_button(
        "Download sample as CSV",
        data=export.to_csv(index=False).encode("utf-8"),
        file_name=f"rer_{code1}_{code2}_{start_label}_{end_label}.csv",
        mime="text/csv",
    )
    st.caption("CSV columns: FX1 and FX2 are local currency units per USD for Country 1 and Country 2.")


main()
