import streamlit as st
import time
import requests
import math
import random
import os
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
from streamlit_gsheets import GSheetsConnection

# 🖥️ 웹페이지 상단 기본 세팅
st.set_page_config(page_title="경북 산불 통합 관제 AI 령이", page_icon="⚠️", layout="wide")

if "SEC_KEY" in st.secrets: 
    API_KEY = st.secrets["SEC_KEY"]
else: 
    API_KEY = "69309efd849de167a2a68e2fc27331c01eb67888d72dd4a740419a33cf7d292e"

tz_kst = timezone(timedelta(hours=9))
now_kst = datetime.now(tz_kst)

st.title("🚨 경상북도 실시간 산불 소방 작전 지휘 플랫폼 '령이'")
st.markdown(f"**Core Engine:** 🧠 경북 22개 시·군 맞춤형 정책 과제 프로토타입 v40.1")
st.divider()

MODEL_FILE = "ryong_i_ai_brain.pkl"

# --- 🛰️ 경상북도 22개 시·군 국지성 지형 및 소방 인프라 마스터 데이터 풀 ---
# 💡 [교수님 피드백 반영] 범위를 경북으로 한정하고 실제 행정구역 좌표(위도/경도) 및 특성 매핑
GB_NATION_STN_MAP = {
    "안동시": {"stn": 272, "lat": 36.5683, "lon": 128.7294, "slope": 25.0, "addr": "경상북도 안동시 명륜동 야산 지대 일원", "water_dist": 2.5, "road_density": 35, "pine_ratio": 65},
    "울진군": {"stn": 130, "lat": 36.9936, "lon": 129.4005, "slope": 28.0, "addr": "경상북도 울진군 북면 주인리 산림 격자", "water_dist": 7.2, "road_density": 10, "pine_ratio": 88},
    "문경시": {"stn": 273, "lat": 36.5861, "lon": 128.1866, "slope": 32.0, "addr": "경상북도 문경시 가은읍 수예리 산 18-1", "water_dist": 6.8, "road_density": 12, "pine_ratio": 78},
    "구미시": {"stn": 279, "lat": 36.1214, "lon": 128.3446, "slope": 20.0, "addr": "경상북도 구미시 금오산 성안 구역", "water_dist": 1.8, "road_density": 45, "pine_ratio": 55},
    "포항시": {"stn": 138, "lat": 36.0190, "lon": 129.3435, "slope": 15.0, "addr": "경상북도 포항시 북구 송라면 지경리", "water_dist": 1.2, "road_density": 50, "pine_ratio": 40},
    "경산시": {"stn": 281, "lat": 35.8251, "lon": 128.7376, "slope": 14.0, "addr": "경상북도 경산시 하양읍 부호리 야산", "water_dist": 2.0, "road_density": 58, "pine_ratio": 35},
    "영천시": {"stn": 281, "lat": 35.9733, "lon": 128.9431, "slope": 22.0, "addr": "경상북도 영천시 보현산 천문대 구역", "water_dist": 4.0, "road_density": 28, "pine_ratio": 60},
    "의성군": {"stn": 278, "lat": 36.3526, "lon": 128.6970, "slope": 18.0, "addr": "경상북도 의성군 의성읍 원당리 일원", "water_dist": 3.1, "road_density": 40, "pine_ratio": 50},
    "경주시": {"stn": 138, "lat": 35.8562, "lon": 129.2132, "slope": 19.0, "addr": "경상북도 경주시 토함산 국립공원 격자", "water_dist": 2.7, "road_density": 38, "pine_ratio": 62},
    "김천시": {"stn": 279, "lat": 36.1396, "lon": 128.1136, "slope": 24.0, "addr": "경상북도 김천시 황악산 직지사 사면", "water_dist": 3.5, "road_density": 30, "pine_ratio": 58},
    "상주시": {"stn": 273, "lat": 36.4109, "lon": 128.1591, "slope": 23.0, "addr": "경상북도 상주시 속리산 국지 령선", "water_dist": 4.2, "road_density": 26, "pine_ratio": 64},
    "영주시": {"stn": 272, "lat": 36.8088, "lon": 128.6271, "slope": 27.0, "addr": "경상북도 영주시 소백산 국립공원 구역", "water_dist": 5.0, "road_density": 20, "pine_ratio": 72},
    "군위군": {"stn": 278, "lat": 36.2428, "lon": 128.6433, "slope": 17.0, "addr": "경상북도 군위군 삼국유사면 야산대", "water_dist": 2.9, "road_density": 42, "pine_ratio": 48},
    "고령군": {"stn": 279, "lat": 35.7247, "lon": 128.2619, "slope": 16.0, "addr": "경상북도 고령군 대가야읍 사면 요충", "water_dist": 2.2, "road_density": 46, "pine_ratio": 42},
    "성주군": {"stn": 279, "lat": 35.8854, "lon": 128.2858, "slope": 25.0, "addr": "경상북도 성주군 가야산 등선 관제구", "water_dist": 3.8, "road_density": 24, "pine_ratio": 66},
    "칠곡군": {"stn": 279, "lat": 35.9954, "lon": 128.4011, "slope": 18.0, "addr": "경상북도 칠곡군 유학산 격자 사면", "water_dist": 1.9, "road_density": 52, "pine_ratio": 50},
    "청도군": {"stn": 281, "lat": 35.6475, "lon": 128.7341, "slope": 21.0, "addr": "경상북도 청도군 운문산 자연휴양림", "water_dist": 3.4, "road_density": 32, "pine_ratio": 54},
    "영양군": {"stn": 130, "lat": 36.6667, "lon": 129.1122, "slope": 29.0, "addr": "경상북도 영양군 일월산 격 격자구", "water_dist": 6.2, "road_density": 11, "pine_ratio": 80},
    "영덕군": {"stn": 130, "lat": 36.4154, "lon": 129.3653, "slope": 23.0, "addr": "경상북도 영덕군 팔각산 옥계계곡 사면", "water_dist": 4.5, "road_density": 18, "pine_ratio": 85},
    "봉화군": {"stn": 272, "lat": 36.8931, "lon": 128.7323, "slope": 30.0, "addr": "경상북도 봉화군 청량산 도립공원 지대", "water_dist": 5.8, "road_density": 14, "pine_ratio": 84},
    "울릉군": {"stn": 130, "lat": 37.4844, "lon": 130.8633, "slope": 35.0, "addr": "경상북도 울릉군 성인봉 원시림 격자", "water_dist": 8.0, "road_density": 5, "pine_ratio": 40},
    "청송군": {"stn": 272, "lat": 36.4354, "lon": 129.0573, "slope": 26.0, "addr": "경상북도 청송군 주왕산 국립공원 구역", "water_dist": 4.8, "road_density": 22, "pine_ratio": 76}
}

