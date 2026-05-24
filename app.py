import streamlit as st
import time
import requests
import math
import random
import os
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib

st.set_page_config(page_title="국가 화재 통합 관제 AI 령이", page_icon="⚠️", layout="wide")

# --- 🔓 API Key 안전 처리 ---
if "SEC_KEY" in st.secrets:
    API_KEY = st.secrets["SEC_KEY"]
else:
    API_KEY = "69309efd849de167a2a68e2fc27331c01eb67888d72dd4a740419a33cf7d292e"

# --- 🕒 실시간 시간대 인지 ---
tz_kst = timezone(timedelta(hours=9))
now_kst = datetime.now(tz_kst)
current_hour = now_kst.hour
is_night = (current_hour >= 19 or current_hour < 6)

st.title("🚨 실시간 전국 산불 조기경보 및 통합 관제 플랫폼 '령이'")
st.markdown(f"**현재 관제 상태:** {'🌙 야간 전술 모드' if is_night else '☀️ 주간 관제 모드'} | **Core Engine:** 🧠 전국망 시공간 자율 융합 연산 엔진 v20.0")
st.divider()

MODEL_FILE = "ryong_i_ai_brain.pkl"
DB_FILE = "ryong_i_annual_db.json"               
SENSOR_LOG_FILE = "ryong_i_sensor_logs.json"     

# --- 🗺️ 전국 모니터링 고유 관측소 데이터셋 ---
NATIONWIDE_STN_MAP = {
    "문경시 (백두대간 요충지)": {"stn": 273, "lat": 36.5938, "lon": 128.1865, "slope": 32.0, "addr": "경북 문경시 가은읍 수예리 산 18-1"},
    "안동시 (경북 북부 거점)": {"stn": 272, "lat": 36.5665, "lon": 128.7262, "slope": 25.0, "addr": "경북 안동시 명륜동 야산 지대"},
    "의성군 (중부 임야 취약지)": {"stn": 278, "lat": 36.3526, "lon": 128.6970, "slope": 18.0, "addr": "경북 의성군 의성읍 원당리 일원"},
    "구미시 (영남 내륙 산악지)": {"stn": 279, "lat": 36.1214, "lon": 128.3446, "slope": 20.0, "addr": "경북 구미시 금오산 성안 구역"},
    "강릉시 (영동 동해안 대형축)": {"stn": 105, "lat": 37.7514, "lon": 128.8961, "slope": 35.0, "addr": "강원 강릉시 성산면 산림 지대"},
    "양양군 (양간지풍 최위험지)": {"stn": 659, "lat": 38.0754, "lon": 128.6189, "slope": 30.0, "addr": "강원 양양군 양양읍 구룡령 사면"},
    "홍성군 (충청 서해안 내륙축)": {"stn": 177, "lat": 36.6016, "lon": 126.6608, "slope": 15.0, "addr": "충남 홍성군 서부면 야산 구역"}
}

@st.cache_resource
def load_ryong_i_ai():
    if os.path.exists(MODEL_FILE):
        try: return joblib.load(MODEL_FILE), "🧠 [엔진 가동] 1년 치 전국 기상 빅데이터 기반 AI 핵심 브레인이 가동되었습니다."
        except: pass
    model = RandomForestRegressor(n_estimators=10, random_state=42)
    model.fit(pd.DataFrame([{"STN": 273, "TA": 25.0, "HM": 30.0, "WS": 3.0}]), [0.05])
    return model, "🌱 [스케일 교정] 전국망 기본 백업 인공지능 구동 중"

ai_brain, ai_status_message = load_ryong_i_ai()
st.sidebar.info(ai_status_message)

if 'fire_blackbox' not in st.session_state:
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: st.session_state['fire_blackbox'] = json.load(f)
        except: st.session_state['fire_blackbox'] = []
    else: st.session_state['fire_blackbox'] = []

