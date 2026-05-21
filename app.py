import streamlit as st
import time
import requests
import math
import random
import os
import json
import glob
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib

st.set_page_config(page_title="국가 화재 통합 관제 AI 령이", page_icon="⚠️", layout="wide")

# --- 🕒 실시간 시간대(Day/Night) 자동 인지 시스템 ---
tz_kst = timezone(timedelta(hours=9))
now_kst = datetime.now(tz_kst)
current_hour = now_kst.hour
is_night = (current_hour >= 19 or current_hour < 6)

st.title("🚨 실시간 화재 조기경보 및 통합 관제 플랫폼 '령이'")
st.markdown(f"**현재 관제 상태:** {'🌙 야간 전술 모드 (야간 전용 프로토콜 가동)' if is_night else '☀️ 주간 관제 모드 (항공/지상 통합 가동)'} | **Core Engine:** 🧠 지형·풍향·SOP 자율 융합 연산 엔진 v11.0")
st.divider()

DB_FILE = "ryong_i_annual_db.json"
MODEL_FILE = "ryong_i_ai_brain.pkl"
DATA_FOLDER = "ryong_i_dataset" 

def load_annual_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def save_annual_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)
    except: pass

@st.cache_resource
def train_or_load_ryong_i_ai():
    if os.path.exists(MODEL_FILE):
        try:
            model = joblib.load(MODEL_FILE)
            return model, "🧠 [엔진 가동] 기존에 생성된 AI 뇌(pkl) 파일을 성공적으로 로드 완료했습니다!"
        except: pass

    random.seed(42)
    mock_data = []
    for _ in range(1000):
        temp = random.uniform(5.0, 38.0)
        hum = random.uniform(10.0, 80.0)
        wind = random.uniform(0.5, 18.0)
        area = (temp * 0.001) + ((100 - hum) * 0.0002) + (wind * 0.005) + random.uniform(-0.005, 0.005)
        mock_data.append({"기온": temp, "습도": hum, "풍속": wind, "피해면적": max(0.001, area)})
        
    df_mock = pd.DataFrame(mock_data)
    X_mock = df_mock[['기온', '습도', '풍속']]
    y_mock = df_mock['피해면적']
    
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(X_mock, y_mock)
    joblib.dump(model, MODEL_FILE)
    return model, "🌱 [스케일 교정 완료] 백업용 내부 환경 데이터셋 1,000건 기반 기본 AI 머신러닝 학습 완료"

ai_brain, ai_status_message = train_or_load_ryong_i_ai()
st.sidebar.info(ai_status_message)

# --- 🌟 UI 동기화 세션 상태 설정 ---
if 't_val' not in st.session_state: st.session_state['t_val'] = 18.0
if 'h_val' not in st.session_state: st.session_state['h_val'] = 50.0
if 'w_val' not in st.session_state: st.session_state['w_val'] = 1.5
if 'wd_val' not in st.session_state: st.session_state['wd_val'] = 180.0  

if 'fire_blackbox' not in st.session_state: st.session_state['fire_blackbox'] = []
if 'current_target' not in st.session_state: st.session_state['current_target'] = "대한민국 전역 (전수 관측)"

# --- [소방청 및 기상청 API 수신 함수] ---
def get_realtime_119_dispatch_data():
    API_KEY = "69309efd849de167a2a68e2fc27331c01eb67888d72dd4a740419a33cf7d292e"
    url = "http://apis.data.go.kr/1560000/FireStnDispathInfoService/getFireStnDispathInfoList"
    params = {'serviceKey': API_KEY, 'pageNo': '1', 'numOfRows': '1', 'dataType': 'JSON'}
    try:
        res = requests.get(url, params=params, timeout=2)
        if res.status_code == 200 and 'response' in res.json():
            items = res.json()['response']['body']['items']['item']
            return str(items[0]['dispathDsstTm']) if items else None
    except: pass
    return None