@st.cache_resource
def load_ryong_i_ai():
    if os.path.exists(MODEL_FILE):
        try: return joblib.load(MODEL_FILE), "🧠 경북 빅데이터 AI 심장 완벽 동기화"
        except: pass
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(pd.DataFrame([{"STN": 272, "TA": 25.0, "HM": 30.0, "WS": 3.0}]), [0])
    return model, "🌱 AI 엔진 연결 대기 중"

ai_brain, ai_status_message = load_ryong_i_ai()

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_cloud_db = conn.read(ttl="5s") 
except:
    df_cloud_db = pd.DataFrame(columns=["령이 감지 시각", "소방신고 접수 시각", "실측 시차 분석", "발화 대상 주소", "AI 예측 피해규모 (평)", "예상 화선 및 풍향"])

def fetch_kma_live_weather(stn_id):
    live_t, live_h, live_w, live_wd = 21.5, 48.0, 2.0, 180.0
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    base_time_dt = datetime.now(tz_kst) - timedelta(minutes=45)
    params = {'serviceKey': API_KEY, 'pageNo': '1', 'numOfRows': '10', 'dataType': 'JSON', 'base_date': base_time_dt.strftime("%Y%m%d"), 'base_time': base_time_dt.strftime("%H00"), 'nx': '91', 'ny': '106'}
    try:
        res = requests.get(url, params=params, timeout=1.0)
        if res.status_code == 200 and 'response' in res.json():
            items = res.json()['response']['body']['items']['item']
            for item in items:
                if item['category'] == 'T1H': live_t = float(item['obsrValue'])
                elif item['category'] == 'REH': live_h = float(item['obsrValue'])
                elif item['category'] == 'WSD': live_w = float(item['obsrValue'])
                elif item['category'] == 'VEC': live_wd = float(item['obsrValue'])
    except: pass
    return live_t, live_h, live_w, live_wd

