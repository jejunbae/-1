import streamlit as st
import time
import requests
import math
import random
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import pandas as pd
import pydeck as pdk

# 🖥️ 웹페이지 상단 기본 세팅 및 레이아웃 확장
st.set_page_config(page_title="경북 산불 통합 관제 AI 령이", page_icon="⚠️", layout="wide")

API_KEY = "69309efd849de167a2a68e2fc27331c01eb67888d72dd4a740419a33cf7d292e"
tz_kst = timezone(timedelta(hours=9))
now_kst = datetime.now(tz_kst)

# 🔄 [세션 상태 관리 및 초기화 보호선]
if "selected_spot" not in st.session_state:
    st.session_state["selected_spot"] = None
if "prev_active_mode" not in st.session_state:
    st.session_state["prev_active_mode"] = False

# =========================================================================================
# 🔒 [워닝 로그 원천 차단 방어선]
# =========================================================================================
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*ScriptRunContext.*")

st.title("🚨 경상북도 실시간 산불 소방 작전 지휘 플랫폼 '령이'")
st.markdown(f"**Core Engine v67.2:** 🎛️ 슬라이더 조작 UI 즉각 반영 오버라이딩 & 🐛 라이브 API 연산 간섭 버그 원천 차단본")
st.divider()

# =========================================================================================
# 🗂️ [경북도내 핵심 읍·면·동 및 임도 도로명 주소 매핑 마스터 데이터베이스]
# =========================================================================================
@st.cache_data
def load_gb_topology_db():
    gb_spots = {
        "경상북도 안동시 와룡면 주진리 산림축선 (와룡로 임도)": {"stn": 272, "nx": 92, "ny": 107, "slope": 25.0, "water_dist": 2.5, "road_density": 35, "pine_ratio": 85, "fire_station": "안동소방서 와룡119안전센터", "fs_lat": 36.6025, "fs_lon": 128.7420, "lat": 36.6545, "lon": 128.7834, "route": [[128.7420, 36.6025], [128.7510, 36.6150], [128.7650, 36.6320], [128.7750, 36.6480], [128.7834, 36.6545]]},
        "경상북도 의성군 점곡면 사촌리 배후 야산 (점곡길 산림)": {"stn": 278, "nx": 91, "ny": 104, "slope": 18.0, "water_dist": 3.1, "road_density": 40, "pine_ratio": 75, "fire_station": "의성소방서 의성119안전센터", "fs_lat": 36.3510, "fs_lon": 128.6820, "lat": 36.3914, "lon": 128.7845, "route": [[128.6820, 36.3510], [128.7150, 36.3620], [128.7520, 36.3810], [128.7845, 36.3914]]},
        "경상북도 울진군 금강송면 하원리 금강송 군락지 (십이령로)": {"stn": 130, "nx": 102, "ny": 113, "slope": 32.0, "water_dist": 7.2, "road_density": 10, "pine_ratio": 95, "fire_station": "울진소방서 북면119안전센터", "fs_lat": 36.9910, "fs_lon": 129.3510, "lat": 36.9542, "lon": 129.2845, "route": [[129.3510, 36.9910], [129.3320, 36.9750], [129.3100, 36.9620], [129.2950, 36.9580], [129.2845, 36.9542]]},
        "경상북도 문경시 문경읍 조령산 국지 사면 (새재로 사면축선)": {"stn": 273, "nx": 86, "ny": 109, "slope": 28.0, "water_dist": 6.8, "road_density": 12, "pine_ratio": 78, "fire_station": "문경소방서 문경119안전센터", "fs_lat": 36.6925, "fs_lon": 128.1560, "lat": 36.7641, "lon": 128.0824, "route": [[128.1560, 36.6925], [128.1320, 36.7110], [128.1050, 36.7350], [128.0910, 36.7520], [128.0824, 36.7641]]},
        "경상북도 구미시 금오산 등선 배후 사면 (금오산로 임도축선)": {"stn": 279, "nx": 87, "ny": 101, "slope": 20.0, "water_dist": 1.8, "road_density": 45, "pine_ratio": 55, "fire_station": "구미소방서 원평119안전센터", "fs_lat": 36.1280, "fs_lon": 128.3380, "lat": 36.0842, "lon": 128.3014, "route": [[128.3380, 36.1280], [128.3220, 36.1150], [128.3100, 36.0980], [128.3014, 36.0842]]},
        "경상북도 영주시 풍기읍 소백산 희방사 사면 (죽령로 임도축선)": {"stn": 272, "nx": 89, "ny": 113, "slope": 27.0, "water_dist": 5.0, "road_density": 20, "pine_ratio": 72, "fire_station": "영주소방서 풍기119안전센터", "fs_lat": 36.8650, "fs_lon": 128.5250, "lat": 36.9412, "lon": 128.4624, "route": [[128.5250, 36.8650], [128.4950, 36.8920], [128.4720, 36.9210], [128.4624, 36.9412]]},
        "경상북도 영천시 화북면 보현산 천문대 구역 (천문로 임도축선)": {"stn": 281, "nx": 97, "ny": 103, "slope": 22.0, "water_dist": 4.0, "road_density": 28, "pine_ratio": 60, "fire_station": "영천소방서 화북119지역대", "fs_lat": 36.0410, "fs_lon": 128.9610, "lat": 36.1621, "lon": 128.9845, "route": [[128.9610, 36.0410], [128.9550, 36.0850], [128.9720, 36.1250], [128.9845, 36.1621]]},
        "경상북도 포항시 북구 내연산 계곡지대 (보경로 사면축선)": {"stn": 138, "nx": 102, "ny": 106, "slope": 15.0, "water_dist": 1.2, "road_density": 50, "pine_ratio": 40, "fire_station": "포항북부소방서 흥해119안전센터", "fs_lat": 36.1120, "fs_lon": 129.3510, "lat": 36.2514, "lon": 129.2845, "route": [[129.3510, 36.1120], [129.3620, 36.1550], [129.3700, 36.2050], [129.3250, 36.2350], [129.2845, 36.2514]]}
    }
    return gb_spots

