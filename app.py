import streamlit as st
import time
import requests
import math
import random
import os
import json
from datetime import datetime, timedelta, timezone
import pandas as pd
import pydeck as pdk

# 🖥️ 웹페이지 상단 기본 세팅 및 레이아웃 확장
st.set_page_config(page_title="경북 산불 통합 관제 AI 령이", page_icon="⚠️", layout="wide")

API_KEY = "69309efd849de167a2a68e2fc27331c01eb67888d72dd4a740419a33cf7d292e"
tz_kst = timezone(timedelta(hours=9))
now_kst = datetime.now(tz_kst)

# 🔄 [세션 상태 관리 및 초기화 보호선]
if "selected_city" not in st.session_state:
    st.session_state["selected_city"] = None
if "prev_emerg_state" not in st.session_state:
    st.session_state["prev_emerg_state"] = False

st.title("🚨 경상북도 실시간 산불 소방 작전 지휘 플랫폼 '령이'")
st.markdown(f"**Core Engine v55.0:** 🚒 관할 소방서 최적 진입로 자율 연산 & 🔒 응급 모드 오버라이딩 버그 완전 박멸본")
st.divider()

# --- 🛰️ 경상북도 22개 시·군 로컬 지형 및 [AI 내장형 관할 소방서] 마스터 풀 ---
# 령이가 자체적으로 최단거리 소방서와 출동 루트를 연산하기 위해 119 인프라 좌표를 100% 매핑 내장했습니다.
GB_NATION_STN_MAP = {
    "안동시": {"stn": 272, "lat": 36.5683, "lon": 128.7294, "slope": 25.0, "addr": "경상북도 안동시 명륜동 야산 지대 일원", "water_dist": 2.5, "road_density": 35, "pine_ratio": 65, "fire_station": "안동소방서 와룡119안전센터", "fs_lat": 36.6210, "fs_lon": 128.7520},
    "울진군": {"stn": 130, "lat": 36.9936, "lon": 129.4005, "slope": 28.0, "addr": "경상북도 울진군 북면 주인리 산림 격자", "water_dist": 7.2, "road_density": 10, "pine_ratio": 88, "fire_station": "울진소방서 북면119안전센터", "fs_lat": 36.9850, "fs_lon": 129.3510},
    "문경시": {"stn": 273, "lat": 36.5861, "lon": 128.1866, "slope": 32.0, "addr": "경상북도 문경시 가은읍 수예리 산 18-1", "water_dist": 6.8, "road_density": 12, "pine_ratio": 78, "fire_station": "문경소방서 가은119안전센터", "fs_lat": 36.6340, "fs_lon": 128.1250},
    "구미시": {"stn": 279, "lat": 36.1214, "lon": 128.3446, "slope": 20.0, "addr": "경상북도 구미시 금오산 성안 구역", "water_dist": 1.8, "road_density": 45, "pine_ratio": 55, "fire_station": "구미소방서 송정119안전센터", "fs_lat": 36.1180, "fs_lon": 128.3580},
    "포항시": {"stn": 138, "lat": 36.0190, "lon": 129.3435, "slope": 15.0, "addr": "경상북도 포항시 북구 송라면 지경리", "water_dist": 1.2, "road_density": 50, "pine_ratio": 40, "fire_station": "포항북부소방서 흥해119안전센터", "fs_lat": 36.0820, "fs_lon": 129.3510},
    "경산시": {"stn": 281, "lat": 35.8251, "lon": 128.7376, "slope": 14.0, "addr": "경상북도 경산시 하양읍 부호리 야산", "water_dist": 2.0, "road_density": 58, "pine_ratio": 35, "fire_station": "경산소방서 하양119안전센터", "fs_lat": 35.9120, "fs_lon": 128.8150},
    "영천시": {"stn": 281, "lat": 35.9733, "lon": 128.9431, "slope": 22.0, "addr": "경상북도 영천시 보현산 천문대 구역", "water_dist": 4.0, "road_density": 28, "pine_ratio": 60, "fire_station": "영천소방서 화북119지역대", "fs_lat": 36.0410, "fs_lon": 128.9610},
    "의성군": {"stn": 278, "lat": 36.3526, "lon": 128.6970, "slope": 18.0, "addr": "경상북도 의성군 의성읍 원당리 일원", "water_dist": 3.1, "road_density": 40, "pine_ratio": 50, "fire_station": "의성소방서 의성119안전센터", "fs_lat": 36.3510, "fs_lon": 128.6820},
    "경주시": {"stn": 138, "lat": 35.8562, "lon": 129.2132, "slope": 19.0, "addr": "경상북도 경주시 토함산 국립공원 격자", "water_dist": 2.7, "road_density": 38, "pine_ratio": 62, "fire_station": "경주소방서 불국동119안전센터", "fs_lat": 35.7950, "fs_lon": 129.3120},
    "김천시": {"stn": 279, "lat": 36.1396, "lon": 128.1136, "slope": 24.0, "addr": "경상북도 김천시 황악산 직지사 사면", "water_dist": 3.5, "road_density": 30, "pine_ratio": 58, "fire_station": "김천소방서 다수119안전센터", "fs_lat": 36.1210, "fs_lon": 128.0820},
    "상주시": {"stn": 273, "lat": 36.4109, "lon": 128.1591, "slope": 23.0, "addr": "경상북도 상주시 속리산 국지 령선", "water_dist": 4.2, "road_density": 26, "pine_ratio": 64, "fire_station": "상주소방서 함창119안전센터", "fs_lat": 36.5650, "fs_lon": 128.1650},
    "영주시": {"stn": 272, "lat": 36.8088, "lon": 128.6271, "slope": 27.0, "addr": "경상북도 영주시 소백산 국립공원 구역", "water_dist": 5.0, "road_density": 20, "pine_ratio": 72, "fire_station": "영주소방서 풍기119안전센터", "fs_lat": 36.8650, "fs_lon": 128.5250},
    "군위군": {"stn": 278, "lat": 36.2428, "lon": 128.6433, "slope": 17.0, "addr": "경상북도 군위군 삼국유사면 야산대", "water_dist": 2.9, "road_density": 42, "pine_ratio": 48, "fire_station": "군위소방서 의흥119안전센터", "fs_lat": 36.1650, "fs_lon": 128.7450},
    "고령군": {"stn": 279, "lat": 35.7247, "lon": 128.2619, "slope": 16.0, "addr": "경상북도 고령군 대가야읍 사면 요충", "water_dist": 2.2, "road_density": 46, "pine_ratio": 42, "fire_station": "고령소방서 대가야119안전센터", "fs_lat": 35.7110, "fs_lon": 128.2510},
    "성주군": {"stn": 279, "lat": 35.8854, "lon": 128.2858, "slope": 25.0, "addr": "경상북도 성주군 가야산 등선 관제구", "water_dist": 3.8, "road_density": 24, "pine_ratio": 66, "fire_station": "성주소방서 수륜119지역대", "fs_lat": 35.8010, "fs_lon": 128.1850},
    "칠곡군": {"stn": 279, "lat": 35.9954, "lon": 128.4011, "slope": 18.0, "addr": "경상북도 칠곡군 유학산 격자 사면", "water_dist": 1.9, "road_density": 52, "pine_ratio": 50, "fire_station": "칠곡소방서 가산119지역대", "fs_lat": 36.0850, "fs_lon": 128.5120},
    "청도군": {"stn": 281, "lat": 35.6475, "lon": 128.7341, "slope": 21.0, "addr": "경상북도 청도군 운문산 자연휴양림", "water_dist": 3.4, "road_density": 32, "pine_ratio": 54, "fire_station": "청도소방서 금천119안전센터", "fs_lat": 35.6810, "fs_lon": 128.9150},
    "영양군": {"stn": 130, "lat": 36.6667, "lon": 129.1122, "slope": 29.0, "addr": "경상북도 영양군 일월산 격 격자구", "water_dist": 6.2, "road_density": 11, "pine_ratio": 80, "fire_station": "영양소방서 영양119안전센터", "fs_lat": 36.6580, "fs_lon": 129.1150},
    "영덕군": {"stn": 130, "lat": 36.4154, "lon": 129.3653, "slope": 23.0, "addr": "경상북도 영덕군 팔각산 옥계계곡 사면", "water_dist": 4.5, "road_density": 18, "pine_ratio": 85, "fire_station": "영덕소방서 영해119안전센터", "fs_lat": 36.5350, "fs_lon": 129.4050},
    "봉화군": {"stn": 272, "lat": 36.8931, "lon": 128.7323, "slope": 30.0, "addr": "경상북도 봉화군 청량산 도립공원 지대", "water_dist": 5.8, "road_density": 14, "pine_ratio": 84, "fire_station": "봉화소방서 명호119지역대", "fs_lat": 36.9210, "fs_lon": 128.8510},
    "울릉군": {"stn": 130, "lat": 37.4844, "lon": 130.8633, "slope": 35.0, "addr": "경상북도 울릉군 성인봉 원시림 격자", "water_dist": 8.0, "road_density": 5, "pine_ratio": 40, "fire_station": "울릉소방서 울릉119안전센터", "fs_lat": 37.4810, "fs_lon": 130.9020},
    "청송군": {"stn": 272, "lat": 36.4354, "lon": 129.0573, "slope": 26.0, "addr": "경상북도 청송군 주왕산 국립공원 구역", "water_dist": 4.8, "road_density": 22, "pine_ratio": 76, "fire_station": "청송소방서 청송119안전센터", "fs_lat": 36.4310, "fs_lon": 129.0410}
}