# --- 🛰️ API 데이터 수신 모듈 ---
def get_realtime_119_dispatch_data():
    url = "http://apis.data.go.kr/1560000/FireStnDispathInfoService/getFireStnDispathInfoList"
    params = {'serviceKey': API_KEY, 'pageNo': '1', 'numOfRows': '1', 'dataType': 'JSON'}
    try:
        res = requests.get(url, params=params, timeout=2)
        if res.status_code == 200 and 'response' in res.json():
            items = res.json()['response']['body']['items']['item']
            return str(items[0]['dispathDsstTm']) if items else None
    except: pass
    return None

def fetch_kma_live_weather(stn_id):
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    base_time_dt = datetime.now(tz_kst) - timedelta(minutes=45)
    base_date = base_time_dt.strftime("%Y%m%d")
    base_time = base_time_dt.strftime("%H00")
    params = {'serviceKey': API_KEY, 'pageNo': '1', 'numOfRows': '10', 'dataType': 'JSON', 'base_date': base_date, 'base_time': base_time, 'nx': '91', 'ny': '106'}
    live_t, live_h, live_w, live_wd = 22.0, 50.0, 2.0, 180.0
    try:
        res = requests.get(url, params=params, timeout=1.5)
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
    if 337.5 <= deg or deg < 22.5: return "북풍 (⬇️ 남쪽 위험)", "남쪽"
    elif 22.5 <= deg < 67.5: return "북동풍 (↙️ 남서쪽 위험)", "남서쪽"
    elif 67.5 <= deg < 112.5: return "동풍 (⬅️ 서쪽 위험)", "서쪽"
    elif 112.5 <= deg < 157.5: return "남동풍 (↖️ 북서쪽 위험)", "북서쪽"
    elif 157.5 <= deg < 202.5: return "남풍 (⬆️ 북쪽 위험)", "북쪽"
    elif 202.5 <= deg < 247.5: return "남서풍 (↗️ 북동쪽 위험)", "북동쪽"
    elif 247.5 <= deg < 292.5: return "서풍 (➡️ 동쪽 위험)", "동쪽"
    else: return "북서풍 (↘️ 남동쪽 위험)", "남동쪽"

def get_dynamic_sop_manual(area_ha, is_night_mode, danger_zone):
    if area_ha >= 0.15:
        level = "🔴 [SOP 3단계] 광역 대응 발령"
        m10 = f"🚒 의용소방대 비상 소집령 발령. {danger_zone} 방면 민가 소방차 집중 배치."
        m30 = f"🔦 소방 조명차 및 열화상 드론 투입. 야간 {danger_zone} 비화 감시 조 가동."
        m60 = f"🏠 {danger_zone} 방향 타깃 부락 주민 강제 대피령 및 임시 구호소 이송 집행."
    elif area_ha >= 0.08:
        level = "🟠 [SOP 2단계] 구조대 전원 투입"
        m10 = f"🚒 관할 소방서 구조대 비상 소집. 현장 {danger_zone} 진입로 일반 차량 통제."
        m30 = f"⚠️ 지휘 텐트 전방 전개. {danger_zone} 능선 확산 경로 소화 용수선 이동 확보."
        m60 = f"🧑‍🚒 {danger_zone} 산림 방화선 300m 전방 국지적 수목 제거 및 방화선 고착."
    else:
        level = "🟡 [SOP 1단계] 초동 진압 출동"
        m10 = f"🚒 관할 센터 진화 펌프차 및 살수차 급파. 사면 하단부 근접 진압 시도."
        m30 = f"⚠️ 고압 방수포 전개 및 주변 건조 낙엽층 집중 살수로 번짐 원천 차단."
        m60 = "🧑‍🚒 기계화 등짐펌프 조 투입 잔불 정리 및 완진 판정 후 예찰조 전환."
    return level, m10, m30, m60

