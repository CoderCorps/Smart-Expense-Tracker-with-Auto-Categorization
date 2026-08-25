import pandas as pd
import plotly.express as px
import streamlit as st

from categorizer import categorize_dataframe
from file_handler import read_csv_file, read_pdf_file


st.set_page_config(
    page_title="Smart Expense Tracker",
    page_icon="S",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inject_styles():
    st.markdown(
        """
        <style>
        :root {
            --ink: #15221f;
            --muted: #697773;
            --line: #e5ebe7;
            --surface: #ffffff;
            --canvas: #f7faf8;
            --accent: #1f6f5b;
            --accent-soft: #e8f3ee;
            --warm: #f4efe6;
        }
        .stApp { background: var(--canvas); color: var(--ink); }
        [data-testid="stHeader"] { display: none; }
        [data-testid="stToolbar"] { display: none; }
        [data-testid="stDecoration"] { display: none; }
        [data-testid="stMainBlockContainer"] { max-width: 1320px; padding-top: 1.2rem; }
        .block-container { padding-bottom: 4rem; }
        h1, h2, h3 { color: var(--ink); letter-spacing: 0; }
        h1 { font-size: 2.7rem !important; line-height: 1.05 !important; }
        h2 { font-size: 1.55rem !important; }
        h3 { font-size: 1.05rem !important; }
        .topbar { display: flex; align-items: center; gap: .75rem; margin-bottom: 1.5rem; }
        .brand-mark { width: 38px; height: 38px; border-radius: 11px; background: var(--ink); color: white; display: grid; place-items: center; font-weight: 700; font-size: 1.1rem; }
        .brand-name { font-weight: 700; color: var(--ink); font-size: 1rem; line-height: 1.15; }
        .brand-subtitle { color: var(--muted); font-size: .72rem; margin-top: .18rem; }
        .status-pill { display: inline-flex; align-items: center; gap: .45rem; color: var(--muted); font-size: .78rem; white-space: nowrap; padding-top: .55rem; }
        .status-dot { width: 7px; height: 7px; background: #41a477; border-radius: 50%; display: inline-block; }
        .hero { background: var(--ink); border-radius: 18px; padding: 2.2rem 2.4rem; color: white; position: relative; overflow: hidden; margin-bottom: 1.3rem; }
        .hero:after { content: ''; position: absolute; width: 300px; height: 300px; border: 1px solid rgba(255,255,255,.13); border-radius: 50%; right: -80px; top: -120px; }
        .hero-kicker { color: #a8d7c5; text-transform: uppercase; letter-spacing: .12em; font-size: .68rem; font-weight: 700; }
        .hero h1 { color: white; max-width: 570px; margin: .65rem 0 .7rem; }
        .hero-copy { color: #cfddd7; max-width: 530px; font-size: 1rem; line-height: 1.55; margin: 0; }
        .section-head { display: flex; align-items: end; justify-content: space-between; margin: 1.7rem 0 .8rem; }
        .section-kicker { color: var(--muted); font-size: .74rem; text-transform: uppercase; letter-spacing: .11em; font-weight: 700; }
        .section-title { font-size: 1.25rem; font-weight: 700; color: var(--ink); margin-top: .2rem; }
        .metric-card { background: var(--surface); border: 1px solid var(--line); border-radius: 13px; padding: 1.15rem 1.2rem; min-height: 112px; box-shadow: 0 5px 18px rgba(21,34,31,.035); }
        .metric-label { color: var(--muted); font-size: .76rem; font-weight: 600; }
        .metric-value { color: var(--ink); font-size: 1.65rem; font-weight: 700; margin-top: .45rem; }
        .metric-detail { color: var(--accent); font-size: .72rem; margin-top: .25rem; }
        .empty-panel { background: var(--surface); border: 1px dashed #cbd9d1; border-radius: 14px; padding: 2.4rem; text-align: center; }
        .empty-panel h3 { margin: 0 0 .4rem; }
        .empty-panel p { color: var(--muted); margin: 0; }
        .upload-panel { background: var(--surface); border: 1px solid var(--line); border-radius: 16px; padding: 1.3rem; box-shadow: 0 5px 18px rgba(21,34,31,.035); }
        .file-meta { background: var(--accent-soft); border-radius: 10px; padding: .8rem 1rem; color: var(--accent); font-size: .85rem; margin: .8rem 0 1rem; }
        .stButton > button { border-radius: 9px; border: 1px solid var(--line); min-height: 2.55rem; font-weight: 600; }
        .stButton > button[kind="primary"] { background: var(--accent); border-color: var(--accent); }
        .stDownloadButton > button { border-radius: 9px; font-weight: 600; }
        [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
        [data-testid="stFileUploader"] { background: #fbfdfb; border: 1px dashed #b8ccc1; border-radius: 12px; padding: .4rem; }
        .caption { color: var(--muted); font-size: .82rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def setup_state():
    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"
    if "transactions" not in st.session_state:
        st.session_state.transactions = None
    if "source_name" not in st.session_state:
        st.session_state.source_name = ""


def navigate(page):
    st.session_state.page = page


def render_topbar():
    columns = st.columns([2.8, 1, 1.15, 1.1, 1, 1.2])
    with columns[0]:
        st.markdown(
            '<div class="topbar"><div class="brand-mark">S</div><div><div class="brand-name">Smart Expense Tracker</div><div class="brand-subtitle">Clarity for every transaction</div></div></div>',
            unsafe_allow_html=True,
        )
    pages = ["Dashboard", "Upload", "Transactions", "Analytics"]
    for index, page in enumerate(pages, start=1):
        with columns[index]:
            st.button(
                page,
                key=f"nav_{page}",
                width="stretch",
                type="primary" if st.session_state.page == page else "secondary",
                on_click=navigate,
                args=(page,),
            )
    with columns[5]:
        st.markdown('<div class="status-pill"><span class="status-dot"></span>Local workspace</div>', unsafe_allow_html=True)


def money(value):
    return f"₹{value:,.0f}"


def render_metric_cards(df):
    total = len(df)
    spending = df["amount"].sum()
    average = df["amount"].mean()
    top_category = df.groupby("category")["amount"].sum().idxmax()
    values = [
        ("Total transactions", f"{total:,}", "Processed successfully"),
        ("Total movement", money(spending), "Across all uploaded rows"),
        ("Top category", top_category, "Highest recorded amount"),
        ("Average transaction", money(average), "Mean transaction value"),
    ]
    columns = st.columns(4)
    for column, (label, value, detail) in zip(columns, values):
        with column:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-detail">{detail}</div></div>',
                unsafe_allow_html=True,
            )


def empty_state(message="Upload a statement to unlock your dashboard."):
    st.markdown(
        f'<div class="empty-panel"><h3>Your financial picture starts here</h3><p>{message}</p></div>',
        unsafe_allow_html=True,
    )
    st.button("Upload transactions", type="primary", on_click=navigate, args=("Upload",), key="empty_upload")


def category_bar(df):
    summary = df.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=True)
    fig = px.bar(summary, x="amount", y="category", orientation="h", text_auto=".2s")
    fig.update_traces(marker_color="#1f6f5b", textfont_color="#15221f")
    fig.update_layout(height=335, margin=dict(l=0, r=10, t=10, b=0), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#697773", xaxis_title=None, yaxis_title=None, showlegend=False)
    return fig


def render_dashboard(df):
    st.markdown('<div class="hero"><div class="hero-kicker">Smart Expense Tracker / Overview</div><h1>Manage your money smarter.</h1><p class="hero-copy">Automatically organize transactions, spot spending patterns, and make better decisions from one calm, focused workspace.</p></div>', unsafe_allow_html=True)
    if df is None:
        st.markdown('<div class="section-head"><div><div class="section-kicker">At a glance</div><div class="section-title">Your dashboard</div></div></div>', unsafe_allow_html=True)
        empty_state()
        return

    render_metric_cards(df)
    st.markdown('<div class="section-head"><div><div class="section-kicker">Overview</div><div class="section-title">Where your money is going</div></div><div class="caption">Based on the latest upload</div></div>', unsafe_allow_html=True)
    left, right = st.columns([1.25, .75])
    with left:
        st.plotly_chart(category_bar(df), width="stretch", config={"displayModeBar": False})
    with right:
        recent = df.sort_values("date", ascending=False).head(5).copy()
        recent["date"] = recent["date"].dt.strftime("%d %b %Y")
        recent["amount"] = recent["amount"].map(money)
        st.markdown("**Recent transactions**")
        st.dataframe(recent[["date", "description", "amount", "category"]], hide_index=True, width="stretch", height=280)


def process_upload(uploaded_file):
    if uploaded_file.name.lower().endswith(".csv"):
        frame = read_csv_file(uploaded_file)
    else:
        frame = read_pdf_file(uploaded_file)
    st.session_state.transactions = categorize_dataframe(frame)
    st.session_state.source_name = uploaded_file.name


def render_upload(df):
    st.markdown('<div class="section-kicker">Import center</div><h1>Upload transactions</h1><p class="caption">Bring in a CSV or PDF bank statement. We will clean, categorize, and prepare it for analysis.</p>', unsafe_allow_html=True)
    st.write("")
    left, right = st.columns([1.25, .75])
    with left:
        st.markdown('<div class="upload-panel">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Choose a statement", type=["csv", "pdf"], help="CSV files need date, description, and amount columns. PDF files should contain a transaction table.")
        if uploaded_file is not None:
            st.markdown(f'<div class="file-meta"><strong>{uploaded_file.name}</strong><br>{uploaded_file.size / 1024:.1f} KB ready to analyze</div>', unsafe_allow_html=True)
            if st.button("Analyze transactions", type="primary", use_container_width=True):
                try:
                    with st.spinner("Cleaning and categorizing transactions..."):
                        process_upload(uploaded_file)
                    st.success(f"Processed {len(st.session_state.transactions)} transactions.")
                    st.session_state.page = "Dashboard"
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="metric-card"><div class="metric-label">Import checklist</div><div class="metric-value">Ready when you are</div><p class="caption">Use a statement with date, description, and amount fields. Currency symbols and commas are cleaned automatically.</p></div>', unsafe_allow_html=True)
        if df is not None:
            st.markdown(f'<div class="file-meta"><strong>Latest upload</strong><br>{st.session_state.source_name} · {len(df)} transactions</div>', unsafe_allow_html=True)


def render_transactions(df):
    st.markdown('<div class="section-kicker">Ledger</div><h1>Transactions</h1><p class="caption">Search and review every cleaned, categorized transaction in your latest statement.</p>', unsafe_allow_html=True)
    if df is None:
        empty_state("Upload a CSV or PDF to view your transaction ledger.")
        return
    first, second, third = st.columns([2.2, 1.1, 1.2])
    with first:
        search = st.text_input("Search descriptions", placeholder="Search merchant or keyword", label_visibility="collapsed")
    with second:
        categories = ["All categories"] + sorted(df["category"].unique().tolist())
        selected = st.selectbox("Filter category", categories, label_visibility="collapsed")
    with third:
        st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), "categorized_transactions.csv", "text/csv", width="stretch")
    result = df.copy()
    if search:
        result = result[result["description"].str.contains(search, case=False, na=False)]
    if selected != "All categories":
        result = result[result["category"] == selected]
    display = result.sort_values("date", ascending=False).copy()
    display["date"] = display["date"].dt.strftime("%d %b %Y")
    display["amount"] = display["amount"].map(money)
    st.caption(f"Showing {len(display)} of {len(df)} transactions")
    st.dataframe(display, hide_index=True, width="stretch", height=520)


def render_analytics(df):
    st.markdown('<div class="section-kicker">Insights</div><h1>Analytics</h1><p class="caption">A closer look at category concentration, merchant patterns, and trends.</p>', unsafe_allow_html=True)
    if df is None:
        empty_state("Upload a statement to generate your analytics.")
        return
    category_summary = df.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    left, right = st.columns(2)
    with left:
        st.markdown("**Spending distribution**")
        pie = px.pie(category_summary, names="category", values="amount", hole=.63, color_discrete_sequence=["#1f6f5b", "#63a58f", "#b1d3c4", "#e0b878", "#9aa9a2", "#cf8e72"])
        pie.update_layout(height=360, margin=dict(l=0, r=0, t=15, b=0), showlegend=True, legend_title=None, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(pie, width="stretch", config={"displayModeBar": False})
    with right:
        st.markdown("**Top merchants and descriptions**")
        merchants = (
            df.groupby("description", as_index=False)
            .agg(total=("amount", "sum"), count=("amount", "count"))
            .sort_values("total", ascending=False)
            .head(7)
        )
        merchants["total"] = merchants["total"].map(money)
        st.dataframe(merchants, hide_index=True, width="stretch", height=360)
    st.markdown('<div class="section-head"><div><div class="section-kicker">Time series</div><div class="section-title">Monthly movement</div></div></div>', unsafe_allow_html=True)
    monthly = df.assign(month=df["date"].dt.to_period("M").astype(str)).groupby("month", as_index=False)["amount"].sum()
    trend = px.area(monthly, x="month", y="amount", markers=True)
    trend.update_traces(line_color="#1f6f5b", fillcolor="rgba(31,111,91,.14)")
    trend.update_layout(height=280, margin=dict(l=0, r=10, t=10, b=0), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis_title=None, yaxis_title=None, showlegend=False)
    st.plotly_chart(trend, width="stretch", config={"displayModeBar": False})


inject_styles()
setup_state()
render_topbar()
current_df = st.session_state.transactions

if st.session_state.page == "Dashboard":
    render_dashboard(current_df)
elif st.session_state.page == "Upload":
    render_upload(current_df)
elif st.session_state.page == "Transactions":
    render_transactions(current_df)
else:
    render_analytics(current_df)