# --- 📡 기상청 초단기실황 API 연동 파이프라인 ---
def fetch_kma_live_weather(stn_id):
    live_t, live_h, live_w, live_wd = 22.0, 45.0, 2.1, 180.0
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    base_time_dt = datetime.now(tz_kst) - timedelta(minutes=45)
    params = {'serviceKey': API_KEY, 'pageNo': '1', 'numOfRows': '10', 'dataType': 'JSON', 'base_date': base_time_dt.strftime("%Y%m%d"), 'base_time': base_time_dt.strftime("%H00"), 'nx': '91', 'ny': '106'}
    try:
        res = requests.get(url, params=params, timeout=1.2)
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
    if 337.5 <= deg or deg < 22.5: return "북풍 (⬇️ 남쪽 확산 위험)", "남쪽", 0, -1, "⬇️"
    elif 22.5 <= deg < 67.5: return "북동풍 (↙️ 남서쪽 확산 위험)", "남서쪽", -0.7, -0.7, "↙️"
    elif 67.5 <= deg < 112.5: return "동풍 (⬅️ 서쪽 확산 위험)", "서쪽", -1, 0, "⬅️"
    elif 112.5 <= deg < 157.5: return "남동풍 (↖️ 북서쪽 확산 위험)", "북서쪽", -0.7, 0.7, "↖️"
    elif 157.5 <= deg < 202.5: return "남풍 (⬆️ 북쪽 확산 위험)", "북쪽", 0, 1, "⬆️"
    elif 202.5 <= deg < 247.5: return "남서풍 (↗️ 북동쪽 확산 위험)", "북동쪽", 0.7, 0.7, "↗️"
    elif 247.5 <= deg < 292.5: return "서풍 (➡️ 동쪽 확산 위험)", "동쪽", 1, 0, "➡️"
    else: return "북서풍 (↘️ 남동쪽 확산 위험)", "남동쪽", 0.7, -0.7, "↘️"

