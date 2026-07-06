# -*- coding: utf-8 -*-
"""
KOSIS 데이터 로더 모음 (모든 함수가 long format DataFrame을 반환)

팀프로젝트: "내 카드 기준, 어떤 쇼핑몰에서 구매하는 게 유리한가?"
담당 파트: 쇼핑 데이터 EDA (세대별 x 품목별 분류)

Streamlit 대시보드 등 다른 모듈에서 그대로 import하여 재사용합니다.
분석/시각화 실행 코드는 이 파일에 두지 않고 eda_report.py에서 담당합니다.

데이터 출처: KOSIS 공공데이터 (통계청)
  [쇼핑 축]
  - 인터넷_쇼핑_성_연령별            : 연령/성별 이용률·구매빈도 (2019~2024, cp949 전용)
  - 온라인쇼핑몰_판매매체별_상품군별   : 인터넷 vs 모바일 거래액 (2021~2025, 연간, 단위: 백만원)
  - 온라인쇼핑몰_취급상품범위별_상품군별: 종합몰 vs 전문몰 거래액 (2025.12~2026.05, 월간, 단위: 백만원)
  [소비 여력 축 - 보조]
  - 가구주_연령별 / 가구원수별 / 소득5분위별 / 소비구간별 가계수지 (2019~2024, 단위: 원)
"""
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# KOSIS 거래액 원본 단위는 '백만원'. 1조원 = 1,000,000백만원이므로
# 조원 환산 시 반드시 1e6으로 나눈다.
# (과거 코드에서 1e5로 나눠 모든 거래액이 실제보다 10배 부풀려진 적이 있으니 재사용 시 주의)
UNIT_MILLION_TO_TRILLION = 1e6

F = {
    "age_usage":  "인터넷_쇼핑_성_연령별__20260629215223.csv",
    "media":      "온라인쇼핑몰_판매매체별_상품군별거래액_20260705225019.csv",
    "mall_type":  "온라인쇼핑몰_취급상품범위별_상품군별거래액_20260705225051.csv",
    "hh_age":     "가구주_연령별_가구당_월평균_가계수지__전국_1인이상__20260627164004.csv",
    "hh_size":    "가구원수별_가구당_월평균_가계수지__전국_1인이상__20260627163932.csv",
    "hh_income":  "소득5분위별_가구당_가계수지__전국_1인이상__20260627164016.csv",
    "hh_expense": "소비구간별_가구당_월평균_가계수지__전국_1인이상__20260627163946.csv",
}
p = lambda k: os.path.join(DATA_DIR, F[k])


# ─────────────────────────────────────────────────────────
# 1. 인터넷쇼핑 성·연령별 이용률/구매빈도 (long format 변환)
#    구조: 2행 헤더(연도 / 측정지표), cp949 인코딩 전용 파일
# ─────────────────────────────────────────────────────────
def load_age_usage():
    raw = pd.read_csv(p("age_usage"), encoding="cp949", header=None)
    years = raw.iloc[0, 2:].astype(str).str.split(".").str[0].tolist()
    metrics = raw.iloc[1, 2:].tolist()
    body = raw.iloc[2:].reset_index(drop=True)
    body.columns = ["성별", "연령"] + [f"{y}|{m}" for y, m in zip(years, metrics)]
    long = body.melt(id_vars=["성별", "연령"], var_name="key", value_name="값")
    long[["연도", "지표"]] = long["key"].str.split("|", expand=True)
    long = long.drop(columns="key")
    long["값"] = pd.to_numeric(long["값"], errors="coerce")
    return long