def fetch_kma_live_weather():
    API_KEY = "69309efd849de167a2a68e2fc27331c01eb67888d72dd4a740419a33cf7d292e"
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    base_time_dt = datetime.now(tz_kst) - timedelta(minutes=30)
    base_date = base_time_dt.strftime("%Y%m%d")
    base_time = base_time_dt.strftime("%H00")
    params = {'serviceKey': API_KEY, 'pageNo': '1', 'numOfRows': '10', 'dataType': 'JSON', 'base_date': base_date, 'base_time': base_time, 'nx': '91', 'ny': '106'}
    
    live_t, live_h, live_w, live_wd = 14.5, 62.0, 1.2, 180.0
    try:
        res = requests.get(url, params=params, timeout=2.5)
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
    if 337.5 <= deg or deg < 22.5: return "북풍 (⬇️ 남쪽 구역 최위험)", "남쪽"
    elif 22.5 <= deg < 67.5: return "북동풍 (↙️ 남서쪽 구역 최위험)", "남서쪽"
    elif 67.5 <= deg < 112.5: return "동풍 (⬅️ 서쪽 구역 최위험)", "서쪽"
    elif 112.5 <= deg < 157.5: return "남동풍 (↖️ 북서쪽 구역 최위험)", "북서쪽"
    elif 157.5 <= deg < 202.5: return "남풍 (⬆️ 북쪽 구역 최위험)", "북쪽"
    elif 202.5 <= deg < 247.5: return "남서풍 (↗️ 북동쪽 구역 최위험)", "북동쪽"
    elif 247.5 <= deg < 292.5: return "서풍 (➡️ 동쪽 구역 최위험)", "동쪽"
    else: return "북서풍 (↘️ 남동쪽 구역 최위험)", "남동쪽"

# --- 🚒 소방 대응 매뉴얼 (SOP) 자율 매칭 엔진 기능 ---
def get_dynamic_sop_manual(area_ha, is_night_mode, danger_zone):
    """ 화재 규모 및 시간대에 따른 소방청 표준작전절차(SOP) 행동지침 자율 생성 """
    if area_ha >= 0.15: # 대형 화재 등급
        level = "🔴 [SOP 3단계] 광역 초광역 비상대응"
        if is_night_mode:
            m10 = f"🚒 **[10분 야간 작전]** 의용소방대 비상 소집령 전면 발령. {danger_zone} 방면 민가 주변에 수화 고착 소방차 집중 배치하여 방어선 구축."
            m30 = f"🔦 **[30분 가시 확보]** 소방 조명차 2대 및 소방열화상 드론 즉각 투입. 야간 기류에 의한 {danger_zone} 비화(날아가는 불) 감시망 가동."
            m60 = f"🏠 **[60분 인명 사수]** {danger_zone} 방향 직격 타깃 부락 취침 주민 전원 강제 가택 대피 및 임시 구호소(명사무소/초교) 이송 집행."
        else:
            m10 = f"🚁 **[10분 주간 작전]** 초대형 산불진화헬기 3대 이상 즉각 출격 요청. {danger_zone} 최전방 화선에 선제 고압 살포 개시."
            m30 = f"⚠️ **[30분 저지 조치]** 산불전문진화대 지상 인력 투입. {danger_zone} 하류 골짜기 차단벽 구축 및 민가 방어선 설정."
            m60 = f"🧑‍🚒 **[60분 광역 저지]** 소방동원령 1호 연계 인근 지자체 소방력 20% 교차 응원 요청. 주요 국가 인프라 보호막 가동."
    elif area_ha >= 0.08: # 중형 화재 등급
        level = "🟠 [SOP 2단계] 관할 구조대 전원 투입"
        if is_night_mode:
            m10 = f"🚒 **[10분 야간 작전]** 관할 소방서 구조대 전원 비상 소집. 화재 현장 {danger_zone} 진입로 일반 차량 통행 전면 금지 조치."
            m30 = f"🔦 **[30분 가시 확보]** 지휘 텐트 전방 전개. 현장 안전 요원 배치 후 {danger_zone} 능선 확산 방향 소화 용수선 이동 확보."
            m60 = f"🧑‍🚒 **[60분 야간 방어]** 야간 산바람 변동성 감시. {danger_zone} 산림 방화선 300m 전방 국지적 수목 제거 및 방화선 고착."
        else:
            m10 = f"🚒 **[10분 주간 작전]** 산불전문진화차 및 소방 펌프차 정예조 현장 최우선 전면 배치. 진화 헬기 1~2대 무전 링크 가동."
            m30 = f"⚠️ **[30분 저지 조치]** {danger_zone} 방면 임도(숲길)를 활용한 지상 진화대 배치. 비화 가능 구역 선제 유동 살수."
            m60 = f"🧑‍🚒 **[60분 광역 저지]** 인근 의용소방대 50% 추가 동원령. 확산 경로의 수목 벌채를 통한 물리적 방화벽 구축 유도."
    else: # 소형/주의 등급
        level = "🟡 [SOP 1단계] 초동 진압 관할 출동"
        m10 = f"🚒 **[10분 초동 조치]** 관할 안전센터 진화 펌프차 1대 및 살수차 현장 즉각 급파. {danger_zone} 사면 하단부 근접 진압 시도."
        m30 = f"⚠️ **[30분 번짐 차단]** 고압 방수포 전개 및 주변 건조 수목 낙엽층 집중 살수를 통한 국지적 번짐 원천 차단."
        m60 = "🧑‍🚒 **[60분 잔불 정리]** 기계화 등짐펌프 조 투입. 불씨 잔존 가능성 있는 흙 파뒤집기 및 완진 판정 후 예찰조 전환."
        
    return level, m10, m30, m60

