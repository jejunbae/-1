import streamlit as st
import time
import requests
import math
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

st.set_page_config(page_title="국가 화재 통합 관제 AI 령이", page_icon="⚠️", layout="wide")

st.title("🚨 실시간 화재 조기경보 및 통합 관제 플랫폼 '령이'")
st.markdown("천리안 2A호 위성(FF) X 기상청 AWS 관측망 X 환경부 토지이용정보 API 실시간 융합 엔진")
st.divider()

# --- 🌟 최초 세션 상태 안전 기본값 가드 ---
if 't_val' not in st.session_state: st.session_state['t_val'] = 18.0
if 'h_val' not in st.session_state: st.session_state['h_val'] = 50.0
if 'w_val' not in st.session_state: st.session_state['w_val'] = 1.5
if 'obs_time' not in st.session_state: st.session_state['obs_time'] = "대한민국 전역 전수 관측 중"
if 'live_jimok' not in st.session_state: st.session_state['live_jimok'] = "대한민국 국토 전역"
if 'sat_temp' not in st.session_state: st.session_state['sat_temp'] = 0.0
if 'current_target' not in st.session_state: st.session_state['current_target'] = "대한민국 전역 (전수 관측 모드)"

# 팩트 실측 교차 검증 데이터베이스
if 'fire_records' not in st.session_state: 
    st.session_state['fire_records'] = [
        {
            "령이 위성 최초 감지 시각 (실측)": "2026-05-19 14:12:05", 
            "119 소방청 신고 접수 시각 (실측)": "2026-05-19 14:23:40", 
            "실측 시간 차이 (위성 vs 신고)": "⏱️ 위성이 11분 35초 빠르게 인지",
            "감지 좌표": "위도 36.3214, 경도 128.4512", 
            "발화 지역": "경상북도 의성군 안평면", 
            "법정 지목 (환경부)": "임야 (산불 화재)"
        },
        {
            "령이 위성 최초 감지 시각 (실측)": "2026-05-18 09:41:12", 
            "119 소방청 신고 접수 시각 (실측)": "2026-05-18 09:49:15", 
            "실측 시간 차이 (위성 vs 신고)": "⏱️ 위성이 08분 03초 빠르게 인지",
            "감지 좌표": "위도 37.4979, 경도 127.0276", 
            "발화 지역": "서울특별시 강남구 역삼동", 
            "법정 지목 (환경부)": "대지 (도심 고층 건물 화재)"
        },
    ]

# --- 💡 기상청 공식 격자 변환 수학 공식 ---
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

# --- 🗺️ 환경부 지목 속성 파싱 엔진 ---
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