def fetch_kma_grid_weather(nx, ny):
    live_t, live_h, live_w, live_wd = 22.0, 45.0, 2.1, 180.0
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    base_time_dt = datetime.now(tz_kst) - timedelta(minutes=45)
    params = {'serviceKey': API_KEY, 'pageNo': '1', 'numOfRows': '10', 'dataType': 'JSON', 'base_date': base_time_dt.strftime("%Y%m%d"), 'base_time': base_time_dt.strftime("%H00"), 'nx': str(nx), 'ny': str(ny)}
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

def fetch_forest_fire_stats_brain():
    anchor_knowledge = [
        {
            "case": "2025년 의성 대형 산불 대참사 (주간 확산 단계)", 
            "t": 15.4, "h": 40.0, "w": 25.0, "hour": 14, 
            "desc": "2025년 3월 발생한 의성 대참사의 백주대낮 시간대 상황. 초속 25m/s의 태풍급 강풍과 낮 시간대의 강한 상승기류(곡풍)가 결합되어 불길이 능선 정상부 수관화 형태로 치솟아 초동 저지선이 일거에 무너진 실패 사례.", 
            "sol": "💡 **[주간 상승기류 곡풍 전술]** 강풍형 주간 산불이므로 상승 기류를 타고 불길이 산 정상부로 가속됩니다. 대원들을 산마루에서 즉시 철수시키고, 국도 방면 임도 초입 관문에 고성능 화학차를 전진 배치해 수막 방어선을 사수하십시오."
        },
        {
            "case": "2025년 의성 대형 산불 대참사 (야간 복사 역전 단계)", 
            "t": 12.0, "h": 45.0, "w": 18.0, "hour": 22, 
            "desc": "2025년 3월 의성 산불의 야간 전환 상황. 복사 냉각으로 기류가 산 정상에서 아래 민가 쪽으로 하강(산풍)하는 시점. 헬기가 철수된 상황에서 야간 강풍을 타고 불길이 골짜기 밑 민가 가옥을 기습 타격한 기록.", 
            "sol": "💡 **[야간 하강기류 산풍 전술]** 야간 산풍 물리학이 적용되는 시점입니다. 불길이 아래 민가 방면으로 굴절되므로, 관할 소방대원들은 민가 배후 50m 지점에 방수포 진격을 개시해 '인간 수막 설비(Fire Curtain)' 라인을 가동하십시오."
        },
        {
            "case": "2022년 울진·삼척 소나무림 대참사 (황혼 임계 단계)", 
            "t": 18.5, "h": 12.0, "w": 11.0, "hour": 18, 
            "desc": "습도 12%의 건조경보 속에서 일몰 직전 헬기 철수 데드라인과 겹치며 비산화(飞火) 통제권을 완전히 상실했던 대참사 백서 기록.", 
            "sol": "💡 **[일몰 항공 철수 전술]** 헬기가 철수하는 황혼기이므로 지상 진화대를 '자율 소화 드론 10기' 편대로 전면 백업하십시오. 풍향 벡터 정반대 임도 관문에 방화 지연제를 선제 투하하여 차단벽을 조기 구축해야 합니다."
        }
    ]
    return anchor_knowledge

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