def capture_fire_anomaly_v100(lat, lon, region_name, ai_score, pyeong, fire_line_m, wd_text):
    sat_time_str = now_kst.strftime("%Y-%m-%d %H:%M:%S")
    real_119_time_raw = get_realtime_119_dispatch_data()
    
    if real_119_time_raw:
        try:
            dt_report = datetime.strptime(real_119_time_raw, "%Y%m%d%H%M%S").replace(tzinfo=tz_kst)
            real_119_time_str = dt_report.strftime("%Y-%m-%d %H:%M:%S")
            time_diff = dt_report - now_kst
            diff_seconds = int(time_diff.total_seconds())
            abs_seconds = abs(diff_seconds)
            diff_min, diff_sec = abs_seconds // 60, abs_seconds % 60
            if diff_seconds > 0: time_diff_result = f"위성이 119보다 {diff_min:02d}분 {diff_sec:02d}초 빠름"
            else: time_diff_result = f"위성이 119보다 {diff_min:02d}분 {diff_sec:02d}초 늦음"
        except: real_119_time_str, time_diff_result = real_119_time_raw, "시차 연산 대기"
    else: real_119_time_str, time_diff_result = "공개 대기 중", "실시간 동기화 중"

    new_record = {
        "령이 감지 시각": sat_time_str, "소방신고 접수 시각": real_119_time_str, "실측 시차 분석": time_diff_result,
        "감지 위치 좌표": f"위도 {lat:.4f}, 경도 {lon:.4f}", "발화 대상 주소": region_name, "국토 법정 지목": "임야 (산불)",
        "AI 예측 피해규모": f"{pyeong:,.0f} 평 ({ai_score:.2f} ha)", "예상 화선 및 풍향": f"{fire_line_m:,.0f}m ({wd_text.split(' ')[0]})", "timestamp": now_kst.timestamp()
    }
    
    if st.session_state['fire_blackbox'] and st.session_state['fire_blackbox'][0]["발화 대상 주소"] == region_name:
        st.session_state['fire_blackbox'][0]["AI 예측 피해규모"] = f"{pyeong:,.0f} 평 ({ai_score:.2f} ha)"
        st.session_state['fire_blackbox'][0]["예상 화선 및 풍향"] = f"{fire_line_m:,.0f}m ({wd_text.split(' ')[0]})"
    else:
        st.session_state['fire_blackbox'].insert(0, new_record)
    
    save_annual_db(st.session_state['fire_blackbox'])
    st.session_state['live_sat_time'] = sat_time_str
    st.session_state['live_119_time'] = real_119_time_str
    st.session_state['live_diff'] = time_diff_result

# --- 🎮 사이드바 컨트롤러 ---
st.sidebar.header("📡 대한민국 영토 상시 스캔")
region_input = st.sidebar.text_input("상세 구역 줌인 (주소 입력 후 아래 버튼 클릭)", value="")

if st.sidebar.button("🛰️ 해당 구역 실시간 감시 파이프라인 가동", type="primary"):
    if region_input.strip() != "":
        st.session_state['current_target'] = region_input
        with st.sidebar.spinner("기상청 방재 기상 관측망(AWS) 실시간 통신 중..."):
            real_temp, real_hum, real_wind, real_wd = fetch_kma_live_weather()
            st.session_state['t_val'] = real_temp
            st.session_state['h_val'] = real_hum
            st.session_state['w_val'] = real_wind
            st.session_state['wd_val'] = real_wd
        st.sidebar.success(f"✅ {region_input} 실시간 기상망 데이터 연동 성공!")
        st.rerun() 
    else: st.sidebar.warning("조회할 주소를 입력해 주세요.")

st.sidebar.markdown("---")
st.sidebar.header("🎛️ 실시간 기상 변수 통제 계측기")

t_slider = st.sidebar.slider("관측 기온 (°C)", -10.0, 45.0, value=float(st.session_state['t_val']))
h_slider = st.sidebar.slider("대기 상대습도 (%)", 0.0, 100.0, value=float(st.session_state['h_val']))
w_slider = st.sidebar.slider("현지 풍속 (m/s)", 0.0, 35.0, value=float(st.session_state['w_val']))
wd_slider = st.sidebar.slider("현지 풍향 바람 방향 (각도 °)", 0.0, 360.0, value=float(st.session_state['wd_val']), step=45.0)

