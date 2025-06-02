import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import pydeck as pdk

# Use default (light) theme; override any dark theme
st.set_page_config(layout="wide")
# Normal black header, default font
st.markdown(
    """
    <style>
    .normal-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #000000;
        margin-bottom: 0.25rem;
    }
    .normal-subheader {
        font-size: 1.2rem;
        color: #333333;
        margin-top: -0.5rem;
        margin-bottom: 1rem;
    }
    </style>
    <div class="normal-header">🧠 Plymouth Psych Group Dashboard</div>
    <div class="normal-subheader">Real-time analytics on providers, revenue, CPTs, and more.</div>
    """,
    unsafe_allow_html=True
)

# File Uploader & Validation
st.sidebar.header("Upload Cleaned Data")
uploaded = st.sidebar.file_uploader("Upload clinic_dashboard_cleaned_with_cpt.csv", type="csv")
if not uploaded:
    st.sidebar.warning("Please upload clinic_dashboard_cleaned_with_cpt.csv to view dashboard.")
    st.stop()

clinic_df = pd.read_csv(uploaded, parse_dates=["Date"])
# Ensure CPT is treated as string for categorical axis
if "CPT" in clinic_df.columns:
    clinic_df["CPT"] = clinic_df["CPT"].astype(str)

st.sidebar.success(f"Loaded {clinic_df.shape[0]} rows")

required_cols = {"Units","Billed Amount","Net Payment","Date","Provider","CPT"}
missing = required_cols - set(clinic_df.columns)
if missing:
    st.error(
        f"⚠️ Uploaded file is missing required columns: {', '.join(missing)}.\n"
        "Please upload clinic_dashboard_cleaned_with_cpt.csv."
    )
    st.stop()

# 1) Executive Summary
st.markdown("---")
st.header("1. 📈 Executive Summary")
clinic_df["Month"] = clinic_df["Date"].dt.to_period("M").astype(str)
all_months = sorted(clinic_df["Month"].unique())
selected_month = st.selectbox("Select Month", all_months)

md = clinic_df[clinic_df["Month"] == selected_month]
tm_units = int(md["Units"].sum())
tm_billed = md["Billed Amount"].sum()
tm_paid = md["Net Payment"].sum()

prev_m = [m for m in all_months if m < selected_month]
if prev_m:
    prev = clinic_df[clinic_df["Month"] == prev_m[-1]]
    pu = int(prev["Units"].sum()); pb = prev["Billed Amount"].sum(); pp = prev["Net Payment"].sum()
else:
    pu = pb = pp = 0

c1,c2,c3 = st.columns(3, gap="large")
c1.metric(f"Units ({selected_month})", f"{tm_units}", f"{tm_units-pu:+d}")
c2.metric(f"Billed ({selected_month})", f"${tm_billed:,.0f}", f"${tm_billed-pb:+,.0f}")
c3.metric(f"Net Payment ({selected_month})", f"${tm_paid:,.0f}", f"${tm_paid-pp:+,.0f}")

# 2) Provider Productivity
st.markdown("---")
st.header("2. 👩‍⚕️ Provider Productivity")
providers = clinic_df["Provider"].dropna().unique().tolist()
sel_prov = st.multiselect("Select Provider(s)", providers, default=providers)

min_date = clinic_df["Date"].min()
max_date = clinic_df["Date"].max()
sel_range = st.date_input("Select Date Range", [min_date, max_date])

fil = clinic_df[
    (clinic_df["Provider"].isin(sel_prov)) &
    (clinic_df["Date"] >= pd.to_datetime(sel_range[0])) &
    (clinic_df["Date"] <= pd.to_datetime(sel_range[1]))
]

sort_metric = st.selectbox("Sort by", ["Units","Billed Amount","Net Payment"])
direction = st.radio("Direction", ("Descending","Ascending"))
asc = direction == "Ascending"

prod_sum = fil.groupby("Provider").agg({"Units":"sum","Billed Amount":"sum","Net Payment":"sum"}).reset_index()
prod_sorted = prod_sum.sort_values(by=sort_metric, ascending=asc)

st.dataframe(
    prod_sorted.style.format({"Billed Amount":"${:,.0f}","Net Payment":"${:,.0f}"}),
    use_container_width=True
)

