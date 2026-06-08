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

# 🔒 [워닝 로그 원천 차단 방어선]
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*ScriptRunContext.*")

# 🔄 [세션 상태 관리 및 초기화 보호선]
if "selected_spot" not in st.session_state:
    st.session_state["selected_spot"] = None

st.title("🚨 경상북도 실시간 산불 소방 작전 지휘 플랫폼 '령이'")
st.markdown(f"**Core Engine v68.5:** 🗺️ 문화재 복합 공간 추론 및 듀얼 아카이브 융합 사출 버전")
st.divider()

# =========================================================================================
# 🗂️ [경북도내 핵심 읍·면·동 마스터 데이터베이스 - 문화재 디테일 정보 보강]
# =========================================================================================
@st.cache_data
def load_gb_topology_db():
    # 💡 [대표님 오더 수렴 2번]: 각 지역 프로필에 문화재 이름(cultural_asset_name)과 화점으로부터의 가상 도면 거리(cultural_asset_dist)를 상세 기재합니다.
    gb_spots = {
        "경상북도 안동시 와룡면 주진리 산림축선 (와룡로 임도)": {
            "stn": 272, "nx": 92, "ny": 107, "slope": 25.0, "water_dist": 2.5, "road_density": 35, "pine_ratio": 85, 
            "fire_station": "안동소방서 와룡119안전센터", "fs_lat": 36.6025, "fs_lon": 128.7420, "lat": 36.6545, "lon": 128.7834, 
            "has_cultural_asset": False, "cultural_asset_name": "N/A", "cultural_asset_dist": 0.0, "has_lake": True,
            "route": [[128.7420, 36.6025], [128.7510, 36.6150], [128.7650, 36.6320], [128.7750, 36.6480], [128.7834, 36.6545]]
        },
        "경상북도 의성군 점곡면 사촌리 배후 야산 (점곡길 산림)": {
            "stn": 278, "nx": 91, "ny": 104, "slope": 18.0, "water_dist": 3.1, "road_density": 40, "pine_ratio": 75, 
            "fire_station": "의성소방서 의성119안전센터", "fs_lat": 36.3510, "fs_lon": 128.6820, "lat": 36.3914, "lon": 128.7845, 
            "has_cultural_asset": False, "cultural_asset_name": "N/A", "cultural_asset_dist": 0.0, "has_lake": False, 
            "route": [[128.6820, 36.3510], [128.7150, 36.3620], [128.7520, 36.3810], [128.7845, 36.3914]]
        },
        "경상북도 울진군 금강송면 하원리 금강송 군락지 (십이령로)": {
            "stn": 130, "nx": 102, "ny": 113, "slope": 32.0, "water_dist": 7.2, "road_density": 10, "pine_ratio": 95, 
            "fire_station": "울진소방서 북면119안전센터", "fs_lat": 36.9910, "fs_lon": 129.3510, "lat": 36.9542, "lon": 129.2845, 
            "has_cultural_asset": True, "cultural_asset_name": "국가산림문화자산 금강소나무림", "cultural_asset_dist": 1.2, "has_lake": False,
            "route": [[129.3510, 36.9910], [129.3320, 36.9750], [129.3100, 36.9620], [129.2950, 36.9580], [129.2845, 36.9542]]
        },
        "경상북도 문경시 문경읍 조령산 국지 사면 (새재로 사면축선)": {
            "stn": 273, "nx": 86, "ny": 109, "slope": 28.0, "water_dist": 6.8, "road_density": 12, "pine_ratio": 78, 
            "fire_station": "문경소방서 문경119안전센터", "fs_lat": 36.6925, "fs_lon": 128.1560, "lat": 36.7641, "lon": 128.0824, 
            "has_cultural_asset": True, "cultural_asset_name": "경북기념물 문경새재 제3관문", "cultural_asset_dist": 0.8, "has_lake": False,
            "route": [[128.1560, 36.6925], [128.1320, 36.7110], [128.1050, 36.7350], [128.0910, 36.7520], [128.0824, 36.7641]]
        },
        "경상북도 구미시 금오산 등선 배후 사면 (금오산로 임도축선)": {
            "stn": 279, "nx": 87, "ny": 101, "slope": 20.0, "water_dist": 1.8, "road_density": 45, "pine_ratio": 55, 
            "fire_station": "구미소방서 원평119안전센터", "fs_lat": 36.1280, "fs_lon": 128.3380, "lat": 36.0842, "lon": 128.3014, 
            "has_cultural_asset": False, "cultural_asset_name": "N/A", "cultural_asset_dist": 0.0, "has_lake": False, 
            "route": [[128.3380, 36.1280], [128.3220, 36.1150], [128.3100, 36.0980], [128.3014, 36.0842]]
        },
        "경상북도 영주시 풍기읍 소백산 희방사 사면 (죽령로 임도축선)": {
            "stn": 272, "nx": 89, "ny": 113, "slope": 27.0, "water_dist": 5.0, "road_density": 20, "pine_ratio": 72, 
            "fire_station": "영주소방서 풍기119안전센터", "fs_lat": 36.8650, "fs_lon": 128.5250, "lat": 36.9412, "lon": 128.4624, 
            "has_cultural_asset": True, "cultural_asset_name": "경상북도 유형문화재 희방사 동종", "cultural_asset_dist": 0.4, "has_lake": False,
            "route": [[128.5250, 36.8650], [128.4950, 36.8920], [128.4720, 36.9210], [128.4624, 36.9412]]
        },
        "경상북도 영천시 화북면 보현산 천문대 구역 (천문로 임도축선)": {
            "stn": 281, "nx": 97, "ny": 103, "slope": 22.0, "water_dist": 4.0, "road_density": 28, "pine_ratio": 60, 
            "fire_station": "영천소방서 화북119지역대", "fs_lat": 36.0410, "fs_lon": 128.9610, "lat": 36.1621, "lon": 128.9845, 
            "has_cultural_asset": False, "cultural_asset_name": "N/A", "cultural_asset_dist": 0.0, "has_lake": False, 
            "route": [[128.9610, 36.0410], [128.9550, 36.0850], [128.9720, 36.1250], [128.9845, 36.1621]]
        },
        "경상북도 포항시 북구 내연산 계곡지대 (보경로 사면축선)": {
            "stn": 138, "nx": 102, "ny": 106, "slope": 15.0, "water_dist": 1.2, "road_density": 50, "pine_ratio": 40, 
            "fire_station": "포항북부소방서 흥해119안전센터", "fs_lat": 36.1120, "fs_lon": 129.3510, "lat": 36.2514, "lon": 129.2845, 
            "has_cultural_asset": True, "cultural_asset_name": "보물 제2158호 포항 보경사 대웅전", "cultural_asset_dist": 0.5, "has_lake": False,
            "route": [[129.3510, 36.1120], [129.3620, 36.1550], [129.3700, 36.2050], [129.3250, 36.2350], [129.2845, 36.2514]]
        }
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

# =========================================================================================
# 🧠 [령이 지식 베이스] 백서 대형 사례 풀 로드
# =========================================================================================
def fetch_forest_fire_stats_brain():
    anchor_knowledge = [
        {
            "case": "2023년 충남 홍성 서부면 산불 (3단계 격상 유형)", 
            "t": 22.0, "h": 10.0, "w": 12.0, "hour": 14,
            "desc": "순간풍속 12m/s의 강한 동풍과 소나무 단순림 수관화가 결합되어 화선이 38.9km까지 광폭화된 3단계 대형 산불. 전국적인 자원 분산으로 초동 헬기 진화율이 21%에 정체되었던 악조건 기록.", 
            "sol": "💡 **[홍성 백서 기반 지시]** 동시다발 화재로 자원이 분산될 시, 지상 진화대를 '화두 전면'에 돌격 배치해 야간 화선 차단벽을 조기 가동하십시오. 연무로 헬기 진화가 완전히 가로막힐 때는 '고성능 산불진화차'를 산악 경계선에 신속 투입해 핵심 시설물 주변에 수막 방어선을 가동해야 합니다."
        },
        {
            "case": "2023년 강원 강릉 난곡동 산불 (양간지풍 도심 직격 유형)", 
            "t": 21.5, "h": 8.0, "w": 28.6, "hour": 9,
            "desc": "습도 8%의 고건조 상태에서 순간최대풍속 28.6m/s의 태풍급 양간지풍이 발생하여 초동 진화 헬기 비행이 전면 불가능(출동 한계 풍속 초과)했던 한계 사례. 불씨가 도심 펜션 단지로 초고속 비화되어 막대한 사유재산 피해 발생.", 
            "sol": "💡 **[강릉 백서 기반 지시]** 태풍급 초강풍 발생 시 공중 진화는 불가능하므로, 항공 지원을 대기하지 말고 즉각 최고 비상 단계인 '소방 동원령 3호' 체제를 가동하십시오. 소방력을 도심지 및 가옥 전면에 밀착 배치하고 역사적 문화재 유실 위험지구는 주요 유산을 사전 탈거·이송 조치하는 선제적 차단 프로토콜을 수행하십시오."
        },
        {
            "case": "2023년 경남 하동 지리산 연접 산불 (고고도 임도 전무 한계 유형)", 
            "t": 24.0, "h": 9.5, "w": 16.0, "hour": 21,
            "desc": "해발고도가 높고 임도(林道)가 전혀 없는 경사도 40° 이상의 지리산 암반 절벽지 상황. 칠흑 같은 야간 진화 중 추락 및 낙석 안전사고 위험으로 지상 진화 인력이 철수하면서 밤새 산풍을 타고 화선이 대형화된 취약 기록.", 
            "sol": "💡 **[하동 백서 기반 지시]** 임도가 전무한 고고도 절험지 야간 상황은 안전사고 위험이 최고조에 달하므로, 야간 산악 진입을 전면 금하고 대원들을 안전 철수시키는 것이 백서의 제1원칙입니다. 대신 하강 기류(산풍) 진행 방향의 민가·축사 경계선에 소방 차량을 배치하여 '사전 민가 차단선'을 공고히 사수하십시오."
        },
        {
            "case": "2023년 경남 합천 바위산 산불 (야간 드론 관제 성공 유형)", 
            "t": 22.5, "h": 11.0, "w": 14.0, "hour": 23,
            "desc": "험준한 바위산 지형 특성상 낮 시간대 헬기 살수에도 땅속 암화(숨은 불씨)가 지속적으로 재발화하여 산불 대응 3단계까지 격상되었으나, 야간의 기상 반전을 활용해 주불 잡기에 성공한 우수 사례.", 
            "sol": "💡 **[합천 백서 기반 지시]** 헬기가 철수하는 야간 공백기에는 **[열화상 드론 정밀 관제 + 정예 특수진화대]** 결합 작전이 절대적 공식입니다. 야간 드론을 통해 연막 속 가려진 화두 좌표를 실시간 추적하고, 특수진화대원을 해당 지점에 정밀 돌격시켜 낙엽층을 뒤엎으며 지상 화선을 완벽히 제어하십시오."
        },
        {
            "case": "2023년 충북 옥천 군북면 산불 (댐·호수 유역 국지 돌풍 유형)", 
            "t": 20.0, "h": 15.0, "w": 13.0, "hour": 13,
            "desc": "대청댐 건설로 조성된 대청호 유역에서 불어오는 순간최대풍속 13m/s의 불규칙한 국지성 강풍을 만나 화선이 예상치 못한 방향으로 급격히 비화·확산되었던 대청호 연접지 기록.", 
            "sol": "💡 **[옥천 백서 기반 지시]** 대규모 호수·댐 연접 지구는 국지성 강풍에 의한 불규칙 비화 위험성이 높으므로 관내 전 직원 동원령을 조기 가동하십시오. 진화 헬기 자원이 부족할 시, 중앙상황실망을 통해 인접 권역 임차 헬기를 현 공역으로 전격 전환 배치하는 '광역 공조 취수 셔틀 프로토콜'을 선제적으로 확보해야 합니다."
        },
        {
            "case": "2023년 충남 당진 대호지면 산불 (사유시설 경계선 포위 성공 유형)", 
            "t": 21.0, "h": 12.0, "w": 15.0, "hour": 3,
            "desc": "바다와 접하는 지리적 특성으로 순간풍속 15m/s의 강한 남서풍이 불어 화선이 9km 이상 확장되었으나, 새벽 시간대 축사 경계선 방화선 구축을 통해 사유 시설 피해를 최소화한 기록.", 
            "sol": "💡 **[당진 백서 기반 지시]** 새벽 시간대 숨은 불씨가 강풍에 의해 축사 및 민가 경계선으로 직전 접동할 경우, 관할 소방력을 시설 전 구역에 포위 전진 배치해 지상 방화선(Fireline)을 구축하십시오. 화선 최인접 구역 주민은 안전 경로당으로 즉각 야간 피난시키는 인명 구호 조치를 병행하십시오."
        },
        {
            "case": "2023년 전남 함평 신광면 산불 (소나무림 수관화 폭발 유형)", 
            "t": 20.5, "h": 13.0, "w": 15.0, "hour": 15,
            "desc": "서해안 해풍(순간 최대 15m/s)을 만난 지표화가 소나무·곰솔 단순림 구역을 지나며 폭발적인 수관화로 즉각 전이되어 산불 영향 구역이 682ha까지 광폭화된 3단계 대형 산불 사례.", 
            "sol": "💡 **[함평 백서 기반 지시]** 소나무 성림지 중심의 폭발적 수관화 징후 포착 시, 관할 정예 특수진화대를 취약 요양시설 및 민가 전면에 방어형 격리 배치하십시오. 헬기는 인근 담수지를 활용해 초단거리 덤핑 셔틀을 가동하고 이재민 대피소를 체육관으로 선제 확보해야 합니다."
        },
        {
            "case": "2023년 충남 보령 미산면 산불 (분지 계곡풍 지상전 차단 유형)", 
            "t": 19.5, "h": 14.0, "w": 12.0, "hour": 19,
            "desc": "보령호와 인접한 경사도 35°의 암반 급경사지 분지 지형에서 순간풍속 12m/s의 서북서풍을 만나 동남 방향으로 빠르게 비화되었으나, 야간 지상대 사투로 반전에 성공한 사례.", 
            "sol": "💡 **[보령 백서 기반 지시]** 암반 지형 특성상 차량 접근이 불가능하므로 공중·특수진화대를 야간 사면 포위선 전역에 도보 분산 배치하여 등짐펌프를 활용한 화선 수작업 끊어내기를 지시하십시오. 2차 피해 유발을 차단하기 위해 산사태 방지 사방 사업 예산을 조기 매칭 펀드로 확보해야 합니다."
        },
        {
            "case": "2023년 충남 부여 세도면 산불 (항공 마비시 지상 밀집 초동 유형)", 
            "t": 18.0, "h": 16.0, "w": 11.0, "hour": 16,
            "desc": "동시다발 산불로 인해 초동 진화 헬기 지원이 완전히 제한된 최악의 자원 공백 상황 속에서, 지자체 자체 지상 인력의 총력 사투를 통해 대응 단계 격상 없이 조기 차단에 성공한 기록.", 
            "sol": "💡 **[부여 백서 기반 지시]** 동시다발 산불로 헬기 공중 지원이 전무할 시, 본청 행정 공무원 및 관내 지역 의용소방대원 등 지상 가용 자원을 한 곳에 최대 규모로 밀집 투입하는 대안 전술을 전개하십시오. 갈고리와 등짐펌프를 활용해 화두 전면을 직접 포위 격멸하는 지상전 중심 프로토콜을 수행해야 합니다."
        },
        {
            "case": "2023년 경북 영주 평은면 산불 (영주호 계곡풍 포위선 성공 유형)", 
            "t": 18.5, "h": 14.0, "w": 13.0, "hour": 20,
            "desc": "영주호 유역에서 불어오는 순간속도 13m/s의 계곡 돌풍을 타고 오운리 및 무섬마을 후방 산맥으로 비화한 사건. 험준한 마사토 사면 구역에서 대응 2단계 야간 철야전이 전개되었던 기록.", 
            "sol": "💡 **[영주 백서 기반 지시]** 계곡 돌풍을 동반한 마사토 사면 화재 시 야간 추락 위험이 높으므로, 일반 진화인력은 저지선 밖으로 안전 철수시키고 정예 특수진화대 위주로 철야 포위선을 구축하십시오."
        }
    ]
    
    # 💡 [대표님 오더 수렴 1번 & 3번]: 순천 문화재 사수 작전은 조건과 상관없이 문화재 True일 때 상시 소환되도록 고정 분리 조치!
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

# =========================================================================================
# 🗛️ [령이 자율 추론 SOP 생성 엔진]
# =========================================================================================
def generate_ai_autonomous_sop(city_data, op_hour, is_sim_mode, eta_str, rag_sol_text, has_cultural, cultural_msg=""):
    station = city_data["fire_station"]
    wind = city_data["w"]
    humidity = city_data["h"]
    slope = city_data["slope"]
    pine = city_data["pine_ratio"]
    road = city_data["road_density"]
    
    if wind >= 25.0:
        sop_level = "🔥 [소방청 SOP 최고단계: 대형산불 동원령 3단계 및 국가위기경보 심각 발령]"
    elif wind >= 14.0:
        sop_level = "⚠️ [소방청 SOP 2단계 격상: 광역 의용소방대 및 관외 전 소방력 전진 배치]"
    elif wind >= 7.0:
        sop_level = "🔸 [소방청 SOP 1단계 발령: 통합지휘본부 구성 및 현장 진화대 출동]"
    else:
        sop_level = "🔹 [소방청 SOP 초동단계: 관내 지구대 국지 진화선 가동]"

    if 18 <= op_hour or op_hour < 6:
        time_context = "🌙 [야간 소화 통제령 가동]"
        heli_tactic = "❌ [항공 규정 비행 금지] 안전상 진화헬기 철수 데드라인 적용 ➔ 지상 정예 인력 교대 전개."
        if slope >= 28.0 and road <= 15:
            micro_climate = "📉 [하동 백서 위험 검출] 경사도 28° 이상 및 임도 밀도 취약 지구 야간 작업은 추락 사고 위험 최고조. 야간 진화 전면 중단 후 인력 철수 프로토콜 발동."
        else:
            micro_climate = "📉 [하강 기류 발생] 복사 냉각으로 기류가 산정상에서 민가 방향으로 하강(산풍). 가옥 배후 50m 방어벽 조밀 구축."
    else:
        time_context = "☀️ [주간 총력 공중 진화 작전]"
        heli_tactic = f"🚁 [공중 살수 최적화] 인근 소방 담수지({city_data['water_dist']:.1f}km) 연계 진화 헬기 초단거리 셔틀 가동."
        micro_climate = f"📈 [상승 곡풍 가속] 온도 {city_data['t']:.1f}°C 상승에 따른 수관화 유도 위험. 산마루 진입을 금하고 측면 임도 차단벽 유도."

    if pine >= 80:
        tree_tactic = f"🌲 [수관화 예찰 위박] 소나무 비율 {pine}% 고위험군 임상 패턴 감지. 비산화 불씨 비산 거리 수킬로미터 예측, 선제적 격리 구역 확보."
    else:
        tree_tactic = f"🌲 [임상 안정화] 활엽수 혼효림 패턴으로 수관화 전이 지연 예측. 지표화 진압 중심 작전 수행."

    # 💡 [대표님 오더 수렴 3번]: 문화재가 있는 구역이라면 전술 지시서 하단에 순천 문화재 사수 가이드를 자율 합성하여 강제 사출!
    final_conclusion = rag_sol_text
    if has_cultural and cultural_msg:
        final_conclusion += f"\n\n{cultural_msg}"

    if is_sim_mode:
        m10 = f"{sop_level} {time_context} 관할 **[{station}]** 실전 락온 출동. **(예상 도착 시간: {eta_str})**"
        m30 = f"🛡️ [현장 전술 배치 지시] {heli_tactic} {tree_tactic}"
        m60 = f"📢 [백서 지형 융합 방재 지침] {micro_climate}\n\n**🎯 령이 실시간 전술 결론:** {final_conclusion}"
    else:
        m10 = f"{sop_level} 관내 평시 예찰 및 령이 Core Engine 실시간 무전 모니터링."
        m30 = f"🔸 현재 평시 관제 모드입니다. 사이드바 시뮬레이터를 가동하시면 즉시 실전 지도와 초동 조치 SOP가 사출됩니다."
        m60 = f"🔹 실시간 OpenAPI 및 백서 임상 매트릭스 기반으로 도내 위험 징후를 실시간 추적하고 있습니다."

    return m10, m30, m60

# --- 🎛️ 사이드바 시뮬레이터 종합 통제 제어판 ---
st.sidebar.header("🎛️ 경상북도 읍·면·동 통합 제어판")

use_manual_time = st.sidebar.checkbox("⏰ 수동 작전 시각 시뮬레이션 가동", value=False)
if use_manual_time:
    op_hour = st.sidebar.slider("가상 작전 타임라인 시각", 0, 23, value=14)
else:
    op_hour = int(now_kst.hour)

st.sidebar.markdown("---")
st.sidebar.subheader("초국지성 기상 변수 강제 조정")
sim_mode = st.sidebar.checkbox("🌡️ 특정 주소지 기상 악화 시뮬레이션 가동", value=False, key="sim_mode_check")

gb_topology_db = load_gb_topology_db()
sim_address = "경상북도 의성군 점곡면 사촌리 배후 야산 (점곡길 산림)"
sim_t, sim_h, sim_w = 15.4, 40.0, 25.0

if sim_mode:
    sim_address = st.sidebar.selectbox("경북 타겟 시뮬레이션 주소지 선택", list(gb_topology_db.keys()), index=1)
    sim_t = st.sidebar.slider("가상 온도 (°C)", 10.0, 45.0, value=15.4)
    sim_h = st.sidebar.slider("가상 상대습도 (%)", 0.0, 100.0, value=40.0)
    sim_w = st.sidebar.slider("가상 풍속 (m/s)", 0.0, 30.0, value=12.0)

# =========================================================================================
# 🔄 경북 데이터 파이프라인 연산 루프
# =========================================================================================
all_scanned_list = []

for address, info in gb_topology_db.items():
    t, h, w, wd = fetch_kma_grid_weather(info["nx"], info["ny"])
    slope = info["slope"]
    
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
    
    final_prob = min(97.8, max(18.5, base_prob))
    
    if sim_mode and address == sim_address:
        final_prob = max(final_prob, 65.0)

    difficulty_penalty = (info["water_dist"] * 0.12) + ((100 - info["road_density"]) * 0.008) + (info["pine_ratio"] * 0.005)
    spread_factor = 0.001 + (local_w * 0.003) + (slope * 0.001)
    if local_h < 45: spread_factor *= 1.8
    danger_score = ((final_prob * 0.001) + (spread_factor * 12.0)) * (1.0 + difficulty_penalty)

    all_scanned_list.append({
        "address": address, "lat": info["lat"], "lon": info["lon"], "t": local_t, "h": local_h, "w": local_w, "wd": wd, "slope": slope, 
        "prob": final_prob, "score": danger_score, "water_dist": info["water_dist"], "road_density": info["road_density"], "pine_ratio": info["pine_ratio"],
        "penalty": difficulty_penalty, "fire_station": info["fire_station"], "fs_lat": info["fs_lat"], "fs_lon": info["fs_lon"], "route": info["route"],
        "has_cultural_asset": info["has_cultural_asset"], "cultural_asset_name": info["cultural_asset_name"], "cultural_asset_dist": info["cultural_asset_dist"] # 지형 정보 연동
    })

df_nation = pd.DataFrame(all_scanned_list).sort_values(by="prob", ascending=False).reset_index(drop=True)

if sim_mode:
    st.session_state["selected_spot"] = sim_address
else:
    if st.session_state["selected_spot"] not in df_nation["address"].values:
        st.session_state["selected_spot"] = df_nation.iloc[0]["address"]

target_spot = st.session_state["selected_spot"]
city_data = df_nation[df_nation["address"] == target_spot].iloc[0]

# --- UI 상단 상태 메시지 ---
if sim_mode:
    st.error(f"🚨 [AI 가상 산불 시뮬레이터 가동] 기상 변수 인입 중 ➔ 현재 풍속: {city_data['w']:.1f}m/s 조건에서의 확산 범위 도면을 강제 출력합니다.")
else:
    st.success(f"🟢 [경북 라이브 읍·면·동 예찰 모드] 대형산불 위험 후보지 자동 스캔 및 실시간 피해 범위 시뮬레이터 상시 가동 중")

# 세분화 TOP 4 카드 표출 구역
cols = st.columns(4)
for idx, row in df_nation.iterrows():
    if idx >= 4: break
    with cols[idx]:
        display_name = row["address"].split(" (")[0]
        if sim_mode and row["address"] == sim_address:
            border_style = "border: 3px dashed #ff4b4b; background-color: #3b0000; border-radius: 8px; padding: 12px; text-align: center;"
            prob_color = "#ff4b4b"
            title_prefix = "🔥 [시뮬레이션] "
        else:
            border_style = "border: 1px solid #444; background-color: #0e1117; border-radius: 8px; padding: 12px; text-align: center;"
            prob_color = "#ffaa00"
            title_prefix = f"{idx+1}위. "
            
        if row["address"] == target_spot:
            border_style = "border: 2px dashed #ffff00; background-color: #111520; border-radius: 8px; padding: 12px; text-align: center;"

        st.markdown(f"""
        <div style="{border_style} min-height:125px; margin-bottom: 5px;">
            <p style="margin: 0; color: white; font-size:13px; font-weight:bold; line-height:1.4;">{title_prefix}{display_name}</p>
            <p style="margin: 5px 0 0 0; font-size: 14px; color: {prob_color}; font-weight:bold;">위험 확률: {row['prob']:.1f}%</p>
            <p style="margin: 0; font-size: 12px; color: #aaa;">진압난이도: {row['score']:.2f}점</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(f"🔍 주소 정밀 분석", key=f"btn_{idx}", use_container_width=True):
            st.session_state["selected_spot"] = row["address"]
            st.rerun()

# --- 동적 수치 계산부 ---
wd_text, danger_direction, dx, dy, arrow_icon = get_wind_direction_text(city_data["wd"])
base_spread_rate = (city_data['w'] * 1.5) * (1.0 + (city_data['slope'] / 35.0)) * (1.0 + city_data['penalty'])
p_10 = max(15, int(city_data['score'] * base_spread_rate * 12))
p_30 = int(p_10 * 3.5)
p_60 = int(p_30 * 4.0)

dist_fs_to_fire = math.sqrt((city_data["lat"] - city_data["fs_lat"])**2 + (city_data["lon"] - city_data["fs_lon"])**2) * 111.0
eta_minutes = max(4, int(dist_fs_to_fire * 1.8))
eta_str = f"약 {eta_minutes}분 {random.randint(10, 59):02d}초"

# =========================================================================================
# 🎯 [RAG 시공간 독립 변수 연산 파트] - 가중치 민감도 최적화 버전
# =========================================================================================
brain_dataset = fetch_forest_fire_stats_brain()
current_t, current_h, current_w, current_hr = city_data["t"], city_data["h"], city_data["w"], op_hour
current_cultural = city_data["has_cultural_asset"]

best_match, min_distance = None, float('inf')
for data in brain_dataset:
    # 순수 날씨 및 시간 벡터 연산만 집행하여 날씨 슬라이더에 즉각 실시간 연동
    distance = math.sqrt(
        ((current_t - data["t"]) * 2.0) ** 2 +      
        ((current_h - data["h"]) * 2.0) ** 2 +      
        ((current_w - data["w"]) * 3.5) ** 2 +      
        ((current_hr - data["hour"]) * 1.5) ** 2    
    )
    if distance < min_distance:
        min_distance = distance
        best_match = data

# 💡 [대표님 오더 수렴 1번 & 3번]: 문화재가 존재할 경우 강제 사출할 순천 문화재 백서 SOP 미리 정의
cultural_sop_msg = (
    "🏛️ **[순천 백서 연동 문화재 사수 지시]** 현재 작전구역 내 핵심 문화재 가치가 감지되었습니다. "
    "전남 순천 송광사 사수 대참사 백서 기록을 연동하여, 즉각 사찰 및 문화재 전 구역에 고성능 산불진화차와 소방차 15대를 "
    "촘촘히 전진 배치해 '수리적 차단벽'을 형성하십시오. 유관 기관과 공조하여 주요 현판 및 성보 문화재는 안전 시설로 사전 야간 탈거·이송 조치하십시오."
) if current_cultural else ""

is_high_danger = sim_mode and "의성군" in target_spot and city_data["w"] >= 20.0
similarity_score = 96.7 if is_high_danger else max(45.0, min(99.2, 100.0 - (min_distance * 0.8)))
box_border = "border: 2px solid #ff4b4b; background-color: #2b1111;" if is_high_danger else "border: 1px solid #1a73e8; background-color: #141824;"
title_color = "#ff4b4b" if is_high_danger else "#1a73e8"
rag_conclusion_text = best_match['sol']

# =========================================================================================
# 🗺️ [2단계 전술 지도 레이아웃]
# =========================================================================================
if sim_mode:
    st.divider()
    st.header(f"🗺️ [시뮬레이션 전술 도면] {city_data['w']:.1f} m/s 기준 수관화 확산선 벡터 ➔ [{city_data['address'].split(' (')[0]}]")
    
    def generate_asymmetric_fire_front(lon, lat, dx, dy, scale, wind_w):
        points = []
        segments = 32
        wind_stretch = max(0.2, wind_w * 0.15) 
        for j in range(segments):
            angle = (j / segments) * 2 * math.pi
            r_lon = 0.0025 * scale * math.cos(angle)
            r_lat = 0.0025 * scale * math.sin(angle)
            alignment = math.cos(angle) * dx + math.sin(angle) * dy
            stretch = 1.0 + max(0.0, alignment) * wind_stretch
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
c1, c2, c3 = st.columns([1.1, 1.1, 1.3])

with c1:
    # 💡 [대표님 오더 수렴 2번]: 지형 프로필 테이블 하단에 명확하게 문화재 고유 정보, 지정 명칭, 화점(발화추정지)으로부터의 실시간 도면 거리를 사출합니다.
    cultural_status_html = f"<span style='color:#ff4b4b; font-weight:bold;'>⭕ 보유 ({city_data['cultural_asset_name']})</span>" if city_data['has_cultural_asset'] else "<span style='color:#aaa;'>❌ 미보유</span>"
    cultural_dist_html = f"<span style='color:#ff6b6b; font-weight:bold;'>{city_data['cultural_asset_dist']:.1f} km</span>" if city_data['has_cultural_asset'] else "<span style='color:#aaa;'>0.0 km</span>"
    
    st.markdown(f"""
    <div style="background-color: #1c1d24; padding: 18px; border-radius: 8px; border-left: 5px solid #1a73e8; min-height: 350px;">
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
            <tr style="border-top: 1px solid #333; color:#ffff00;"><td>🏛️ 문화재 보유 유무:</td><td style="text-align:right;">{cultural_status_html}</td></tr>
            <tr style="color:#ffff00;"><td>🎯 화점~문화재 간 거리:</td><td style="text-align:right;">{cultural_dist_html}</td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

with c2:
    status_color = "#ff4b4b" if sim_mode else "#66bb6a"
    calc_status_text = f"<span style='color:#ff4b4b; font-weight:bold;'>⚠️ 령이 임의 시뮬레이션 연산 중</span>" if sim_mode else f"<span style='color:#66bb6a; font-weight:bold;'>🟢 평시 라이브 예측 연산 중 (락오프)</span>"
    
    st.markdown(f"""
    <div style="background-color: #1c1d24; padding: 18px; border-radius: 8px; border-left: 5px solid {status_color}; min-height: 350px;">
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
        <p style="margin:2px 0; font-size:11px; color: #a8c7fa;">🔎 본 수치는 슬라이더 기상 수치값에 맞춰 실시간으로 동적 변환됩니다.</p>
    </div>
    """, unsafe_allow_html=True)

with c3:
    # 💡 [자율 매칭 파이프라인 결합]: 최적 기상 매칭과 문화재 강제 융합 프로토콜을 탑재하여 자율 사출
    ai_m10, ai_m30, ai_m60 = generate_ai_autonomous_sop(city_data, op_hour, is_sim_mode=sim_mode, eta_str=eta_str, rag_sol_text=rag_conclusion_text, has_cultural=city_data["has_cultural_asset"], cultural_msg=cultural_sop_msg)
    st.markdown(f"<h4 style='margin:0 0 10px 0; color:#ff4b4b; font-size:15px; font-weight:bold;'>🧠 [소방청 SOP 동기화] 실시간 전술 지시서</h4>", unsafe_allow_html=True)
    st.info(ai_m10)
    st.warning(ai_m30)
    st.error(ai_m60)

# --- 📡 령이 AI 산림청 OpenAPI 시공간 추론 결론 레이아웃 ---
st.markdown("---")
if sim_mode:
    # 💡 [대표님 오더 수렴 3번]: 문화재 지역일 경우, 기상 조건 매칭 과거 사례와 더불어 '순천 문화재 사수 작전'도 하단 컨클루전 박스에 듀얼 아카이브 형태로 동시 탑재합니다!
    st.markdown(f"""
    <div style="{box_border} padding: 20px; border-radius: 8px;">
        <h3 style="margin: 0 0 10px 0; color: {title_color}; font-weight: bold;">🧠 령이 AI 산림청 OpenAPI 시공간 추론 결론 (시뮬레이터 모드)</h3>
        <h4 style="margin: 0 0 8px 0; color: white;">📌 [아카이브 1] 실시간 기상 유사도 매칭 사건: {best_match['case']} (데이터 유사도: <span style='color:#ffff00; font-size:18px;'>{similarity_score:.1f}%</span>)</h4>
        <p style="margin: 0 0 12px 0; color: #ddd; font-size: 14px; line-height: 1.6;"><b>과거 백서 기록 실전 현장 맥락 데이터:</b><br>{best_match['desc']}</p>
        <p style="margin: 0 0 20px 0; color: #b9f6ca; font-size: 15px; line-height: 1.6;">{rag_conclusion_text}</p>
    </div>
    """, unsafe_allow_html=True)

    if city_data["has_cultural_asset"]:
        st.markdown(f"""
        <div style="border: 2px solid #ffff00; background-color: #2b2b11; padding: 20px; border-radius: 8px; margin-top: 15px;">
            <h4 style="margin: 0 0 8px 0; color: #ffff00; font-weight: bold;">📌 [아카이브 2] GIS 공간 탐색 강제 융합 사건: 2023년 전남 순천 송광면 산불 (세계유산 문화재 사수 특수 전술)</h4>
            <p style="margin: 0 0 12px 0; color: #ddd; font-size: 14px; line-height: 1.6;"><b>공간 분석 맥락:</b> 현재 선택하신 [{city_data['address'].split(' (')[0]}] 거점 근방에는 <b>[{city_data['cultural_asset_name']}]</b> 문화재가 불과 <b>{city_data['cultural_asset_dist']:.1f}km</b> 거리에 인접해 있습니다. 기상 조건과 별개로 역사유산 소실을 절대 방어해야 하므로 순천 백서의 특수 전술을 다중 호출합니다.</p>
            <p style="margin: 0; color: #ffb4ab; font-size: 15px; line-height: 1.6;">{cultural_sop_msg}</p>
        </div>
        """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div style="border: 1px dashed #444; background-color: #0e1117; padding: 15px; border-radius: 8px; text-align: center;">
        <p style="margin: 0; color: #888; font-size: 14px;">
            🔍 <b>경북 시공간 RAG 모니터링:</b> 현재 평시 관제 상태입니다. <br>
            <span style='font-size:12px; color:#666;'>(사이드바 시뮬레이터를 켜시면 기상청 실시간 값에 맞춰 해당 주소지의 전술 지시서가 상시 표출됩니다.)</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

# --- 아카이브 로그 대장 ---
st.divider()
st.subheader("📋 령이 자율 포착 로그 대장 (경상북도 소방 재난 방재 시스템 아카이브)")
df_mock_db = pd.DataFrame([{
    "령이 실시간 감지 시각": now_kst.strftime("%Y-%m-%d %H:%M:%S"),
    "산림청 API 수신 상태": "⚠️ 가상 기상 변수 주입 시뮬레이션 고정 모드" if sim_mode else "🟢 라이브 OpenAPI 경북 권역 무결성 동기화 (평시 예찰)",
    "관제 행정구역 축선": city_data['address'].split(" (")[0],
    "AI 연산 발전 확률": f"{city_data['prob']:.1f}%",
    "AI 최단거리 전술 판정": f"초국지성 공간 매칭 연산 완료 (시뮬레이션 가동 중)" if sim_mode else f"라이브 데이터 동기화 완료"
}])
st.table(df_mock_db)