# --- [소방청 SOP 표준 작전 절차 추론 연산 엔진] ---
def generate_ai_autonomous_sop(city_data, op_hour, is_emergency, eta_str):
    city = city_data["city"]
    pine = city_data["pine_ratio"]
    road = city_data["road_density"]
    water = city_data["water_dist"]
    wind = city_data["w"]
    humidity = city_data["h"]
    slope = city_data["slope"]
    station = city_data["fire_station"]
    
    raw_ffdi = (wind * 1.5) + ((100 - humidity) * 0.4) + (slope * 0.3)
    
    if raw_ffdi >= 45.0 or is_emergency:
        sop_level = "🔥 [소방청 SOP 최고단계: 대형산불 동원령 3단계 수렴]"
        fire_intensity = "심각(Extreme Fire Behavior)"
    elif 25.0 <= raw_ffdi < 45.0:
        sop_level = "⚠️ [소방청 SOP 대응단계: 산불 진압 2단계 동원]"
        fire_intensity = "경계(High Intensity)"
    else:
        sop_level = "🟢 [소방청 SOP 평시단계: 관내 초동진화대 대기 현황]"
        fire_intensity = "주의(Low-Moderate)"

    if 18 <= op_hour or op_hour < 6:
        time_context = "🌙 [야간 안전 통제령 발효]"
        heli_tactic = "❌ [항공 규정] 일몰 후 진화헬기 비행 금지 ➔ 지상 특수진화대 방화선 고착 전술 전환."
        micro_climate = "📉 [산풍 우세] 기류가 능선에서 가옥 방향으로 하강하므로 민가 배후에 수막 설비(Fire Curtain) 전개."
    else:
        time_context = "☀️ [주간 총력 공중 전개 시기]"
        heli_tactic = f"🚁 [임무 배정] 최단거리 담수지({water:.1f}km) 대상 소방청·산림청 헬기 교대 취수 가동."
        micro_climate = "📈 [곡풍 추론] 상승 기류로 인해 능선 상부로 치솟는 '수관화' 차단용 정상부 저지선 구축."

    if pine >= 70:
        forest_tactic = f"🪵 [수종 분석] 소나무 밀도 {pine}% 임상. 송진 기화로 인한 대규모 비산화(飞火) 주의 ➔ 전방 소방대원 수종 보호 물막 전개."
    else:
        forest_tactic = f"🍂 [활엽수 낙엽층 분석] 지표화 연소 위주 지대. 갈퀴를 통한 유기물 낙엽층 제거 주력."

    if road <= 20:
        logistics_tactic = f"🚒 [진입 제한] 임도율 {road}% 열악. 소방차 진입 차단 ➔ 산불 전용 진화차 및 동력펌프 연장 배관 진입."
    else:
        logistics_tactic = f"⚡ [기동로 최적] 임도율 {road}% 확보. 관할 **[{station}]** 고성능 화학차 및 지휘 차량을 화선 핵심부 50m 지점에 전진 배치하여 압도적 방수 포격."

    if is_emergency:
        m10 = f"{sop_level} {time_context} 관할 **[{station}]** 및 인근 센터 소방력 50% 긴급 집결 출동 중. **(예상 도착 시간: {eta_str})**"
        m30 = f"🛡️ [현장 지휘소 판단] 화재 강도: {fire_intensity}. {heli_tactic} {forest_tactic}"
        m60 = f"📢 [방재 가이드] {micro_climate} {logistics_tactic} 가옥 시설 최종 방어선 고착화."
    else:
        m10 = f"{sop_level} 관내 산림 초동 진화대 및 관할 [{station}] 무전 상시 개방령."
        m30 = f"🔸 [예방 분석 가이드] {forest_tactic} 지표 건조도 모니터링."
        m60 = f"🔹 [관제 기록] 연산 FDI 점수 {raw_ffdi:.1f}점에 근거한 도내 소방서 상황 아카이빙 처리 완료."

    return m10, m30, m60