# 3) CPT Code Analysis
st.markdown("---")
st.header("3. 📋 CPT Code Analysis")
cpt_sum = (
    clinic_df.groupby("CPT")
    .agg({"Units":"sum","Billed Amount":"sum","Net Payment":"sum"})
    .sort_values("Units",ascending=False).reset_index().head(10)
)
fig_cpt = go.Figure(data=[
    go.Bar(x=cpt_sum["CPT"], y=cpt_sum["Units"], name="Units", marker_color="#000000", text=cpt_sum["Units"], textposition='outside'),
    go.Bar(x=cpt_sum["CPT"], y=cpt_sum["Billed Amount"], name="Billed", marker_color="#1f77b4", text=cpt_sum["Billed Amount"], textposition='outside'),
    go.Bar(x=cpt_sum["CPT"], y=cpt_sum["Net Payment"], name="Net Payment", marker_color="#ff7f0e", text=cpt_sum["Net Payment"], textposition='outside'),
])
fig_cpt.update_layout(
    template="plotly_white", title="Top 10 CPT Codes by Units",
    xaxis=dict(title="CPT Code", tickfont=dict(family="Arial"), type="category"),
    yaxis=dict(title="Value", tickfont=dict(family="Arial"), gridcolor="#DDDDDD"),
    plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
    legend=dict(font=dict(color="#000000")),
    font=dict(color="#000000", family="Arial"),
    barmode="group", margin=dict(t=60, b=20, l=20, r=20)
)
st.plotly_chart(fig_cpt, use_container_width=True)

# 4) Monthly Revenue Trend
st.markdown("---")
st.header("4. 📊 Monthly Revenue Trend")
def plot_monthly_trend(df):
    dfm = df.groupby(df["Date"].dt.to_period("M")).agg({"Billed Amount":"sum","Net Payment":"sum"}).reset_index()
    dfm["Month"] = dfm["Date"].astype(str)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dfm["Month"], y=dfm["Billed Amount"], mode="lines+markers", name="Billed", line=dict(color="#1f77b4", width=3), marker=dict(size=8)))
    fig.add_trace(go.Scatter(x=dfm["Month"], y=dfm["Net Payment"], mode="lines+markers", name="Paid", line=dict(color="#ff7f0e", width=3), marker=dict(size=8)))
    fig.update_layout(
        template="plotly_white", title="Monthly Revenue Trend",
        xaxis=dict(title="Month", tickfont=dict(family="Arial")),
        yaxis=dict(title="Amount ($)", tickfont=dict(family="Arial"), gridcolor="#DDDDDD"),
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        legend=dict(font=dict(color="#000000")), font=dict(color="#000000", family="Arial"),
        margin=dict(t=60, b=20, l=20, r=20)
    )
    return fig

st.plotly_chart(plot_monthly_trend(clinic_df), use_container_width=True)

# 5) Billed vs Paid
st.markdown("---")
st.header("5. 💰 Billed vs Paid")
def plot_billed_vs_paid(df):
    dfm = df.groupby(df["Date"].dt.to_period("M")).agg({"Billed Amount":"sum","Net Payment":"sum"}).reset_index()
    dfm["Month"] = dfm["Date"].astype(str)
    fig = go.Figure(data=[
        go.Bar(x=dfm["Month"], y=dfm["Billed Amount"], name="Billed", marker_color="#1f77b4", text=dfm["Billed Amount"], textposition='outside'),
        go.Bar(x=dfm["Month"], y=dfm["Net Payment"], name="Paid", marker_color="#ff7f0e", text=dfm["Net Payment"], textposition='outside')
    ])
    fig.update_layout(
        barmode="stack", template="plotly_white", title="Billed vs Paid",
        xaxis=dict(title="Month", tickfont=dict(family="Arial")),
        yaxis=dict(title="Amount ($)", tickfont=dict(family="Arial"), gridcolor="#DDDDDD"),
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", font=dict(color="#000000", family="Arial"),
        margin=dict(t=60, b=20, l=20, r=20)
    )
    return fig

st.plotly_chart(plot_billed_vs_paid(clinic_df), use_container_width=True)

