import pandas as pd
import plotly.express as px
import streamlit as st

from common import clean_text, parse_keywords, render_sidebar, require_credentials
from naver_api import NaverAPIError, search_cafearticle

st.set_page_config(page_title="카페글 검색", page_icon="☕", layout="wide")
client_id, client_secret = render_sidebar()

st.title("☕ 카페글 검색")
st.caption("검색어별 카페글 검색 결과 수를 비교하고, 게시물 목록을 확인합니다.")
st.info("카페글 검색 API 응답에는 작성일 필드가 없어 기간 필터는 지원하지 않습니다.", icon="ℹ️")

require_credentials(client_id, client_secret)

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    keywords_raw = st.text_input("검색어 (쉼표로 구분, 최대 5개)", placeholder="육아, 다이어트, 인테리어")
with col2:
    display = st.slider("검색어당 결과 수", 10, 100, 20, step=10)
with col3:
    sort = st.selectbox("정렬", ["sim", "date"], format_func=lambda x: {"sim": "정확도순", "date": "날짜순"}[x])

if st.button("조회", type="primary"):
    keywords = parse_keywords(keywords_raw, max_count=5)
    if not keywords:
        st.warning("검색어를 1개 이상 입력하세요.")
        st.stop()

    all_items = {}
    totals = []
    try:
        with st.spinner("카페글 검색 중..."):
            for kw in keywords:
                result = search_cafearticle(client_id, client_secret, kw, display=display, sort=sort)
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

    st.subheader("카페별 게시물 분포")
    cafe_counts = []
    for kw, items in all_items.items():
        for item in items:
            cafe_counts.append({"검색어": kw, "카페명": item.get("cafename", "")})
    if cafe_counts:
        df_cafe = pd.DataFrame(cafe_counts)
        top_cafes = (
            df_cafe.groupby(["검색어", "카페명"]).size().reset_index(name="게시물수")
            .sort_values("게시물수", ascending=False).groupby("검색어").head(5)
        )
        fig2 = px.bar(top_cafes, x="카페명", y="게시물수", color="검색어", barmode="group", title="검색어별 상위 카페 (Top 5)")
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("게시물 목록")
    tabs = st.tabs(keywords)
    for tab, kw in zip(tabs, keywords):
        with tab:
            items = all_items[kw]
            if not items:
                st.info("검색 결과가 없습니다.")
                continue
            df = pd.DataFrame(items)
            cols = [c for c in ["title", "cafename", "link", "cafeurl", "description"] if c in df.columns]
            st.dataframe(df[cols], use_container_width=True, column_config={
                "link": st.column_config.LinkColumn("link"),
                "cafeurl": st.column_config.LinkColumn("cafeurl"),
            })
            st.download_button(
                f"'{kw}' CSV 다운로드",
                df[cols].to_csv(index=False).encode("utf-8-sig"),
                file_name=f"cafearticle_{kw}.csv",
                mime="text/csv",
                key=f"dl_{kw}",
            )
