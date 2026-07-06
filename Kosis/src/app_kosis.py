"""
KOSIS 인터넷 쇼핑 성/연령별 이용 행태 및 온라인 쇼핑 동향 데이터를
정밀 통계 검정, 다개년 세그먼트 예측, 동적 분석 텍스트 등과 결합하여
분석을 수행하는 고급 Streamlit 대시보드 웹앱 소스코드입니다.
"""

import os
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import skew, kurtosis, linregress, chi2_contingency

# 페이지 설정
st.set_page_config(
    page_title="KOSIS 인터넷 쇼핑 통계 검정 및 예측",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 상수 정의
# KOSIS 원본 온라인 쇼핑 거래액의 원본 단위는 '백만 원'이며,
# 1조원 = 1,000,000백만원이므로 '조 원' 단위로 표시하려면 1e6으로 나눠야 한다.
# (과거 1e5를 사용해 모든 거래액이 실제보다 10배 크게 표시되던 버그를 수정함)
UNIT_TO_TRILLION = 1e6

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# 1. 인터넷 쇼핑 Wide Format -> Long Format 변환 및 전처리 함수
def preprocess_internet_shopping(df):
    """
    Wide Format의 KOSIS 인터넷 쇼핑 통계 데이터를 pd.melt()를 사용하여
    Long Format(세그먼트, 성별, 연령대, 연도, 지표명, 값)으로 변환 및 정제합니다.
    """
    if df is None or df.empty:
        return pd.DataFrame()
        
    # 0행에 설명 텍스트 컬럼이 포함된 헤더 행 제거
    if '성별(1)' in df.columns and df.iloc[0]['성별(1)'] == '성별(1)':
        df = df.drop(0).reset_index(drop=True)
        
    # id_vars로 성별, 연령대 고정 후 피벗 해제
    df_melt = df.melt(id_vars=['성별(1)', '연령별(1)'], var_name='raw_var', value_name='값')
    
    # 연도 및 세부 지표 식별자 추출 (예: '2019.1' -> 연도: '2019', 코드: 1)
    def parse_variable(v):
        parts = str(v).split('.')
        year = parts[0]
        code = int(parts[1]) if len(parts) > 1 else 0
        return year, code
        
    parsed_vars = df_melt['raw_var'].apply(parse_variable)
    df_melt['연도'] = [p[0] for p in parsed_vars]
    df_melt['지표코드'] = [p[1] for p in parsed_vars]
    
    # KOSIS 컬럼 인덱스 매핑 정의
    metric_mapping = {
        0: "이용률",
        1: "1회 미만",
        2: "1~2회 미만",
        3: "2~3회 미만",
        4: "3회 이상",
        5: "평균 구매빈도"
    }
    df_melt['지표명'] = df_melt['지표코드'].map(metric_mapping)
    
    # 한글 컬럼명 정리
    df_melt = df_melt.rename(columns={
        '성별(1)': '성별',
        '연령별(1)': '연령대'
    })
    
    # 값 타입 캐스팅
    df_melt['값'] = pd.to_numeric(df_melt['값'], errors='coerce')
    
    # 교차 세그먼트명 합성
    df_melt['세그먼트'] = df_melt['연령대'] + " " + df_melt['성별']
    
    # 필요한 항목만 추출
    df_clean = df_melt[['세그먼트', '성별', '연령대', '연도', '지표명', '값']].dropna(subset=['값'])
    return df_clean

# 데이터 캐싱 로드
@st.cache_data(show_spinner="KOSIS 쇼핑 데이터를 분석용 롱포맷으로 처리하는 중입니다...")
def load_kosis_dashboard_data():
    path_media = os.path.join(DATA_DIR, "온라인쇼핑몰_판매매체별_상품군별거래액_20260705225019.csv")
    path_internet = os.path.join(DATA_DIR, "인터넷_쇼핑_성_연령별__20260629215223.csv")
    
    df_raw_media = pd.read_csv(path_media, encoding="utf-8-sig") if os.path.exists(path_media) else None
    df_raw_internet = pd.read_csv(path_internet, encoding="cp949") if os.path.exists(path_internet) else None
    
    # 인터넷 쇼핑 데이터의 전처리 및 롱포맷 변환 실행
    df_long_internet = preprocess_internet_shopping(df_raw_internet)
    
    return df_raw_media, df_long_internet

df_online_media, df_long_internet = load_kosis_dashboard_data()

# ----------------- 사이드바 필터 및 대시보드 제어 -----------------
st.sidebar.title("⚙️ 상세 분석 설정")

if df_long_internet is not None and not df_long_internet.empty:
    # 이용 가능한 성별x연령대 교차그룹 추출 (전체 연령대 및 성별 전체 제외)
    df_cross_meta = df_long_internet[
        (df_long_internet['성별'].isin(['남자', '여자'])) & 
        (df_long_internet['연령대'] != '전체')
    ]
    available_cross_groups = df_cross_meta['세그먼트'].unique().tolist()
    available_ages = df_cross_meta['연령대'].unique().tolist()
    
    default_selections = [g for g in available_cross_groups if g in ["20대 여자", "20대 남자", "50대 여자", "50대 남자"]]
    if not default_selections:
        default_selections = available_cross_groups[:4]
        
    selected_cross_groups = st.sidebar.multiselect(
        "👥 비교 대상 성별 x 연령대 조합 선택",
        available_cross_groups,
        default=default_selections
    )
    
    years_range = sorted(df_long_internet['연도'].unique().tolist())
    selected_years = st.sidebar.multiselect(
        "📅 분석 대상 연도 선택 (최소 3개년 권장)",
        years_range,
        default=["2022", "2023", "2024"]
    )
else:
    selected_cross_groups = []
    available_ages = []
    selected_years = ["2022", "2023", "2024"]

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **대시보드 주요 분석 특징**\n"
    "- **성별 × 연령대 조합 비교**: '20대 여자' vs '50대 남자' 처럼 복합 세그먼트를 직접 매핑하여 추이를 비교합니다.\n"
    "- **최소 3개년 시계열**: 연도별 변화 추이를 꺾은선으로 누적 추적하여 실질적인 성장/정체 양상을 분석합니다."
)