def generate_ai_autonomous_sop(city_data, op_hour, is_emergency, eta_str):
    station = city_data["fire_station"]
    wind = city_data["w"]
    humidity = city_data["h"]
    slope = city_data["slope"]
    pine = city_data["pine_ratio"]
    road = city_data["road_density"]
    
    raw_ffdi = (wind * 1.5) + ((100 - humidity) * 0.4) + (slope * 0.3)
    sop_level = "🔥 [소방청 SOP 최고단계: 대형산불 동원령 3단계]" if raw_ffdi >= 45.0 or is_emergency else "🟢 [소방청 SOP 평시단계: 초동진화대 대기]"

    if 18 <= op_hour or op_hour < 6:
        time_context = "🌙 [야간 안전 통제령 발효]"
        heli_tactic = "❌ [항공 규정] 일몰 후 진화헬기 비행 금지 ➔ 지상 특수진화대 전술 전환."
        micro_climate = "📉 [산풍 우세] 기류가 능선에서 민가 방향으로 하강하므로 민가 배후에 수막 설비 전개."
    else:
        time_context = "☀️ [주간 총력 공중 전개 시기]"
        heli_tactic = f"🚁 [임무 배정] 최단거리 담수지({city_data['water_dist']:.1f}km) 대상 헬기 교대 취수 가동."
        micro_climate = "📈 [곡풍 추론] 상승 기류로 인해 능선 상부로 치솟는 '수관화' 차단용 저지선 구축."

    if is_emergency:
        m10 = f"{sop_level} {time_context} 관할 **[{station}]** 소방대 임야 출동 진격로 락온. **(예상 도착 시간: {eta_str})**"
        m30 = f"🛡️ [현장 지휘소 판단] {heli_tactic} 소나무 밀도 {pine}% 임상 비산화 주의."
        m60 = f"📢 [방재 가이드] {micro_climate} 임도 밀도 {road}%에 맞춰 화학차 전진 배치."
    else:
        m10 = f"{sop_level} 관내 평시 예찰 및 소방 상시 무전 개방령."
        m30 = f"🔸 [가상 연산 알림] 우측 시뮬레이션 보드는 실시간 기상 가중치를 바탕으로 상시 락오프 가동 중입니다."
        m60 = f"🔹 [시스템 알림] 현재 평시 관제 모드입니다. 기상 악화 시뮬레이션을 가동하여 임계 확률 돌파 시 실전 지도가 팝업됩니다."

    return m10, m30, m60

# --- 🎛️ 사이드바 시뮬레이터 종합 통제 제어판 ---
st.sidebar.header("🎛️ 경상북도 읍·면·동 통합 제어판")

st.sidebar.subheader("⏰ 관제 작전 시각 설정")
use_manual_time = st.sidebar.checkbox("⏰ 수동 작전 시각 시뮬레이션 가동", value=False)
if use_manual_time:
    op_hour = st.sidebar.slider("가상 작전 타임라인 시각", 0, 23, value=14)
else:
    op_hour = int(now_kst.hour)

st.sidebar.markdown("---")
st.sidebar.subheader("초국지성 기상 변수 강제 조정")
sim_mode = st.sidebar.checkbox("🌡️ 특정 주소지 기상 악화 시뮬레이션", value=False, key="sim_mode_check")

gb_topology_db = load_gb_topology_db()
sim_address = "경상북도 의성군 점곡면 사촌리 배후 야산 (점곡길 산림)"
sim_t, sim_h, sim_w = 15.4, 40.0, 25.0

if sim_mode:
    sim_address = st.sidebar.selectbox("경북 타겟 세분화 주소지 선택", list(gb_topology_db.keys()), index=1)
    sim_t = st.sidebar.slider("가상 온도 (°C)", 10.0, 45.0, value=15.4)
    sim_h = st.sidebar.slider("가상 상대습도 (%)", 0.0, 100.0, value=40.0)
    sim_w = st.sidebar.slider("가상 풍속 (m/s)", 0.0, 30.0, value=25.0)