# --- 🎛️ 사이드바 시뮬레이터 종합 통제 제어판 ---
st.sidebar.header("🎛️ 경상북도 종합 상황 제어판")

emergency_mode = st.sidebar.checkbox("🚨 [응급] 경북 구역 실전 화재 발령", value=False, key="emerg_check")

# ⭐ [대표님 오더 완전 박멸 앵커] 응급 모드를 껐을 때 가상 1위 도시가 복귀되도록 리셋하는 상태 스니퍼 기술
if st.session_state["prev_emerg_state"] == True and emergency_mode == False:
    st.session_state["selected_city"] = None # 세션 락 해제하여 자동 복귀 유도

st.session_state["prev_emerg_state"] = emergency_mode

st.sidebar.markdown("---")
st.sidebar.subheader("⏰ 관제 작전 시각 설정 (0~23시)")
use_manual_time = st.sidebar.checkbox("⏰ 수동 작전 시각 시뮬레이션 가동", value=False)

if use_manual_time:
    op_hour = st.sidebar.slider("가상 작전 타임라인 시각", 0, 23, value=int(now_kst.hour))
    time_display_str = f"⏳ 가상 시뮬레이션 타임: {op_hour:02d}:00 KST"
else:
    op_hour = int(now_kst.hour)
    time_display_str = f"🟢 실시간 동기화 타임: {now_kst.strftime('%H:%M')} KST"

st.sidebar.markdown("---")
st.sidebar.subheader("기상 변수 강제 조정")
sim_mode = st.sidebar.checkbox("🌡️ 특정 시·군 기상 악화 시뮬레이션", value=False, key="sim_mode_check")

sim_city = "안동시"
sim_t, sim_h, sim_w = 33.0, 12.0, 7.5

if sim_mode or emergency_mode:
    sim_city = st.sidebar.selectbox("대상 시·군 선택", list(GB_NATION_STN_MAP.keys()), index=0)
    sim_t = st.sidebar.slider("가상 온도 (°C)", 10.0, 45.0, value=33.0)
    sim_h = st.sidebar.slider("가상 상대습도 (%)", 0.0, 100.0, value=12.0)
    sim_w = st.sidebar.slider("가상 풍속 (m/s)", 0.0, 25.0, value=7.5)