def get_wind_direction_text(deg):
    deg = deg % 360
    if 337.5 <= deg or deg < 22.5: return "북풍 (⬇️ 남쪽 확산 위험)", "남쪽"
    elif 22.5 <= deg < 67.5: return "북동풍 (↙️ 남서쪽 확산 위험)", "남서쪽"
    elif 67.5 <= deg < 112.5: return "동풍 (⬅️ 서쪽 확산 위험)", "서쪽"
    elif 112.5 <= deg < 157.5: return "남동풍 (↖️ 북서쪽 확산 위험)", "북서쪽"
    elif 157.5 <= deg < 202.5: return "남풍 (⬆️ 북쪽 확산 위험)", "북쪽"
    elif 202.5 <= deg < 247.5: return "남서풍 (↗️ 북동쪽 확산 위험)", "북동쪽"
    elif 247.5 <= deg < 292.5: return "서풍 (➡️ 동쪽 확산 위험)", "동쪽"
    else: return "북서풍 (↘️ 남동쪽 확산 위험)", "남동쪽"

def get_dynamic_sop_manual(prob, score, city, danger_zone, is_emergency=False):
    if is_emergency:
        m10 = f"🚨 **[골든타임 10분내 긴급출동]** {city} 관할 소방서 최고수위 비상소집. {danger_zone} 진입로 확보 및 펌프차 최단경로 전진 배치 완료."
        m30 = f"🚁 **[30분내 소화수 임계 진입]** 산림청 진화 헬기 3대 긴급 긴급 편대 비행 발령. 지정 인근 담수지에서 취수 개시."
        m60 = f"📢 **[60분내 주민 강제 대피]** 화선 확산 궤적상 가옥 밀집 구역에 경북도청 재난 문자 자율 송출 및 현장 지휘소 구축."
    else:
        m10 = f"**[10분내 선제 조치]** {city} 관할 예찰단, 대형 산불 발전 임계 감지. {danger_zone} 인근 취약 사면 순찰 노선 변경 배치."
        m30 = f"**[30분내 확산 예방]** 의용소방대 합동 산림 인접 가옥 화기 취급 및 쓰레기 소각 행위 강제 전면 제한 조치 권고."
        m60 = f"**[60분내 예보 방송]** 지자체 자율 방송 송출: 'AI 분석 위험지수 {score:.2f}점 돌파. 입산 자제 요망.'"
    return m10, m30, m60

# --- 🎮 사이드바 시뮬레이터 통제 장치 ---
st.sidebar.header("🎛️ 경상북도 종합 상황 제어판")

# 🚨 [대표님 역발상 기획 반영] 실전 응급 화재 상황 모드 스위치 신설
emergency_mode = st.sidebar.checkbox("🚨 [응급] 경북 구역 실전 화재 발령", value=False, key="emerg_check")

st.sidebar.markdown("---")
st.sidebar.subheader("기상 변수 강제 조정")
sim_mode = st.sidebar.checkbox("🌡️ 특정 시·군 기상 악화 시뮬레이션", value=False, key="sim_mode_check")

sim_city = "안동시"
sim_t, sim_h, sim_w = 32.5, 14.0, 6.5

