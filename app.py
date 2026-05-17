import streamlit as st
import time
import requests
import math
from datetime import datetime

st.set_page_config(page_title="산불 예방 AI 령이", page_icon="🌲", layout="wide")

st.title("🌲 산불 예방 및 대응 예측 AI '령이' (RYEONG-I)")
st.markdown("선진국 대형산불 대응 사례 모티브 및 대한민국 대형산불 역사 데이터 기반 예측 시스템")
st.divider()

# --- 💡 기상청 공식 '위도/경도 ➡️ 격자 좌표(X, Y)' 변환 수학 공식 ---
def convert_to_grid(v1, v2):
    RE = 6371.00877  # 지구 반경(km)
    GRID = 5.0       # 격자 간격(km)
    SLAT1 = 30.0     # 투영 위도1(degree)
    SLAT2 = 60.0     # 투영 위도2(degree)
    OLON = 126.0     # 기준점 경도(degree)
    OLAT = 38.0      # 기준점 위도(degree)
    XO = 43          # 기준점 X좌표(GRID)
    YO = 136         # 기준점 Y좌표(GRID)

    DEGRAD = math.pi / 180.0
    
    re = RE / GRID
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = (math.pow(sf, sn) * math.cos(slat1)) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = (re * sf) / math.pow(ro, sn)
    
    ra = math.tan(math.pi * 0.25 + v1 * DEGRAD * 0.5)
    ra = (re * sf) / math.pow(ra, sn)
    theta = v2 * DEGRAD - olon
    if theta > math.pi: theta -= 2.0 * math.pi
    if theta < -math.pi: theta += 2.0 * math.pi
    theta *= sn
    
    x = math.floor(ra * math.sin(theta) + XO + 0.5)
    y = math.floor(ro - ra * math.cos(theta) + YO + 0.5)
    return x, y