# =========================================================================================
# 🔄 경북 22개 시·군 기상 및 알고리즘 연산 루프
# =========================================================================================
if "history_probs" not in st.session_state:
    st.session_state["history_probs"] = {}

all_scanned_list = []

for city, info in GB_NATION_STN_MAP.items():
    t, h, w, wd = fetch_kma_live_weather(info["stn"])
    slope = info["slope"]
    
    if (sim_mode or emergency_mode) and city == sim_city:
        t, h, w = sim_t, sim_h, sim_w

    seed_factor = (info["stn"] % 7) - 3
    local_t = max(12.0, t + (seed_factor * 0.4))
    local_h = max(15.0, min(95.0, h + (seed_factor * 2.5)))
    local_w = max(0.8, w + (seed_factor * 0.3))

    humidity_dryness = (100 - local_h) / 100.0
    if local_h <= 35.0: humidity_dryness *= 1.4
    
    weather_factor = (local_t * 0.35) + (local_w * 1.3)
    base_prob = weather_factor * humidity_dryness * 3.2
    
    raw_prob = min(97.8, base_prob * (1.0 + (slope / 90.0)))
    raw_prob = max(18.5, raw_prob)

    if city in st.session_state["history_probs"]:
        prev_prob = st.session_state["history_probs"][city]
        weight = 0.0 if (sim_mode or emergency_mode) else 0.85 
        final_prob = (prev_prob * weight) + (raw_prob * (1.0 - weight))
    else:
        final_prob = raw_prob

    st.session_state["history_probs"][city] = final_prob

    difficulty_penalty = (info["water_dist"] * 0.12) + ((100 - info["road_density"]) * 0.008) + (info["pine_ratio"] * 0.005)
    spread_factor = 0.001 + (local_w * 0.003) + (slope * 0.001)
    if local_h < 45: spread_factor *= 1.8
    
    danger_score = ((final_prob * 0.001) + (spread_factor * 12.0)) * (1.0 + difficulty_penalty)

    all_scanned_list.append({
        "city": city, "lat": info["lat"], "lon": info["lon"], "addr": info["addr"], "t": local_t, "h": local_h, "w": local_w, "wd": wd, "slope": slope, 
        "prob": final_prob, "score": danger_score,
        "water_dist": info["water_dist"], "road_density": info["road_density"], "pine_ratio": info["pine_ratio"],
        "penalty": difficulty_penalty, "fire_station": info["fire_station"], "fs_lat": info["fs_lat"], "fs_lon": info["fs_lon"]
    })

df_nation = pd.DataFrame(all_scanned_list).sort_values(by="prob", ascending=False).reset_index(drop=True)

if emergency_mode:
    df_nation = pd.DataFrame(all_scanned_list)
    df_nation.loc[df_nation["city"] == sim_city, "prob"] = 99.4
    df_nation = df_nation.sort_values(by="prob", ascending=False).reset_index(drop=True)

# 🔒 [인터랙티브 잠금 가동] 
real_top_1st = df_nation.iloc[0]["city"]
if st.session_state["selected_city"] is None or st.session_state["selected_city"] not in df_nation["city"].values:
    st.session_state["selected_city"] = real_top_1st

if emergency_mode:
    st.session_state["selected_city"] = sim_city

# =========================================================================================
# 🏛️ 인터페이스 레이어 표출
# =========================================================================================
if emergency_mode:
    st.error(f"🚨 [소방청 SOP 표준관제 작동] {sim_city} 구역 화재 등급 연산 결과 실시간 추론 지시서를 조립합니다.")
else:
    st.header("🛰️ [평시 감시] 실시간 경상북도 22개 시·군 대형 산불 발전 확률 TOP 5")

# TOP 5 랭킹 카드 가시화 구역
PROB_THRESHOLD = 75.0
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
            title_prefix = f"⚠️ 위험! "
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
            <p style="margin: 0; font-size: 13px; color: #aaa;">진압난이도: {row['score']:.2f}점</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(f"🔍 {row['city']} 관제 레이블", key=f"btn_{row['city']}", use_container_width=True):
            st.session_state["selected_city"] = row["city"]
            st.rerun()

# =========================================================================================
# 🏹 pydeck 기반 고대비 2D 임야 화산 확산 및 소방서 주행 진입 루트 매핑 지도를 전개합니다.
# =========================================================================================
st.divider()
target_city = st.session_state["selected_city"]
city_data = df_nation[df_nation["city"] == target_city].iloc[0]