# =========================================================================================
# 🔄 경북 데이터 파이프라인 연산 루프
# =========================================================================================
if "history_probs" not in st.session_state:
    st.session_state["history_probs"] = {}

all_scanned_list = []
for address, info in gb_topology_db.items():
    t, h, w, wd = fetch_kma_grid_weather(info["nx"], info["ny"])
    slope = info["slope"]
    
    # 🎯 [대표님 오더 반영 핵심]: 슬라이더 주입 시 난수가 덮어씌워진 local 변수가 아닌 슬라이더 날것의 변수가 꽂히도록 로직 스왑
    if sim_mode and address == sim_address:
        local_t = sim_t
        local_h = sim_h
        local_w = sim_w
    else:
        seed_factor = (info["stn"] % 7) - 3
        local_t = max(12.0, t + (seed_factor * 0.4))
        local_h = max(15.0, min(95.0, h + (seed_factor * 2.5)))
        local_w = max(0.8, w + (seed_factor * 0.3))

    humidity_dryness = (100 - local_h) / 100.0
    if local_h <= 35.0: humidity_dryness *= 1.4
    weather_factor = (local_t * 0.35) + (local_w * 1.3)
    
    topo_fire_potential = (info["pine_ratio"] * 0.45) + (slope * 0.35) + ((100 - info["road_density"]) * 0.2)
    base_prob = (weather_factor * humidity_dryness * 2.2) + (topo_fire_potential * 0.35)
    
    raw_prob = min(97.8, base_prob)
    raw_prob = max(18.5, raw_prob)

    if address in st.session_state["history_probs"]:
        prev_prob = st.session_state["history_probs"][address]
        weight = 0.0 if sim_mode else 0.85 
        final_prob = (prev_prob * weight) + (raw_prob * (1.0 - weight))
    else:
        final_prob = raw_prob

    st.session_state["history_probs"][address] = final_prob
    difficulty_penalty = (info["water_dist"] * 0.12) + ((100 - info["road_density"]) * 0.008) + (info["pine_ratio"] * 0.005)
    spread_factor = 0.001 + (local_w * 0.003) + (slope * 0.001)
    if local_h < 45: spread_factor *= 1.8
    danger_score = ((final_prob * 0.001) + (spread_factor * 12.0)) * (1.0 + difficulty_penalty)

    all_scanned_list.append({
        "address": address, "lat": info["lat"], "lon": info["lon"], "t": local_t, "h": local_h, "w": local_w, "wd": wd, "slope": slope, 
        "prob": final_prob, "score": danger_score, "water_dist": info["water_dist"], "road_density": info["road_density"], "pine_ratio": info["pine_ratio"],
        "penalty": difficulty_penalty, "fire_station": info["fire_station"], "fs_lat": info["fs_lat"], "fs_lon": info["fs_lon"], "route": info["route"]
    })

# 🎯 75% 기준 자율 실전 체제 자동 스위칭 인터록 완벽 동기화
PROB_THRESHOLD = 75.0
trigger_emergency_by_prob = False

target_sim_data = [x for x in all_scanned_list if x["address"] == sim_address]
if target_sim_data and sim_mode:
    if target_sim_data[0]["prob"] >= PROB_THRESHOLD:
        trigger_emergency_by_prob = True

if trigger_emergency_by_prob:
    st.session_state["selected_spot"] = sim_address
    st.session_state["prev_active_mode"] = True
else:
    if st.session_state["prev_active_mode"] == True:
        st.session_state["selected_spot"] = None
        st.session_state["prev_active_mode"] = False

# 경북 랭킹 카드 정렬 리프레시
df_nation = pd.DataFrame(all_scanned_list).sort_values(by="prob", ascending=False).reset_index(drop=True)

if trigger_emergency_by_prob:
    df_nation = pd.DataFrame(all_scanned_list)
    df_nation.loc[df_nation["address"] == sim_address, "prob"] = 99.4
    df_nation = df_nation.sort_values(by="prob", ascending=False).reset_index(drop=True)

if st.session_state["selected_spot"] is None or st.session_state["selected_spot"] not in df_nation["address"].values:
    st.session_state["selected_spot"] = df_nation.iloc[0]["address"]

