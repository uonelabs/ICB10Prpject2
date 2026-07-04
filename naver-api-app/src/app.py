import streamlit as st

from common import render_sidebar

st.set_page_config(page_title="네이버 오픈 API 대시보드", page_icon="📊", layout="wide")

client_id, client_secret = render_sidebar()

st.title("📊 네이버 오픈 API 통합 대시보드")
st.markdown(
    """
네이버 검색/데이터랩 오픈 API를 활용해 검색어 트렌드, 블로그, 뉴스, 카페, 쇼핑 데이터를
수집하고 분석하는 대시보드입니다. 왼쪽 사이드바에서 API 인증 정보를 입력한 뒤,
왼쪽 메뉴에서 원하는 페이지로 이동하세요.
"""
)

if client_id and client_secret:
    st.success("API 인증 정보가 입력되었습니다. 왼쪽 메뉴에서 페이지를 선택하세요.")
else:
    st.warning("아직 API 인증 정보가 입력되지 않았습니다. 왼쪽 사이드바를 확인하세요.")

st.divider()

st.subheader("페이지 구성")
st.markdown(
    """
| 페이지 | 설명 |
| --- | --- |
| 🔍 검색어 트렌드 | 데이터랩 API로 여러 검색어(쉼표 구분)의 기간별 상대 검색량 추이 비교 |
| 📝 블로그 | 검색어별 블로그 검색 결과 수 비교 및 게시물 목록 |
| 📰 뉴스 | 검색어별 뉴스 검색 결과 수 비교 및 기사 목록 |
| ☕ 카페 | 검색어별 카페글 검색 결과 수 비교 및 게시물 목록 |
| 🛒 쇼핑 | 검색어별 상품 검색 결과, 가격대·카테고리 분석 |
| 📈 쇼핑트렌드 | 데이터랩 트렌드(기기/성별/연령 필터) + 실시간 쇼핑 가격 스냅샷 결합 분석 |

모든 검색 페이지는 검색어를 **쉼표(,)로 구분**해 여러 개를 동시에 입력할 수 있고,
트렌드 페이지에서는 **조회 기간**을 직접 설정할 수 있습니다.
"""
)

st.caption("API 문서: naver-api-app/docs 폴더 참고")
