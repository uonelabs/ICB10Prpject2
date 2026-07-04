"""네이버 데이터랩 쇼핑인사이트 및 검색어 트렌드와 쇼핑 검색 스냅샷 데이터를 결합한 쇼핑 트렌드 분석 화면.

작성자: Antigravity
최종 수정일: 2026-07-04
"""
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from common import clean_text, parse_keywords, render_sidebar, require_credentials
from naver_api import (
    SHOPPING_CATEGORIES,
    NaverAPIError,
    datalab_search_trend,
    datalab_shopping_category_trend,
    search_shopping,
)

st.set_page_config(page_title="쇼핑트렌드", page_icon="📈", layout="wide")
client_id, client_secret = render_sidebar()

st.title("📈 쇼핑트렌드")
st.caption(
    "데이터랩 트렌드(기기/성별/연령 조건)와 실시간 쇼핑 검색 스냅샷(가격·판매처)을 "
    "함께 보여줘 관심도 추이와 현재 시장 상황을 같이 파악할 수 있습니다."
)

require_credentials(client_id, client_secret)

analysis_mode = st.radio(
    "분석 기준", ["검색어 직접 입력", "쇼핑 카테고리(분야)"], horizontal=True
)

default_end = date.today()
default_start = default_end - timedelta(days=90)

device_map = {"전체": None, "PC": "pc", "모바일": "mo"}
gender_map = {"전체": None, "남성": "m", "여성": "f"}
age_options = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]
age_labels = {
    "1": "0~12세", "2": "13~18세", "3": "19~24세", "4": "25~29세",
    "5": "30~34세", "6": "35~39세", "7": "40~44세", "8": "45~49세",
    "9": "50~54세", "10": "55~59세", "11": "60세 이상",
}

if analysis_mode == "검색어 직접 입력":
    col1, col2 = st.columns([2, 1])
    with col1:
        keywords_raw = st.text_input("상품 검색어 (쉼표로 구분, 최대 5개)", placeholder="캠핑의자, 텀블러, 에어프라이어")
    with col2:
        time_unit = st.selectbox("구간 단위", ["date", "week", "month"], format_func=lambda x: {"date": "일간", "week": "주간", "month": "월간"}[x], key="kw_unit")
else:
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_categories = st.multiselect(
            "쇼핑 카테고리 (분야, 최대 3개)", options=list(SHOPPING_CATEGORIES.keys())
        )
    with col2:
        time_unit = st.selectbox("구간 단위", ["date", "week", "month"], format_func=lambda x: {"date": "일간", "week": "주간", "month": "월간"}[x], key="cat_unit")

start_date, end_date = st.date_input(
    "조회 기간", value=(default_start, default_end), min_value=date(2016, 1, 1), max_value=default_end
)

c1, c2, c3 = st.columns(3)
device = c1.selectbox("기기", ["전체", "PC", "모바일"])
gender = c2.selectbox("성별", ["전체", "남성", "여성"])
ages = c3.multiselect("연령대", options=age_options, format_func=lambda v: age_labels[v])