# --- 💡 주소 텍스트를 위도/경도로 바꿔주는 무료 지오코딩 엔진 ---
def get_lat_lon(location_text):
    # 전세계 오픈 주소 검색 API 활용 (별도 인증키 필요 없음)
    url = f"https://nominatim.openstreetmap.org/search?q={location_text}&format=json&limit=1"
    headers = {'User-Agent': 'ryong-i-wildfire-app'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200 and len(response.json()) > 0:
            result = response.json()[0]
            return float(result['lat']), float(result['lon'])
    except:
        return None, None
    return None, None

# --- 📡 통합 실시간 데이터 패치 엔진 ---
def get_realtime_weather_global(region_name):
    API_KEY = "69309efd849de167a2a68e2fc27331c01eb67888d72dd4a740419a33cf7d292e"
    
    # 1단계: 주소명에서 위도, 경도 추출
    lat, lon = get_lat_lon(region_name)
    if not lat or not lon:
        return None, None, None # 주소 못 찾음 에러 방지
        
    # 2단계: 위경도를 기상청 격자 X, Y로 실시간 수학 공식 변환
    nx, ny = convert_to_grid(lat, lon)

    now = datetime.now()
    base_date = now.strftime("%Y%m%d")
    if now.minute < 30:
        base_time = f"{now.hour - 1:02d}00" if now.hour > 0 else "2300"
    else:
        base_time = f"{now.hour:02d}00"

    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    params = {'serviceKey': API_KEY, 'pageNo': '1', 'numOfRows': '10', 'dataType': 'JSON', 'base_date': base_date, 'base_time': base_time, 'nx': nx, 'ny': ny}
    
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            items = data['response']['body']['items']['item']
            weather_info = {}
            for item in items:
                if item['category'] == 'REH': weather_info['humidity'] = float(item['obsrValue'])
                elif item['category'] == 'WSD': weather_info['wind_speed'] = float(item['obsrValue'])
            return weather_info, nx, ny
    except: 
        return None, nx, ny
    return None, nx, ny

# --- 사이드바 UI 구성 ---
st.sidebar.header("📊 전국의령이 환경 데이터")
region = st.sidebar.text_input("분석 대상 지역명 (예: 강릉, 홍성, 울진, 제주)", value="안동시 임하면")

if st.sidebar.button("📡 전국 실시간 날씨 동기화"):
    with st.sidebar.spinner(f"🗺️ '{region}' 위치 분석 후 기상청 노드 동기화 중..."):
        weather, calc_x, calc_y = get_realtime_weather_global(region)
        if weather:
            st.session_state['humidity'] = weather['humidity']
            st.session_state['wind_speed'] = weather['wind_speed']
            st.sidebar.success(f"✅ {region} (격자좌표: X={calc_x}, Y={calc_y}) 실시간 연동 성공!")
        else:
            # 주소는 맞는데 기상청 승인 지연 시 안전장치용 가상 시뮬레이션 데이터 매칭
            st.session_state['humidity'] = 19.0
            st.session_state['wind_speed'] = 22.5
            st.sidebar.warning(f"⚠️ 기상청 서버 매칭 대기 중으로, {region}(X={calc_x if calc_x else 97}, Y={calc_y if calc_y else 95}) 가상 시나리오 수치로 우회 가동합니다.")

if 'humidity' not in st.session_state: st.session_state['humidity'] = 25.0
if 'wind_speed' not in st.session_state: st.session_state['wind_speed'] = 12.0

humidity = st.sidebar.slider("현재 습도 (%)", min_value=0.0, max_value=100.0, value=float(st.session_state['humidity']), key="h_slider")
wind_speed = st.sidebar.slider("풍속 (m/s)", min_value=0.0, max_value=30.0, value=float(st.session_state['wind_speed']), key="w_slider")
oil_content = st.sidebar.slider("산림 내 유분 분포 (%)", min_value=0.0, max_value=100.0, value=65.0) / 100.0
slope = st.sidebar.slider("지형 경사도 (°)", min_value=0.0, max_value=60.0, value=25.0)

# 위험도 점수 계산
humidity_score = (100 - humidity) * 0.3
wind_score = wind_speed * 2.0
oil_score = oil_content * 30
slope_score = slope * 0.5
total_risk = humidity_score + wind_score + oil_score + slope_score

# --- 역사적 대형 산불 기상 매칭 알고리즘 (임계점 감지) ---
matched_fire = None
if humidity <= 20 and 4 <= wind_speed <= 15: matched_fire = "hongseong"
if humidity <= 25 and wind_speed >= 15: matched_fire = "gangneung"
if humidity <= 22 and wind_speed >= 19: matched_fire = "andong_uiseong"

# 화면 출력부
col1, col2 = st.columns(2)
with col1:
    st.subheader(f"📍 {region} 분석 결과")
    if total_risk >= 75: st.error(f"### 🔥 심각 등급 (점수: {total_risk:.1f}점)")
    elif total_risk >= 50: st.warning(f"### ⚠️ 경계 등급 (점수: {total_risk:.1f}점)")
    else: st.success(f"### ✅ 보통 등급 (점수: {total_risk:.1f}점)")

with col2:
    st.subheader("📋 입력된 환경 데이터 현황")
    st.text(f"• 기상: 습도 {humidity}% / 풍속 {wind_speed}m/s")
    st.text(f"• 산림 및 지형: 유분 {oil_content*100:.0f}% / 경사도 {slope}°")

# 역사 데이터 매칭 알림창 팝업
if matched_fire:
    st.divider()
    if matched_fire == "hongseong":
        st.info("🚨 **[역사적 산불 데이터 매칭]** 현재 기상 조건은 **2023년 홍성 대형산불** 당시와 매우 유사합니다. (습도 20% 이하, 순간풍속 10~15m/s 지형풍)")
    elif matched_fire == "gangneung":
        st.error("💀 **[⚠️ 최악의 재난 경보]** 현재 기상 조건은 **2023년 강릉 난곡동 대형산불** 당시와 일치합니다. (태풍급 양간지풍 순간풍속 30m/s 이상, 강풍형 산불)")
    elif matched_fire == "andong_uiseong":
        st.error("🔥 **[⚠️ 초고속 확산 경보]** 현재 기상 조건은 **2025년 의성·안동 대형산불** 당시의 최악의 기후 조건과 일치합니다. (습도 15~22%, 돌풍 19.7~25.4m/s, 역사상 가장 빠른 확산 속도 기록)")

st.divider()
st.subheader("🚨 화재 발생 시 예상 피해 및 최적 대응 대책 수립")

if total_risk < 45:
    st.info("현재 위험도 점수가 낮아 대형 확산 시뮬레이션을 가동하지 않습니다.")
else:
    if st.button("🔥 가상 화재 시뮬레이션 가동"):
        spread_speed = (wind_speed * 1.8) + (slope * 1.2) * (1 + oil_content)
        if matched_fire == "andong_uiseong": spread_speed = max(spread_speed, 136.6)
            
        st.write(f"📈 **예상 산불 확산 속도:** 분당 약 **{spread_speed:.1f}m**")
        
        time_steps = [10, 30, 60]
        for idx, minutes in enumerate(time_steps):
            distance = spread_speed * minutes
            time.sleep(0.3)
            
            if minutes == 10:
                if matched_fire == "hongseong":
                    action = "🚒 **[실전 매뉴얼 - 홍성 모티브]** 축사 및 민가 밀집 지형입니다. 산림 내부 진화보다 '연소 확대 방지(민가 방어선 구축)'를 1순위 목표로 소방차를 전면 배치하십시오. 지자체는 지형풍을 감안하여 산림청에 진화 헬기를 즉시 SOS 요청하고, 군청 전 직원 비상소집령 예고 문자를 송출하십시오."
                elif matched_fire == "gangneung":
                    action = "❌ **[실전 매뉴얼 - 강릉 모티브] 태풍급 양간지풍으로 진화 헬기 이륙 절대 불가!** 초기 10분은 오직 지상 주민 대피에 올인해야 합니다. 즉시 경포동·난곡동 일대 및 관광객 대상 강제 대피령 재난문자를 즉각 발송하고, 소방청 상황실은 강원 관할을 넘어 전국 단위로 소방력을 모으는 '전국 소방동원령' 가동 준비에 착수하십시오."
                elif matched_fire == "andong_uiseong":
                    action = "🚨 **[실전 매뉴얼 - 의성·안동 모티브] 역사상 가장 빠른 확산 속도(시간당 8.2km) 감지!** 현장 도착 전이라도 119상황실은 연기 규모를 보고 즉시 관할 전 인력을 동원하는 '대응 1단계'를 선제 발령하십시오. 소방은 경로 상의 요양원, 마을회관 등 취약시설 위치를 파악하여 인명 구조 임무를 최우선 시달하고, 지자체는 부군수/부시장 주재 재난안전대책본부를 즉시 가동하여 이장단 연락망으로 긴급 마을 대피 방송을 지시하십시오."
                else:
                    action = f"🚒 **일반 초동 조치 가동.** 풍속 {wind_speed}m/s로 지상/공중 합동 진화가 가능하므로 진화 헬기 투입 지시 및 산림 인접 민가 방화벽 배치를 점검하십시오."
            elif minutes == 30:
                if slope >= 30 or oil_content >= 0.7:
                    action = f"🪓 **비상! 폭발적 화선 확산 상황.** 현재 경사도({slope}°)와 유분 분포({oil_content*100:.0f}%)가 매우 높아 '침엽수림 수관화' 및 '계곡 풍동 효과'가 동시 발생 중입니다. 1차 방화선 구축 조를 즉시 후퇴시키고, 예상 경로 {distance:.0f}m 앞 지점의 대형 임도와 강을 거점으로 삼아 2차 저지선을 대대적으로 재구축하십시오."
                else:
                    action = f"🪓 **1차 방화선 구축 단계.** 확산 속도를 고려하여 화두 전방 저지선 구축. 내화수림대 유휴지와 소방 용수 공급로를 선점하여 {region} 일대 산림 확산을 저지하기 위한 맞춤형 차단벽을 형성하십시오."
            else:
                if total_risk >= 85:
                    action = f"💀 **대형산불 통제 불능 단계 경보.** 위험 점수가 {total_risk:.1f}점으로 재앙적 수준입니다. 화선이 반경 {distance/1000:.1f}km까지 확장되어 일반 진화 방식으로는 대응이 불가능합니다. 야간 확산에 대비하여 소방력을 주요 국가 기간시설 및 민가 방어에 전면 재배치하고, 확산 예측 경로의 산림을 미리 태워버리는 **'선진국형 맞불 작전(Backfire)'** 구역을 산출하여 진입로를 전면 통제하십시오."
                else:
                    action = f"🧑‍🚒 **광역 대응 단계 가동.** 인근 시·도 소방력 응원 요청 완료. {region} 일대 화재 확산 차단을 위한 맞불 저지선을 형성하고, 야간 산불로의 전환을 막기 위해 열화상 드론을 투입하여 실시간 화선 지도를 제작, 진화 대원들을 적재적소에 배치하십시오."

            st.info(f"⏱️ **발화 후 {minutes}분** | 예상 확산 범위: 반경 **{distance:.1f}m**\n\n{action}")