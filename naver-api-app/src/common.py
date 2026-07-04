"""페이지 공통 유틸리티: 사이드바 API 키 입력, 검색어 파싱, HTML 클린징 등.

수정 내역:
- 최근 검색 히스토리 로드/저장 기능 추가 (history.json 캐시 활용)
- 네이버 API 호출 상태 코드 경고 유틸 추가
"""
from __future__ import annotations

import os
import re
import html as html_lib
import json
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# naver-api-app/.env 를 명시적으로 로드 (실행 위치와 무관하게 동작)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_TAG_RE = re.compile(r"<[^>]+>")


def clean_text(text: str) -> str:
    """검색 결과에 포함된 <b> 태그와 HTML 엔티티를 제거합니다."""
    if not text:
        return ""
    return html_lib.unescape(_TAG_RE.sub("", text))


def render_sidebar() -> tuple[str, str]:
    """왼쪽 사이드바에 API 인증 상태를 표시하고 환경변수에서 키를 가져옵니다.

    naver-api-app/.env 에 설정된 NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET 값을 사용합니다.
    """
    st.sidebar.header("🔑 네이버 API 인증")

    client_id = os.getenv("NAVER_CLIENT_ID", "").strip()
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip()

    if client_id and client_secret:
        st.sidebar.success("API 인증 완료 (.env)")
        # 보안을 위해 ID 일부 마스킹 처리하여 노출
        masked_id = client_id[:4] + "*" * (len(client_id) - 4) if len(client_id) > 4 else "****"
        st.sidebar.text(f"ID: {masked_id}")
    else:
        st.sidebar.error("API 인증 정보가 없습니다. (.env)")
        st.sidebar.warning(
            "naver-api-app/.env 파일에\n"
            "NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을\n"
            "입력한 후 저장해 주세요."
        )
        with st.sidebar.expander("발급 방법 안내"):
            st.markdown(
                "1. [네이버 개발자센터](https://developers.naver.com/apps/#/register) 에서 애플리케이션 등록\n"
                "2. 사용 API에서 **검색**, **데이터랩** 선택\n"
                "3. 등록 후 발급되는 Client ID / Client Secret을\n"
                "   `naver-api-app/.env` 파일에 저장하세요."
            )
        st.stop()

    st.sidebar.divider()
    return client_id, client_secret


def require_credentials(client_id: str, client_secret: str) -> None:
    """API 키가 없으면 안내 메시지를 띄우고 페이지 실행을 중단합니다."""
    if not client_id or not client_secret:
        st.info("왼쪽 사이드바에 네이버 API Client ID / Client Secret을 입력하면 조회를 시작할 수 있습니다.")
        st.stop()


def parse_keywords(raw: str, max_count: int | None = None) -> list[str]:
    """쉼표로 구분된 검색어 문자열을 정제된 리스트로 변환합니다."""
    keywords = [kw.strip() for kw in raw.split(",")]
    keywords = [kw for kw in keywords if kw]
    # 순서를 유지하며 중복 제거
    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)

    if max_count and len(unique) > max_count:
        st.warning(f"검색어는 최대 {max_count}개까지 지원합니다. 앞의 {max_count}개만 사용합니다.")
        unique = unique[:max_count]
    return unique


HISTORY_FILE_PATH = Path(__file__).resolve().parent.parent / "data" / "history.json"


def save_search_history(page_name: str, query: str) -> None:
    """최근 검색어 내역을 로컬 JSON 파일에 기록합니다 (최대 5개 유지)."""
    if not query:
        return

    # 디렉토리 생성 보장
    HISTORY_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    data = {}
    if HISTORY_FILE_PATH.exists():
        try:
            with open(HISTORY_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            data = {}

    history = data.setdefault(page_name, [])

    # 중복 제거 후 가장 앞으로 배치
    if query in history:
        history.remove(query)
    history.insert(0, query)

    # 최대 5개 이력만 유지
    data[page_name] = history[:5]

    try:
        with open(HISTORY_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except IOError:
        pass


def load_search_history(page_name: str) -> list[str]:
    """해당 페이지의 최근 검색어 내역을 가져옵니다."""
    if not HISTORY_FILE_PATH.exists():
        return []
    try:
        with open(HISTORY_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get(page_name, [])
    except (json.JSONDecodeError, IOError):
        return []


def check_api_quota_warning(response_status: int) -> None:
    """네이버 API 호출 결과 중 제한 상태 코드를 감지하고 경고를 출력합니다."""
    if response_status == 429:
        st.error("🚨 [API 호출 한도 초과] 오늘 허용된 네이버 API 호출량을 모두 소모했습니다. 내일 다시 이용해 주시거나 다른 Client ID로 변경해 주세요.")
        st.stop()
    elif response_status == 500:
        st.error("🚨 [네이버 서버 오류] 네이버 API 서버 내부에서 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")
        st.stop()