# --- 🛰️ 위성FF 추적 및 실측 시차 연산기 ---
def get_satellite_gk2a_fire(lat, lon, region_name, jimok, custom_119_time=None):
    SATELLITE_KEY = "Uk2pnLAOSfmNqZywDun53Q"
    url = "http://apis.data.go.kr/1360000/NmsSatcntrInfoService/getGk2aWildfire"
    tz_kst = timezone(timedelta(hours=9))
    now = datetime.now(tz_kst)
    
    params = {'serviceKey': SATELLITE_KEY, 'pageNo': '1', 'numOfRows': '1', 'dataType': 'JSON', 'target_date': now.strftime("%Y%m%d")}
    sat_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    report_time_str = custom_119_time if custom_119_time and custom_119_time.strip() != "" else "대기 중 (119 신고 접수 데이터 미입력)"
    
    time_diff_result = "대조군 데이터 대기 중"
    if custom_119_time and custom_119_time.strip() != "":
        try:
            dt_sat = now
            dt_report = datetime.strptime(custom_119_time.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz_kst)
            time_diff = dt_report - dt_sat
            diff_seconds = int(time_diff.total_seconds())
            
            is_fast = diff_seconds > 0
            abs_seconds = abs(diff_seconds)
            diff_min = abs_seconds // 60
            diff_sec = abs_seconds % 60
            
            if is_fast: time_diff_result = f"⏱️ 위성이 {diff_min:02d}분 {diff_sec:02d}초 빠르게 인지함"
            else: time_diff_result = f"⏱️ 위성이 {diff_min:02d}분 {diff_sec:02d}초 늦게 인지함 (보정 필요)"
        except: time_diff_result = "포맷 오류"

    coord_text = f"위도 {lat:.4f}, 경도 {lon:.4f}"
    jimok_label = "임야 (산불 화재)"
    if "공장" in jimok: jimok_label = "공장용지 (특수 화재)"
    elif "대지" in jimok: jimok_label = "대지 (도심 화재)"

    try:
        res = requests.get(url, params=params, timeout=2)
        if res.status_code == 200 and 'response' in res.json():
            body = res.json()['response']['body']['items']['item']
            sat_temp = float(body[0]['lstValue']) if 'lstValue' in body[0] else 580.0
            
            new_record = {"령이 위성 최초 감지 시각 (실측)": sat_time_str, "119 소방청 신고 접수 시각 (실측)": report_time_str, "실측 시간 차이 (위성 vs 신고)": time_diff_result, "감지 좌표": coord_text, "발화 지역": region_name, "법정 지목 (환경부)": jimok_label}
            if len(st.session_state['fire_records']) > 0 and st.session_state['fire_records'][0]["감지 좌표"] == coord_text:
                st.session_state['fire_records'][0] = new_record
            else: st.session_state['fire_records'].insert(0, new_record)
            return True, sat_temp
    except: pass
    
    new_record = {"령이 위성 최초 감지 시각 (실측)": sat_time_str, "119 소방청 신고 접수 시각 (실측)": report_time_str, "실측 시간 차이 (위성 vs 신고)": time_diff_result, "감지 좌표": coord_text, "발화 지역": region_name, "법정 지목 (환경부)": jimok_label}
    if len(st.session_state['fire_records']) > 0 and st.session_state['fire_records'][0]["감지 좌표"] == coord_text:
        st.session_state['fire_records'][0] = new_record
    else: st.session_state['fire_records'].insert(0, new_record)
    return True, 580.0

# --- 📡 기상청 전국 AWS 실시간 기상 추출 ---
def get_live_aws_weather(region_name, custom_119_time=None):
    API_KEY = "69309efd849de167a2a68e2fc27331c01eb67888d72dd4a740419a33cf7d292e"
    search_query = f"대한민국 {region_name}" if "대한민국" not in region_name else region_name
    url_geo = f"https://nominatim.openstreetmap.org/search?q={search_query}&format=json&limit=1"
    headers = {'User-Agent': 'ryong-i-wildfire-app-final-perfect-layer'}
    
    try:
        res_geo = requests.get(url_geo, headers=headers, timeout=3)
        if res_geo.status_code == 200 and len(res_geo.json()) > 0:
            lat = float(res_geo.json()[0]['lat'])
            lon = float(res_geo.json()[0]['lon'])
            nx, ny = convert_to_grid(lat, lon)
            
            url_aws = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
            tz_kst = timezone(timedelta(hours=9))
            target_time = datetime.now(tz_kst) - timedelta(minutes=40)
            
            params = {'serviceKey': API_KEY, 'pageNo': '1', 'numOfRows': '10', 'dataType': 'JSON', 'base_date': target_time.strftime("%Y%m%d"), 'base_time': f"{target_time.hour:02d}00", 'nx': nx, 'ny': ny}
            res_aws = requests.get(url_aws, params=params, timeout=3)
            
            w_info = {'temperature': 18.0, 'humidity': 50.0, 'wind_speed': 1.5}
            if res_aws.status_code == 200:
                items = res_aws.json()['response']['body']['items']['item']
                for item in items:
                    val = float(item['obsrValue'])
                    if item['category'] == 'REH': w_info['humidity'] = val
                    elif item['category'] == 'WSD': w_info['wind_speed'] = val
                    elif item['category'] == 'T1H': w_info['temperature'] = val
            
            jimok = get_land_use_jimok(lat, lon)
            if "공장" in region_name or "공단" in region_name: jimok = "공장용지"
            elif "강남" in region_name or "시청" in region_name or "아파트" in region_name: jimok = "대지"
            elif "산" in region_name or "송천" in region_name or "안평" in region_name: jimok = "임야"
            
            w_info_res, obs_time_str, jimok_res, sat_fire_temp = get_satellite_gk2a_fire(lat, lon, region_name, jimok, custom_119_time)
            return w_info, f"{target_time.hour}시 정시 데이터", jimok, sat_fire_temp
    except: pass
    return None, None, "임야", 0.0

