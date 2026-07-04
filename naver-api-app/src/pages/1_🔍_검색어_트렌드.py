"""네이버 데이터랩 API를 이용하여 다중 검색어의 기간별 상대 검색량 트렌드를 비교 분석하는 화면.

작성자: Antigravity
최종 수정일: 2026-07-04
"""
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from common import (
    parse_keywords,
    render_sidebar,
    require_credentials,
    load_search_history,
    save_search_history,
    check_api_quota_warning,
)
from naver_api import NaverAPIError, datalab_search_trend

st.set_page_config(page_title="검색어 트렌드", page_icon="🔍", layout="wide")
client_id, client_secret = render_sidebar()

st.title("🔍 검색어 트렌드")
st.caption("데이터랩 API로 여러 검색어의 기간별 상대 검색량(0~100)을 비교합니다.")

require_credentials(client_id, client_secret)

# 1단계: 필수 입력 및 최근 기록 로드
st.subheader("1단계: 검색어 및 분석 단위 설정")
history = load_search_history("search_trend")
selected_history = None
if history:
    selected_history = st.selectbox(
        "🕒 최근 분석한 검색어 불러오기",
        options=["선택 안 함"] + history,
        index=0
    )

default_keywords = ""
if selected_history and selected_history != "선택 안 함":
    default_keywords = selected_history

col1, col2 = st.columns([2, 1])
with col1:
    keywords_raw = st.text_input(
        "검색어 (쉼표로 구분, 최대 5개)", value=default_keywords, placeholder="아이폰, 갤럭시, 삼성"
    )
with col2:
    time_unit = st.selectbox("구간 단위", ["date", "week", "month"], format_func=lambda x: {"date": "일간", "week": "주간", "month": "월간"}[x])

default_end = date.today()
default_start = default_end - timedelta(days=90)
start_date, end_date = st.date_input(
    "조회 기간",
    value=(default_start, default_end),
    min_value=date(2016, 1, 1),
    max_value=default_end,
)
st.subheader("2단계: 분석 조건 및 필터 설정")
with st.expander("세부 조건 (선택)"):
    c1, c2, c3 = st.columns(3)
    device = c1.selectbox("기기", ["전체", "PC", "모바일"])
    gender = c2.selectbox("성별", ["전체", "남성", "여성"])
    ages = c3.multiselect(
        "연령대",
        options=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
        format_func=lambda v: {
            "1": "0~12세", "2": "13~18세", "3": "19~24세", "4": "25~29세",
            "5": "30~34세", "6": "35~39세", "7": "40~44세", "8": "45~49세",
            "9": "50~54세", "10": "55~59세", "11": "60세 이상",
        }[v],
    )

device_map = {"전체": None, "PC": "pc", "모바일": "mo"}
gender_map = {"전체": None, "남성": "m", "여성": "f"}

if st.button("조회", type="primary"):
    keywords = parse_keywords(keywords_raw, max_count=5)
    if not keywords:
        st.warning("검색어를 1개 이상 입력하세요.")
        st.stop()

    keyword_groups = [{"groupName": kw, "keywords": [kw]} for kw in keywords]

    try:
        with st.spinner("데이터랩 조회 중..."):
            result = datalab_search_trend(
                client_id,
                client_secret,
                start_date.isoformat(),
                end_date.isoformat(),
                time_unit,
                keyword_groups,
                device=device_map[device],
                gender=gender_map[gender],
                ages=ages or None,
            )
    except NaverAPIError as e:
        error_msg = str(e)
        if "[429]" in error_msg:
            check_api_quota_warning(429)
        elif "[500]" in error_msg:
            check_api_quota_warning(500)
        else:
            st.error(f"API 호출 실패: {e}")
        st.stop()

    rows = []
    for group in result.get("results", []):
        for point in group.get("data", []):
            rows.append({"검색어": group["title"], "날짜": point["period"], "검색비율": point["ratio"]})
    df = pd.DataFrame(rows)

    # 성공적으로 조회 시 검색어 히스토리에 기록
    save_search_history("search_trend", keywords_raw)

    if df.empty:
        st.info("조회된 데이터가 없습니다.")
        st.stop()

    # 프리미엄 HSL 계열 색상 팔레트 정의 (다양한 검색어에 조화롭고 세련된 느낌 전달)
    colors = ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD"]

    fig = px.line(
        df,
        x="날짜",
        y="검색비율",
        color="검색어",
        title="검색어별 상대 검색량 추이",
        color_discrete_sequence=colors,
    )

    # 개별 라인 및 마커 상세 디자인 설정
    fig.update_traces(
        line=dict(width=3, shape="spline"),  # 곡선 스플라인 형태로 부드러운 전개
        marker=dict(size=7, symbol="circle", line=dict(width=1.5, color="white")),  # 테두리가 있는 마커
        hovertemplate="<b>%{data.name}</b><br>날짜: %{x}<br>검색비율: %{y:.1f}%<extra></extra>"
    )

    # 레이아웃 고도화 설정
    fig.update_layout(
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Pretendard, Inter, sans-serif"),
        title=dict(
            text="📈 검색어별 상대 검색량 추이",
            font=dict(size=18, weight="bold"),
            x=0.0,
            y=0.95
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(128, 128, 128, 0.15)",
            gridwidth=1,
            linecolor="rgba(128, 128, 128, 0.3)"
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(128, 128, 128, 0.15)",
            gridwidth=1,
            linecolor="rgba(128, 128, 128, 0.3)",
            ticksuffix="%"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=20, r=20, t=80, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("요약 통계")
    summary = df.groupby("검색어")["검색비율"].agg(평균="mean", 최댓값="max", 최솟값="min").round(2)
    st.dataframe(summary, use_container_width=True)

    st.subheader("원본 데이터")
    st.dataframe(df, use_container_width=True)
    st.download_button(
        "CSV 다운로드", df.to_csv(index=False).encode("utf-8-sig"), file_name="search_trend.csv", mime="text/csv"
    )