if st.button("조회", type="primary"):
    if analysis_mode == "검색어 직접 입력":
        keywords = parse_keywords(keywords_raw, max_count=5)
        if not keywords:
            st.warning("검색어를 1개 이상 입력하세요.")
            st.stop()

        keyword_groups = [{"groupName": kw, "keywords": [kw]} for kw in keywords]
        try:
            with st.spinner("검색 관심도 트렌드 조회 중..."):
                trend_result = datalab_search_trend(
                    client_id, client_secret, start_date.isoformat(), end_date.isoformat(), time_unit,
                    keyword_groups, device=device_map[device], gender=gender_map[gender], ages=ages or None,
                )
        except NaverAPIError as e:
            st.error(f"데이터랩 API 호출 실패: {e}")
            st.stop()

        label_col = "검색어"
        rows = []
        for group in trend_result.get("results", []):
            for point in group.get("data", []):
                rows.append({label_col: group["title"], "날짜": point["period"], "검색비율": point["ratio"]})
        snapshot_queries = keywords

    else:
        if not selected_categories:
            st.warning("카테고리를 1개 이상 선택하세요.")
            st.stop()
        if len(selected_categories) > 3:
            st.warning("카테고리는 최대 3개까지 비교할 수 있습니다. 앞의 3개만 사용합니다.")
            selected_categories = selected_categories[:3]

        categories_param = [
            {"name": cat, "param": [SHOPPING_CATEGORIES[cat]]} for cat in selected_categories
        ]
        try:
            with st.spinner("쇼핑인사이트 분야 트렌드 조회 중..."):
                trend_result = datalab_shopping_category_trend(
                    client_id, client_secret, start_date.isoformat(), end_date.isoformat(), time_unit,
                    categories_param, device=device_map[device], gender=gender_map[gender], ages=ages or None,
                )
        except NaverAPIError as e:
            st.error(f"데이터랩 쇼핑인사이트 API 호출 실패: {e}")
            st.stop()

        label_col = "분야"
        rows = []
        for group in trend_result.get("results", []):
            for point in group.get("data", []):
                rows.append({label_col: group["title"], "날짜": point["period"], "검색비율": point["ratio"]})
        snapshot_queries = selected_categories

    df_trend = pd.DataFrame(rows)

    st.subheader("관심도 추이")
    if df_trend.empty:
        st.info("조회된 트렌드 데이터가 없습니다.")
    else:
        colors = ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD"]
        fig = px.line(
            df_trend,
            x="날짜",
            y="검색비율",
            color=label_col,
            color_discrete_sequence=colors,
        )
        fig.update_traces(
            line=dict(width=3, shape="spline"),
            marker=dict(size=7, symbol="circle", line=dict(width=1.5, color="white")),
            hovertemplate="<b>%{data.name}</b><br>날짜: %{x}<br>검색비율: %{y:.1f}%<extra></extra>"
        )
        fig.update_layout(
            hovermode="x unified",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Pretendard, Inter, sans-serif"),
            xaxis=dict(showgrid=True, gridcolor="rgba(128, 128, 128, 0.15)", gridwidth=1),
            yaxis=dict(showgrid=True, gridcolor="rgba(128, 128, 128, 0.15)", gridwidth=1, ticksuffix="%"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("현재 쇼핑 스냅샷 (가격/판매처)")
    if analysis_mode == "쇼핑 카테고리(분야)":
        st.caption("쇼핑 검색 API는 분야 코드로 직접 필터링을 지원하지 않아, 분야명을 검색어로 사용한 근사 스냅샷입니다.")

    snapshot_rows = []
    try:
        with st.spinner("쇼핑 검색 중..."):
            for q in snapshot_queries:
                result = search_shopping(client_id, client_secret, q, display=40, sort="sim")
                for item in result.get("items", []):
                    lprice = pd.to_numeric(item.get("lprice"), errors="coerce")
                    snapshot_rows.append({
                        label_col: q,
                        "상품명": clean_text(item.get("title", "")),
                        "최저가": lprice,
                        "쇼핑몰": item.get("mallName", ""),
                        "카테고리": item.get("category1", ""),
                    })
    except NaverAPIError as e:
        st.error(f"쇼핑 API 호출 실패: {e}")
        st.stop()

    df_snap = pd.DataFrame(snapshot_rows)
    if df_snap.empty:
        st.info("쇼핑 검색 결과가 없습니다.")
        st.stop()

    # 바 차트 고급화
    colors = ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD"]
    col_a, col_b = st.columns(2)
    with col_a:
        avg_price = df_snap.groupby(label_col)["최저가"].mean().round(0).reset_index()
        fig_price = px.bar(
            avg_price,
            x=label_col,
            y="최저가",
            color=label_col,
            text_auto=".0f",
            title=f"📊 {label_col}별 평균 최저가 (원)",
            color_discrete_sequence=colors
        )
        fig_price.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Pretendard, Inter, sans-serif"),
            xaxis=dict(linecolor="rgba(128, 128, 128, 0.3)"),
            yaxis=dict(showgrid=True, gridcolor="rgba(128, 128, 128, 0.15)", gridwidth=1),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig_price.update_traces(textposition="outside")
        st.plotly_chart(fig_price, use_container_width=True)

    with col_b:
        cat_counts = df_snap.groupby([label_col, "카테고리"]).size().reset_index(name="상품수")
        fig_cat = px.bar(
            cat_counts,
            x="카테고리",
            y="상품수",
            color=label_col,
            barmode="group",
            title=f"📊 {label_col}별 카테고리 분포 (상품수)",
            color_discrete_sequence=colors
        )
        fig_cat.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Pretendard, Inter, sans-serif"),
            xaxis=dict(linecolor="rgba(128, 128, 128, 0.3)"),
            yaxis=dict(showgrid=True, gridcolor="rgba(128, 128, 128, 0.15)", gridwidth=1),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_cat, use_container_width=True)

    st.subheader("상품 스냅샷 테이블")
    st.dataframe(df_snap, use_container_width=True)
    st.download_button(
        "쇼핑 스냅샷 CSV 다운로드", df_snap.to_csv(index=False).encode("utf-8-sig"),
        file_name="shopping_trend_snapshot.csv", mime="text/csv",
    )
