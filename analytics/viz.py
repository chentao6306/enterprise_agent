import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from db.repository import get_all_contracts
from config import REMIND_DAYS

def load_contracts_df():
    contracts = get_all_contracts()
    data = []
    for c in contracts:
        data.append({
            "ID": c.id,
            "文件名": c.filename,
            "甲方": c.party_a,
            "乙方": c.party_b,
            "金额": c.contract_amount,
            "开始日期": c.start_date,
            "结束日期": c.end_date,
            "项目名称": c.project_name
        })
    return pd.DataFrame(data)

def plot_amount_distribution(df):
    if df.empty or df["金额"].isna().all():
        return None
    fig = px.histogram(df, x="金额", nbins=20, title="合同金额分布")
    return fig

def plot_monthly_trend(df):
    if df.empty:
        return None
    df = df.dropna(subset=["开始日期"])
    if df.empty:
        return None
    df["月份"] = pd.to_datetime(df["开始日期"]).dt.to_period("M").astype(str)
    trend = df.groupby("月份").size().reset_index(name="签约数量")
    fig = px.line(trend, x="月份", y="签约数量", title="月度签约趋势", markers=True)
    return fig

def plot_party_pie(df):
    if df.empty:
        return None
    party_counts = df["甲方"].value_counts().reset_index()
    party_counts.columns = ["甲方", "合同数"]
    fig = px.pie(party_counts, names="甲方", values="合同数", title="合作甲方分布")
    return fig

def get_expiring_contracts(df):
    if df.empty:
        return []
    today = datetime.now().date()
    deadline = today + timedelta(days=REMIND_DAYS)
    expiring = df.dropna(subset=["结束日期"])
    expiring = expiring[(expiring["结束日期"] >= today) & (expiring["结束日期"] <= deadline)]
    return expiring[["ID", "文件名", "甲方", "结束日期", "项目名称"]].to_dict(orient="records")