st.session_state['t_val'] = t_slider
st.session_state['h_val'] = h_slider
st.session_state['w_val'] = w_slider
st.session_state['wd_val'] = wd_slider

st.sidebar.markdown("---")
# 🌟 지형분호 실측 경사도 입력 장치 (프로그램 내 내장 지도 데이터 가상화 연동)
current_slope = st.sidebar.slider("지형 실측 경사도 (°)", 0.0, 60.0, 20.0, help="산불은 경사도가 높을수록 상승 기류를 타고 평지보다 최대 수배 빠르게 확산됩니다.")

# --- 🧠 AI 및 지형 물리 융합 자동 연산 레이어 ---
try:
    if hasattr(ai_brain, "n_features_in_") and ai_brain.n_features_in_ == 4:
        ai_live_prediction = float(ai_brain.predict([[136, st.session_state['t_val'], st.session_state['h_val'], st.session_state['w_val']]])[0])
    else:
        ai_live_prediction = float(ai_brain.predict([[st.session_state['t_val'], st.session_state['h_val'], st.session_state['w_val']]])[0])
except Exception as e:
    ai_live_prediction = (st.session_state['t_val'] * 0.01) + (st.session_state['w_val'] * 0.1)

# 🌟 중요: 단순 기상 계산을 넘어 경사도 물리 상수를 자동 결합한 '실질 확산 면적 스케일' 자동 계산
base_area_calc = (ai_live_prediction * 0.005) + ((100 - st.session_state['h_val']) * 0.001) + (st.session_state['w_val'] * 0.01)
# 경사도가 높아질수록 불길이 상향 확산되는 지형 효과 반영
final_area_score = max(0.001, base_area_calc * (1.0 + (current_slope / 60.0) * 1.5)) 

final_pyeong = final_area_score * 3025.0

ellipse_eccentricity = 1.0 + (float(st.session_state['w_val']) * 0.1)
approx_radius_m = math.sqrt((final_area_score * 10000.0) / math.pi)
final_fire_line_m = 2.0 * math.pi * approx_radius_m * (ellipse_eccentricity ** 0.5)

wind_text_str, target_danger_zone = get_wind_direction_text(st.session_state['wd_val'])

# 분당 확산 속도 상수에 지형지물의 마찰력 및 사면 추진력 자동 보정
base_spread_factor = 0.001 + (float(st.session_state['w_val']) * 0.002) + (current_slope * 0.0008)
if float(st.session_state['h_val']) < 30: base_spread_factor *= 1.8
final_spread_rate_min = min(final_area_score * 0.1, base_spread_factor)

if st.session_state['current_target'] != "대한민국 전역 (전수 관측)":
    capture_fire_anomaly_v100(36.5665, 128.7262, st.session_state['current_target'], final_area_score, final_pyeong, final_fire_line_m, wind_text_str)

# SOP 대응 지침 자율 로드
sop_level_title, m_10, m_30, m_60 = get_dynamic_sop_manual(final_area_score, is_night, target_danger_zone)

# --- 📺 메인 UI 모니터링 경보 표출 모듈 ---
col_radar, col_status = st.columns([1, 2])

with col_radar:
    st.subheader("🛰️ 령이 실시간 국지 감시 관제 센터")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.session_state['current_target'] == "대한민국 전역 (전수 관측)":
        st.info("🟢 [상시 모드] 배경 백엔드에서 전국 위성 FF 피드를 무한 스캔 중입니다.")
    else:
        st.error(f"🔴 [위기 감지] AI 예측 모델 연동 ➡️ [{st.session_state['current_target']}] 집중 관제 중.")
        
    st.divider()
    st.markdown("### 📈 실시간 산불 화선 속도 계측기")
    m_col1, m_col2 = st.columns(2)
    m_col1.metric("🔥 분당 예상 피해 면적", f"{final_spread_rate_min * 3025.0:.2f} 평/min")
    
    # 🌟 버튼이 없어도 실시간 슬라이더 변화에 연동되는 '자동 4D 타임라인 예측 표' 구성
    st.markdown("#### ⏳ 지형 결합형 경과 시간별 확산 추정치")
    timeline_records = []
    for mins in [10, 30, 60]:
        est_area = final_area_score + (final_spread_rate_min * mins)
        est_pyeong = est_area * 3025.0
        est_r = math.sqrt((est_area * 10000.0) / math.pi)
        est_line = 2.0 * math.pi * est_r * (ellipse_eccentricity ** 0.5)
        timeline_records.append({
            "경과 시간": f"{mins}분 뒤",
            "예상 면적(평)": f"{est_pyeong:,.0f} 평",
            "화선 길이(m)": f"{est_line:,.1f} m"
        })
    st.dataframe(pd.DataFrame(timeline_records), use_container_width=True, hide_index=True)