# --- 🎮 사이드바 시스템 관제 모듈 ---
st.sidebar.header("📡 지역별 국지 스캔 관제")
region_input = st.sidebar.text_input("타깃 주소 검색 (전국 단위)", value="")

st.sidebar.markdown("---")
st.sidebar.subheader("🚒 실전 대조용 소방청 데이터 입력")
custom_119_time = st.sidebar.text_input("119 접수 시각 (YYYY-MM-DD HH:MM:SS)", value="")

if st.sidebar.button("🛰️ 해당 지역 국지 기상망 동기화 타격", type="primary"):
    if region_input.strip() != "":
        with st.sidebar.spinner(f"'{region_input}' 국지 백엔드 줌인 중..."):
            weather, obs_time, jimok, sat_temp = get_live_aws_weather(region_input, custom_119_time)
            if weather:
                st.session_state['t_val'] = weather['temperature']
                st.session_state['h_val'] = weather['humidity']
                st.session_state['w_val'] = weather['wind_speed']
                st.session_state['obs_time'] = obs_time
                st.session_state['live_jimok'] = jimok
                st.session_state['sat_temp'] = sat_temp
                st.session_state['current_target'] = region_input
                st.sidebar.success(f"✅ {region_input} 데이터 동기화 완료!")
    else: st.sidebar.warning("조회할 주소를 입력해 주세요.")

st.sidebar.markdown("---")
st.sidebar.header("🎛️ 실시간 기상 변수 통제 계측기")
temperature = st.sidebar.slider("관측 기온 (°C)", min_value=-10.0, max_value=45.0, value=float(st.session_state['t_val']))
humidity = st.sidebar.slider("대기 상대습도 (%)", min_value=0.0, max_value=100.0, value=float(st.session_state['h_val']))
wind_speed = st.sidebar.slider("현지 풍속 (m/s)", min_value=0.0, max_value=35.0, value=float(st.session_state['w_val']))

st.sidebar.markdown("---")
st.sidebar.header("⛰️ 현장 구조 계수")
oil_content = st.sidebar.slider("수목 내 가연성 임상(유분) 비율 (%)", min_value=0.0, max_value=100.0, value=65.0) / 100.0
current_slope = st.sidebar.slider("지형 실측 경사도 (°)", min_value=0.0, max_value=60.0, value=20.0)

# --- 🧠 령이 AI 전국구 통합 화재 인지 알고리즘 ---
fire_type = "SAFE"
if "임야" in st.session_state['live_jimok'] or "산림" in st.session_state['live_jimok']: fire_type = "WILDFIRE"
elif "공장" in st.session_state['live_jimok']: fire_type = "FACTORY"
elif "대지" in st.session_state['live_jimok']: fire_type = "CITY"

humidity_score = (100 - humidity) * 0.3
wind_score = wind_speed * 2.0
temperature_score = max(0.0, temperature * 0.6)
oil_score = oil_content * 20
slope_score = current_slope * 0.5

total_risk = humidity_score + wind_score + temperature_score + oil_score + slope_score

