# -*- coding: utf-8 -*-
"""
KOSIS 통합 EDA 분석/시각화 실행 스크립트

data_loader.py의 로더 함수(long format)만 사용해 아래를 수행한다.
  1) 7개 원본 데이터셋 무결성(행/열/중복/결측) 요약        -> report/data_summary.txt
  2) eda_kosis.py의 10개 시각화 (전부 long format 기반으로 재계산)
     - 시각화 2(TOP10)는 상품군별(2)=='소계' 필터를 강제 적용해 재계산
       (구 버전 버그: 소계+하위분류를 합산해 가전이 46조로 2배 부풀려짐 -> 올바르게는 23조, 1위는 음식서비스)
     - 거래액 단위는 전부 '백만원 -> 조원'(÷1e6)으로 통일
       (구 버전 버그: ÷1e5를 사용해 모든 거래액 표/차트가 실제의 10배로 표시됨)
  3) eda_shopping.py의 품목별 모바일 비중 / 품목별 전문몰 비중 분석 추가
     -> 카드x쇼핑몰 매칭 조인 키로 report/product_channel_mix.csv 로 저장

실행: python eda_report.py
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import koreanize_matplotlib

from data_loader import (
    BASE_DIR, DATA_DIR,
    load_age_usage, load_media, load_mall_type, load_household, load_raw_frames,
)

IMAGE_DIR = os.path.join(BASE_DIR, "images")
REPORT_DIR = os.path.join(BASE_DIR, "report")
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

plt.rcParams["font.size"] = 11
plt.rcParams["axes.unicode_minus"] = False

TRILLION = 1e6  # 백만원 -> 조원


def savefig(name):
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGE_DIR, name), dpi=150)
    plt.close()


# ─────────────────────────────────────────────────────────
# 0. 데이터 무결성 요약
# ─────────────────────────────────────────────────────────
def report_data_summary():
    frames = load_raw_frames()
    path = os.path.join(REPORT_DIR, "data_summary.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("=== KOSIS 원본 데이터 관찰 요약 ===\n\n")
        for name, df in frames.items():
            f.write(f"데이터셋: {name}\n")
            f.write(f"- 행 수: {df.shape[0]}, 열 수: {df.shape[1]}\n")
            f.write(f"- 중복 행 수: {df.duplicated().sum()}\n")
            f.write(f"- 결측치 개수: {df.isnull().sum().sum()}\n")
            f.write("-" * 50 + "\n")
    print(f"[0] 데이터 무결성 요약 저장 완료 -> {path}")


# ─────────────────────────────────────────────────────────
# 1. 온라인 쇼핑 판매매체별 연간 거래액 추이 (2021~2025)
# ─────────────────────────────────────────────────────────
def plot1_media_trend(media):
    years = ["2021", "2022", "2023", "2024", "2025"]
    total = media[(media["상품군"] == "합계") & (media["매체"] == "인터넷쇼핑")].set_index("연도")["거래액"]
    mobile = media[(media["상품군"] == "합계") & (media["매체"] == "모바일쇼핑")].set_index("연도")["거래액"]

    val_internet = [total[y] / TRILLION for y in years]
    val_mobile = [mobile[y] / TRILLION for y in years]

    plt.figure(figsize=(10, 6))
    plt.plot(years, val_internet, marker="o", label="인터넷 쇼핑 (조원)", color="#1f77b4", linewidth=2.5)
    plt.plot(years, val_mobile, marker="s", label="모바일 쇼핑 (조원)", color="#ff7f0e", linewidth=2.5)
    plt.title("온라인 쇼핑 판매 매체별 연간 거래액 추이 (2021~2025)")
    plt.xlabel("연도"); plt.ylabel("거래액 (조원)")
    plt.grid(True, linestyle="--", alpha=0.5); plt.legend()
    savefig("plot01_media_trend.png")

    print("[1] 매체별 거래액(조원):")
    print(pd.DataFrame({"연도": years, "인터넷쇼핑": val_internet, "모바일쇼핑": val_mobile}).round(2).to_string(index=False))


# ─────────────────────────────────────────────────────────
# 2. 2025년 온라인 쇼핑 상품군별 거래액 TOP10 (소계 필터 강제 적용)
# ─────────────────────────────────────────────────────────
def plot2_top10_products(media):
    t = media[(media["매체"] == "계") & (media["연도"] == "2025") & (media["상품군"] != "합계")].copy()
    t = t.nlargest(10, "거래액").sort_values("거래액")
    t["조원"] = t["거래액"] / TRILLION

    plt.figure(figsize=(10, 6))
    plt.barh(t["상품군"], t["조원"], color="#2ca02c")
    plt.title("2025년 온라인 쇼핑 상품군별 거래액 TOP 10 (소계 기준)")
    plt.xlabel("거래액 (조원)")
    plt.grid(True, axis="x", linestyle="--", alpha=0.5)
    savefig("plot02_top10_products.png")

    print("[2] 2025 TOP10 상품군(조원, 소계 기준):")
    print(t[["상품군", "조원"]].sort_values("조원", ascending=False).round(2).to_string(index=False))


# ─────────────────────────────────────────────────────────
# 3. 온라인쇼핑몰 취급범위별(종합몰 vs 전문몰) 월간 거래액 추이
# ─────────────────────────────────────────────────────────
def plot3_scope_trend(mall):
    months = sorted(mall["월"].unique())
    total_mall = mall[(mall["상품군"] == "합계") & (mall["몰유형"] == "종합몰")].set_index("월")["거래액"]
    special_mall = mall[(mall["상품군"] == "합계") & (mall["몰유형"] == "전문몰")].set_index("월")["거래액"]

    val_total = [total_mall[m] / TRILLION for m in months]
    val_special = [special_mall[m] / TRILLION for m in months]

    x = np.arange(len(months)); width = 0.35
    plt.figure(figsize=(10, 6))
    plt.bar(x - width / 2, val_total, width, label="종합몰 (조원)", color="#9467bd")
    plt.bar(x + width / 2, val_special, width, label="전문몰 (조원)", color="#8c564b")
    plt.xticks(x, months)
    plt.title("온라인 쇼핑몰 취급범위별(종합몰 vs 전문몰) 월간 거래액 추이")
    plt.xlabel("조사 월"); plt.ylabel("거래액 (조원)")
    plt.grid(True, axis="y", linestyle="--", alpha=0.5); plt.legend()
    savefig("plot03_scope_trend.png")

    print("[3] 월별 종합몰/전문몰 거래액(조원):")
    print(pd.DataFrame({"월": months, "종합몰": val_total, "전문몰": val_special}).round(2).to_string(index=False))


# ─────────────────────────────────────────────────────────
# 4. 연령대별 인터넷 쇼핑 이용자 비율 추이 (2019~2024)
# ─────────────────────────────────────────────────────────
def plot4_internet_user_ratio(age_usage):
    years = ["2019", "2020", "2021", "2022", "2023", "2024"]
    ages = ["12-19세", "20대", "30대", "40대", "50대", "60대", "70세 이상"]
    base = age_usage[(age_usage["성별"] == "전체") & (age_usage["지표"] == "인터넷 쇼핑 이용자 비율")]

    plt.figure(figsize=(10, 6))
    table = {}
    for age in ages:
        row = base[base["연령"] == age].set_index("연도")["값"]
        rates = [row[y] for y in years]
        table[age] = rates
        plt.plot(years, rates, marker="o", label=age)

    plt.title("연령대별 인터넷 쇼핑 이용자 비율 추이 (2019~2024)")
    plt.xlabel("연도"); plt.ylabel("이용률 (%)")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    savefig("plot04_internet_user_ratio.png")

    print("[4] 연령대별 인터넷 쇼핑 이용률(%):")
    print(pd.DataFrame(table, index=years).T.to_string())


# ─────────────────────────────────────────────────────────
# 5. 2024년 인터넷 쇼핑 이용자 연령별 월평균 구매빈도 분포
# ─────────────────────────────────────────────────────────
def plot5_purchase_frequency(age_usage):
    ages = ["12-19세", "20대", "30대", "40대", "50대", "60대", "70세 이상"]
    cats = ["월 평균 구매빈도-1회 미만", "월 평균 구매빈도-1~2회 미만",
            "월 평균 구매빈도-2~3회 미만", "월 평균 구매빈도-3회 이상"]
    labels = ["1회 미만", "1~2회 미만", "2~3회 미만", "3회 이상"]

    df2024 = age_usage[(age_usage["성별"] == "전체") & (age_usage["연도"] == "2024") & (age_usage["지표"].isin(cats))]
    piv = df2024.pivot(index="연령", columns="지표", values="값").loc[ages, cats]
    piv.columns = labels

    plt.figure(figsize=(10, 6))
    bottoms = np.zeros(len(ages))
    colors = ["#d62728", "#bcbd22", "#17becf", "#1f77b4"]
    for i, col in enumerate(labels):
        plt.bar(ages, piv[col].values, bottom=bottoms, label=col, color=colors[i])
        bottoms += piv[col].values

    plt.title("2024년 인터넷 쇼핑 이용자 연령별 월평균 구매빈도 분포")
    plt.xlabel("연령대"); plt.ylabel("비율 (%)")
    plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    savefig("plot05_purchase_frequency.png")

    print("[5] 2024 연령별 구매빈도 분포(%):")
    print(piv.to_string())


# ─────────────────────────────────────────────────────────
# 6. 가구원수별 월평균 가계지출 추이 (2019~2024)
# ─────────────────────────────────────────────────────────
def plot6_member_expenditure(hh_size):
    years = ["2019", "2020", "2021", "2022", "2023", "2024"]
    members = ["1인", "2인", "3인", "4인", "5인이상"]
    base = hh_size[(hh_size["항목"] == "가계지출") & (hh_size["가구유형"] == "전체가구")]

    plt.figure(figsize=(10, 6))
    table = {}
    for m in members:
        row = base[base["가구원수별"] == m].set_index("연도")["값"]
        vals = [row[y] / 10000 for y in years]
        table[m] = vals
        plt.plot(years, vals, marker="o", label=f"{m} 가구")

    plt.title("가구원수별 월평균 가계지출 추이 (2019~2024)")
    plt.xlabel("연도"); plt.ylabel("가계지출 (만원)")
    plt.grid(True, linestyle="--", alpha=0.5); plt.legend()
    savefig("plot06_member_expenditure.png")

    print("[6] 가구원수별 가계지출(만원):")
    print(pd.DataFrame(table, index=years).T.round(1).to_string())


# ─────────────────────────────────────────────────────────
# 7. 2024년 소득 5분위별 가계지출 비교 (전체 vs 근로자가구)
# ─────────────────────────────────────────────────────────
def plot7_income_expenditure(hh_income):
    incomes = ["1분위", "2분위", "3분위", "4분위", "5분위"]
    df2024 = hh_income[(hh_income["항목"] == "가계지출") & (hh_income["연도"] == "2024")]

    vals_total, vals_worker = [], []
    for inc in incomes:
        row = df2024[df2024["월소득 5분위별"] == inc]
        vals_total.append(row[row["가구유형"] == "전체가구"]["값"].values[0] / 10000)
        vals_worker.append(row[row["가구유형"] == "근로자가구"]["값"].values[0] / 10000)

    x = np.arange(len(incomes)); width = 0.35
    plt.figure(figsize=(10, 6))
    plt.bar(x - width / 2, vals_total, width, label="전체 가구", color="#17becf")
    plt.bar(x + width / 2, vals_worker, width, label="근로자 가구", color="#1f77b4")
    plt.xticks(x, incomes)
    plt.title("2024년 소득 5분위별 월평균 가계지출 비교")
    plt.xlabel("소득 분위"); plt.ylabel("가계지출 (만원)")
    plt.grid(True, axis="y", linestyle="--", alpha=0.5); plt.legend()
    savefig("plot07_income_expenditure.png")

    print("[7] 2024 소득분위별 가계지출(만원):")
    print(pd.DataFrame({"소득분위": incomes, "전체가구": vals_total, "근로자가구": vals_worker}).round(1).to_string(index=False))


# ─────────────────────────────────────────────────────────
# 8. 2024년 가구주 연령대별 월평균 가계지출 비교
# ─────────────────────────────────────────────────────────
def plot8_age_expenditure(hh_age):
    groups = ["39세이하가구", "40~49세가구", "50~59세가구", "60세이상 가구"]
    df2024 = hh_age[(hh_age["항목"] == "가계지출") & (hh_age["연도"] == "2024") & (hh_age["가구유형"] == "전체가구")]

    vals = [df2024[df2024["가구주연령별"] == g]["값"].values[0] / 10000 for g in groups]

    plt.figure(figsize=(10, 6))
    plt.bar(groups, vals, color="#e377c2", width=0.5)
    plt.title("2024년 가구주 연령대별 월평균 가계지출 비교")
    plt.xlabel("가구주 연령대"); plt.ylabel("가계지출 (만원)")
    plt.grid(True, axis="y", linestyle="--", alpha=0.5)
    savefig("plot08_age_expenditure.png")

    print("[8] 2024 가구주 연령대별 가계지출(만원):")
    print(pd.DataFrame({"연령대": groups, "가계지출(만원)": vals}).round(1).to_string(index=False))


# ─────────────────────────────────────────────────────────
# 9. 소비구간별 가구 분포 비율 추이 (2019~2024)
# ─────────────────────────────────────────────────────────
def plot9_consumption_distribution(hh_expense):
    years = ["2019", "2020", "2021", "2022", "2023", "2024"]
    ranges = ["100만원 미만", "100~200만원 미만", "200~300만원 미만", "300~400만원 미만", "400만원이상"]
    base = hh_expense[(hh_expense["항목"] == "가구분포 (%)") & (hh_expense["가구유형"] == "전체가구")]

    plt.figure(figsize=(10, 6))
    bottoms = np.zeros(len(years))
    table = {}
    for r in ranges:
        row = base[base["소비구간별"] == r].set_index("연도")["값"]
        vals = np.array([row[y] for y in years])
        table[r] = vals
        plt.bar(years, vals, bottom=bottoms, label=r)
        bottoms += vals

    plt.title("소비구간별 가구 분포 비율 추이 (2019~2024)")
    plt.xlabel("연도"); plt.ylabel("가구 비율 (%)")
    plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    savefig("plot09_consumption_distribution.png")

    print("[9] 소비구간별 가구분포(%):")
    print(pd.DataFrame(table, index=years).T.to_string())


# ─────────────────────────────────────────────────────────
# 10. 온라인 쇼핑 내 화장품 상품군 거래액 및 판매매체별 추이 (2021~2025)
# ─────────────────────────────────────────────────────────
def plot10_beauty_trend(media):
    years = ["2021", "2022", "2023", "2024", "2025"]
    beauty = media[media["상품군"] == "화장품"]

    total = beauty[beauty["매체"] == "계"].set_index("연도")["거래액"]
    mobile = beauty[beauty["매체"] == "모바일쇼핑"].set_index("연도")["거래액"]
    internet = beauty[beauty["매체"] == "인터넷쇼핑"].set_index("연도")["거래액"]

    val_total = [total[y] / TRILLION for y in years]
    val_mobile = [mobile[y] / TRILLION for y in years]
    val_internet = [internet[y] / TRILLION for y in years]

    plt.figure(figsize=(10, 6))
    plt.plot(years, val_total, marker="o", label="화장품 거래액 합계 (조원)", color="#d62728", linewidth=2.5)
    plt.plot(years, val_mobile, marker="s", label="화장품 모바일 쇼핑 (조원)", color="#bcbd22", linewidth=2)
    plt.plot(years, val_internet, marker="^", label="화장품 인터넷 쇼핑 (조원)", color="#17becf", linewidth=2)
    plt.title("온라인 쇼핑 내 화장품 상품군 거래액 및 판매매체별 추이 (2021~2025)")
    plt.xlabel("연도"); plt.ylabel("거래액 (조원)")
    plt.grid(True, linestyle="--", alpha=0.5); plt.legend()
    savefig("plot10_beauty_trend.png")

    print("[10] 화장품 거래액(조원):")
    print(pd.DataFrame({"연도": years, "합계": val_total, "모바일쇼핑": val_mobile, "인터넷쇼핑": val_internet}).round(2).to_string(index=False))


# ─────────────────────────────────────────────────────────
# 11~12. 품목별 모바일 비중 / 품목별 전문몰 비중 (카드x쇼핑몰 매칭 조인 키)
# ─────────────────────────────────────────────────────────
def plot11_12_channel_mix(media, mall):
    # 11. 품목별 모바일 비중 (2025년 기준)
    total_2025 = media[(media["매체"] == "계") & (media["연도"] == "2025") & (media["상품군"] != "합계")]
    mobile_2025 = media[(media["매체"] == "모바일쇼핑") & (media["연도"] == "2025") & (media["상품군"] != "합계")]
    mob = total_2025.merge(mobile_2025, on="상품군", suffixes=("_계", "_모바일"))
    mob["모바일비중(%)"] = (mob["거래액_모바일"] / mob["거래액_계"] * 100).round(1)
    mob = mob[["상품군", "모바일비중(%)"]].sort_values("모바일비중(%)", ascending=False)

    plt.figure(figsize=(10, 7))
    plt.barh(mob["상품군"][::-1], mob["모바일비중(%)"][::-1], color="#ff7f0e")
    plt.title("2025년 품목별 모바일 쇼핑 거래 비중")
    plt.xlabel("모바일 비중 (%)")
    plt.grid(True, axis="x", linestyle="--", alpha=0.5)
    savefig("plot11_mobile_share_by_category.png")

    # 12. 품목별 전문몰 비중 (최신월 기준)
    latest_month = sorted(mall["월"].unique())[-1]
    total_m = mall[(mall["몰유형"] == "계") & (mall["월"] == latest_month) & (mall["상품군"] != "합계")]
    special_m = mall[(mall["몰유형"] == "전문몰") & (mall["월"] == latest_month) & (mall["상품군"] != "합계")]
    sp = total_m.merge(special_m, on="상품군", suffixes=("_계", "_전문몰"))
    sp["전문몰비중(%)"] = (sp["거래액_전문몰"] / sp["거래액_계"] * 100).round(1)
    sp = sp[["상품군", "전문몰비중(%)"]].sort_values("전문몰비중(%)", ascending=False)

    plt.figure(figsize=(10, 7))
    plt.barh(sp["상품군"][::-1], sp["전문몰비중(%)"][::-1], color="#8c564b")
    plt.title(f"품목별 전문몰 거래 비중 (기준월: {latest_month})")
    plt.xlabel("전문몰 비중 (%)")
    plt.grid(True, axis="x", linestyle="--", alpha=0.5)
    savefig("plot12_special_mall_share_by_category.png")

    # 카드x쇼핑몰 매칭용 조인 키 테이블로 저장
    join_table = mob.merge(sp, on="상품군", how="inner")
    out_path = os.path.join(REPORT_DIR, "product_channel_mix.csv")
    join_table.to_csv(out_path, index=False, encoding="utf-8-sig")

    print("[11] 2025 품목별 모바일 비중(%):")
    print(mob.to_string(index=False))
    print(f"\n[12] 품목별 전문몰 비중(%, 기준월 {latest_month}):")
    print(sp.to_string(index=False))
    print(f"\n[11-12] 조인 키 테이블 저장 완료 -> {out_path}")


def main():
    print("=" * 60)
    print("KOSIS 통합 EDA 분석 시작")
    print("=" * 60)

    report_data_summary()

    media = load_media()
    mall = load_mall_type()
    age_usage = load_age_usage()
    hh_size = load_household("hh_size")
    hh_income = load_household("hh_income")
    hh_age = load_household("hh_age")
    hh_expense = load_household("hh_expense")

    plot1_media_trend(media)
    plot2_top10_products(media)
    plot3_scope_trend(mall)
    plot4_internet_user_ratio(age_usage)
    plot5_purchase_frequency(age_usage)
    plot6_member_expenditure(hh_size)
    plot7_income_expenditure(hh_income)
    plot8_age_expenditure(hh_age)
    plot9_consumption_distribution(hh_expense)
    plot10_beauty_trend(media)
    plot11_12_channel_mix(media, mall)

    print("\n" + "=" * 60)
    print("모든 시각화 이미지 및 리포트 산출물 저장 완료.")
    print("=" * 60)


if __name__ == "__main__":
    main()
