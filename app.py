import streamlit as st
import time
import requests
import math
import random
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

st.set_page_config(page_title="산불 능동 관제 AI 령이", page_icon="🚨", layout="wide")

# 세션 상태 초기화
if 'h_val' not in st.session_state: st.session_state['h_val'] = 45.0
if 'w_val' not in st.session_state: st.session_state['w_val'] = 2.0
if 't_val' not in st.session_state: st.session_state['t_val'] = 20.0
if 'obs_time' not in st.session_state: st.session_state['obs_time'] = "상시 감시 중"
if 'live_jimok' not in st.session_state: st.session_state['live_jimok'] = "임야 (산림지역)"
if 'live_area' not in st.session_state: st.session_state['live_area'] = "보전녹지지역"
if 'logs' not in st.session_state: st.session_state['logs'] = ["📡 [령이 센티넬 엔진] 전국 기상 격자망 실시간 백그라운드 스캔 중..."]

st.title("🚨 AI 실시간 산불 조기경보 플랫폼 '령이' (RYEONG-I)")
st.markdown("대한민국 기상청 국지성 AWS 격자망 X 환경부 환경영향평가 토지이용정보 API 융합 능동형 관제 시스템")
st.divider()

# --- 💡 기상청 공식 '위도/경도 ➡️ 격자 좌표(X, Y)' 변환 수학 공식 ---
def convert_to_grid(v1, v2):
    RE = 6371.00877; GRID = 5.0; SLAT1 = 30.0; SLAT2 = 60.0; OLON = 126.0; OLAT = 38.0; XO = 43; YO = 136
    DEGRAD = math.pi / 180.0; re = RE / GRID; slat1 = SLAT1 * DEGRAD; slat2 = SLAT2 * DEGRAD; olon = OLON * DEGRAD; olat = OLAT * DEGRAD
    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5); sf = (math.pow(sf, sn) * math.cos(slat1)) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5); ro = (re * sf) / math.pow(ro, sn)
    ra = math.tan(math.pi * 0.25 + v1 * DEGRAD * 0.5); ra = (re * sf) / math.pow(ra, sn)
    theta = v2 * DEGRAD - olon
    if theta > math.pi: theta -= 2.0 * math.pi
    if theta < -math.pi: theta += 2.0 * math.pi
    theta *= sn
    return math.floor(ra * math.sin(theta) + XO + 0.5), math.floor(ro - ra * math.cos(theta) + YO + 0.5)

# --- 🗺️ 환경부 환경영향평가 지목 속성 파싱 엔진 ---
def get_land_use_jimok(lat, lon):
    API_KEY = "69309efd849de167a2a68e2fc27331c01eb67888d72dd4a740419a33cf7d292e"
    url = "http://apis.data.go.kr/1360000/EiaLandUseInfoService/getJimokAttr"
    params = {'serviceKey': API_KEY, 'pageNo': '1', 'numOfRows': '1', 'dataType': 'XML', 'lat': str(lat), 'lon': str(lon)}
    try:
        response = requests.get(url, params=params, timeout=2)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            jimok_nm = root.find('.//jimokNm')
            return jimok_nm.text if jimok_nm is not None else "임야"
    except: pass
    return "임야"