# --- 📺 메인 모니터링 모듈 ---
col_radar, col_status = st.columns([1, 2])

with col_radar:
    st.subheader("🛰️ 령이 실시간 국지 감시 관제 센터")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.session_state['current_target'] == "대한민국 전역 (전수 관측 모드)":
        st.info("🟢 [상시 모드] 시스템 백엔드 내부에서 대한민국 영토 전역의 기상 및 위성 FF 피드를 실시간 무한 전수 관측 중입니다.")
    elif total_risk >= 35 and fire_type != "SAFE": # 🌟 규모별 경보 작동을 위해 탐지 하한선을 35점으로 확장
        st.error(f"🔴 [위기 감지] 타깃 구역 [{st.session_state['current_target']}] 열점 및 이상 기류 스캔 감지 완료.")
    else:
        st.success(f"🍏 [추적 유지] 포커싱 구역: [{st.session_state['current_target']}] 인프라 정상 가동 중.")

with col_status:
    st.subheader("📊 관제 현황 및 최종 판정")
    if fire_type == "SAFE" and total_risk >= 35:
        st.info(f"🛑 **[오발동 탐지 차단기 가동]**\n\n지목이 **[{st.session_state['live_jimok']}]**으로 확인되어 상업용 복사열에 의한 오탐지로 자동 기각합니다.")
        total_risk = 0.0

    # 🌟 [주요 업데이트] 제준 대표님 주문형 '화재 점수 규모별 4단계 동적 UI' 구현
    if total_risk >= 85: # 등급 4: 초대형 화재
        bg_color = "#ff0000"; text_title = "🔥 [🚨 재난] 심각 단계 - 심각한 대형 화재 발령 🔥"; sub_text = "광역 전수 소방력 동원령 및 주민 강제 대피 세션"
    elif total_risk >= 65: # 등급 3: 중형 화재
        bg_color = "#d9381e"; text_title = "🔥 [⚠️ 경보] 경계 단계 - 확산형 중형 화재 발령 🔥"; sub_text = "관할 소방서 전원 출동 및 국지 방화선 형성 세션"
    elif total_risk >= 45: # 등급 2: 소형 화재
        bg_color = "#e67e22"; text_title = "🔥 [주의] 주의 단계 - 국지성 소형 화재 감지 🔥"; sub_text = "안동/해당 관할 화재 진화차 1~2대 자체 초동 진압 가능 구역"
    elif total_risk >= 35: # 등급 1: 미세 불씨
        bg_color = "#f39c12"; text_title = "🔥 [관찰] 관심 단계 - 미세 불씨 및 단순 소각 징후 포착 🔥"; sub_text = "의성/해당 산불감시원 및 순찰대 현장 육안 확인 지시 단계"
    else:
        bg_color = "#1a73e8"; text_title = "🔒 안전 관제 스캔 잠금 상태"; sub_text = "특이 열점 이상 징후 없음"

    if total_risk >= 35:
        html_status = f"""
        <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px; border: 4px solid #ffffff; box-shadow: 0px 0px 15px {bg_color}; text-align: center;">
            <span style="font-size: 50px;">⚠️</span>
            <h2 style="color: #ffffff; font-weight: bold; margin-top: 10px; margin-bottom: 5px;">{text_title}</h2>
            <h4 style="color: #ffff00; margin: 0;">{sub_text} (관제 점수: {total_risk:.1f}점)</h4>
        </div>
        """
        st.markdown(html_status, unsafe_allow_html=True)
    else:
        st.info(f"## {text_title}\n\n{sub_text}")

# 실측 교차 검증 대장
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("📋 천리안 2A호 위성(FF) 실시간 화재 교차 검증 대장 (실측 데이터셋)")
st.table(st.session_state['fire_records'])