# ─────────────────────────────────────────────────────────
# 2. 판매매체별(인터넷/모바일) 상품군 거래액 (연간, 단위: 백만원)
#    핵심: 상품군별(2)=='소계' 만 사용해야 한다.
#    소계 + 하위분류(예: 가전·전자·통신기기의 '가전·전자','통신기기')를
#    함께 합산하면 거래액이 중복 집계된다.
# ─────────────────────────────────────────────────────────
def load_media():
    df = pd.read_csv(p("media"), encoding="utf-8-sig")
    df = df[df["상품군별(2)"] == "소계"].copy()
    year_cols = [c for c in df.columns if c[:2] == "20"]
    long = df.melt(
        id_vars=["상품군별(1)", "판매매체별(1)"],
        value_vars=year_cols, var_name="연도", value_name="거래액",
    ).rename(columns={"상품군별(1)": "상품군", "판매매체별(1)": "매체"})
    long["거래액"] = pd.to_numeric(long["거래액"], errors="coerce")
    return long


# ─────────────────────────────────────────────────────────
# 3. 취급상품범위별(종합몰/전문몰) 상품군 거래액 (월간, 단위: 백만원)
#    주의: '2026.04 p)' 처럼 잠정치 표기 → 제거해야 월 라벨이 일관됨
#    핵심: 여기서도 상품군별(2)=='소계' 만 사용
# ─────────────────────────────────────────────────────────
def load_mall_type():
    df = pd.read_csv(p("mall_type"), encoding="utf-8-sig")
    df = df[df["상품군별(2)"] == "소계"].copy()
    month_cols = [c for c in df.columns if c[:2] == "20"]
    long = df.melt(
        id_vars=["상품군별(1)", "범위별(1)"],
        value_vars=month_cols, var_name="월", value_name="거래액",
    ).rename(columns={"상품군별(1)": "상품군", "범위별(1)": "몰유형"})
    long["월"] = long["월"].str.replace(r"\s*p\)", "", regex=True)  # 잠정치 표기 제거
    long["거래액"] = pd.to_numeric(long["거래액"], errors="coerce")
    return long


# ─────────────────────────────────────────────────────────
# 4. 가계수지 (연령별/가구원수별/소득5분위별/소비구간별) - 소비 여력 보조 데이터
#    구조: 2행 헤더(연도 / 가구유형: 전체가구·근로자가구·근로자외가구)
#    key: "hh_age" | "hh_size" | "hh_income" | "hh_expense"
# ─────────────────────────────────────────────────────────
def load_household(key):
    raw = pd.read_csv(p(key), header=None, encoding="utf-8-sig")
    dim_name = raw.iloc[0, 0]
    years = raw.iloc[0, 2:].astype(str).str.split(".").str[0].tolist()
    htypes = raw.iloc[1, 2:].tolist()
    body = raw.iloc[2:].reset_index(drop=True)
    body.columns = [dim_name, "항목"] + [f"{y}|{h}" for y, h in zip(years, htypes)]
    long = body.melt(id_vars=[dim_name, "항목"], var_name="key", value_name="값")
    long[["연도", "가구유형"]] = long["key"].str.split("|", expand=True)
    long = long.drop(columns="key")
    long["값"] = pd.to_numeric(long["값"], errors="coerce")
    return long


# ─────────────────────────────────────────────────────────
# 5. 데이터 무결성(행/열/중복/결측) 요약 - 7개 데이터셋 공용
# ─────────────────────────────────────────────────────────
def load_raw_frames():
    """원본 그대로(가공 전) DataFrame 7종을 dict로 반환. 무결성 점검 등에 사용."""
    return {
        "가구원수별 가계수지": pd.read_csv(p("hh_size"), encoding="utf-8-sig"),
        "가구주 연령별 가계수지": pd.read_csv(p("hh_age"), encoding="utf-8-sig"),
        "소득5분위별 가계수지": pd.read_csv(p("hh_income"), encoding="utf-8-sig"),
        "소비구간별 가계수지": pd.read_csv(p("hh_expense"), encoding="utf-8-sig"),
        "온라인쇼핑몰 취급범위별 거래액": pd.read_csv(p("mall_type"), encoding="utf-8-sig"),
        "온라인쇼핑몰 판매매체별 거래액": pd.read_csv(p("media"), encoding="utf-8-sig"),
        "인터넷 쇼핑 성/연령별 이용 행태": pd.read_csv(p("age_usage"), encoding="cp949"),
    }