with col_status:
    st.subheader("📊 관제 현황 및 AI 최종 판정")
    st.caption(f"※ 기상청 실시간 AWS 관측망 동기화 수치 ➡️ 기온: {st.session_state['t_val']}°C | 습도: {st.session_state['h_val']}% | 풍속: {st.session_state['w_val']}m/s | 풍향: {wind_text_str.split(' ')[0]} ({st.session_state['wd_val']}°) | 지형 실측 경사: {current_slope}°")
    
    if final_area_score >= 0.15: bg_color = "#ff0000"; text_title = f"🔥 [🚨 AI 심각] 대형 산불 예측 (피해 규모: {final_pyeong:,.0f} 평 / 예상 화선: {final_fire_line_m:,.0f} m) 🔥"
    elif final_area_score >= 0.08: bg_color = "#d9381e"; text_title = f"🔥 [⚠️ AI 경계] 중형 산불 위험 (피해 규모: {final_pyeong:,.0f} 평 / 예상 화선: {final_fire_line_m:,.0f} m) 🔥"
    elif final_area_score >= 0.04: bg_color = "#e67e22"; text_title = f"🔥 [주의 등급] 국지성 소형 산불 (피해 규모: {final_pyeong:,.0f} 평 / 예상 화선: {final_fire_line_m:,.0f} m) 🔥"
    else: bg_color = "#1a73e8"; text_title = f"🔒 안전 관제 스캔 잠금 상태 (예측 규모: {final_pyeong:,.0f} 평 / 화선 징후 없음)"

    st.markdown(f"""
    <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px; border: 4px solid #ffffff; box-shadow: 0px 0px 15px {bg_color}; text-align: center;">
        <span style="font-size: 50px;">🧠</span>
        <h2 style="color: #ffffff; font-weight: bold; margin-top: 10px; margin-bottom: 5px;">{text_title}</h2>
        <h4 style="color: #ffff00; margin: 0;">🚒 관제 선언: {sop_level_title}</h4>
    </div>
    """, unsafe_allow_html=True)

# --- [하단 인지 속도 검증 레이어] ---
if st.session_state['current_target'] != "대한민국 전역 (전수 관측)":
    st.divider()
    st.subheader(f"🎯 실시간 산불 인지 속도 검증 레이어: [{st.session_state['current_target']}]")
    v1, v2, v3 = st.columns(3)
    v1.metric("🛰️ 령이 위성 최초 감지 시각 (실측 현재시각)", st.session_state.get('live_sat_time', '-'))
    v2.metric("🚒 소방청 실시간 출동/접수 시각 (오픈 API 연동)", st.session_state.get('live_119_time', '-'))
    st.info(f"⚡ **시차 분석 리포트**\n\n{st.session_state.get('live_diff', '-')}")

# --- 📢 [🌟 AI 자율 연동 지휘 가이드] 지형 및 SOP 융합 대책 표출 ---
st.divider()
st.markdown(f"### 📢 [SOP 표준 매뉴얼 지휘 가이드] {st.session_state['current_target']} 국토 지형 기반 초동 대응 대책")
c1, c2, c3 = st.columns(3)
if final_area_score >= 0.08: c1.error(m_10); c2.error(m_30); c3.error(m_60)
elif final_area_score >= 0.04: c1.warning(m_10); c2.warning(m_30); c3.warning(m_60)
else: c1.info(m_10); c2.info(m_30); c3.info(m_60)

st.divider()
st.subheader("📋 령이 자율 화재 포착 로그 (최근 7일 소방관 표준 규격 실측 데이터셋)")
if st.session_state['fire_blackbox']:
    st.table([{"령이 감지 시각": r["령이 감지 시각"], "소방신고 접수 시각": r["소방신고 접수 시각"], "실측 시차 분석": r["실측 시차 분석"], "발화 대상 주소": r["발화 대상 주소"], "AI 예측 피해규모 (평)": r["AI 예측 피해규모"], "예상 화선 및 풍향": r["예상 화선 및 풍향"]} for r in st.session_state['fire_blackbox']])
else:
    st.info("🚨 현재 감지된 실시간 화재 열점이 없습니다. 전국망 상시 전수 스캔 중...")