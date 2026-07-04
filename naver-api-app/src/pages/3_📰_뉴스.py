from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from common import clean_text, parse_keywords, render_sidebar, require_credentials
from naver_api import NaverAPIError, search_news

st.set_page_config(page_title="뉴스 검색", page_icon="📰", layout="wide")
client_id, client_secret = render_sidebar()

st.title("📰 뉴스 검색")
st.caption("검색어별 뉴스 검색 결과 수를 비교하고, 기사 목록을 확인합니다.")

require_credentials(client_id, client_secret)

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    keywords_raw = st.text_input("검색어 (쉼표로 구분, 최대 5개)", placeholder="반도체, 인공지능, 전기차")
with col2:
    display = st.slider("검색어당 결과 수", 10, 100, 20, step=10)
with col3:
    sort = st.selectbox("정렬", ["sim", "date"], format_func=lambda x: {"sim": "정확도순", "date": "날짜순"}[x])

use_date_filter = st.checkbox("게재일로 결과 필터링")
if use_date_filter:
    default_end = date.today()
    default_start = default_end - timedelta(days=30)
    start_date, end_date = st.date_input("게재일 범위", value=(default_start, default_end), max_value=default_end)

if st.button("조회", type="primary"):
    keywords = parse_keywords(keywords_raw, max_count=5)
    if not keywords:
        st.warning("검색어를 1개 이상 입력하세요.")
        st.stop()

    all_items = {}
    totals = []
    try:
        with st.spinner("뉴스 검색 중..."):
            for kw in keywords:
                result = search_news(client_id, client_secret, kw, display=display, sort=sort)
                items = result.get("items", [])
                for item in items:
                    item["title"] = clean_text(item.get("title", ""))
                    item["description"] = clean_text(item.get("description", ""))
                all_items[kw] = items
                totals.append({"검색어": kw, "총 검색결과수": result.get("total", 0)})
    except NaverAPIError as e:
        st.error(f"API 호출 실패: {e}")
        st.stop()

    st.subheader("검색어별 총 결과 수 비교")
    df_totals = pd.DataFrame(totals)
    fig = px.bar(df_totals, x="검색어", y="총 검색결과수", color="검색어", text="총 검색결과수")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("기사 목록")
    tabs = st.tabs(keywords)
    for tab, kw in zip(tabs, keywords):
        with tab:
            items = all_items[kw]
            if not items:
                st.info("검색 결과가 없습니다.")
                continue
            df = pd.DataFrame(items)
            if "pubDate" in df.columns:
                df["pubDate_dt"] = pd.to_datetime(df["pubDate"], errors="coerce", utc=True)
                if use_date_filter:
                    mask = (df["pubDate_dt"].dt.date >= start_date) & (df["pubDate_dt"].dt.date <= end_date)
                    df = df[mask]
                df = df.drop(columns=["pubDate_dt"])
            cols = [c for c in ["title", "pubDate", "originallink", "link", "description"] if c in df.columns]
            st.dataframe(df[cols], use_container_width=True, column_config={
                "link": st.column_config.LinkColumn("link"),
                "originallink": st.column_config.LinkColumn("originallink"),
            })
            st.download_button(
                f"'{kw}' CSV 다운로드",
                df[cols].to_csv(index=False).encode("utf-8-sig"),
                file_name=f"news_{kw}.csv",
                mime="text/csv",
                key=f"dl_{kw}",
            )
