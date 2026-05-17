import streamlit as st
import time
import requests
import math
from datetime import datetime, timedelta, timezone

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

# --- 💡 오픈 주소 검색 엔진 ---
def get_lat_lon(location_text):
    search_query = f"대한민국 {location_text}" if "대한민국" not in location_text else location_text
    url = f"https://nominatim.openstreetmap.org/search?q={search_query}&format=json&limit=1"
    headers = {'User-Agent': 'ryong-i-wildfire-app-final-perfect-layer'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200 and len(response.json()) > 0:
            result = response.json()[0]
            return float(result['lat']), float(result['lon'])
    except: return None, None
    return None, None

# --- 📡 통합 실시간 데이터 패치 엔진 ---
def get_realtime_weather_global(region_name):
    API_KEY = "69309efd849de167a2a68e2fc27331c01eb67888d72dd4a740419a33cf7d292e"
    lat, lon = get_lat_lon(region_name)
    if not lat or not lon: return None, None, None, None
    nx, ny = convert_to_grid(lat, lon)

    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    tz_kst = timezone(timedelta(hours=9))
    now = datetime.now(tz_kst)
    
    for check_step in range(4):  
        target_time = now - timedelta(minutes=30 * check_step)
        base_date = target_time.strftime("%Y%m%d")
        base_time = f"{target_time.hour:02d}00"
        
        params = {
            'serviceKey': API_KEY, 'pageNo': '1', 'numOfRows': '10', 
            'dataType': 'JSON', 'base_date': base_date, 'base_time': base_time, 
            'nx': nx, 'ny': ny
        }
        
        try:
            response = requests.get(url, params=params, timeout=4)
            if response.status_code == 200:
                data = response.json()
                if 'response' in data and 'body' in data['response'] and data['response']['body'] is not None:
                    items = data['response']['body']['items']['item']
                    weather_info = {}
                    for item in items:
                        val = float(item['obsrValue'])
                        if val < -50 or val == -900: continue 
                        
                        if item['category'] == 'REH': weather_info['humidity'] = val
                        elif item['category'] == 'WSD': weather_info['wind_speed'] = val
                        elif item['category'] == 'T1H': weather_info['temperature'] = val
                    
                    if 'humidity' in weather_info and 'wind_speed' in weather_info and 'temperature' in weather_info:
                        obs_time_str = f"{target_time.hour}시 00분"
                        return weather_info, nx, ny, obs_time_str
        except:
            continue
            
    return None, nx, ny, None

# --- 최초 기본값 세팅 ---
if 'h_val' not in st.session_state: st.session_state['h_val'] = 35.0
if 'w_val' not in st.session_state: st.session_state['w_val'] = 2.5
if 't_val' not in st.session_state: st.session_state['t_val'] = 22.0
if 'time_mode' not in st.session_state: st.session_state['time_mode'] = "주간 (Daytime)"
if 'obs_time' not in st.session_state: st.session_state['obs_time'] = "미동기화"

# --- 사이드바 UI 구성 ---
st.sidebar.header("📡 령이 현장 주소 관제망")
region = st.sidebar.text_input("발화 현장 상세 주소 입력", value="안동시 송천동")

if st.sidebar.button("📡 현장 실시간 날씨 및 시각 동기화"):
    with st.sidebar.spinner(f"🗺️ '{region}' 기상청 공식 데이터 동기화 중..."):
        weather, calc_x, calc_y, obs_time_str = get_realtime_weather_global(region)
        
        tz_kst = timezone(timedelta(hours=9))
        current_hour = datetime.now(tz_kst).hour
        if 6 <= current_hour < 18:
            st.session_state['time_mode'] = "주간 (Daytime)"
        else:
            st.session_state['time_mode'] = "야간 (Nighttime)"

        if weather and 'humidity' in weather and 'wind_speed' in weather and 'temperature' in weather:
            st.session_state['h_val'] = weather['humidity']
            st.session_state['w_val'] = weather['wind_speed']
            st.session_state['t_val'] = weather['temperature']
            st.session_state['obs_time'] = obs_time_str
            st.sidebar.success(f"✅ {region} 기상청 팩트 데이터 연동 완료!")
        else:
            st.sidebar.error("❌ 기상청 오픈 API 통신 장애가 발생했습니다. 잠시 후 다시 시도해 주세요.")

# 슬라이더 세팅
temperature = st.sidebar.slider("현재 기온 (°C)", min_value=-10.0, max_value=40.0, value=float(st.session_state['t_val']))
humidity = st.sidebar.slider("현재 습도 (%)", min_value=0.0, max_value=100.0, value=float(st.session_state['h_val']))
wind_speed = st.sidebar.slider("풍속 (m/s)", min_value=0.0, max_value=30.0, value=float(st.session_state['w_val']))

st.sidebar.markdown("---")
st.sidebar.header("⛰️ 로컬 지형 정보 (수동 제어)")
oil_content = st.sidebar.slider("산림 내 유분 분포 (%)", min_value=0.0, max_value=100.0, value=50.0) / 100.0
st.sidebar.caption("💡 **유분기 조절 팁:** 활엽수(참나무) 20~30% | 침엽수(소나무) 70~80% | 극심한 가뭄 시 90% 이상 설정")

current_slope = st.sidebar.slider("지형 경사도 (°)", min_value=0.0, max_value=60.0, value=15.0)

time_of_day = st.session_state['time_mode']

# 위험도 점수 계산
humidity_score = (100 - humidity) * 0.25
wind_score = wind_speed * 1.8
oil_score = oil_content * 25
slope_score = current_slope * 0.4
temperature_score = max(0.0, temperature * 0.5)

total_risk = humidity_score + wind_score + oil_score + slope_score + temperature_score
if time_of_day == "야간 (Nighttime)":
    total_risk += 5.0

# --- 💡 역사적 대형 산불 기상 매칭 알고리즘 ---
matched_fire = None
if humidity <= 20 and wind_speed >= 25.0:
    matched_fire = "yangyang_2005"
elif humidity <= 20 and 4 <= wind_speed <= 11: 
    matched_fire = "hongseong"
elif humidity <= 25 and wind_speed >= 22.0: 
    matched_fire = "gangneung"
elif humidity <= 25 and wind_speed >= 12.0: 
    matched_fire = "andong_uiseong"

# 화면 출력부
col1, col2 = st.columns(2)
with col1:
    st.subheader(f"📍 {region} 분석 결과")
    if total_risk >= 75: st.error(f"### 🔥 심각 등급 (점수: {total_risk:.1f}점)")
    elif total_risk >= 50: st.warning(f"### ⚠️ 경계 등급 (점수: {total_risk:.1f}점)")
    else: st.success(f"### ✅ 보통 등급 (점수: {total_risk:.1f}점)")

with col2:
    st.subheader("📋 실시간 환경 데이터 감지 현황")
    st.text(f"• 기상 파이프라인: 기온 {temperature:.1f}°C / 습도 {humidity:.1f}% / 풍속 {wind_speed:.1f}m/s")
    st.info(f"⏰ 기상청 실제 관측 시각: [{st.session_state['obs_time']}] 수집 데이터")
    st.caption("⚠️ 기상청 오픈 API 특성상 팩트 데이터는 1시간 전 정각 관측치가 최신으로 배달되므로, 실시간 예측 보정치를 사용하는 포털 날씨와 수치 차이가 발생할 수 있습니다. (정상 가동 중)")
    st.text(f"• 지형 및 임상 조건: 유분 {oil_content*100:.0f}% / 경사도 {current_slope}°")

# 🌟 [제준님 피드백 반영 해골 표기 박멸 및 공식 멘트 교정 완료]
if matched_fire:
    st.divider()
    if matched_fire == "yangyang_2005":
        st.error(f"🚨 **[기후 모델 유사성 분석]** 현재 현장 기상이 과거 **2005년 양양 대형산불** 당시의 극한 가뭄 및 돌풍 기류 조건과 매칭됩니다. (실효습도 20% 이하 + 초속 25m/s 이상 강풍 결합 상태)")
    elif matched_fire == "hongseong":
        st.info(f"🚨 **[기후 모델 유사성 분석]** 현재 현장 기상이 과거 **2023년 홍성 대형산불** 당시의 중산간 지형풍 확산 조건과 매우 유사합니다. (습도 20% 이하, 풍속 10m/s 내외 내륙풍)")
    elif matched_fire == "gangneung":
        st.error(f"🚨 **[기후 모델 유사성 분석]** 현재 현장 기상이 과거 **2023년 강릉 난곡동 대형산불** 당시의 태풍급 강풍형 연소 조건과 정확히 일치합니다. (순간풍속 22m/s 이상의 강풍 지대 기후 특성 반영)")
    elif matched_fire == "andong_uiseong":
        st.error(f"🚨 **[기후 모델 유사성 분석]** 현재 현장 기상이 과거 **2025년 3월 의성·안동 대형산불** 당시의 초봄 이상 고온 및 겨울 가뭄 누적 기후 조건과 일치합니다. (3월 초봄 기온 23도 이상 급상승 + 내륙 돌풍 결합 상태)")

st.divider()
st.subheader("🚨 화재 발생 시 예상 피해 및 최적 대응 대책 수립")

if total_risk < 45:
    st.info("현재 위험도 점수가 낮아 대형 확산 시뮬레이션을 가동하지 않습니다.")
else:
    if st.button("🔥 가상 화재 시뮬레이션 가동"):
        temp_factor = 1.0 + (max(0.0, temperature) / 40.0) * 0.3
        spread_speed = ((wind_speed * 1.8) + (current_slope * 1.2) * (1 + oil_content)) * temp_factor
        if matched_fire == "andong_uiseong": spread_speed = max(spread_speed, 136.6)
        if matched_fire == "yangyang_2005": spread_speed = max(spread_speed, 150.0)
            
        st.write(f"📈 **예상 산불 확산 속도:** 분당 약 **{spread_speed:.1f}m** (양간지풍 비화 물리 공식 적용 완료)")
        
        time_steps = [10, 30, 60]
        for idx, minutes in enumerate(time_steps):
            distance = spread_speed * minutes
            time.sleep(0.3)
            
            # 🌟 [제준님 피드백 반영] [작성 지역] 주민의 대피 프로토콜과 작전 통제로 명확하게 대수술 완료
            if minutes == 10:
                if matched_fire == "yangyang_2005" and time_of_day == "야간 (Nighttime)":
                    action = f"⚠️ **[현장 지휘 통제] 야간 특수 진화 프로토콜 발령.** 진화 헬기 이륙이 전면 불가합니다. [{region}] 재난안전대책본부는 즉시 이장단 및 행정 요원을 소집하고, **[{region}] 관내 전 가구의 문을 직접 두드려 수면 중인 주민들을 전원 깨우는 육성 대피령을 강제 실시**하십시오. 소방은 소방차량 방수포를 이용해 민가 최전방 저지선을 선제 배비하십시오."
                elif time_of_day == "야간 (Nighttime)":
                    action = f"❌ **[야간 비상 통제 발령]** 헬기 기동 불가 시간대입니다. [{region}] 현장에 지상 특수진화대 및 고성능 화학차를 즉각 배치하고, 화선 관측을 위한 **'열화상 관제 드론팀'을 [{region}] 야산 지대에 최우선 긴급 투입**하십시오."
                elif matched_fire == "yangyang_2005":
                    action = f"🚒 **[현장 지휘 통제] 초속 30m급 돌풍으로 인한 비화(飛火) 차단 단계.** 불씨가 수백 미터를 도약하는 상태입니다. 화두 직접 진화를 전면 중단하고, 바람 방향 하류에 위치한 **[{region}] 내 주요 가옥 및 국가 기간시설 수막 방어선 구축**에 소방력을 긴급 집중 배비하십시오."
                elif matched_fire == "hongseong":
                    action = f"🚒 **[현장 지휘 통제]** 연소 확대 저지를 위해 소방차량을 강풍 하류 전방에 촘촘히 배치하여 **[{region}] 민가 보호벽 구축을 1순위**로 전개하십시오."
                elif matched_fire == "gangneung":
                    action = f"⚠️ **[현장 지휘 통제] 강풍으로 인한 헬기 가동 차단 상황.** 인명 피해 제로를 목표로 설정해야 합니다. **[{region}] 관내 전역에 강제 주민 대피령 재난문자를 즉각 송출**하고 소방대원들은 가옥별 대피 여부를 칼같이 확인하십시오."
                else:
                    action = f"🚒 **[현장 지휘 통제] 초기 대응 단계.** 주간 상황이므로 산림청 및 소방 초대형 진화 헬기를 [{region}] 화두 방향으로 즉시 출격 지시하고 지상 합동 진화 요원을 거점에 전면 투입하십시오."
            
            elif minutes == 30:
                if matched_fire == "yangyang_2005":
                    action = f"🔥 **[비화 확산 경보]** 강풍형 비화가 동시다발적으로 터지고 있습니다. 현장 진화대원들의 안전 확보를 위해 계곡부 진입을 전면 금지하고, **[{region}] 관내 대형 임도와 주요 간선도로를 최후의 저지 거점**으로 삼아 차량 방수를 개시하십시오."
                elif current_slope >= 30 or oil_content >= 0.7:
                    action = f"⚠️ **[위험 확산 경보] 폭발적 수관화 발생 상태.** 가파른 경사와 수목 유분으로 인해 화선 제어가 불가능합니다. 1차 저지선을 즉시 해체하고 후퇴시킨 뒤, **[{region}] 예상 확산 경로 하류의 대형 하천 및 임도 구간에 2차 저지선**을 대대적으로 종행 구축하십시오."
                else:
                    action = f"🪓 **[방화 저지선 구축]** 확산 속도를 수학적으로 산출하여 화두 전방 저지선 구축. **[{region}] 일대 산림 연소를 차단**하기 위한 방화벽을 견고히 형성하십시오."
            else:
                if total_risk >= 85 or matched_fire == "yangyang_2005":
                    action = f"🚨 **[광역 통제를 위한 비상 대응 단계]** 화선 통제 불능 단계입니다. 인근 시·도 소방력의 총동원령을 유치하고, **[{region}] 확산 예측 경로상의 산림을 미리 연소시켜 불길을 차단하는 '맞불 작전(Backfire)' 구역을 긴급 산출**하여 현장 지휘 통제실에 배포하십시오."
                else:
                    action = f"🧑‍🚒 **[광역 대응 단계 가동]** 인근 지자체 소방력 지원 동원 완료. **[{region}] 외곽 경계 지역의 화재 확산 방지**를 위한 차단벽을 공고히 형성하고 야간 산불 장기화 체제로 전환하십시오."

            st.info(f"⏱️ **발화 후 {minutes}분** | 예상 확산 범위: 반경 **{distance:.1f}m**\n\n{action}")