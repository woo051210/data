import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="의료 불평등 분석", layout="wide")
st.title("🏥 지역별 경제 수준(GRDP)에 따른 의료 수요 격차 분석")

@st.cache_data
def load_and_process_data():
    # 1. 의료 데이터 전처리 (파일 이름 .csv.csv 반영)
    try:
        df_med = pd.read_csv('med.csv.csv', encoding='cp949').iloc[1:].copy()
    except:
        df_med = pd.read_csv('med.csv.csv', encoding='utf-8').iloc[1:].copy()
        
    df_med.columns = ['sido', 'sigungu', 'type1', 'type2', 'patients', 'visit_days', 'care_days', 'total_cost', 'covered_cost']
    df_med = df_med[(df_med['sigungu'] == '소계') & (df_med['type1'] == '합계') & (df_med['type2'] == '소계')]
    df_med = df_med[df_med['sido'] != '계']
    for col in ['patients', 'visit_days']:
        df_med[col] = pd.to_numeric(df_med[col], errors='coerce')
        
    # 2. 경제(GRDP) 데이터 전처리 (파일 이름 .csv.csv 반영)
    try:
        df_grdp = pd.read_csv('grdp.csv.csv', encoding='cp949').iloc[1:].copy()
    except:
        df_grdp = pd.read_csv('grdp.csv.csv', encoding='utf-8').iloc[1:].copy()
        
    df_grdp.columns = ['sido', 'economy_type', 'grdp_nominal', 'grdp_real', 'grdp_contribution']
    df_grdp = df_grdp[df_grdp['economy_type'] == '지역내총생산(시장가격)']
    df_grdp = df_grdp[df_grdp['sido'] != '전국']
    df_grdp['grdp_nominal'] = pd.to_numeric(df_grdp['grdp_nominal'], errors='coerce')
    
    # 3. 지역명 통일화 함수
    def normalize_sido(name):
        name = str(name)
        if '서울' in name: return '서울'
        if '부산' in name: return '부산'
        if '대구' in name: return '대구'
        if '인천' in name: return '인천'
        if '광주' in name: return '광주'
        if '대전' in name: return '대전'
        if '울산' in name: return '울산'
        if '세종' in name: return '세종'
        if '경기' in name: return '경기'
        if '강원' in name: return '강원'
        if '충북' in name or '충청북도' in name: return '충북'
        if '충남' in name or '충청남도' in name: return '충남'
        if '전북' in name or '전라북도' in name: return '전북'
        if '전남' in name or '전라남도' in name: return '전남'
        if '경북' in name or '경상북도' in name: return '경북'
        if '경남' in name or '경상남도' in name: return '경남'
        if '제주' in name: return '제주'
        return name
        
    df_med['sido'] = df_med['sido'].apply(normalize_sido)
    df_grdp['sido'] = df_grdp['sido'].apply(normalize_sido)
    
    return df_med, df_grdp

df_med, df_grdp = load_and_process_data()

# SQL 분석을 위한 가상 DB 구축
conn = sqlite3.connect(':memory:')
df_med[['sido', 'patients', 'visit_days']].to_sql('medical', conn, index=False)
df_grdp[['sido', 'grdp_nominal']].to_sql('economy', conn, index=False)

# 핵심 SQL 쿼리 실행
query = """
SELECT 
    m.sido AS '지역',
    e.grdp_nominal AS '지역내총생산',
    m.patients AS '총환자수',
    m.visit_days AS '총내원일수',
    CAST(m.visit_days AS FLOAT) / m.patients AS '환자1인당_연간내원일수'
FROM medical m
JOIN economy e ON m.sido = e.sido
ORDER BY e.grdp_nominal DESC;
"""
result_df = pd.read_sql(query, conn)

# 스트림릿 화면 출력
st.subheader("1. 핵심 SQL 분석 결과")
st.code(query, language="sql")
st.dataframe(result_df, use_container_width=True)

st.subheader("2. 시각화: 경제 수준과 환자 1인당 내원일수")
st.markdown("**(그래프 설명: 위에서부터 경제 수준 1위입니다. 아래로 갈수록 환자의 병원 방문 횟수가 급증하는 것을 볼 수 있습니다.)**")
chart_data = result_df.set_index('지역')[['환자1인당_연간내원일수']]
st.bar_chart(chart_data)

st.subheader("3. 결과 논의 및 인사이트")
st.success("""
- **결론:** GRDP 상위 지역(서울, 경기)은 환자 1인당 내원일수가 약 20일로 낮지만, 하위 지역(전북, 전남 등)은 약 26~27일로 매우 높게 나타납니다.
- **인사이트:** 병원 등의 인프라는 고소득 지역에 집중되어 있으나, 실질적인 의료 수요(아픔)는 저소득 지역에 집중되어 심각한 '의료 과부하'가 발생하고 있음을 데이터로 증명했습니다.
""")

import streamlit as st
import pandas as pd
import plotly.express as px

# 데이터 로드
med = pd.read_csv("med.csv.csv", encoding="cp949")
grdp = pd.read_csv("grdp.csv.csv", encoding="cp949")

# 데이터 병합 (공통 키를 sido로 가정)
df = pd.merge(med, grdp, on="sido", how="inner")

# 산점도용 지표 생성
df["환자1인당_연간내원일수"] = df["visit_days"] / df["patients"]

# 산점도
fig = px.scatter(
    df,
    x="grdp_nominal",  # grdp.csv.csv의 열 이름이 다르면 수정
    y="환자1인당_연간내원일수",
    color="sido",
    hover_data=["sigungu","patients","visit_days","grdp_nominal"]
)

st.title("GRDP vs 의료 수요 산점도")
st.plotly_chart(fig, use_container_width=True)

st.plotly_chart(fig, use_container_width=True)