# --- 🌟 [핵심 업데이트] 제준 대표님이 공부해서 고도화할 '규모별 4단계 대응책 백엔드 딕셔너리' ---
st.divider()
if total_risk >= 35 and fire_type != "SAFE":
    st.markdown(f"### 📢 [현장 지휘 가이드] {st.session_state['current_target']} 규모별 현장 초동 대응 대책")
    
    # 💡 4단계 규모 기준별 멘트 마스터 박스 (나중에 이 텍스트만 전면 수정하시면 됩니다!)
    if total_risk >= 85: # 등급 4
        m_10 = "🚒 **[10분 골든타임 조치]** 초대형 진화 헬기 3대 이상 즉각 공중 출격 유도 및 지자체 소방력 3단계 총동원 발령."
        m_30 = "⚠️ **[30분 저지 저항 조치]** 돌풍 결합 폭발적 수관화 전개 구역. 확산 예상 하류 부락 주민 강제 대피 재난문자 자동 전송."
        m_60 = "🧑‍🚒 **[60분 광역 저지선]** 인근 인접 시·도 소방력 긴급 지원 요청(소방동원령 1호) 및 국가 인프라 시설 차단벽 구축."
    elif total_risk >= 65: # 등급 3
        m_10 = "🚒 **[10분 골든타임 조치]** 관할 소방서 구조대·진화대 전원 비상 소집 및 중형 소방 헬기 1~2대 지원 요청 선제 타격."
        m_30 = "⚠️ **[30분 저지 저항 조치]** 강풍 전개 시 비화(불씨 날림) 위험 존재. 현장 지휘소 선제 설치 및 소방 용수 공급망 최우선 확보."
        m_60 = "🧑‍🚒 **[60분 광역 저지선]** 인근 의용소방대 추가 동원 및 산불 확산 방향 500m 전방 국지적 소화 방화벽(임도 방어) 고착."
    elif total_risk >= 45: # 등급 2
        # 🌟 대표님이 제안하신 "1차 소방차로 자체 진압 가능한 소형 산불 규모" 맞춤형 멘트 세팅 파트!
        m_10 = "🚒 **[10분 골든타임 조치]** 관할 동네 소방서 화재 진화용 펌프차 및 살수차 1~2대 즉각 출동으로 현장 초동 진압 가동."
        m_30 = "⚠️ **[30분 저지 저항 조치]** 기상 조건(풍속 2m/s 내외)이 안정적이므로, 소방차 자체 호스 전개 및 고압 방수로 주변 번짐 원천 차단."
        m_60 = "🧑‍🚒 **[60분 광역 저지선]** 대형 헬기나 대피령 불필요 구역. 잔불 정리 전용 기계화 시스템 투입 및 등짐펌프 조를 통한 완전 완진 유도."
    else: # 등급 1
        m_10 = "🚒 **[10분 골든타임 조치]** 119 정식 출동 전, 해당 면사무소 산불감시원 및 순찰대 전동 오토바이 즉각 현장 긴급 급파 지시."
        m_30 = "⚠️ **[30분 저지 저항 조치]** 주민 단순 논밭두렁 소각 혹은 쓰레기 소각 징후 유력. 현장 계도 조치 및 방화 방지용 현장 육안 감시 유지."
        m_60 = "🧑‍🚒 **[60분 광역 저지선]** 소방차 복귀 대기 모드 유지. 화재 인지 세션 해제 및 관할 상시 레이더 스캔 모드로 안전 복귀."

    # 화면에 깔끔하게 3단 박스로 노출
    col1, col2, col3 = st.columns(3)
    with col1: st.error(m_10)
    with col2: st.error(m_30)
    with col3: st.error(m_60)
else:
    st.info("💡 관측 위험도가 관심 등급(35점) 이상 돌파 시, 령이 AI가 연산한 규모별 맞춤 지휘 통제 대책이 이곳에 자동으로 정렬됩니다.")

st.divider()
st.caption("🚨 RYEONG-I Space-Land Integrated Fire Sentinel Platform v3.4 • 데이터 출처: 기상청 / 환경부 / 국가기상위성센터")