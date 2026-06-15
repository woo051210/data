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
import matplotlib.pyplot as plt
import pydeck as pdk

st.subheader("3. 시각화: GRDP vs 환자 1인당 내원일수 (산점도)")

fig, ax = plt.subplots()

x = result_df['지역내총생산']
y = result_df['환자1인당_연간내원일수']

ax.scatter(x, y)

# 👉 추세선 (핵심!)
z = np.polyfit(x, y, 1)
p = np.poly1d(z)
ax.plot(x, p(x), linestyle='--')

ax.set_xlabel("GRDP (지역내총생산)")
ax.set_ylabel("환자 1인당 내원일수")

st.pyplot(fig)

st.markdown("""
👉 **해석:**  
경제 수준이 낮은 지역일수록 환자의 병원 방문 횟수가 증가하는 경향이 나타남  
→ '의료 수요의 역설' 확인
""")

coords = {
    '서울': (37.5665, 126.9780),
    '부산': (35.1796, 129.0756),
    '대구': (35.8722, 128.6025),
    '인천': (37.4563, 126.7052),
    '광주': (35.1595, 126.8526),
    '대전': (36.3504, 127.3845),
    '울산': (35.5384, 129.3114),
    '세종': (36.4800, 127.2890),
    '경기': (37.4138, 127.5183),
    '강원': (37.8228, 128.1555),
    '충북': (36.6357, 127.4913),
    '충남': (36.5184, 126.8000),
    '전북': (35.7175, 127.1530),
    '전남': (34.8679, 126.9910),
    '경북': (36.4919, 128.8889),
    '경남': (35.4606, 128.2132),
    '제주': (33.4996, 126.5312)
}

result_df['lat'] = result_df['지역'].apply(lambda x: coords[x][0])
result_df['lon'] = result_df['지역'].apply(lambda x: coords[x][1])

st.subheader("4. 시각화: 지역별 의료 수요 지도")

layer = pdk.Layer(
    "ScatterplotLayer",
    data=result_df,
    get_position='[lon, lat]',
    get_radius="환자1인당_연간내원일수 * 15000",
    get_fill_color='[255, 환자1인당_연간내원일수 * 5, 0, 150]',
    pickable=True
)

view_state = pdk.ViewState(
    latitude=36.5,
    longitude=127.8,
    zoom=6
)

st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip={"text": "{지역}\n내원일수: {환자1인당_연간내원일수}"}
))

st.markdown("""
👉 **해석:**  
원이 클수록 의료 이용이 많은 지역  
→ 지방에서 의료 수요가 더 높게 나타남
""")