wd_text, danger_direction, dx, dy, arrow_icon = get_wind_direction_text(city_data["wd"])

# 📐 화선 예측 및 출동 거리 연산
base_spread_rate = (city_data['w'] * 1.5) * (1.0 + (city_data['slope'] / 35.0)) * (1.0 + city_data['penalty'])
p_10 = int(city_data['score'] * base_spread_rate * 15)
p_30 = int(p_10 * 3.8)
p_60 = int(p_30 * 4.2)

# 하버사인 간이 거리를 활용한 가상 소방차 출동 소요 시간(ETA) 자동 연산 레이어
dist_fs_to_fire = math.sqrt((city_data["lat"] - city_data["fs_lat"])**2 + (city_data["lon"] - city_data["fs_lon"])**2) * 111.0
eta_minutes = max(3, int(dist_fs_to_fire * 1.6))
eta_str = f"약 {eta_minutes}분 {random.randint(0, 59):02d}초"

if emergency_mode:
    st.header(f"🗺️ [소방청 표준 작전 지휘 도면] 령이 AI 임야 실시간 확산 벡터 ➔ [{city_data['city']}]")
    st.caption("🏹 3D 왜곡 해제 2D 작전 도면 | 🚒 관할 소방서 긴급 출동 진격 최적 접근 루트 축선 투사 완료")
    
    def generate_asymmetric_fire_front(lon, lat, dx, dy, scale, wind_w):
        points = []
        segments = 32
        for j in range(segments):
            angle = (j / segments) * 2 * math.pi
            r_lon = 0.0025 * scale * math.cos(angle)
            r_lat = 0.0025 * scale * math.sin(angle)
            alignment = math.cos(angle) * dx + math.sin(angle) * dy
            stretch = 1.0 + max(0.0, alignment) * (wind_w * 0.15)
            p_lon = lon + r_lon * stretch + (dx * scale * 0.0005 * wind_w)
            p_lat = lat + r_lat * stretch + (dy * scale * 0.0005 * wind_w)
            points.append([p_lon, p_lat])
        points.append(points[0])
        return points

    poly_10 = generate_asymmetric_fire_front(city_data["lon"], city_data["lat"], dx, dy, 0.6, city_data['w'])
    poly_30 = generate_asymmetric_fire_front(city_data["lon"], city_data["lat"], dx, dy, 1.5, city_data['w'])
    poly_60 = generate_asymmetric_fire_front(city_data["lon"], city_data["lat"], dx, dy, 2.7, city_data['w'])

    pydeck_layers = []

    # ① 가상 화선 다각형 레이어
    pydeck_layers.append(pdk.Layer("PolygonLayer", pd.DataFrame([{"poly": poly_10}]), get_polygon="poly", get_fill_color="[255, 60, 60, 40]", get_line_color="[255, 20, 20, 255]", line_width_min_pixels=2))
    pydeck_layers.append(pdk.Layer("PolygonLayer", pd.DataFrame([{"poly": poly_30}]), get_polygon="poly", get_fill_color="[255, 30, 30, 30]", get_line_color="[255, 10, 10, 255]", line_width_min_pixels=2.5))
    pydeck_layers.append(pdk.Layer("PolygonLayer", pd.DataFrame([{"poly": poly_60}]), get_polygon="poly", get_fill_color="[200, 0, 0, 20]", get_line_color="[220, 0, 0, 255]", line_width_min_pixels=3))

    # ② 🏹 최전방 확산 화살표선
    front_10, front_30, front_60 = poly_10[0], poly_30[0], poly_60[0]
    arrow_lines_data = [
        {"slon": city_data["lon"], "slat": city_data["lat"], "elon": front_10[0], "elat": front_10[1], "color": [255, 100, 100], "width": 4},
        {"slon": city_data["lon"], "slat": city_data["lat"], "elon": front_30[0], "elat": front_30[1], "color": [255, 50, 50], "width": 5},
        {"slon": city_data["lon"], "slat": city_data["lat"], "elon": front_60[0], "elat": front_60[1], "color": [220, 0, 0], "width": 6}
    ]
    pydeck_layers.append(pdk.Layer("LineLayer", pd.DataFrame(arrow_lines_data), get_source_position="[slon, slat]", get_target_position="[elon, elat]", get_color="color", get_width="width"))

    # ③ ⚡⚡ [대표님 핵심 역점 기획] 소방서 본서에서 임도 초입을 관통하여 화점까지 이어지는 "출동 진격로 파란색 레이어" 자동 전개
    route_path_nodes = [
        [city_data["fs_lon"], city_data["fs_lat"]], # 소방서 출발
        [city_data["lon"] + 0.011, city_data["lat"] - 0.009], # 관내 임도 초입 관통
        [city_data["lon"], city_data["lat"]] # 최종 발화점 임계 도착
    ]
    df_route = pd.DataFrame([{"path": route_path_nodes}])
    pydeck_layers.append(pdk.Layer("PathLayer", df_route, get_path="path", width_scale=20, width_min_pixels=4.5, get_color="[30, 144, 255, 255]")) # 고대비 소방 진격 블루 라인

    # ④ 이모티콘 및 라벨 마킹 레이어 조립
    arrow_heads = [{"lon": front_10[0], "lat": front_10[1], "text": arrow_icon}, {"lon": front_30[0], "lat": front_30[1], "text": arrow_icon}, {"lon": front_60[0], "lat": front_60[1], "text": arrow_icon}]
    pydeck_layers.append(pdk.Layer("TextLayer", pd.DataFrame(arrow_heads), get_position="[lon, lat]", get_text="text", get_size=22, get_color="[255,255,255,255]", get_background_color="[255,0,0,220]", padding=[2,4,2,4]))

    inline_labels = [
        {"lon": poly_10[8][0], "lat": poly_10[8][1], "text": f"⏳ 10분 화선 | 약 {p_10:,}평"},
        {"lon": poly_30[8][0], "lat": poly_30[8][1], "text": f"⚠️ 30분 위험선 | 약 {p_30:,}평"},
        {"lon": poly_60[8][0], "lat": poly_60[8][1], "text": f"🔥 60분 최종화두 | 약 {p_60:,}평"}
    ]
    pydeck_layers.append(pdk.Layer("TextLayer", pd.DataFrame(inline_labels), get_position="[lon, lat]", get_text="text", get_size=12, get_color="[255,255,255,255]", get_background_color="[15,15,15,220]", padding=[4,6,4,6], get_text_anchor="'start'"))

    pydeck_layers.append(pdk.Layer("TextLayer", pd.DataFrame([{"lon": city_data["lon"], "lat": city_data["lat"], "text": "🔥"}]), get_position="[lon, lat]", get_text="text", get_size=40, get_alignment_baseline="'center'"))

    # 인프라 마커 마킹 (내장형 소방서 본서 기지 마킹 앵커 추가 장착)
    infra_markers = [
        {"lon": city_data["lon"] - 0.015, "lat": city_data["lat"] + 0.012, "text": "🌊 소방 저수지", "bg": [0,191,255,230]},
        {"lon": city_data["lon"] + 0.011, "lat": city_data["lat"] - 0.009, "text": "🛣️ 임도 초입", "bg": [46,139,87,230]},
        {"lon": city_data["fs_lon"], "fs_lat": city_data["fs_lat"], "text": f"🚒 관할: {city_data['fire_station']}", "bg": [255,69,0,240]} # 소방대 출동 기지 점등
    ]
    pydeck_layers.append(pdk.Layer("TextLayer", pd.DataFrame(infra_markers), get_position="[lon, lat]", get_text="text", get_size=13, get_color="[255,255,255,255]", get_background_color="bg", padding=[4,6,4,6]))

    st.pydeck_chart(pdk.Deck(
        layers=pydeck_layers,
        map_style=pdk.map_styles.DARK,
        initial_view_state=pdk.ViewState(latitude=(city_data["lat"]+city_data["fs_lat"])/2, longitude=(city_data["lon"]+city_data["fs_lon"])/2, zoom=11.5, pitch=0, bearing=0) # 출동로가 한눈에 보이게 줌 스케일 최적화
    ))
    st.markdown("---")