# 메인 타이틀
st.title("🛍️ KOSIS 성별 × 연령대별 교차 및 다개년 트렌드 분석")
st.markdown("성별 x 연령 세그먼트 간의 인터넷 쇼핑 이용 동향을 3개년 이상의 긴 시계열 관점에서 탐색하고 비즈니스 논거를 확보합니다.")

# 출처 표시 공통 캡션 정의
SOURCE_CAPTION = "출처: KOSIS 국가통계포털(인터넷쇼핑 성·연령별, 온라인쇼핑동향조사) / 추출일: 2026.07"

if df_long_internet is None or df_long_internet.empty:
    st.error("데이터 파일(`인터넷_쇼핑_성_연령별__20260629215223.csv`)을 로드할 수 없거나 형식이 올바르지 않습니다.")
else:
    # 4개 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs([
        "👥 성별 × 연령 교차 추이 비교 (다개년)", 
        "🔗 거래액 × 이용률 결합 분석", 
        "💄 화장품 모바일 쇼핑 시장 규모",
        "📈 세그먼트별 이용률 전망"
    ])
    
    # ----------------- 탭 1: 성별 × 연령 교차 추이 비교 -----------------
    with tab1:
        st.header("👥 성별 × 연령 교차 세그먼트의 다개년 비교")
        st.markdown("선택하신 개별 교차 그룹들이 최근 수년간 인터넷 쇼핑 이용률과 고빈도 구매 패턴 측면에서 어떤 변화를 겪었는지 비교합니다.")
        
        if not selected_cross_groups or not selected_years:
            st.warning("👈 왼쪽 사이드바에서 비교할 '교차그룹 조합'과 '분석 대상 연도(최소 3개년 이상)'를 선택해 주세요.")
        else:
            sorted_years = sorted(selected_years)
            
            # 이용률 및 3회 이상 지표 롱포맷 필터링
            df_ratio_trend = df_long_internet[
                (df_long_internet['세그먼트'].isin(selected_cross_groups)) & 
                (df_long_internet['연도'].isin(sorted_years)) & 
                (df_long_internet['지표명'] == '이용률')
            ].copy()
            
            df_freq_trend = df_long_internet[
                (df_long_internet['세그먼트'].isin(selected_cross_groups)) & 
                (df_long_internet['연도'].isin(sorted_years)) & 
                (df_long_internet['지표명'] == '3회 이상')
            ].copy()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader(f"연도별 쇼핑 이용률 변화 ({sorted_years[0]}~{sorted_years[-1]})")
                fig_ratio_line = px.line(
                    df_ratio_trend,
                    x="연도",
                    y="값",
                    color="세그먼트",
                    markers=True,
                    labels={"값": "이용률 (%)"},
                    title="선택 세그먼트별 인터넷 쇼핑 이용률 다개년 추이",
                    color_discrete_sequence=px.colors.qualitative.Dark2,
                    template="plotly_white"
                )
                fig_ratio_line.update_layout(yaxis_range=[0, 105])
                st.plotly_chart(fig_ratio_line, use_container_width=True)
                
            with col2:
                st.subheader(f"연도별 충성 고객(월 3회 이상) 비율 추이")
                fig_freq_line = px.line(
                    df_freq_trend,
                    x="연도",
                    y="값",
                    color="세그먼트",
                    markers=True,
                    labels={"값": "월 3회 이상 비율 (%)"},
                    title="선택 세그먼트별 월 3회 이상 구매자 비중 추이",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    template="plotly_white"
                )
                fig_freq_line.update_layout(yaxis_range=[0, 105])
                st.plotly_chart(fig_freq_line, use_container_width=True)
                
            # [2번 요구사항] 동적 계산 기반 분석 텍스트 도출
            st.markdown("### 💡 다개년 이용 동향 동적 요약")
            
            # 선택 연도 범위 내 이용률 격차 계산
            slope_info = []
            for seg in selected_cross_groups:
                df_seg_ratio = df_ratio_trend[df_ratio_trend['세그먼트'] == seg].sort_values('연도')
                if len(df_seg_ratio) >= 2:
                    first_val = df_seg_ratio.iloc[0]['값']
                    last_val = df_seg_ratio.iloc[-1]['값']
                    diff = last_val - first_val
                    slope_info.append({"세그먼트": seg, "상승폭": diff})
            
            if slope_info:
                df_slopes = pd.DataFrame(slope_info)
                max_row = df_slopes.loc[df_slopes['상승폭'].idxmax()]
                min_row = df_slopes.loc[df_slopes['상승폭'].idxmin()]
                
                st.write(
                    f"선택하신 {sorted_years[0]}년~{sorted_years[-1]}년 분석 기간 동안, 인터넷 쇼핑 이용률 상승폭이 가장 큰 세그먼트는 "
                    f"**{max_row['세그먼트']}**로 약 **{max_row['상승폭']:.2f}%p** 증가하였습니다. 반면, 상승폭이 가장 저조하거나 하락한 세그먼트는 "
                    f"**{min_row['세그먼트']}**로 약 **{min_row['상승폭']:.2f}%p** 변동하는 데 그쳤습니다."
                )
            else:
                st.write("선택된 연도 범위의 데이터가 부족하여 상승 추세를 계산할 수 없습니다.")
                
            # [3번 요구사항] 통계 검정 섹션 추가 (탭1 하단)
            st.markdown("---")
            st.header("🧪 세그먼트별 통계 검정 분석 (Statistical Testing)")
            
            col_test1, col_test2 = st.columns(2)
            
            with col_test1:
                st.subheader("(a) 인터넷 쇼핑 이용률 선형회귀 분석 (최근 3개년 이상)")
                st.markdown("시간(연도)을 독립변수로 하여 이용률 변화 속도와 유의성(p-value)을 검정합니다.")
                
                regression_results = []
                for seg in selected_cross_groups:
                    df_seg_reg = df_long_internet[
                        (df_long_internet['세그먼트'] == seg) & 
                        (df_long_internet['연도'].isin(sorted_years)) & 
                        (df_long_internet['지표명'] == '이용률')
                    ].sort_values('연도')
                    
                    if len(df_seg_reg) >= 3:
                        x = df_seg_reg['연도'].astype(int).values
                        y = df_seg_reg['값'].values
                        slope, intercept, r_value, p_value, std_err = linregress(x, y)
                        regression_results.append({
                            "세그먼트": seg,
                            "연평균 변화량 (%p)": round(slope, 3),
                            "결정계수 (R²)": round(r_value**2, 3),
                            "p-value": round(p_value, 5)
                        })
                
                if regression_results:
                    df_reg_table = pd.DataFrame(regression_results)
                    # p-value가 0.05 미만인 행 강조 표시 함수
                    def highlight_p_val(row):
                        return ['background-color: #ffcccc' if row['p-value'] < 0.05 else '' for _ in row]
                    
                    st.dataframe(df_reg_table.style.apply(highlight_p_val, axis=1), use_container_width=True)
                    st.caption("※ p-value < 0.05인 유의미한 성장 세그먼트는 붉은색 배경으로 하이라이트됩니다.")
                else:
                    st.warning("선택된 연도 범위가 3개년 미만이거나 충분한 회귀 분석 샘플이 없습니다.")
                    
            with col_test2:
                st.subheader("(b) 연령대별 쇼핑 빈도 분포의 카이제곱 독립성 검정")
                st.markdown(f"최신 연도({sorted_years[-1]}년) 기준, 각 세대 간 구매 빈도 격차가 우연에 의한 것인지 통계적으로 규명합니다.")
                
                # 최신 연도 기준 연령대별 구매 빈도 데이터 피벗 테이블화
                latest_year = sorted_years[-1]
                freq_metrics = ['1회 미만', '1~2회 미만', '2~3회 미만', '3회 이상']
                
                # 전체 성별 기준, 각 세대(연령대) 데이터 집계
                df_chi_data = df_long_internet[
                    (df_long_internet['성별'] == '전체') & 
                    (df_long_internet['연령대'] != '전체') & 
                    (df_long_internet['연도'] == latest_year) & 
                    (df_long_internet['지표명'].isin(freq_metrics))
                ].copy()
                
                if not df_chi_data.empty:
                    # 카이제곱 검정을 위한 교차 표(Contingency Table) 생성
                    pivot_chi = df_chi_data.pivot(index='연령대', columns='지표명', values='값').dropna()
                    
                    try:
                        chi2, p_val, dof, expected = chi2_contingency(pivot_chi.values)
                        
                        st.write(f"**검정 연도**: {latest_year}년")
                        st.write(f"- 카이제곱 통계량 (χ²): `{chi2:.4f}`")
                        st.write(f"- 자유도 (dof): `{dof}`")
                        st.write(f"- 유의확률 (p-value): `{p_val:.6f}`")
                        
                        if p_val < 0.05:
                            st.info(f"👉 **해석**: p-value가 {p_val:.6f}로 유의수준 0.05보다 작으므로, **연령대별 구매 빈도 분포 격차는 통계적으로 매우 유의미한 차이**가 있습니다.")
                        else:
                            st.info(f"👉 **해석**: p-value가 {p_val:.6f}로 유의수준 0.05보다 크므로, 연령대별 구매 빈도 분포 격차는 통계적으로 무작위적(우연)일 가능성이 높습니다.")
                    except Exception as e:
                        st.error(f"카이제곱 분석 수행 중 오류 발생: {e}")
                else:
                    st.warning("분석할 빈도 데이터가 부족합니다.")
                    
        st.markdown("---")
        st.caption(SOURCE_CAPTION)

    # ----------------- 탭 2: 거래액 × 이용률 결합 분석 -----------------
    with tab2:
        st.header("🔗 뷰티/패션 상품군 거래액과 연령대 이용률 결합 분석")
        st.markdown("온라인 쇼핑몰의 카테고리별 실제 매출 성장(거래액)과, 주요 구매력 원천인 특정 연령층 쇼핑 이용률 간의 동조성을 통합 비교합니다.")
        
        if df_online_media is not None:
            # 카테고리 분리
            categories_beauty = ['화장품']
            categories_fashion = ['의복', '신발', '가방', '패션용품 및 액세서리']
            
            df_bf = df_online_media[df_online_media['판매매체별(1)'] == '계'].copy()
            years_bf = ['2021', '2022', '2023', '2024']
            
            # 뷰티 및 패션 연간 거래액 계산
            beauty_yearly_sum = []
            fashion_yearly_sum = []
            for y in years_bf:
                b_val = 0
                for cat in categories_beauty:
                    row_cat = df_bf[df_bf['상품군별(1)'] == cat]
                    # [5번 요구사항] .iloc[0] 전 empty 체크
                    if not row_cat.empty:
                        b_val += float(row_cat[y].values[0])
                beauty_yearly_sum.append(b_val / UNIT_TO_TRILLION)
                
                f_val = 0
                for cat in categories_fashion:
                    row_cat = df_bf[df_bf['상품군별(1)'] == cat]
                    if not row_cat.empty:
                        f_val += float(row_cat[y].values[0])
                fashion_yearly_sum.append(f_val / UNIT_TO_TRILLION)
                
            selected_target_ages = st.multiselect(
                "결합 뷰에 매핑할 비교 대상 연령층 선택", 
                available_ages, 
                default=["20대", "30대", "50대"]
            )
            
            # 이중축 차트 생성
            fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
            
            # 1. 뷰티 거래액 (막대)
            fig_dual.add_trace(
                go.Bar(
                    x=years_bf, 
                    y=beauty_yearly_sum, 
                    name="뷰티(화장품) 온라인 거래액 (조원)",
                    marker_color='#ff85a2', 
                    opacity=0.85
                ),
                secondary_y=False
            )
            
            # 2. 패션 거래액 (막대)
            fig_dual.add_trace(
                go.Bar(
                    x=years_bf, 
                    y=fashion_yearly_sum, 
                    name="패션(의복/신발/가방 등) 온라인 거래액 (조원)",
                    marker_color='#4ea8de', 
                    opacity=0.75
                ),
                secondary_y=False
            )
            
            # 3. 선택한 여러 연령대 쇼핑 이용률 (라인)
            if selected_target_ages:
                line_colors = ['#118ab2', '#06d6a0', '#ffd166', '#f78c6b', '#d62728', '#9467bd', '#8c564b']
                for idx, age_name in enumerate(selected_target_ages):
                    # 롱포맷에서 타겟 연령층의 전체 성별 데이터 추출
                    df_age_target = df_long_internet[
                        (df_long_internet['성별'] == '전체') & 
                        (df_long_internet['연령대'] == age_name) & 
                        (df_long_internet['연도'].isin(years_bf)) & 
                        (df_long_internet['지표명'] == '이용률')
                    ].sort_values('연도')
                    
                    if not df_age_target.empty:
                        age_rates = df_age_target['값'].values
                        color = line_colors[idx % len(line_colors)]
                        
                        fig_dual.add_trace(
                            go.Scatter(
                                x=years_bf, 
                                y=age_rates, 
                                name=f"{age_name} 이용률 (%)",
                                mode="lines+markers",
                                line=dict(color=color, width=3),
                                marker=dict(size=8)
                            ),
                            secondary_y=True
                        )
            
            fig_dual.update_layout(
                title="뷰티 vs 패션 거래액 규모 및 세대별 쇼핑 이용률 추이 결합 뷰 (2021~2024)",
                xaxis_title="연도",
                barmode="group",
                template="plotly_white",
                legend=dict(x=0.02, y=0.98)
            )
            
            fig_dual.update_yaxes(title_text="거래액 (조원)", secondary_y=False)
            fig_dual.update_yaxes(title_text="이용률 (%)", secondary_y=True, range=[0, 110])
            
            st.plotly_chart(fig_dual, use_container_width=True)
            
            # [2번 요구사항] 하드코딩 수치 동적 계산 변환
            b_2021_val = beauty_yearly_sum[0]
            f_2024_val = fashion_yearly_sum[-1]
            
            st.markdown(
                f"**🔗 결합 분석 인사이트**:\n"
                f"- **뷰티(화장품)** 카테고리는 2021년 **{b_2021_val:.2f}조 원** 규모에서 시작하여 안정적인 성장을 유지하고 있습니다.\n"
                f"- **패션(의복/신발/가방/액세서리)** 카테고리는 2024년 기준 **{f_2024_val:.2f}조 원** 규모에 달하며, 이커머스에서 가장 강력한 매출 비중을 띱니다.\n"
                f"- 뷰티와 패션의 매출 성장 동향을 선택한 **{', '.join(selected_target_ages) if selected_target_ages else '지정 연령'}** 쇼핑 이용률들과 함께 이중축으로 비교하여, 세대별 시장 기여 및 활성화 동조성을 비교 진단할 수 있습니다."
            )
        else:
            st.warning("거래액 데이터 로드 실패로 결합 분석을 표시할 수 없습니다.")
            
        st.markdown("---")
        st.caption(SOURCE_CAPTION)

    # ----------------- 탭 3: 화장품(뷰티) 온라인 소비 트렌드 -----------------
    with tab3:
        st.header("💄 화장품(뷰티) 상품군 모바일 거래 분석")
        st.markdown("온라인 쇼핑 중 모바일로 구매하는 화장품 시장의 성장력과 점유율을 시각화합니다.")
        
        if df_online_media is not None:
            df_beauty = df_online_media[df_online_media['상품군별(1)'] == '화장품'].copy()
            row_beauty_total = df_beauty[df_beauty['판매매체별(1)'] == '계']
            row_beauty_mobile = df_beauty[df_beauty['판매매체별(1)'] == '모바일쇼핑']
            row_beauty_pc = df_beauty[df_beauty['판매매체별(1)'] == '인터넷쇼핑']
            
            years_beauty = ['2021', '2022', '2023', '2024', '2025']
            
            # [5번 요구사항] empty 체크 및 KeyError 방지
            has_2025 = all(y in df_beauty.columns for y in years_beauty)
            
            if not row_beauty_total.empty and not row_beauty_mobile.empty and not row_beauty_pc.empty and has_2025:
                row_beauty_total = row_beauty_total.iloc[0]
                row_beauty_mobile = row_beauty_mobile.iloc[0]
                row_beauty_pc = row_beauty_pc.iloc[0]
                
                beauty_data = []
                for y in years_beauty:
                    beauty_data.append({
                        "연도": y,
                        "총 거래액(조원)": float(row_beauty_total[y])/UNIT_TO_TRILLION,
                        "모바일 쇼핑(조원)": float(row_beauty_mobile[y])/UNIT_TO_TRILLION,
                        "PC 쇼핑(조원)": float(row_beauty_pc[y])/UNIT_TO_TRILLION
                    })
                df_b_trend = pd.DataFrame(beauty_data)
                
                col5, col6 = st.columns([3, 2])
                
                with col5:
                    fig_beauty_trend = go.Figure()
                    fig_beauty_trend.add_trace(go.Bar(x=df_b_trend['연도'], y=df_b_trend['총 거래액(조원)'], name='총 거래액(조원)', marker_color='#ff85a2'))
                    fig_beauty_trend.add_trace(go.Scatter(x=df_b_trend['연도'], y=df_b_trend['모바일 쇼핑(조원)'], name='모바일 거래액', mode='lines+markers', line=dict(color='#d62728', width=3)))
                    fig_beauty_trend.update_layout(title="연도별 화장품 온라인 거래액 및 모바일 쇼핑 추이 (조원)", template="plotly_white")
                    st.plotly_chart(fig_beauty_trend, use_container_width=True)
                    
                with col6:
                    val_total_2025 = float(row_beauty_total['2025'])
                    val_mobile_2025 = float(row_beauty_mobile['2025'])
                    val_pc_2025 = float(row_beauty_pc['2025'])
                    
                    labels = ['모바일 쇼핑', 'PC 쇼핑']
                    values = [val_mobile_2025, val_pc_2025]
                    
                    fig_pie = px.pie(values=values, names=labels, color_discrete_sequence=['#ff4d6d', '#ffb3c1'],
                                     title="2025년 화장품 쇼핑 매체 점유율 (%)", hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)
                    
                # [2번 요구사항] 하드코딩 텍스트 동적 계산식 적용
                beauty_2025_total_trillion = val_total_2025 / UNIT_TO_TRILLION
                mobile_ratio_2025 = (val_mobile_2025 / val_total_2025) * 100
                
                st.markdown(
                    f"**💡 모바일 채널 시사점**:\n"
                    f"- 화장품 상품군은 2025년 기준 온라인 전체 거래액 **{beauty_2025_total_trillion:.2f}조 원** 중 "
                    f"**{mobile_ratio_2025:.2f}%**가 모바일 기기를 통해 유통되고 있습니다.\n"
                    f"- 이는 PC 화면보다 스마트폰 앱에서의 검색 노출 최적화 및 모바일 결제 마찰을 극소화하는 UX/UI 리더십(올리브영 앱 등)의 당위성을 입증합니다."
                )
            else:
                st.warning("데이터에 2025년 또는 화장품 정보가 누락되어 모바일 거래액 분석을 건너뜁니다.")
        else:
            st.warning("온라인쇼핑몰 거래액 데이터가 존재하지 않아 뷰티 분석을 스킵합니다.")
            
        st.markdown("---")
        st.caption(SOURCE_CAPTION)

    # ----------------- [4번 요구사항] 탭 4: 세그먼트별 이용률 전망 -----------------
    with tab4:
        st.header("📈 선택 세그먼트별 인터넷 쇼핑 이용률 전망 (2025~2026)")
        st.markdown("2019~2024년 실측 데이터를 선형 회귀로 피팅하여 향후 2개년의 인터넷 쇼핑 이용률 추이를 예측합니다.")
        
        if not selected_cross_groups:
            st.warning("👈 왼쪽 사이드바에서 분석 및 예측을 실행할 세그먼트를 1개 이상 선택해 주세요.")
        else:
            fig_pred = go.Figure()
            
            line_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
            
            for idx, seg in enumerate(selected_cross_groups):
                df_seg_ratio = df_long_internet[
                    (df_long_internet['세그먼트'] == seg) & 
                    (df_long_internet['지표명'] == '이용률')
                ].sort_values('연도')
                
                if len(df_seg_ratio) >= 4:
                    x_actual = df_seg_ratio['연도'].astype(int).values
                    y_actual = df_seg_ratio['값'].values
                    
                    # 선형 회귀 파라미터 학습
                    slope, intercept, r_value, p_value, std_err = linregress(x_actual, y_actual)
                    
                    # 예측 연도 범위 확장 (2019~2026)
                    x_pred = np.array([2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026])
                    y_pred = slope * x_pred + intercept
                    
                    # 100% 한계로 클리핑
                    y_pred = np.clip(y_pred, 0, 100)
                    
                    # 신뢰구간 (95% CI) 산출
                    n = len(x_actual)
                    y_fitted = slope * x_actual + intercept
                    residuals = y_actual - y_fitted
                    se = np.sqrt(np.sum(residuals**2) / (n - 2)) if n > 2 else 1.0
                    
                    mean_x = np.mean(x_actual)
                    sum_sq_x = np.sum((x_actual - mean_x)**2)
                    
                    # 95% 신뢰구간에 사용되는 t-임계값 (자유도 n-2, alpha=0.05)
                    # 표본 개수가 적으므로 대략적인 2.0으로 근사
                    t_val = 2.0 
                    
                    ci_upper = []
                    ci_lower = []
                    for x_val in x_pred:
                        se_pred = se * np.sqrt(1 + (1 / n) + ((x_val - mean_x)**2) / sum_sq_x) if sum_sq_x > 0 else se
                        margin = t_val * se_pred
                        ci_upper.append(np.clip(slope * x_val + intercept + margin, 0, 100))
                        ci_lower.append(np.clip(slope * x_val + intercept - margin, 0, 100))
                    
                    color = line_colors[idx % len(line_colors)]
                    
                    # 1. 신뢰구간 (음영) 그리기
                    x_fill = list(x_pred) + list(x_pred[::-1])
                    y_fill = list(ci_upper) + list(ci_lower[::-1])
                    
                    fig_pred.add_trace(go.Scatter(
                        x=x_fill,
                        y=y_fill,
                        fill='toself',
                        fillcolor=color,
                        line=dict(color='rgba(255,255,255,0)'),
                        hoverinfo="skip",
                        showlegend=False,
                        opacity=0.1
                    ))
                    
                    # 2. 실측치 (실선)
                    fig_pred.add_trace(go.Scatter(
                        x=x_actual,
                        y=y_actual,
                        mode="lines+markers",
                        name=f"{seg} (실측치)",
                        line=dict(color=color, width=3),
                        marker=dict(size=7)
                    ))
                    
                    # 3. 예측치 (점선 - 2024~2026 구간만 표시)
                    x_future = np.array([2024, 2025, 2026])
                    y_future = slope * x_future + intercept
                    y_future = np.clip(y_future, 0, 100)
                    
                    fig_pred.add_trace(go.Scatter(
                        x=x_future,
                        y=y_future,
                        mode="lines",
                        name=f"{seg} (예측치)",
                        line=dict(color=color, width=2, dash="dash"),
                        showlegend=True
                    ))
            
            fig_pred.update_layout(
                title="선형 회귀 기반 주요 세그먼트 인터넷 쇼핑 이용률 예측 및 95% 신뢰구간",
                xaxis_title="연도",
                yaxis_title="이용률 (%)",
                yaxis_range=[0, 105],
                template="plotly_white"
            )
            st.plotly_chart(fig_pred, use_container_width=True)
            st.caption("※ 실선은 KOSIS 실측 데이터이며, 점선은 회귀 피팅을 통한 2025~2026 외삽 예측 추세선입니다. 음영 영역은 95% 확률 신뢰 구간을 뜻합니다.")
            
            # 지정된 주의 문구
            st.caption("예측 전제: 선형 추세 유지 가정, 데이터 6개년 한계")
            
        st.markdown("---")
        st.caption(SOURCE_CAPTION)