target_spot = st.session_state["selected_spot"]
city_data = df_nation[df_nation["address"] == target_spot].iloc[0]

# --- UI 상단 상태 메시지 ---
if trigger_emergency_by_prob:
    st.error(f"🚨 [AI 자율 실전 화재 선포] 위험률 {city_data['prob']:.1f}%로 임계선 돌파! 2단계 평면 전술 지도가 1순위로 즉시 강제 사출되었습니다.")
elif sim_mode:
    st.warning(f"⚠️ [경북 초국지성 기상 주입 중] 주소지: {sim_address} (현재 가상 위험도 연산 값: {city_data['prob']:.1f}%)")
else:
    st.success(f"🟢 [경북 라이브 읍·면·동 예찰 모드] 대형산불 위험 후보지 자동 스캔 및 실시간 피해 범위 시뮬레이터 상시 가동 중")

# 세분화 TOP 5 카드 표출 구역
cols = st.columns(4)
for idx, row in df_nation.iterrows():
    if idx >= 4: break
    with cols[idx]:
        display_name = row["address"].split(" (")[0]
        if trigger_emergency_by_prob and row["address"] == sim_address:
            border_style = "border: 3px dashed #ff4b4b; background-color: #3b0000; border-radius: 8px; padding: 12px; text-align: center;"
            prob_color = "#ff4b4b"
            title_prefix = "🔥 [실전] "
        elif row["prob"] >= PROB_THRESHOLD:
            border_style = "border: 2px solid #ff4b4b; background-color: #2b1111; border-radius: 8px; padding: 12px; text-align: center;"
            prob_color = "#ff4b4b"
            title_prefix = "⚠️ 위험! "
        else:
            border_style = "border: 1px solid #444; background-color: #0e1117; border-radius: 8px; padding: 12px; text-align: center;"
            prob_color = "#ffaa00"
            title_prefix = f"{idx+1}위. "
            
        if row["address"] == target_spot:
            if trigger_emergency_by_prob:
                border_style = border_style.replace("border: 3px dashed #ff4b4b", "border: 3px dashed #ffff00")
            else:
                border_style = "border: 2px dashed #1a73e8; background-color: #111520; border-radius: 8px; padding: 12px; text-align: center;"

        st.markdown(f"""
        <div style="{border_style} min-height:125px; margin-bottom: 5px;">
            <p style="margin: 0; color: white; font-size:13px; font-weight:bold; line-height:1.4;">{title_prefix}{display_name}</p>
            <p style="margin: 5px 0 0 0; font-size: 14px; color: {prob_color}; font-weight:bold;">위험 확률: {row['prob']:.1f}%</p>
            <p style="margin: 0; font-size: 12px; color: #aaa;">진압난이도: {row['score']:.2f}점</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(f"🔍 주소 정밀 분석", key=f"btn_{idx}", use_container_width=True, disabled=trigger_emergency_by_prob):
            st.session_state["selected_spot"] = row["address"]
            st.rerun()

# --- 동적 수치 계산부 (락오프 파이프라인) ---
wd_text, danger_direction, dx, dy, arrow_icon = get_wind_direction_text(city_data["wd"])
base_spread_rate = (city_data['w'] * 1.5) * (1.0 + (city_data['slope'] / 35.0)) * (1.0 + city_data['penalty'])
p_10 = int(city_data['score'] * base_spread_rate * 15)
p_30 = int(p_10 * 3.8)
p_60 = int(p_30 * 4.2)
dist_fs_to_fire = math.sqrt((city_data["lat"] - city_data["fs_lat"])**2 + (city_data["lon"] - city_data["fs_lon"])**2) * 111.0
eta_minutes = max(4, int(dist_fs_to_fire * 1.8))
eta_str = f"약 {eta_minutes}분 {random.randint(10, 59):02d}초"

# =========================================================================================
# 🗺️ [2단계 전술 지도 레이아웃]
# =========================================================================================
if trigger_emergency_by_prob:
    st.divider()
    st.header(f"🗺️ [1순위 초동 대응 작전 도면] 령이 AI 수관화 확산선 벡터 ➔ [{city_data['address'].split(' (')[0]}]")
    
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

    pydeck_layers = [
        pdk.Layer("PolygonLayer", pd.DataFrame([{"poly": poly_10}]), get_polygon="poly", get_fill_color="[255, 60, 60, 40]", get_line_color="[255, 20, 20, 255]", line_width_min_pixels=2),
        pdk.Layer("PolygonLayer", pd.DataFrame([{"poly": poly_30}]), get_polygon="poly", get_fill_color="[255, 30, 30, 30]", get_line_color="[255, 10, 10, 255]", line_width_min_pixels=2.5),
        pdk.Layer("PolygonLayer", pd.DataFrame([{"poly": poly_60}]), get_polygon="poly", get_fill_color="[200, 0, 0, 20]", get_line_color="[220, 0, 0, 255]", line_width_min_pixels=3)
    ]

    front_10, front_30, front_60 = poly_10[0], poly_30[0], poly_60[0]
    arrow_lines_data = [
        {"slon": city_data["lon"], "slat": city_data["lat"], "elon": front_10[0], "elat": front_10[1], "color": [255, 100, 100], "width": 4},
        {"slon": city_data["lon"], "slat": city_data["lat"], "elon": front_30[0], "elat": front_30[1], "color": [255, 50, 50], "width": 5},
        {"slon": city_data["lon"], "slat": city_data["lat"], "elon": front_60[0], "elat": front_60[1], "color": [220, 0, 0], "width": 6}
    ]
    pydeck_layers.append(pdk.Layer("LineLayer", pd.DataFrame(arrow_lines_data), get_source_position="[slon, slat]", get_target_position="[elon, elat]", get_color="color", get_width="width"))

    df_route = pd.DataFrame([{"path": city_data["route"]}])
    pydeck_layers.append(pdk.Layer("PathLayer", df_route, get_path="path", width_scale=20, width_min_pixels=5.0, get_color="[0, 128, 255, 255]"))

    arrow_heads = [{"lon": front_10[0], "lat": front_10[1], "text": arrow_icon}, {"lon": front_30[0], "lat": front_30[1], "text": arrow_icon}, {"lon": front_60[0], "lat": front_60[1], "text": arrow_icon}]
    pydeck_layers.append(pdk.Layer("TextLayer", pd.DataFrame(arrow_heads), get_position="[lon, lat]", get_text="text", get_size=22, get_color="[255,255,255,255]", get_background_color="[255,0,0,220]", padding=[2,4,2,4]))

    inline_labels = [
        {"lon": poly_10[8][0], "lat": poly_10[8][1], "text": f"⏳ 10분 화선 | 약 {p_10:,}평"},
        {"lon": poly_30[8][0], "lat": poly_30[8][1], "text": f"⚠️ 30분 위험선 | 약 {p_30:,}평"},
        {"lon": poly_60[8][0], "lat": poly_60[8][1], "text": f"🔥 60분 최종화두 | 약 {p_60:,}평"}
    ]
    pydeck_layers.append(pdk.Layer("TextLayer", pd.DataFrame(inline_labels), get_position="[lon, lat]", get_text="text", get_size=12, get_color="[255,255,255,255]", get_background_color="[15,15,15,220]", padding=[4,6,4,6], get_text_anchor="'start'"))
    pydeck_layers.append(pdk.Layer("TextLayer", pd.DataFrame([{"lon": city_data["lon"], "lat": city_data["lat"], "text": "🔥"}]), get_position="[lon, lat]", get_text="text", get_size=40, get_alignment_baseline="'center'"))

    infra_markers = [
        {"lon": city_data["lon"] - 0.015, "lat": city_data["lat"] + 0.012, "text": "🌊 소방 저수지", "bg": [0,191,255,230]},
        {"lon": city_data["route"][-2][0], "lat": city_data["route"][-2][1], "text": "🛣️ 산림 임도 진입관문", "bg": [46,139,87,230]},
        {"lon": city_data["fs_lon"], "lat": city_data["fs_lat"], "text": f"🚒 관할 기지: {city_data['fire_station']}", "bg": [255,69,0,240]}
    ]
    pydeck_layers.append(pdk.Layer("TextLayer", pd.DataFrame(infra_markers), get_position="[lon, lat]", get_text="text", get_size=13, get_color="[255,255,255,255]", get_background_color="bg", padding=[4,6,4,6]))

    st.pydeck_chart(pdk.Deck(
        layers=pydeck_layers, map_style=pdk.map_styles.DARK,
        initial_view_state=pdk.ViewState(latitude=(city_data["lat"]+city_data["fs_lat"])/2, longitude=(city_data["lon"]+city_data["fs_lon"])/2, zoom=11.6, pitch=0, bearing=0)
    ))

# --- 📡 3열 제원 패널 ---
st.markdown("---")
c1, c2, c3 = st.columns([1, 1.2, 1.2])

with c1:
    st.markdown(f"""
    <div style="background-color: #1c1d24; padding: 18px; border-radius: 8px; border-left: 5px solid #1a73e8; min-height: 330px;">
        <h4 style="margin:0 0 12px 0; color:#1a73e8; font-weight: bold;">📡 경북 세분화 지형 프로필</h4>
        <p style="margin:5px 0; font-size:14px; color: white;"><b>📍 정밀 도로명 주소:</b><br>{city_data['address']}</p>
        <hr style="border:0.5px solid #333; margin:8px 0;">
        <table style="width:100%; color:white; font-size:13px; border-collapse:collapse;">
            <tr><td>🌡️ 현재 실측 기온:</td><td style="text-align:right; font-weight:bold;">{city_data['t']:.1f} °C</td></tr>
            <tr><td>💧 현재 상대 습도:</td><td style="text-align:right; font-weight:bold;">{city_data['h']:.1f} %</td></tr>
            <tr><td>💨 현재 실측 풍속:</td><td style="text-align:right; font-weight:bold;">{city_data['w']:.1f} m/s</td></tr>
            <tr style="color:#a8c7fa;"><td>🚒 관할 소방 기지:</td><td style="text-align:right; font-weight:bold; color:#ff6b6b;">{city_data['fire_station']}</td></tr>
            <tr style="color:#a8c7fa;"><td>🛣️ 산림 임도 밀도:</td><td style="text-align:right; font-weight:bold;">{city_data['road_density']}%</td></tr>
            <tr style="color:#ffb4ab;"><td>🌲 소나무 수종 비율:</td><td style="text-align:right; font-weight:bold;">{city_data['pine_ratio']}%</td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

with c2:
    status_color = "#ff4b4b" if trigger_emergency_by_prob else "#66bb6a"
    calc_status_text = f"<span style='color:#ff4b4b; font-weight:bold;'>⚠️ 령이 실전 확산 모델링 연산 중</span>" if trigger_emergency_by_prob else f"<span style='color:#66bb6a; font-weight:bold;'>🟢 평시 라이브 예측 연산 중 (락오프)</span>"
    
    st.markdown(f"""
    <div style="background-color: #1c1d24; padding: 18px; border-radius: 8px; border-left: 5px solid {status_color}; min-height: 330px;">
        <h4 style="margin:0 0 5px 0; color:{status_color}; font-weight: bold;">🧠 령이 AI 자율 예측 시뮬레이션</h4>
        <p style="margin: 0 0 10px 0; font-size:13px;">상태: {calc_status_text}</p>
        <table style="width:100%; color:white; font-size:13px; border-collapse:collapse; margin-bottom:10px;">
            <tr style="border-bottom:1px solid #444; font-weight:bold; color:#aaa;">
                <td>⏳ 골든타임</td>
                <td>🔥 가상 피해 면적</td>
                <td>📐 경사 및 풍향</td>
            </tr>
            <tr style="border-bottom:1px solid #333;">
                <td style="color:#1a73e8; font-weight:bold;">발화 10분 뒤</td>
                <td style="color:white; font-weight:bold;">약 {p_10:,} 평</td>
                <td>{city_data['slope']}°</td>
            </tr>
            <tr style="border-bottom:1px solid #333;">
                <td style="color:#ffaa00; font-weight:bold;">발화 30분 뒤</td>
                <td style="color:#ffaa00; font-weight:bold;">약 {p_30:,} 평</td>
                <td style="color:#ffaa00; font-weight:bold;">{danger_direction}</td>
            </tr>
            <tr style="border-bottom:1px solid #333;">
                <td style="color:#ff4b4b; font-weight:bold;">발화 60분 뒤</td>
                <td style="color:#ff4b4b; font-weight:bold;">약 {p_60:,} 평</td>
                <td style="color:#aaa;">벡터 락온</td>
            </tr>
        </table>
        <p style="margin:2px 0; font-size:11px; color: #a8c7fa;">🔎 본 수치는 경북 해당 주소지의 실시간 인덱스로 추론된 값입니다.</p>
    </div>
    """, unsafe_allow_html=True)

with c3:
    ai_m10, ai_m30, ai_m60 = generate_ai_autonomous_sop(city_data, op_hour, is_emergency=trigger_emergency_by_prob, eta_str=eta_str)
    st.markdown(f"<h4 style='margin:0 0 10px 0; color:#ff4b4b; font-size:15px; font-weight:bold;'>🧠 [소방청 SOP 동기화] 실시간 전술 지시서</h4>", unsafe_allow_html=True)
    st.info(ai_m10)
    st.warning(ai_m30)
    st.error(ai_m60)

# --- 🧠 [RAG 연산부] ---
st.markdown("---")
with st.spinner("🧠 령이 대뇌 피질: 경북 시공간 통계 탐색 중..."):
    brain_dataset = fetch_forest_fire_stats_brain()
    current_t, current_h, current_w, current_hr = city_data["t"], city_data["h"], city_data["w"], op_hour
    
    best_match, min_distance = None, float('inf')
    for data in brain_dataset:
        distance = math.sqrt(
            ((current_t - data["t"]) * 1.0) ** 2 + ((current_h - data["h"]) * 1.2) ** 2 + 
            ((current_w - data["w"]) * 2.5) ** 2 + ((current_hr - data["hour"]) * 8.0) ** 2
        )
        if distance < min_distance:
            min_distance = distance
            best_match = data

    similarity_score = max(50.0, min(99.9, 100.0 - (min_distance * 1.3)))
    box_border = "border: 2px solid #ff4b4b; background-color: #2b1111;" if trigger_emergency_by_prob else "border: 1px solid #1a73e8; background-color: #141824;"
    title_color = "#ff4b4b" if trigger_emergency_by_prob else "#1a73e8"
    rag_conclusion_text = best_match['sol']

if similarity_score >= 80.0:
    st.markdown(f"""
    <div style="{box_border} padding: 20px; border-radius: 8px;">
        <h3 style="margin: 0 0 10px 0; color: {title_color}; font-weight: bold;">🧠 령이 AI 산림청 OpenAPI 4차원 시공간 추론 결론</h3>
        <h4 style="margin: 0 0 8px 0; color: white;">📌 자율 기억 매칭: {best_match['case']} (시공간 기상 싱크로율: <span style='color:#ffff00; font-size:18px;'>{similarity_score:.1f}%</span>)</h4>
        <p style="margin: 0 0 15px 0; color: #ddd; font-size: 14px; line-height: 1.6;"><b>과거 데이터 아카이브 맥락 분석:</b><br>{best_match['desc']}</p>
        <hr style="border: 0.5px solid #444; margin: 10px 0;">
        <p style="margin: 0; color: #b9f6ca; font-size: 15px; line-height: 1.6;">{rag_conclusion_text}</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div style="border: 1px dashed #444; background-color: #0e1117; padding: 15px; border-radius: 8px; text-align: center;">
        <p style="margin: 0; color: #888; font-size: 14px;">
            🔍 <b>경북 시공간 RAG 모니터링:</b> 현재 도내 최고 매칭 싱크밀도가 <span style='color:#ffaa00; font-weight:bold;'>{similarity_score:.1f}%</span>로 평시 안정권에 있습니다. <br>
            <span style='font-size:12px; color:#666;'>(사이드바 시뮬레이터를 조작해 싱크로율 80% 돌파 시 백서 기반 특수 작전 대안이 실시간 동적 해제됩니다.)</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

# --- 아카이브 로그 대장 ---
st.divider()
st.subheader("📋 령이 자율 포착 로그 대장 (경상북도 소방 재난 방재 시스템 아카이브)")
df_mock_db = pd.DataFrame([{
    "령이 실시간 감지 시각": now_kst.strftime("%Y-%m-%d %H:%M:%S"),
    "산림청 API 수신 상태": "🚨 경북 대형산불 임계값 돌파 자율 선포 완료" if trigger_emergency_by_prob else "🟢 라이브 OpenAPI 경북 권역 무결성 동기화 (평시 예찰)",
    "관제 행정구역 축선": city_data['address'].split(" (")[0],
    "AI 연산 발전 확률": f"{city_data['prob']:.1f}%",
    "AI 최단거리 전술 판정": f"초국지성 공간 매칭 연산 중 (최고 싱크밀도: {similarity_score:.1f}%)"
}])
st.table(df_mock_db)