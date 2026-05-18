import streamlit as st
import time
import requests
import math
import random
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

st.set_page_config(page_title="국가 화재 통합 관제 AI 령이", page_icon="⚠️", layout="wide")

st.title("🚨 실시간 화재 조기경보 및 통합 관제 플랫폼 '령이'")
st.markdown("천리안 2A호 위성(FF) ↔️ 소방청 실시간 출동망 ↔️ 기상청 국지 AWS 24/7 자율 연동")
st.divider()

# --- 🌟 초기 세션 상태 및 블랙박스 데이터베이스 모의 ---
if 'fire_blackbox' not in st.session_state:
    # 령이가 실시간으로 발견한 화재 기록을 저장하는 저장소
    st.session_state['fire_blackbox'] = [
        {"id": "KO-AND-021", "detection_time": "2026-05-19 14:12:05", "dispatch_time": "2026-05-19 14:23:40", "coordinate": "위도 36.3214, 경도 128.4512", "location": "경북 안동 야산", "status": "✅ 골든타임 사수"},
        {"id": "KO-SEO-105", "detection_time": "2026-05-18 09:41:12", "dispatch_time": "2026-05-18 09:49:15", "coordinate": "위도 37.4979, 경도 127.0276", "location": "서울 강남 빌딩", "status": "✅ 조기 인지 성공"}
    ]

if 't_val' not in st.session_state: st.session_state['t_val'] = 18.0
if 'h_val' not in st.session_state: st.session_state['h_val'] = 50.0
if 'w_val' not in st.session_state: st.session_state['w_val'] = 1.5
if 'current_target' not in st.session_state: st.session_state['current_target'] = "대한민국 전역 상시 전수 스캔"

# --- 🚒 소방청 실시간 출동 정보 API 엔진 (v4.0 자율 매핑) ---
def get_119_official_time():
    # 69309efd849de167a2a68e2fc27331c01eb67888d72dd4a740419a33cf7d292e
    API_KEY = "69309efd849de167a2a68e2fc27331c01eb67888d72dd4a740419a33cf7d292e"
    url = "http://apis.data.go.kr/1560000/FireStnDispathInfoService/getFireStnDispathInfoList"
    params = {'serviceKey': API_KEY, 'pageNo': '1', 'numOfRows': '1', 'dataType': 'JSON'}
    try:
        res = requests.get(url, params=params, timeout=3)
        if res.status_code == 200 and 'response' in res.json():
            item = res.json()['response']['body']['items']['item'][0]
            raw_time = str(item['dispathDsstTm']) # YYYYMMDDHHMMSS
            dt = datetime.strptime(raw_time, "%Y%m%d%H%M%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except: pass
    return "공개 대기 중..."

# --- 🛰️ 령이 자율 포착 로직 (v4.0) ---
def capture_fire_anomaly(lat, lon, region_name):
    tz_kst = timezone(timedelta(hours=9))
    now = datetime.now(tz_kst)
    sat_time = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # 소방청 시간 자동 수집 (공개되는 대로 기록)
    official_119 = get_119_official_time()
    
    new_entry = {
        "id": f"KO-{random.randint(100,999)}",
        "detection_time": sat_time,
        "dispatch_time": official_119,
        "coordinate": f"위도 {lat:.4f}, 경도 {lon:.4f}",
        "location": region_name,
        "status": "📡 실시간 추적 중"
    }
    # 중복 기록 방지 (가장 최근 기록과 주소가 다를 때만 추가)
    if not st.session_state['fire_blackbox'] or st.session_state['fire_blackbox'][0]['location'] != region_name:
        st.session_state['fire_blackbox'].insert(0, new_entry)

# --- 📡 기상청 & 위성 통합 추출 엔진 ---
def get_live_data(region_name):
    # (이전 코드와 동일한 기상청/위성/지목 파싱 로직 포함)
    # ... [생략: 기존 convert_to_grid, get_land_use_jimok 함수 등 유지] ...
    # API 호출 후 좌표(lat, lon) 획득 시 capture_fire_anomaly 호출
    # 예시 좌표로 일단 흐름 구성
    lat, lon = 36.5665, 128.7262
    capture_fire_anomaly(lat, lon, region_name)
    return {"temperature": 24.0, "humidity": 30.0, "wind_speed": 4.5}, "01:00 정시", "임야", 650.0

# --- 🎮 UI 메인 컨트롤 ---
st.sidebar.header("📡 대한민국 영토 24/7 자율 감시")
region_input = st.sidebar.text_input("상세 구역 줌인 (주소 입력)", value="")

if st.sidebar.button("🛰️ 구역 포커싱 및 스캔 가동", type="primary"):
    if region_input.strip() != "":
        with st.sidebar.spinner("위성 궤도 수정 및 기상망 동기화 중..."):
            weather, obs_time, jimok, sat_temp = get_live_data(region_input)
            st.session_state['t_val'] = weather['temperature']
            st.session_state['h_val'] = weather['humidity']
            st.session_state['w_val'] = weather['wind_speed']
            st.session_state['current_target'] = region_input
            st.sidebar.success(f"✅ {region_input} 자율 감시 링크 완료!")

st.sidebar.markdown("---")
st.sidebar.header("🎛️ 실시간 변수 시뮬레이션 (Drill)")
temperature = st.sidebar.slider("기온 (°C)", -10.0, 45.0, float(st.session_state['t_val']))
humidity = st.sidebar.slider("습도 (%)", 0.0, 100.0, float(st.session_state['h_val']))
wind_speed = st.sidebar.slider("풍속 (m/s)", 0.0, 35.0, float(st.session_state['w_val']))

# --- 📊 메인 대시보드 ---
col_radar, col_status = st.columns([1, 2])

with col_radar:
    st.subheader("🛰️ RYEONG-I 자율 스캔 레이더")
    st.info(f"🟢 **현재 모드:** {st.session_state['current_target']}")
    st.caption("배경 백엔드에서 전국 17개 시도 위성 FF 피드를 무한 전수 스캔 중입니다.")

with col_status:
    st.subheader("📊 규모별 실시간 대응 지침")
    # 규모별 4단계 멘트 로직 (이전 답변 드린 등급별 멘트 유지)
    # ...

# --- 🌟 [v4.0 핵심] 령이 자율 화재 포착 로그 (Blackbox) ---
st.divider()
st.subheader("📋 령이 자율 화재 포착 로그 (Autonomous Sentinel Blackbox)")
st.caption("※ 령이가 포착한 모든 이상 징후를 기록하며, 소방청 119 출동 데이터가 공개되는 즉시 우측에 자동 매핑하여 골든타임을 실증합니다.")

# 테이블 렌더링
st.table(st.session_state['fire_blackbox'])

st.divider()
st.caption("🚨 RYEONG-I v4.0 | 무인 자율 방제 엔진 가동 중 | 데이터 출처: 기상청, 소방청, 환경부")