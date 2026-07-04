import pandas as pd
import plotly.express as px
import streamlit as st

from common import clean_text, parse_keywords, render_sidebar, require_credentials
from naver_api import NaverAPIError, search_shopping

st.set_page_config(page_title="쇼핑 검색", page_icon="🛒", layout="wide")
client_id, client_secret = render_sidebar()

st.title("🛒 쇼핑 검색")
st.caption("검색어별 상품 검색 결과와 가격대, 카테고리를 분석합니다.")
st.info("쇼핑 검색 API 응답에는 등록일 필드가 없어 기간 필터는 지원하지 않습니다.", icon="ℹ️")

require_credentials(client_id, client_secret)

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    keywords_raw = st.text_input("검색어 (쉼표로 구분, 최대 5개)", placeholder="무선이어폰, 노트북, 러닝화")
with col2:
    display = st.slider("검색어당 결과 수", 10, 100, 30, step=10)
with col3:
    sort = st.selectbox("정렬", ["sim", "date", "asc", "dsc"], format_func=lambda x: {
        "sim": "정확도순", "date": "날짜순", "asc": "가격 낮은순", "dsc": "가격 높은순",
    }[x])

with st.expander("필터 옵션 (선택)"):
    c1, c2 = st.columns(2)
    naverpay_only = c1.checkbox("네이버페이 연동 상품만")
    exclude_options = c2.multiselect(
        "제외할 상품 유형", options=["used", "rental", "cbshop"],
        format_func=lambda v: {"used": "중고", "rental": "렌탈", "cbshop": "해외직구/구매대행"}[v],
    )

if st.button("조회", type="primary"):
    keywords = parse_keywords(keywords_raw, max_count=5)
    if not keywords:
        st.warning("검색어를 1개 이상 입력하세요.")
        st.stop()

    filter_param = "naverpay" if naverpay_only else None
    exclude_param = ":".join(exclude_options) if exclude_options else None

    all_items = {}
    totals = []
    try:
        with st.spinner("쇼핑 검색 중..."):
            for kw in keywords:
                result = search_shopping(
                    client_id, client_secret, kw, display=display, sort=sort,
                    filter=filter_param, exclude=exclude_param,
                )
                items = result.get("items", [])
                for item in items:
                    item["title"] = clean_text(item.get("title", ""))
                    item["lprice"] = pd.to_numeric(item.get("lprice"), errors="coerce")
                    item["hprice"] = pd.to_numeric(item.get("hprice"), errors="coerce")
                all_items[kw] = items
                totals.append({"검색어": kw, "총 검색결과수": result.get("total", 0)})
    except NaverAPIError as e:
        st.error(f"API 호출 실패: {e}")
        st.stop()

    st.subheader("검색어별 총 결과 수 비교")
    df_totals = pd.DataFrame(totals)
    fig = px.bar(df_totals, x="검색어", y="총 검색결과수", color="검색어", text="총 검색결과수")
    st.plotly_chart(fig, use_container_width=True)

    price_rows = []
    for kw, items in all_items.items():
        for item in items:
            if item.get("lprice"):
                price_rows.append({"검색어": kw, "최저가": item["lprice"], "쇼핑몰": item.get("mallName", ""), "브랜드": item.get("brand", "")})
    if price_rows:
        df_price = pd.DataFrame(price_rows)
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("검색어별 평균 최저가")
            avg_price = df_price.groupby("검색어")["최저가"].mean().round(0).reset_index()
            fig2 = px.bar(avg_price, x="검색어", y="최저가", color="검색어", text="최저가")
            st.plotly_chart(fig2, use_container_width=True)
        with col_b:
            st.subheader("검색어별 가격 분포")
            fig3 = px.box(df_price, x="검색어", y="최저가", color="검색어", points="all")
            st.plotly_chart(fig3, use_container_width=True)

    st.subheader("상품 목록")
    tabs = st.tabs(keywords)
    for tab, kw in zip(tabs, keywords):
        with tab:
            items = all_items[kw]
            if not items:
                st.info("검색 결과가 없습니다.")
                continue
            df = pd.DataFrame(items)
            cols = [c for c in ["title", "lprice", "mallName", "brand", "category1", "category2", "link"] if c in df.columns]
            st.dataframe(df[cols], use_container_width=True, column_config={"link": st.column_config.LinkColumn("link")})
            st.download_button(
                f"'{kw}' CSV 다운로드",
                df[cols].to_csv(index=False).encode("utf-8-sig"),
                file_name=f"shopping_{kw}.csv",
                mime="text/csv",
                key=f"dl_{kw}",
            )