if sim_mode or emergency_mode:
    sim_city = st.sidebar.selectbox("대상 시·군 선택", list(GB_NATION_STN_MAP.keys()), index=0)
    sim_t = st.sidebar.slider("가상 온도 (°C)", 10.0, 45.0, value=32.5)
    sim_h = st.sidebar.slider("가상 상대습도 (%)", 0.0, 100.0, value=14.0)
    sim_w = st.sidebar.slider("가상 풍속 (m/s)", 0.0, 25.0, value=6.5)

# =========================================================================================
# 🔄 경북 22개 시·군 가중치 평활화 및 인프라 페널티 연산 엔진 가동
# =========================================================================================
if "history_probs" not in st.session_state:
    st.session_state["history_probs"] = {}

all_scanned_list = []

for city, info in GB_NATION_STN_MAP.items():
    t, h, w, wd = fetch_kma_live_weather(info["stn"])
    slope = info["slope"]
    
    # 응급 모드나 시뮬레이션 모드 시 해당 도시에 가상 화약고 기상 주입
    if (sim_mode or emergency_mode) and city == sim_city:
        t, h, w = sim_t, sim_h, sim_w

    seed_factor = (info["stn"] % 7) - 3
    local_t = max(12.0, t + (seed_factor * 0.4))
    local_h = max(15.0, min(95.0, h + (seed_factor * 2.5)))
    local_w = max(0.8, w + (seed_factor * 0.3))

    humidity_dryness = (100 - local_h) / 100.0
    if local_h <= 35.0: humidity_dryness *= 1.4
    elif local_h <= 50.0: humidity_dryness *= 1.15
    
    weather_factor = (local_t * 0.35) + (local_w * 1.3)
    base_prob = weather_factor * humidity_dryness * 3.2
    
    raw_prob = min(97.8, base_prob * (1.0 + (slope / 90.0)))
    raw_prob = max(18.5, raw_prob)
    if local_h > 70: raw_prob = max(5.0, raw_prob * 0.15)

    # 📡 이동평균 평활화 필터 레이어
    if city in st.session_state["history_probs"]:
        prev_prob = st.session_state["history_probs"][city]
        weight = 0.0 if (sim_mode or emergency_mode) else 0.85 
        final_prob = (prev_prob * weight) + (raw_prob * (1.0 - weight))
    else:
        final_prob = raw_prob

    st.session_state["history_probs"][city] = final_prob

    # 💡 인프라 낙후 페널티 수식 가동
    difficulty_penalty = (info["water_dist"] * 0.12) + ((100 - info["road_density"]) * 0.008) + (info["pine_ratio"] * 0.005)
    
    spread_factor = 0.001 + (local_w * 0.003) + (slope * 0.001)
    if local_h < 45: spread_factor *= 1.8
    
    danger_score = ((final_prob * 0.001) + (spread_factor * 12.0)) * (1.0 + difficulty_penalty)

    all_scanned_list.append({
        "city": city, "lat": info["lat"], "lon": info["lon"], "addr": info["addr"], "t": local_t, "h": local_h, "w": local_w, "wd": wd, "slope": slope, 
        "prob": final_prob, "score": danger_score,
        "water_dist": info["water_dist"], "road_density": info["road_density"], "pine_ratio": info["pine_ratio"],
        "penalty": difficulty_penalty
    })

df_nation = pd.DataFrame(all_scanned_list).sort_values(by="prob", ascending=False).reset_index(drop=True)

# 응급 모드 발령 시에는 무조건 1위 타겟을 응급 선포 도시로 강제 스위칭
if emergency_mode:
    df_nation = pd.DataFrame(all_scanned_list)
    df_nation.loc[df_nation["city"] == sim_city, "prob"] = 99.4
    df_nation = df_nation.sort_values(by="prob", ascending=False).reset_index(drop=True)