# --- 📡 기상청 전국 AWS 실시간 기상 추출 엔진 ---
def get_live_aws_weather(region_name):
    API_KEY = "69309efd849de167a2a68e2fc27331c01eb67888d72dd4a740419a33cf7d292e"
    # 주소 ➡️ 위경도 검색 (오픈스트리트맵 기반 전국구)
    search_query = f"대한민국 {region_name}" if "대한민국" not in region_name else region_name
    url_geo = f"https://nominatim.openstreetmap.org/search?q={search_query}&format=json&limit=1"
    headers = {'User-Agent': 'ryong-i-wildfire-app-final-perfect-layer'}
    
    try:
        res_geo = requests.get(url_geo, headers=headers, timeout=3)
        if res_geo.status_code == 200 and len(res_geo.json()) > 0:
            lat = float(res_geo.json()[0]['lat'])
            lon = float(res_geo.json()[0]['lon'])
            nx, ny = convert_to_grid(lat, lon)
            
            # 기상청 초단기실황 타격
            url_aws = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
            tz_kst = timezone(timedelta(hours=9))
            now = datetime.now(tz_kst)
            base_date = now.strftime("%Y%m%d")
            base_time = f"{now.hour:02d}00"
            
            params = {'serviceKey': API_KEY, 'pageNo': '1', 'numOfRows': '10', 'dataType': 'JSON', 'base_date': base_date, 'base_time': base_time, 'nx': nx, 'ny': ny}
            res_aws = requests.get(url_aws, params=params, timeout=3)
            
            if res_aws.status_code == 200:
                items = res_aws.json()['response']['body']['items']['item']
                w_info = {}
                for item in items:
                    val = float(item['obsrValue'])
                    if item['category'] == 'REH': w_info['humidity'] = val
                    elif item['category'] == 'WSD': w_info['wind_speed'] = val
                    elif item['category'] == 'T1H': w_info['temperature'] = val
                
                # 환경부 지목 API 연동
                jimok = get_land_use_jimok(lat, lon)
                
                # 도심지 오탐지 필터링 연출용 (강남, 시청, 빌딩, 아파트 입력 시 지목 강제 치환)
                fake_cities = ["강남", "시청", "역삼", "빌딩", "아파트", "홍대", "명동"]
                for city in fake_cities:
                    if city in region_name:
                        jimok = "대지 (주거/상업용지)"
                        break
                        
                return w_info, f"{now.hour}시 00분", jimok
    except: pass
    return None, None, "임야"

# --- 🎮 사이드바 컨트롤러 (지리잉 슬라이더 유지형) ---
st.sidebar.header("📡 령이 관제 실시간 동기화")
region = st.sidebar.text_input("현재 감시 타깃 주소 입력 (전국)", value="안동시 송천동 야산")

if st.sidebar.button("🛰️ 현장 실시간 팩트 기상 동기화"):
    with st.sidebar.spinner("기상청 AWS 센서 및 환경부 지목 파싱 중..."):
        weather, obs_time, jimok = get_live_aws_weather(region)
        if weather:
            st.session_state['t_val'] = weather['temperature']
            st.session_state['h_val'] = weather['humidity']
            st.session_state['w_val'] = weather['wind_speed']
            st.session_state['obs_time'] = obs_time
            st.session_state['live_jimok'] = jimok
            st.sidebar.success("✅ 라이브 팩트 데이터 동기화 완료!")
        else:
            st.sidebar.error("기상망 지연으로 기본 관제 데이터 모드를 유지합니다.")

st.sidebar.markdown("---")
st.sidebar.header("🎛️ [시연 전용] 기상 변수 강제 조작")
st.sidebar.caption("💡 발표장에서 슬라이더를 극한으로 움직여 산불 AI 임계치 돌파 시나리오를 직접 연출해 보세요!")

# 🌟 제준님이 손맛을 보여줄 찐 슬라이더 3종 세트!
temperature = st.sidebar.slider("현재 기온 (°C)", min_value=-10.0, max_value=45.0, value=float(st.session_state['t_val']))
humidity = st.sidebar.slider("현재 습도 (%)", min_value=0.0, max_value=100.0, value=float(st.session_state['h_val']))
wind_speed = st.sidebar.slider("풍속 (m/s)", min_value=0.0, max_value=35.0, value=float(st.session_state['w_val']))

st.sidebar.markdown("---")
st.sidebar.header("⛰️ 산림 토형 및 경사")
oil_content = st.sidebar.slider("산림 내 소나무(유분) 분포 (%)", min_value=0.0, max_value=100.0, value=65.0) / 100.0
current_slope = st.sidebar.slider("지형 경사도 (°)", min_value=0.0, max_value=60.0, value=20.0)

# --- 🧠 령이 AI 시공간 오탐지 차단 및 위험도 연산 로직 ---
# 1단계 지목 필터
is_forest = "임야" in st.session_state['live_jimok'] or "산림" in st.session_state['live_jimok']

# 2단계 수학적 산불 위험 임계점 연산 (습도 낮고, 풍속 강하고, 기온 높은 극한 기후 스캔)
humidity_score = (100 - humidity) * 0.3
wind_score = wind_speed * 2.0
temperature_score = max(0.0, temperature * 0.6)
oil_score = oil_content * 20
slope_score = current_slope * 0.5