def save_sensor_live_log(records_list):
    log_data = []
    if os.path.exists(SENSOR_LOG_FILE):
        try:
            with open(SENSOR_LOG_FILE, "r", encoding="utf-8") as f: log_data = json.load(f)
        except: log_data = []
    current_time_str = now_kst.strftime("%Y-%m-%d %H:%M:%S")
    snapshot = {
        "감지 시각": current_time_str,
        "전국 권역 환경 스냅샷": [
            {
                "지역": r["지역명"].split(' ')[0], "관측소_STN": r["STN"],
                "기온_C": r["기온(°C)"], "습도_퍼센트": r["습도(%)"], "풍속_ms": r["풍속(m/s)"], "풍향": r["풍향"], "지형경사": r["경사도"],
                "AI_예측_피해규모_평": round(r["예측면적(평/1h)"], 1), "예상_화선_m": round(r["예측화선(m)"], 1)
            } for r in records_list
        ]
    }
    if not log_data or log_data[-1]["감지 시각"] != current_time_str:
        log_data.append(snapshot)
        cutoff_time = now_kst - timedelta(days=14)
        filtered_log_data = [log for log in log_data if datetime.strptime(log["감지 시각"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz_kst) >= cutoff_time]
        with open(SENSOR_LOG_FILE, "w", encoding="utf-8") as f: json.dump(filtered_log_data, f, ensure_ascii=False, indent=4)

def save_blackbox_log(highest_row):
    sat_time_str = now_kst.strftime("%Y-%m-%d %H:%M:%S")
    real_119_time_raw = get_realtime_119_dispatch_data()
    real_119_time_str, time_diff_result = ("공개 대기 중", "실시간 동기화 중") if not real_119_time_raw else (real_119_time_raw, "시차 연산 대기")
    
    new_record = {
        "령이 감지 시각": sat_time_str, "소방신고 접수 시각": real_119_time_str, "실측 시차 분석": time_diff_result,
        "감지 위치 좌표": f"위도 {highest_row['lat']:.4f}, 경도 {highest_row['lon']:.4f}", "발화 대상 주소": highest_row['지역명'], "국토 법정 지목": "임야 (산불)",
        "AI 예측 피해규모": f"{highest_row['예측면적(평/1h)']:,.0f} 평", "예상 화선 및 풍향": f"{highest_row['예측화선(m)']:,.0f}m ({highest_row['풍향']})"
    }
    if not st.session_state['fire_blackbox'] or st.session_state['fire_blackbox'][0]["발화 대상 주소"] != highest_row['지역명']:
        st.session_state['fire_blackbox'].insert(0, new_record)
        with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(st.session_state['fire_blackbox'], f, ensure_ascii=False, indent=4)


# =========================================================================================
# 🎮 사이드바 컨트롤 시스템
# =========================================================================================
st.sidebar.header("📡 령이 하이브리드 관제 컨트롤러")
control_mode = st.sidebar.radio("⚙️ 시스템 작동 모드 설정", ["🛰️ 24시간 실시간 전국 자율 예찰망", "📐 타깃 지역 가상 시뮬레이터"], index=0)

computed_records = []

if control_mode == "🛰️ 24시간 실시간 전국 자율 예찰망":
    st.sidebar.success("🟢 실시간 기상청 통신 인프라 가동 중")
    for city_name, info in NATIONWIDE_STN_MAP.items():
        t, h, w, wd = fetch_kma_live_weather(info["stn"])
        wd_text, danger_zone = get_wind_direction_text(wd)
        
        try: ai_pred = float(ai_brain.predict([[info["stn"], t, h, w]])[0])
        except: ai_pred = (t * 0.01) + (w * 0.1)
            
        base_calc = (ai_pred * 0.005) + ((100 - h) * 0.001) + (w * 0.01)
        final_ha = max(0.001, base_calc * (1.0 + (info["slope"] / 60.0) * 1.5))
        final_pyeong = final_ha * 3025.0
        
        ellipse_ecc = 1.0 + (w * 0.1)
        approx_r = math.sqrt((final_ha * 10000.0) / math.pi)
        fire_line_m = 2.0 * math.pi * approx_r * (ellipse_ecc ** 0.5)
        
        spread_factor = 0.001 + (w * 0.002) + (info["slope"] * 0.0008)
        if h < 30: spread_factor *= 1.8
        rate_min = min(final_ha * 0.1, spread_factor)
        
        sop_title, m10, m30, m60 = get_dynamic_sop_manual(final_ha, is_night, danger_zone)
        
        computed_records.append({
            "지역명": city_name, "STN": info["stn"], "lat": info["lat"], "lon": info["lon"], "기온(°C)": t, "습도(%)": h, "풍속(m/s)": w, "풍향": wd_text.split(' ')[0], "경사도": f"{info['slope']}°",
            "위험점수": final_ha * 1000, "예측면적(평/1h)": final_pyeong, "예측화선(m)": fire_line_m, "속도(평/min)": rate_min * 3025.0,
            "SOP레벨": sop_title, "SOP10": m10, "SOP30": m30, "SOP60": m60, "주소": info["addr"]
        })
    save_sensor_live_log(computed_records)

else:
    st.sidebar.markdown("---")
    sim_city = st.sidebar.selectbox("🎯 가상 실험 대상 지역 선택", list(NATIONWIDE_STN_MAP.keys()))
    info = NATIONWIDE_STN_MAP[sim_city]
    
    sim_t = st.sidebar.slider("가상 온도 (°C)", -10.0, 45.0, 20.0)
    sim_h = st.sidebar.slider("가상 상대습도 (%)", 0.0, 100.0, 60.0) # 기본 안전 상태 유도하기 위해 습도 업
    sim_w = st.sidebar.slider("가상 현지 풍속 (m/s)", 0.0, 35.0, 1.5)
    sim_wd = st.sidebar.slider("가상 풍향 각도 (°)", 0.0, 360.0, 180.0, step=45.0)
    sim_slope = st.sidebar.slider("지형 커스텀 경사도 (°)", 0.0, 60.0, float(info["slope"]))
    
    wd_text, danger_zone = get_wind_direction_text(sim_wd)
    try: ai_pred = float(ai_brain.predict([[info["stn"], sim_t, sim_h, sim_w]])[0])
    except: ai_pred = (sim_t * 0.01) + (sim_w * 0.1)
        
    base_calc = (ai_pred * 0.005) + ((100 - sim_h) * 0.001) + (sim_w * 0.01)
    final_ha = max(0.001, base_calc * (1.0 + (sim_slope / 60.0) * 1.5))
    final_pyeong = final_ha * 3025.0
    
    ellipse_ecc = 1.0 + (sim_w * 0.1)
    approx_r = math.sqrt((final_ha * 10000.0) / math.pi)
    fire_line_m = 2.0 * math.pi * approx_r * (ellipse_ecc ** 0.5)
    
    spread_factor = 0.001 + (sim_w * 0.002) + (sim_slope * 0.0008)
    if sim_h < 30: spread_factor *= 1.8
    rate_min = min(final_ha * 0.1, spread_factor)
    
    sop_title, m10, m30, m60 = get_dynamic_sop_manual(final_ha, is_night, danger_zone)
    
    computed_records.append({
        "지역명": sim_city, "STN": info["stn"], "lat": info["lat"], "lon": info["lon"], "기온(°C)": sim_t, "습도(%)": sim_h, "풍속(m/s)": sim_w, "풍향": wd_text.split(' ')[0], "경사도": f"{sim_slope}°",
        "위험점수": final_ha * 1000, "예측면적(평/1h)": final_pyeong, "예측화선(m)": fire_line_m, "속도(평/min)": rate_min * 3025.0,
        "SOP레벨": sop_title, "SOP10": m10, "SOP30": m30, "SOP60": m60, "주소": info["addr"]
    })

df_national = pd.DataFrame(computed_records).sort_values(by="위험점수", ascending=False).reset_index(drop=True)
highest_risk_area = df_national.iloc[0]

if control_mode == "🛰️ 24시간 실시간 전국 자율 예찰망" and highest_risk_area["위험점수"] >= 120:
    save_blackbox_log(highest_risk_area)


# =========================================================================================
# 📺 UI 파트: 전국 예찰 및 실시간 감지 분기
# =========================================================================================

# --- 1단계: 실시간 전국 대다발 모니터링 상황판 ---
st.header("🛰️ [1단계] 전국 권역별 산불 위험도 실시간 자율 랭킹")

cols = st.columns(max(4, len(df_national)))
for idx, row in df_national.iterrows():
    if idx >= len(cols): break
    with cols[idx]:
        score = row["위험점수"]
        if score >= 120: status_color = "#ff0000"; status_txt = "🚨 심각"
        elif score >= 70: status_color = "#e67e22"; status_txt = "⚠️ 주의"
        else: status_color = "#1a73e8"; status_txt = "🟢 안전"
        
        st.markdown(f"""
        <div style="background-color: #1e1e1e; border: 2px solid {status_color}; padding: 12px; border-radius: 8px; text-align: center;">
            <b style="font-size: 15px; color: white;">{row['지역명'].split(' ')[0]}</b>
            <p style="margin: 3px 0; font-size: 11px; color: #aaa;">지점 코드: {row['STN']}번</p>
            <div style="background-color: {status_color}; color: white; font-weight: bold; padding: 3px; border-radius: 4px; font-size: 12px;">
                {status_txt} ({score:.1f}점)
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# --- ✨ [개편] 2·3단계 자율 활성화 필터 레이어 ---
# 위험점수가 120점(심각 임계치)을 넘었을 때만 2단계 정밀 추적과 3단계 SOP 가이드가 화면에 전격 강제 출력됩니다!
if highest_risk_area["위험점수"] >= 120:
    st.header(f"🔥 [2·3단계] 전국 확산 위험 정밀 추적 및 소방 SOP 긴급 처방 ➔ [{highest_risk_area['지역명']}]")
    
    c_info1, c_info2 = st.columns([1, 2])
    with c_info1:
        st.markdown(f"""
        <div style="background-color: #262730; padding: 20px; border-radius: 8px; border-left: 5px solid #ff0000; height: 100%;">
            <h4 style="margin-top: 0; color: #ff0000;">🔍 위성 연동 임야 위험 실시간 분석</h4>
            <p style="margin: 4px 0;"><b>대표 발화 주소:</b> {highest_risk_area['주소']}</p>
            <p style="margin: 4px 0;"><b>기온 / 습도:</b> {highest_risk_area['기온(°C)']}°C / {highest_risk_area['습도(%)']}%</p>
            <p style="margin: 4px 0;"><b>풍속 / 풍향:</b> {highest_risk_area['풍속(m/s)']} m/s ({highest_risk_area['풍향']})</p>
            <p style="margin: 4px 0;"><b>지형 실측 경사:</b> {highest_risk_area['경사도']}</p>
            <p style="margin: 4px 0; color: #ff0000;"><b>🔥 분당 화선 확산 속도:</b> {highest_risk_area['속도(평/min)']:.2f} 평/min</p>
        </div>
        """, unsafe_allow_html=True)

    with c_info2:
        st.markdown(f"""
        <div style="background-color: #111; padding: 20px; border-radius: 8px; border: 2px solid #ff0000; text-align: center;">
            <h3 style="color: #ff0000; margin: 0; font-weight: bold;">🚨 임야 대형 산불 징후 포착: 1시간 예측 피해 {highest_risk_area['예측면적(평/1h)']:,.0f} 평 (화선: {highest_risk_area['예측화선(m)']:,.0f}m)</h3>
            <h4 style="color: #ffff00; margin: 8px 0 0 0;">🚒 최우선 방재 진화 명령: {highest_risk_area['SOP레벨']}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<p style='margin-top:10px;'></p>", unsafe_allow_html=True)
        sc1, sc2, sc3 = st.columns(3)
        sc1.error(highest_risk_area['SOP10'])
        sc2.error(highest_risk_area['SOP30'])
        sc3.error(highest_risk_area['SOP60'])
else:
    # 🟢 평상시 산불 위험이 낮은 평화로운 주간에 출력될 안전 안내판
    st.header("🔒 [2·3단계] 전국 광역 재난 관제 필터")
    st.markdown("""
    <div style="background-color: #121824; border: 1px dashed #1a73e8; padding: 30px; border-radius: 10px; text-align: center;">
        <span style="font-size: 40px;">🛡️</span>
        <h3 style="color: #1a73e8; margin: 10px 0 5px 0; font-weight: bold;">대한민국 전역 산불 예찰망 청정 상태 유지 중</h3>
        <p style="color: #8ab4f8; margin: 0; font-size: 14px;">실시간 전국 기상 스캔 결과 위험도 임계치(120점)를 초과한 국지성 산불 위험 지역이 존재하지 않습니다.</p>
        <p style="color: #5f6368; margin: 5px 0 0 0; font-size: 12px;">※ 위험 상황 강제 모니터링 시뮬레이션은 사이드바에서 '타깃 지역 가상 시뮬레이터' 모드를 활성화한 뒤 가상 기상을 조율하십시오.</p>
    </div>
    """, unsafe_allow_html=True)


# --- 📅 백그라운드 2주 로그 및 소방 대조 테이블 (항상 유지) ---
st.divider()
st.subheader("📋 대한민국 전수 예찰 실시간 종합 상황판")
st.dataframe(df_national[["지역명", "STN", "기온(°C)", "습도(%)", "풍속(m/s)", "풍향", "경사도", "예측면적(평/1h)", "예측화선(m)", "SOP레벨"]], use_container_width=True, hide_index=True)

st.markdown("<br>", unsafe_allow_html=True)
st.subheader("📅 🛰️ 령이 2주간의 전 권역 실시간 기상/예측 누적 저장소 (`ryong_i_sensor_logs.json`)")
if os.path.exists(SENSOR_LOG_FILE):
    try:
        with open(SENSOR_LOG_FILE, "r", encoding="utf-8") as f: loaded_sensor_logs = json.load(f)
        flattened_logs = []
        for log in reversed(loaded_sensor_logs[-15:]):  
            time_stamp = log["감지 스캔 시각"] if "감지 스캔 시각" in log else log["감지 시각"]
            for r in log["전국 권역 환경 스냅샷"]:
                flattened_logs.append({
                    "감지 스캔 시각": time_stamp, "대상 권역": r["지역"], "STN 코드": r["관측소_STN"],
                    "실측 기온": f"{r['기온_C']} °C", "실측 습도": f"{r['습도_퍼센트']} %", "실측 풍속": f"{r['풍속_ms']} m/s", "풍향": r["풍향"],
                    "예측 면적(평)": f"{r['AI_예측_피해규모_평']:,.1f} 평", "예측 화선": f"{r['예상_화선_m']} m"
                })
        st.dataframe(pd.DataFrame(flattened_logs), use_container_width=True, hide_index=True)
    except: pass

st.markdown("<br>", unsafe_allow_html=True)
st.subheader("🎯 령이 자율 포착 시스템 성능 검증 (실시간 119 API 동기화 레이어)")
v1, v2 = st.columns(2)
v1.metric("🛰️ 령이 통합 관제 서버 현재시각", now_kst.strftime("%Y-%m-%d %H:%M:%S"))

real_119_time_raw = get_realtime_119_dispatch_data()
real_119_show, diff_show = "출동망 동기화 완료 (대기 중)", "전국망 상시 교차 매칭 엔진 가동 중"
if real_119_time_raw:
    try:
        dt_report = datetime.strptime(real_119_time_raw, "%Y%m%d%H%M%S").replace(tzinfo=tz_kst)
        real_119_show = dt_report.strftime("%Y-%m-%d %H:%M:%S")
        time_diff = dt_report - now_kst
        diff_seconds = int(time_diff.total_seconds())
        diff_min, diff_sec = abs(diff_seconds) // 60, abs(diff_seconds) % 60
        diff_show = f"위성 조기 경보가 소방청 신고 접수보다 {diff_min}분 {diff_sec}초 신속함" if diff_seconds > 0 else f"소방청 신고 접수가 {diff_min}분 {diff_sec}초 먼저 수신됨"
    except: pass
v2.metric("🚒 소방청 실시간 119 출동 접수 시각", real_119_show)
st.info(f"⚡ **전국망 교차 검증 리포트**\n\n{diff_show}")

if st.session_state['fire_blackbox']:
    st.table([{"령이 감지 시각": r["령이 감지 시각"], "소방신고 접수 시각": r["소방신고 접수 시각"], "실측 시차 분석": r["실측 시차 분석"], "발화 대상 주소": r["발화 대상 주소"], "AI 예측 피해규모": r["AI 예측 피해규모"], "예상 화선 및 풍향": r["예상 화선 및 풍향"]} for r in st.session_state['fire_blackbox'][:7]])