# 6) Provider Comparison
st.markdown("---")
st.header("6. 🤝 Provider Comparison")
providers = clinic_df["Provider"].dropna().unique().tolist()
sel_two = st.multiselect("Select exactly 2 providers", providers, max_selections=2)
if len(sel_two) == 2:
    cf = clinic_df[clinic_df["Provider"].isin(sel_two)]
    cs = cf.groupby("Provider").agg({"Units":"sum","Billed Amount":"sum","Net Payment":"sum"}).reset_index()
    st.subheader("Comparison Table")
    st.dataframe(cs.style.format({"Billed Amount":"${:,.0f}", "Net Payment":"${:,.0f}"}), use_container_width=True)

    fig2 = go.Figure(data=[
        go.Bar(name="Units", x=cs["Provider"], y=cs["Units"], marker_color="#000000", text=cs["Units"], textposition='outside'),
        go.Bar(name="Billed Amount", x=cs["Provider"], y=cs["Billed Amount"], marker_color="#1f77b4", text=cs["Billed Amount"], textposition='outside'),
        go.Bar(name="Net Payment", x=cs["Provider"], y=cs["Net Payment"], marker_color="#ff7f0e", text=cs["Net Payment"], textposition='outside')
    ])
    fig2.update_layout(
        barmode="group", template="plotly_white",
        xaxis=dict(tickfont=dict(family="Arial")),
        yaxis=dict(title="Value", tickfont=dict(family="Arial"), gridcolor="#DDDDDD"),
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        font=dict(color="#000000", family="Arial"), margin=dict(t=60,b=20,l=20,r=20)
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("🔍 Please select exactly two providers to compare.")

# 7) Operational & Financial KPIs (Synthetic)
@st.cache_data
def generate_fake_kpis(start_date="2024-01-01", days=365):
    dates = pd.date_range(start_date, periods=days)
    ps = clinic_df["Provider"].dropna().unique().tolist()
    out = []
    for date in dates:
        for prov in ps:
            visits = np.random.poisson(12)
            no_shows = np.random.binomial(visits, 0.10)
            completed = visits - no_shows
            tms = np.random.binomial(completed, 0.25)
            billed = np.round(completed * np.random.normal(200,50),2)
            collect = np.random.uniform(0.70,0.95)
            net_paid = np.round(billed * collect,2)
            denials = np.random.binomial(completed,0.10)
            ar_tot = billed - net_paid
            b = np.random.dirichlet([2,1,0.5,0.3])
            ar_age = np.round(ar_tot * b,2)
            out.append({ "Date": date, "Provider": prov, "Visits": visits,
                         "NoShows": no_shows, "TMS": tms,
                         "Billed": billed, "NetPayment": net_paid,
                         "Denials": denials,
                         "AR_0_30": ar_age[0], "AR_31_60": ar_age[1],
                         "AR_61_90": ar_age[2], "AR_90_plus": ar_age[3],
                         "AvgRevPerVisit": net_paid/completed if completed>0 else 0 })
    return pd.DataFrame(out)

fake_kpis = generate_fake_kpis()
st.markdown("---")
st.header("7. ⚙️ Operational & Financial KPIs (Synthetic)")
kpi = fake_kpis.copy()
kpi["Month"] = kpi["Date"].dt.to_period("M").astype(str)
mp = kpi.groupby("Month").agg({ "Visits":"sum","NoShows":"sum","TMS":"sum",
                                "Denials":"sum","Billed":"sum","NetPayment":"sum" }).reset_index()
mp["NoShowRate"] = mp["NoShows"]/mp["Visits"]
mp["DenialRate"] = mp["Denials"]/mp["Visits"]

latest = mp.iloc[-1]
d1,d2,d3,d4 = st.columns(4)
d1.metric("Visits (Last Month)", int(latest["Visits"]))
d2.metric("TMS %", f"{(latest['TMS']/latest['Visits']*100):.1f}%")
d3.metric("No-Show Rate", f"{latest['NoShowRate']:.1%}")
d4.metric("Denial Rate", f"{latest['DenialRate']:.1%}")

aging = kpi.groupby("Month")[["AR_0_30","AR_31_60","AR_61_90","AR_90_plus"]].sum()
st.subheader("A/R Aging by Month")
st.plotly_chart(
    go.Figure(data=[
        go.Bar(name="0-30 days", x=aging.index, y=aging["AR_0_30"], marker_color="#000000", text=aging["AR_0_30"], textposition='outside'),
        go.Bar(name="31-60 days", x=aging.index, y=aging["AR_31_60"], marker_color="#1f77b4", text=aging["AR_31_60"], textposition='outside'),
        go.Bar(name="61-90 days", x=aging.index, y=aging["AR_61_90"], marker_color="#ff7f0e", text=aging["AR_61_90"], textposition='outside'),
        go.Bar(name="90+ days", x=aging.index, y=aging["AR_90_plus"], marker_color="#2ca02c", text=aging["AR_90_plus"], textposition='outside'),
    ]).update_layout(
         barmode="stack", template="plotly_white", plot_bgcolor="#FFFFFF",
         paper_bgcolor="#FFFFFF", font=dict(color="#000000", family="Arial"),
         margin=dict(t=60,b=20,l=20,r=20)
    ),
    use_container_width=True
)