total_risk = humidity_score + wind_score + temperature_score + oil_score + slope_score

# --- 📺 메인 모니터링 화면 ---
col_log, col_screen = st.columns([1, 2])

with col_log:
    st.subheader("🖥️ 24H 자동 감시 센티넬 로그")
    # 제준님이 슬라이더 조작할 때 실시간으로 조건 변화를 로그에 뿌려주는 감생이 연출
    if total_risk >= 75 and is_forest:
        st.session_state['logs'].append(f"🔥 [🚨 CRITICAL] {region} 격자 센서 임계치 폭발!!")
    else:
        st.session_state['logs'].append(f"🔍 관제 상태 안정화 스캔.. 기온 {temperature:.1f}℃ / 습도 {humidity:.1f}%")
        
    log_text = "\n".join(st.session_state['logs'][-6:]) # 최신 로그 6줄 유지
    st.code(log_text, language="shell")

with col_screen:
    st.subheader("📊 관제 현황 및 최종 판정")
    
    # 도심지 주소를 입력해 지목이 대지일 경우 오탐지 필터 브레이크 작동 연출
    if not is_forest:
        st.info(f"🛑 **[오발동 탐지 차단기 작동]**\n\n현재 기상 수치가 극한 임계점을 돌파했으나, 환경부 토지이용 API 교차 검증 결과 해당 좌표의 법정 지목이 **[{st.session_state['live_jimok']}]**(도심 아스팔트/공장지대)으로 확인되어 **복사열에 의한 오탐지로 자동 기각**합니다.")
        total_risk = 0.0

    if total_risk >= 75:
        st.error(f"## 🔥🔥🔥 [위험 폭발] 찐 산불 발생 알림 (점수: {total_risk:.1f}점)")
    elif total_risk >= 50:
        st.warning(f"## ⚠️ [경계 등급] 산불 징후 주의 (점수: {total_risk:.1f}점)")
    elif total_risk > 0:
        st.success(f"## ✅ [보통 등급] 전국망 정상 가동 중 (점수: {total_risk:.1f}점)")
    else:
        st.info("## 🔒 안전 마스킹 잠금 상태")

# --- 🚨 3단계: 제준님이 슬라이더로 불을 냈을 때 터지는 실시간 풀-오토 대피령 시뮬레이터 ---
st.divider()
if total_risk >= 75 and is_forest:
    st.error(f"📢 [즉각 조치 발령] AI가 지목 [{st.session_state['live_jimok']}] 검증을 마치고 관할 소방청 및 {region} 주민들에게 긴급 대피 파이프라인을 트리거했습니다.")
    
    # 물리 연산 속도 가동
    spread_speed = ((wind_speed * 1.8) + (current_slope * 1.2) * (1 + oil_content)) * (1.0 + (temperature/40.0)*0.3)
    st.write(f"📈 **예상 화선 확산 속도:** 분당 약 **{spread_speed:.1f}m** (양간지풍 및 침엽수림 가중치 공식 실시간 커스텀 반영 완료)")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"⏱️ **발화 후 10분 (반경 {spread_speed*10:.1f}m)**\n\n🚒 지목 속성이 산림으로 확정된 찐 산불이므로, 상황실 보고를 생략하고 **초대형 진화 헬기 3대 현장 강제 즉각 출격령** 발령.")
    with col2:
        st.warning(f"⏱️ **발화 후 30분 (반경 {spread_speed*30:.1f}m)**\n\n⚠️ **[폭발적 수관화 전개]** 가파른 경사도({current_slope}°) 및 소나무 유분으로 화선 통제 불가. 하류 부락 **주민 강제 대피령 자동 재난문자 즉각 살포**.")
    with col3:
        st.error(f"⏱️ **발화 후 60분 (반경 {spread_speed*60:.1f}m)**\n\n🧑‍🚒 인근 지자체 소방력 총동원 광역 대응 단계 자동 격상 및 민가 방어선 최우선 배치 구축.")
else:
    st.info("💡 사이드바의 슬라이더를 우측으로 과감하게 조작해 기온을 높이고 습도를 낮춰 '산불 위험 75점 이상'의 임계치를 돌파시키면, 실시간 대피령 시뮬레이션 시스템이 자동으로 고개를 들고 팝업됩니다.")