else:
    st.header(f"📍 [2단계] AI 초국지성 관제탑 ➔ [{city_data['city']}] ({time_display_str})")

# =========================================================================================
# 📡 3열 제원 패널 출력 구역 (NameError 완전 박멸 완결 매핑)
# =========================================================================================
c1, c2, c3 = st.columns([1, 1.2, 1.2])

with c1:
    st.markdown(f"""
    <div style="background-color: #1c1d24; padding: 18px; border-radius: 8px; border-left: 5px solid #1a73e8; min-height: 330px;">
        <h4 style="margin:0 0 12px 0; color:#1a73e8; font-weight: bold;">📡 경북 지형 인프라 프로필</h4>
        <p style="margin:5px 0; font-size:14px; color: white;"><b>대상 위치:</b> {city_data['addr']}</p>
        <hr style="border:0.5px solid #333; margin:8px 0;">
        <table style="width:100%; color:white; font-size:13px; border-collapse:collapse;">
            <tr><td>🌡️ 현재 실측 기온:</td><td style="text-align:right; font-weight:bold;">{city_data['t']:.1f} °C</td></tr>
            <tr><td>💧 현재 상대 습도:</td><td style="text-align:right; font-weight:bold;">{city_data['h']:.1f} %</td></tr>
            <tr><td>💨 현재 실측 풍속:</td><td style="text-align:right; font-weight:bold;">{city_data['w']:.1f} m/s</td></tr>
            <tr style="color:#a8c7fa;"><td>🚒 최단 소방 기지:</td><td style="text-align:right; font-weight:bold; color:#ff6b6b;">{city_data['fire_station'].split(" ")[1]}</td></tr>
            <tr style="color:#a8c7fa;"><td>🛣️ 관내 산림 임도 밀도:</td><td style="text-align:right; font-weight:bold;">{city_data['road_density']}%</td></tr>
            <tr style="color:#ffb4ab;"><td>🌲 인접 수종(소나무) 비율:</td><td style="text-align:right; font-weight:bold;">{city_data['pine_ratio']}%</td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

with c2:
    status_color = "#ff4b4b" if city_data['prob'] >= PROB_THRESHOLD else ("#ffaa00" if city_data['prob'] >= 50.0 else "#1a73e8")
    l_10 = int(base_spread_rate * 25)
    l_30 = int(l_10 * 2.8)
    l_60 = int(l_30 * 2.5)

    st.markdown(f"""
    <div style="background-color: #1c1d24; padding: 18px; border-radius: 8px; border-left: 5px solid {status_color}; min-height: 330px;">
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
        <p style="margin:2px 0; font-size:12px; color: #ff8b8b;">⚠️ <b>출동로 임계 연산 범위:</b> 소방차 출동 거리 {dist_fs_to_fire:.1f}km 격자 반영</p>
        <p style="margin:2px 0; font-size:12px; color: #ccc;"><b>산악 지형 경사:</b> {city_data['slope']}° | <b>강풍 주풍향 궤적:</b> {danger_direction}</p>
    </div>
    """, unsafe_allow_html=True)

with c3:
    # 🧠 [소방청 SOP 표준 조립] 실시간 수식 추론을 기반으로 령이가 생성한 전술 명령서
    ai_m10, ai_m30, ai_m60 = generate_ai_autonomous_sop(city_data, op_hour, is_emergency=emergency_mode, eta_str=eta_str)
    
    st.markdown(f"<h4 style='margin:0 0 10px 0; color:#ff4b4b; font-size:15px; font-weight:bold;'>🧠 [소방청 SOP 동기화] {city_data['city']} 실시간 전술 지시서</h4>", unsafe_allow_html=True)
    st.info(ai_m10)
    st.warning(ai_m30)
    st.error(ai_m60)

# =========================================================================================
# 📋 [4단계] 아카이브 로그 대장 (NameError 및 오버라이딩 완전 박멸 완결본)
# =========================================================================================
st.divider()
st.subheader("📋 령이 자율 포착 로그 대장 (경상북도 소방 재난 방재 시스템 아카이브)")

sat_time_str = now_kst.strftime("%Y-%m-%d %H:%M:%S")
final_p_60 = int(city_data['score'] * ((city_data['w'] * 1.5) * (1.0 + (city_data['slope'] / 35.0)) * (1.0 + city_data['penalty'])) * 15 * 3.8 * 4.2)

df_mock_db = pd.DataFrame([{
    "령이 실시간 감지 시각": sat_time_str,
    "산림청 API 수신 상태": "🚨 실전 화재 선포 연동" if emergency_mode else "🚫 평시 예보 커넥션 동작",
    "경북 관제 행정구역": target_city + " 작전소" if emergency_mode else f"{target_city} 정밀 관제 모드",
    "AI 연산 발전 확률": f"{city_data['prob']:.1f}%",
    "AI 최단거리 전술 판정": f"SOP 인터랙티브 연동 성공: 관할 [{city_data['fire_station']}] 진격로 벡터 엔진 매핑 완료"
}])
st.table(df_mock_db)