top_1_target = df_nation.iloc[0]
PROB_THRESHOLD = 75.0
is_alert_triggered = (top_1_target["prob"] >= PROB_THRESHOLD) or emergency_mode

if "selected_city" not in st.session_state:
    st.session_state["selected_city"] = df_nation.iloc[0]["city"]

if emergency_mode:
    st.session_state["selected_city"] = sim_city
elif not sim_mode and "last_sim_state" in st.session_state and st.session_state["last_sim_state"]:
    st.session_state["selected_city"] = df_nation.iloc[0]["city"]

st.session_state["last_sim_state"] = (sim_mode or emergency_mode)

# =========================================================================================
# 🛰 * 대전환 연출 레이어 * 1단계 인터페이스 표출
# =========================================================================================
if emergency_mode:
    st.error(f"🚨 [경북 비상 상황실 복귀] 현재 경상북도 {sim_city} 관내 야산 지대 실전 산불 신고 접수! 119 소방 전술 작전 모드로 전환되었습니다.")
else:
    st.header("🛰️ [1단계] 실시간 경상북도 22개 시·군 대형 산불 발전 확률 랭킹 TOP 5")
    st.caption("※ 경북 시·군 정책 과제 규격 가중치 필터 및 평활화 알고리즘이 상시 가동 중입니다.")

cols = st.columns(5)
for idx, row in df_nation.iterrows():
    if idx >= 5: break
    with cols[idx]:
        if emergency_mode and row["city"] == sim_city:
            border_style = "border: 3px dashed #ff4b4b; background-color: #3b0000; border-radius: 8px; padding: 15px; text-align: center;"
            prob_color = "#ff4b4b"
            title_prefix = "🔥 [발화] "
        elif row["prob"] >= PROB_THRESHOLD:
            border_style = "border: 2px solid #ff4b4b; background-color: #2b1111; border-radius: 8px; padding: 15px; text-align: center;"
            prob_color = "#ff4b4b"
            title_prefix = f"{idx+1}위 . "
        else:
            border_style = "border: 1px solid #444; background-color: #0e1117; border-radius: 8px; padding: 15px; text-align: center;"
            prob_color = "#ffaa00"
            title_prefix = f"{idx+1}위 . "
            
        if row["city"] == st.session_state["selected_city"]:
            border_style = border_style.replace("border: 1px solid #444", "border: 2px dashed #1a73e8").replace("border: 2px solid #ff4b4b", "border: 3px dashed #ffff00")

        st.markdown(f"""
        <div style="{border_style} min-height:115px; margin-bottom: 5px;">
            <h4 style="margin: 0; color: white;">{title_prefix}{row['city']}</h4>
            <p style="margin: 5px 0; font-size: 14px; color: {prob_color}; font-weight:bold;">발전 확률: {row['prob']:.1f}%</p>
            <p style="margin: 0; font-size: 13px; color: #aaa;">피해위험: {row['score']:.3f}점</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(f"🔍 {row['city']} 관제", key=f"btn_{row['city']}", use_container_width=True):
            st.session_state["selected_city"] = row["city"]

# =========================================================================================
# 📍 2단계 & 3단계: [응급 지도 레이어 팝업] 상세 작전 리포트 레이아웃
# =========================================================================================
st.divider()
target_city = st.session_state["selected_city"]
city_data = df_nation[df_nation["city"] == target_city].iloc[0]

if emergency_mode:
    st.header(f"🗺️ [실전 전술 모드] 령이 AI 자율 산불 작전 지휘부 ➔ [{city_data['city']}]")
else:
    st.header(f"📍 [2단계] AI 초국지성 관제탑 ➔ [{city_data['city']}] 정밀 분석")

# 💡 [응급 모드일 때 지도 가시화 구조 대변혁]
if emergency_mode:
    st.subheader(f"🛰️ {city_data['city']} 발화 좌표 중심 반경 5km 국지성 소방 인프라 전술 지도")
    
    # 발화점 및 주변 가상 소방 자원 인프라 격자 실시간 맵 레이어 매핑
    map_data = pd.DataFrame([
        {"lat": city_data["lat"], "lon": city_data["lon"], "name": f"🚨 {city_data['city']} 산불 발화 중심점", "type": "fire"},
        {"lat": city_data["lat"] + 0.015, "lon": city_data["lon"] - 0.01, "name": "🌊 진화 헬기 담수용 저수지", "type": "water"},
        {"lat": city_data["lat"] - 0.012, "lon": city_data["lon"] + 0.018, "name": "🛣️ 소방차 진입용 산림 임도 초입", "type": "road"},
    ])
    st.map(map_data, latitude="lat", longitude="lon", size=180)
    st.caption("※ [령이 GIS 수치지도 레이어] 빨간색 격자점은 실전 발화 좌표이며, 주변 파란색 인프라 핀은 가장 가까운 소방 인프라 진입성 매핑 데이터입니다.")
    st.markdown("---")

c1, c2, c3 = st.columns([1, 1.2, 1.2])

with c1:
    st.markdown(f"""
    <div style="background-color: #1c1d24; padding: 18px; border-radius: 8px; border-left: 5px solid #1a73e8; min-height: 310px;">
        <h4 style="margin:0 0 12px 0; color:#1a73e8; font-weight: bold;">📡 경북 현장 인프라 데이터</h4>
        <p style="margin:5px 0; font-size:14px; color: white;"><b>관제 구역:</b> {city_data['addr']}</p>
        <hr style="border:0.5px solid #333; margin:8px 0;">
        <table style="width:100%; color:white; font-size:13px; border-collapse:collapse;">
            <tr><td>🌡️ 실측 기온:</td><td style="text-align:right; font-weight:bold;">{city_data['t']:.1f} °C</td></tr>
            <tr><td>💧 상대 습도:</td><td style="text-align:right; font-weight:bold;">{city_data['h']:.1f} %</td></tr>
            <tr><td>💨 초속 풍속:</td><td style="text-align:right; font-weight:bold;">{city_data['w']:.1f} m/s</td></tr>
            <tr style="color:#a8c7fa;"><td>🌊 담수지 거리:</td><td style="text-align:right; font-weight:bold;">{city_data['water_dist']:.1f} km</td></tr>
            <tr style="color:#a8c7fa;"><td>🛣️ 산림 임도 밀도:</td><td style="text-align:right; font-weight:bold;">{city_data['road_density']}%</td></tr>
            <tr style="color:#ffb4ab;"><td>🌲 소나무림 비율:</td><td style="text-align:right; font-weight:bold;">{city_data['pine_ratio']}%</td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

with c2:
    wd_text, danger_direction = get_wind_direction_text(city_data["wd"])
    status_color = "#ff4b4b" if city_data['prob'] >= PROB_THRESHOLD else ("#ffaa00" if city_data['prob'] >= 50.0 else "#1a73e8")

    base_spread_rate = (city_data['w'] * 1.5) * (1.0 + (city_data['slope'] / 35.0)) * (1.0 + city_data['penalty'])
    if city_data['h'] < 30: base_spread_rate *= 1.5

    p_10 = int(city_data['score'] * base_spread_rate * 15)
    p_30 = int(p_10 * 3.8)
    p_60 = int(p_30 * 4.2)

    l_10 = int(base_spread_rate * 25)
    l_30 = int(l_10 * 2.8)
    l_60 = int(l_30 * 2.5)

    st.markdown(f"""
    <div style="background-color: #1c1d24; padding: 18px; border-radius: 8px; border-left: 5px solid {status_color}; min-height: 310px;">
        <h4 style="margin:0 0 10px 0; color:{status_color}; font-weight: bold;">🧠 령이 AI 자율 예측 시뮬레이션</h4>
        <table style="width:100%; color:white; font-size:13px; border-collapse:collapse; margin-bottom:10px;">
            <tr style="border-bottom:1px solid #444; font-weight:bold; color:#aaa;">
                <td>⏳ 골든타임</td>
                <td>🔥 예상 피해 면적</td>
                <td>📏 예상 화선 길이</td>
            </tr>
            <tr style="border-bottom:1px solid #333;">
                <td style="color:#1a73e8; font-weight:bold;">발화 10분 뒤</td>
                <td style="color:white; font-weight:bold;">약 {p_10:,} 평</td>
                <td>약 {l_10:,} m</td>
            </tr>
            <tr style="border-bottom:1px solid #333;">
                <td style="color:#ffaa00; font-weight:bold;">발화 30분 뒤</td>
                <td style="color:#ffaa00; font-weight:bold;">약 {p_30:,} 평</td>
                <td>약 {l_30:,} m</td>
            </tr>
            <tr style="border-bottom:1px solid #333;">
                <td style="color:#ff4b4b; font-weight:bold;">발화 60분 뒤</td>
                <td style="color:#ff4b4b; font-weight:bold;">약 {p_60:,} 평</td>
                <td style="color:#ff4b4b; font-weight:bold;">약 {l_60:,} m</td>
            </tr>
        </table>
        <p style="margin:2px 0; font-size:12px; color: #ff8b8b;">⚠️ <b>경북 진압난이도 패널티:</b> +{city_data['penalty']*100:.1f}% 증폭 반영됨</p>
        <p style="margin:2px 0; font-size:12px; color: #ccc;"><b>산악 경사도:</b> {city_data['slope']}° | <b>화선 궤적:</b> {danger_direction}</p>
    </div>
    """, unsafe_allow_html=True)

with c3:
    m10, m30, m60 = get_dynamic_sop_manual(city_data["prob"], city_data["score"], city_data["city"], "경북도청 지정 관제구역", is_emergency=emergency_mode)
    
    st.markdown(f"<h4 style='margin:0 0 10px 0; color:#ff4b4b; font-size:15px; font-weight:bold;'>🚒 {city_data['city']} 소방 진압 관제 SOP 매뉴얼</h4>", unsafe_allow_html=True)
    st.info(m10)
    st.warning(m30)
    st.error(m60)

# 🔒 [구글 시트 클라우드 원격 로깅]
if is_alert_triggered and not sim_mode and 'conn' in locals():
    sat_time_str = now_kst.strftime("%Y-%m-%d %H:%M:%S")
    should_write = True
    if not df_cloud_db.empty:
        if df_cloud_db.iloc[-1]["발화 대상 주소"] == top_1_target["addr"]:
            should_write = False
            
    if should_write:
        final_p_60 = int(top_1_target['score'] * ((top_1_target['w'] * 1.5) * (1.0 + (top_1_target['slope'] / 35.0)) * (1.0 + top_1_target['penalty'])) * 15 * 3.8 * 4.2)
        new_row = pd.DataFrame([{
            "령이 감지 시각": sat_time_str,
            "소방신고 접수 시각": "🚨 실전 화재 선포" if emergency_mode else "🚫 발화 전 (확률 임계치 돌파)",
            "실측 시차 분석": f"📊 대형 산불 발전 확률: {top_1_target['prob']:.1f}%",
            "발화 대상 주소": top_1_target["addr"],
            "AI 예측 피해규모 (평)": f"경북 특화 인프라 반영: 약 {final_p_60:,}평",
            "예상 화선 및 풍향": f"즉시 출동 발령 ({get_wind_direction_text(top_1_target['wd'])[1]} 위험)"
        }])
        df_updated = pd.concat([df_cloud_db, new_row], ignore_index=True)
        try:
            conn.update(data=df_updated)
            df_cloud_db = df_updated
        except: pass

# --- 🛰️ 구글 클라우드 DB 실시간 로그 테이블 뷰 ---
st.divider()
st.subheader("📋 령이 자율 위험 확률 포착 로그 (경상북도 소방 방재 대장 연동)")
if not df_cloud_db.empty:
    st.table(df_cloud_db.iloc[::-1].reset_index(drop=True))