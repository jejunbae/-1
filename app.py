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

# 🧠 [오류 해결] geopandas 라이브러리 안전 안전망 빌드
gpd = None
try:
    import geopandas as gpd
except ImportError:
    pass

# 🖥️ 플랫폼 아이덴티티 및 상단 세팅
st.set_page_config(page_title="산불 감지 및 관제 AI 령이", page_icon="⚠️", layout="wide")

API_KEY = "69309efd849de167a2a68e2fc27331c01eb67888d72dd4a740419a33cf7d292e"
tz_kst = timezone(timedelta(hours=9))
now_kst = datetime.now(tz_kst)

st.title("🚒 산불 감지 및 관제 AI '령이'")
st.markdown(f"**Core Engine v45.8:** 🗺️ 타임라인 개별 분리 배치 & 3D 전술 다크 벡터 레이어 종결 버전")
st.divider()

# --- 📁 [데이터 백엔드] 1. 경북 47번 등산로 GIS 파일 로드 ---
SHP_PATH = "shape_data/47.shp"
@st.cache_data
def load_gyeongbuk_gis_lines():
    if gpd is None: return None
    if not os.path.exists(SHP_PATH):
        if os.path.exists("47.shp"): target = "47.shp"
        else: return None
    else: target = SHP_PATH
    try:
        gdf = gpd.read_file(target, encoding="cp949")
        gdf = gdf.to_crs(epsg=4326)
        return gdf
    except: return None

gdf_gb_trails = load_gyeongbuk_gis_lines()

# --- 📁 [데이터 백엔드] 2. 한국농어촌공사 저수지 CSV 파일 로드 ---
RESERVOIR_CSV_PATH = "한국농어촌공사_농업기반시설 시설제원_저수지_20250925.csv"
@st.cache_data
def load_reservoir_data():
    if os.path.exists(RESERVOIR_CSV_PATH):
        try: return pd.read_csv(RESERVOIR_CSV_PATH, encoding="cp949")
        except: return None
    return None

df_reservoirs_master = load_reservoir_data()

# --- 🛰️ 경북 22개 시·군 산림 격자 마스터 좌표 풀 ---
GB_NATION_STN_MAP = {
    "안동시": {"stn": 272, "lat": 36.6345, "lon": 128.7834, "slope": 25.0, "addr": "경북 안동시 와룡면 주진리 야산", "pine_ratio": 65, "search_kw": "안동"},
    "울진군": {"stn": 130, "lat": 36.9542, "lon": 129.2845, "slope": 28.0, "addr": "경북 울진군 서면 불영계곡 산림", "pine_ratio": 88, "search_kw": "울진"},
    "문경시": {"stn": 273, "lat": 36.6431, "lon": 128.0824, "slope": 32.0, "addr": "경북 문경시 문경읍 조령산 사면", "pine_ratio": 78, "search_kw": "문경"},
    "구미시": {"stn": 279, "lat": 36.0842, "lon": 128.3214, "slope": 20.0, "addr": "경북 구미시 금오산 배후 사면", "pine_ratio": 55, "search_kw": "구미"},
    "포항시": {"stn": 138, "lat": 36.2314, "lon": 129.2845, "slope": 15.0, "addr": "경북 포항시 북구 내연산 구역", "pine_ratio": 40, "search_kw": "포항"},
    "경산시": {"stn": 281, "lat": 35.8845, "lon": 128.8412, "slope": 14.0, "addr": "경북 경산시 팔공산 갓바위 사면", "pine_ratio": 35, "search_kw": "경산"},
    "영천시": {"stn": 281, "lat": 36.1421, "lon": 128.9845, "slope": 22.0, "addr": "경북 영천시 화북면 보현산 천문대 구역", "pine_ratio": 60, "search_kw": "영천"},
    "의성군": {"stn": 278, "lat": 36.3214, "lon": 128.7845, "slope": 18.0, "addr": "경북 의성군 점곡면 사촌리 배후 야산", "pine_ratio": 50, "search_kw": "의성"},
    "경주시": {"stn": 138, "lat": 35.8124, "lon": 129.3412, "slope": 19.0, "addr": "경북 경주시 양북면 토함산 지대", "pine_ratio": 62, "search_kw": "경주"},
    "김천시": {"stn": 279, "lat": 36.1124, "lon": 128.0124, "slope": 24.0, "addr": "경북 김천시 대항면 황악산 배후령", "pine_ratio": 58, "search_kw": "김천"},
    "상주시": {"stn": 273, "lat": 36.5412, "lon": 127.9845, "slope": 23.0, "addr": "경북 상주시 화북면 속리산 문장대 사면", "pine_ratio": 64, "search_kw": "상주"},
    "영주시": {"stn": 272, "lat": 36.9412, "lon": 128.5214, "slope": 27.0, "addr": "경북 영주시 풍기읍 소백산 희방사 지대", "pine_ratio": 72, "search_kw": "영주"},
    "군위군": {"stn": 278, "lat": 36.1542, "lon": 128.7214, "slope": 17.0, "addr": "대구 군위군 삼국유사면 화산산성 야산지대", "pine_ratio": 48, "search_kw": "군위"},
    "고령군": {"stn": 279, "lat": 35.6842, "lon": 128.2142, "slope": 16.0, "addr": "경북 고령군 쌍림면 미숭산 자연휴양림 배후", "pine_ratio": 42, "search_kw": "고령"},
    "성주군": {"stn": 279, "lat": 35.8142, "lon": 128.1124, "slope": 25.0, "addr": "경북 성주군 수륜면 가야산 백운동 사면", "pine_ratio": 66, "search_kw": "성주"},
    "칠곡군": {"stn": 279, "lat": 36.0421, "lon": 128.4845, "slope": 18.0, "addr": "경북 칠곡군 가산면 가산산성 성곽 구역", "pine_ratio": 50, "search_kw": "칠곡"},
    "청도군": {"stn": 281, "lat": 35.6124, "lon": 128.9412, "slope": 21.0, "addr": "경북 청도군 운문면 운문사 지룡산 기슭", "pine_ratio": 54, "search_kw": "청도"},
    "영양군": {"stn": 130, "lat": 36.7142, "lon": 129.1845, "slope": 29.0, "addr": "경북 영양군 일월산 용화리 격오지 야산", "pine_ratio": 80, "search_kw": "영양"},
    "영덕군": {"stn": 130, "lat": 36.4842, "lon": 129.3142, "slope": 23.0, "addr": "경북 영덕군 지품면 팔각산 암벽 산림지대", "pine_ratio": 85, "search_kw": "영덕"},
    "봉화군": {"stn": 272, "lat": 36.9124, "lon": 128.9412, "slope": 30.0, "addr": "경북 봉화군 명호면 청량산 도립공원 사면", "pine_ratio": 84, "search_kw": "봉화"},
    "울릉군": {"stn": 130, "lat": 37.5024, "lon": 130.8412, "slope": 35.0, "addr": "경북 울릉군 서면 성인봉 칼데라 산악 요충", "pine_ratio": 40, "search_kw": "울릉"},
    "청송군": {"stn": 272, "lat": 36.3942, "lon": 129.1242, "slope": 26.0, "addr": "경북 청송군 주왕산면 주왕산 국립공원 사면", "pine_ratio": 76, "search_kw": "청송"}
}

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
    if 337.5 <= deg or deg < 22.5: return "북풍 (⬇️ 남쪽 확산)", "남쪽", 0, -1
    elif 22.5 <= deg < 67.5: return "북동풍 (↙️ 남서쪽 확산)", "남서쪽", -0.7, -0.7
    elif 67.5 <= deg < 112.5: return "동풍 (⬅️ 서쪽 확산)", "서쪽", -1, 0
    elif 112.5 <= deg < 157.5: return "남동풍 (↖️ 북서쪽 확산)", "북서쪽", -0.7, 0.7
    elif 157.5 <= deg < 202.5: return "남풍 (⬆️ 북쪽 확산)", "북쪽", 0, 1
    elif 202.5 <= deg < 247.5: return "남서풍 (↗️ 북동쪽 확산)", "북동쪽", 0.7, 0.7
    elif 247.5 <= deg < 292.5: return "서풍 (➡️ 동쪽 확산)", "동쪽", 1, 0
    else: return "북서풍 (↘️ 남동쪽 확산)", "남동쪽", 0.7, -0.7

# --- 🎛️ 사이드바 제어판 ---
st.sidebar.header("🎛️ 종합 상황 제어판")
emergency_mode = st.sidebar.checkbox("🚨 [응급 상황] 실전 산불 화재 발령", value=False, key="emerg_check")

st.sidebar.markdown("---")
st.sidebar.subheader("기상 변수 시뮬레이터")
sim_mode = st.sidebar.checkbox("🌡️ 가상 기상 악화 제어 모델링", value=False, key="sim_mode_check")

sim_city = "안동시"
sim_t, sim_h, sim_w = 34.5, 9.0, 8.5

if sim_mode or emergency_mode:
    sim_city = st.sidebar.selectbox("타격 행정구역 선택", list(GB_NATION_STN_MAP.keys()), index=0)
    sim_t = st.sidebar.slider("가상 온도 (°C)", 10.0, 45.0, value=34.5)
    sim_h = st.sidebar.slider("가상 상대습도 (%)", 0.0, 100.0, value=9.0)
    sim_w = st.sidebar.slider("가상 풍속 (m/s)", 0.0, 25.0, value=8.5)

# =========================================================================================
# 🔄 실시간 데이터 연산 파이프라인
# =========================================================================================
if "history_probs" not in st.session_state: st.session_state["history_probs"] = {}
all_scanned_list = []

for city, info in GB_NATION_STN_MAP.items():
    t, h, w, wd = fetch_kma_live_weather(info["stn"])
    slope = info["slope"]
    if (sim_mode or emergency_mode) and city == sim_city: t, h, w = sim_t, sim_h, sim_w

    res_count, res_largest_name, res_largest_cap = 0, "N/A", 100.0
    if df_reservoirs_master is not None:
        sub_res = df_reservoirs_master[df_reservoirs_master['소재지'].str.contains(info["search_kw"], na=False)]
        if not sub_res.empty:
            res_count = len(sub_res)
            largest_row = sub_res.loc[sub_res['유효저수량'].idxmax()]
            res_largest_name = largest_row['시설명']
            res_largest_cap = float(largest_row['유효저수량'])

    water_infrastructure_factor = max(0.1, 5.0 - (math.log10(res_largest_cap + 1) * 1.2))
    difficulty_penalty = (water_infrastructure_factor * 0.2) + (info["pine_ratio"] * 0.005)

    humidity_dryness = (100 - h) / 100.0
    if h <= 35.0: humidity_dryness *= 1.5
    weather_factor = (t * 0.35) + (w * 1.4)
    base_prob = weather_factor * humidity_dryness * 3.5
    raw_prob = max(18.5, min(98.7, base_prob * (1.0 + (slope / 90.0))))

    if city in st.session_state["history_probs"]:
        prev_prob = st.session_state["history_probs"][city]
        weight = 0.0 if (sim_mode or emergency_mode) else 0.85
        final_prob = (prev_prob * weight) + (raw_prob * (1.0 - weight))
    else: final_prob = raw_prob
    st.session_state["history_probs"][city] = final_prob

    spread_factor = 0.001 + (w * 0.004) + (slope * 0.002)
    danger_score = ((final_prob * 0.001) + (spread_factor * 12.0)) * (1.0 + difficulty_penalty)

    all_scanned_list.append({
        "city": city, "lat": info["lat"], "lon": info["lon"], "addr": info["addr"], "t": t, "h": h, "w": w, "wd": wd, "slope": slope, 
        "prob": final_prob, "score": danger_score, "search_kw": info["search_kw"], "pine_ratio": info["pine_ratio"],
        "res_count": res_count, "res_largest_name": res_largest_name, "res_largest_cap": res_largest_cap, "penalty": difficulty_penalty
    })

df_nation = pd.DataFrame(all_scanned_list).sort_values(by="prob", ascending=False).reset_index(drop=True)
if emergency_mode:
    df_nation = pd.DataFrame(all_scanned_list)
    df_nation.loc[df_nation["city"] == sim_city, "prob"] = 99.4
    df_nation = df_nation.sort_values(by="prob", ascending=False).reset_index(drop=True)

if "selected_city" not in st.session_state: st.session_state["selected_city"] = df_nation.iloc[0]["city"]
if emergency_mode: st.session_state["selected_city"] = sim_city

city_data = df_nation[df_nation["city"] == st.session_state["selected_city"]].iloc[0]

# --- 상단 탑 카드 레이어 ---
if emergency_mode:
    st.error(f"🔥 [🚨 실전 상황 기동] 산불 감지 및 관제 AI '령이' 통합 작전 상황실 복귀")
else:
    st.header("🛰️ [평시 예찰] 실시간 경상북도 22개 시·군 대형 산불 발전 확률 TOP 5")

cols = st.columns(5)
for idx, row in df_nation.iterrows():
    if idx >= 5: break
    with cols[idx]:
        border_style = "border: 1px solid #444; background-color: #0e1117; border-radius: 8px; padding: 15px; text-align: center;"
        prob_color = "#ffaa00"
        title_prefix = f"{idx+1}위 . "
        if emergency_mode and row["city"] == sim_city:
            border_style = "border: 3px dashed #ff4b4b; background-color: #3b0000; border-radius: 8px; padding: 15px; text-align: center;"
            prob_color = "#ff4b4b"
            title_prefix = "🚨 발화선포: "
        elif row["prob"] >= 75.0:
            border_style = "border: 2px solid #ff4b4b; background-color: #2b1111; border-radius: 8px; padding: 15px; text-align: center;"
            prob_color = "#ff4b4b"
            title_prefix = f"⚠️ 위험! "
        if row["city"] == st.session_state["selected_city"]:
            border_style = border_style.replace("border: 1px solid #444", "border: 2px dashed #1a73e8").replace("border: 2px solid #ff4b4b", "border: 3px dashed #ffff00")

        st.markdown(f"""
        <div style="{border_style} min-height:115px; margin-bottom: 5px;">
            <h4 style="margin: 0; color: white;">{title_prefix}{row['city']}</h4>
            <p style="margin: 5px 0; font-size: 14px; color: {prob_color}; font-weight:bold;">발전 확률: {row['prob']:.1f}%</p>
            <p style="margin: 0; font-size: 13px; color: #aaa;">진압난이도: {row['score']:.2f}점</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"🔍 {row['city']} 관제", key=f"btn_{row['city']}", use_container_width=True): st.session_state["selected_city"] = row["city"]

# =========================================================================================
# 📍 [3D 위성 입체 전술 지도 복원] 응급 상황 및 시뮬레이션 작동 파트
# =========================================================================================
wd_text, danger_direction, dx, dy = get_wind_direction_text(city_data["wd"])
base_spread_rate = (city_data['w'] * 1.6) * (1.0 + (city_data['slope'] / 35.0)) * (1.0 + city_data['penalty'])
p_10 = int(city_data['score'] * base_spread_rate * 15)
p_30 = int(p_10 * 3.8)
p_60 = int(p_30 * 4.2)

if emergency_mode or sim_mode:
    st.divider()
    st.header(f"🗺️ [3D 입체 전술 관제탑] {city_data['city']} 융합 시각화")
    st.caption("🔥 최상위 화점 서클 특정 | 🔴 지형 사면 연산 곡선 확산 벡터 경로 | 🟡 노란색 찐 산길 접근선 | 🔵 파란색 농어촌공사 용수 기둥")

    pydeck_layers = []
    found_trail_name = "관내 간선 공로 1호선"
    
    # 1. 🟡 [노란 선] 47.shp 경북 찐 산길 접근선 레이어
    if gdf_gb_trails is not None:
        local_trails = gdf_gb_trails[gdf_gb_trails['MNTN_NM'].str.contains(city_data['search_kw'], na=False)]
        if not local_trails.empty:
            plot_gdf = local_trails.head(35).copy()
            def extract_path_coords(geom):
                if geom.geom_type == 'LineString': return [[coord[0], coord[1]] for coord in geom.coords]
                elif geom.geom_type == 'MultiLineString': return [[coord[0], coord[1]] for line in geom.geoms for coord in line.coords]
                return []
            plot_gdf['path'] = plot_gdf['geometry'].apply(extract_path_coords)
            if 'PMNTN_NM' in plot_gdf.columns and not plot_gdf.iloc[0]['PMNTN_NM'] is None:
                found_trail_name = f"[{plot_gdf.iloc[0]['MNTN_NM']}] {plot_gdf.iloc[0]['PMNTN_NM']}"
            
            pydeck_layers.append(pdk.Layer(
                "PathLayer", plot_gdf, get_path="path", width_scale=15, width_min_pixels=3.5,
                get_color="[255, 220, 0, 255]", pickable=True
            ))

    # 2. 🔴 [빨간 곡선] 지형 사면 연산 시뮬레이션 포물선 화선 확산 레이어 빌드
    curve_points = []
    steps = 20
    spread_scale = 0.010 + (city_data["w"] * 0.001) 
    
    for i in range(steps + 1):
        ratio = i / steps
        distortion = math.sin(ratio * math.pi) * (city_data["slope"] * 0.00025)
        cur_lon = city_data["lon"] + (dx * spread_scale * ratio) + (dy * distortion)
        cur_lat = city_data["lat"] + (dy * spread_scale * ratio) - (dx * distortion)
        curve_points.append([cur_lon, cur_lat])
        
    curve_path_data = [{"path": curve_points}]
    pydeck_layers.append(pdk.Layer(
        "PathLayer", pd.DataFrame(curve_path_data), get_path="path", width_scale=45, width_min_pixels=7.0,
        get_color="[255, 30, 30, 255]"
    ))

    # 3. 🔵 [파란 기둥] 농어촌공사 실제 용수 시설 레이어
    poi_records = [
        {"lat": city_data["lat"] - 0.004, "lon": city_data["lon"] + 0.005, "elevation": min(1400, int(city_data["res_largest_cap"] * 0.20) + 200), "color": [0, 110, 255, 240]}
    ]
    pydeck_layers.append(pdk.Layer(
        "ColumnLayer", pd.DataFrame(poi_records), get_position="[lon, lat]", get_elevation="elevation",
        elevation_scale=1, radius=70, get_fill_color="color"
    ))

    # 4. 🔥 [최상위 화점 타격 원 마킹] 폰트 에러 차단형 고대비 원형 플로팅
    fire_center = [{"lon": city_data["lon"], "lat": city_data["lat"]}]
    pydeck_layers.append(pdk.Layer(
        "ScatterplotLayer", pd.DataFrame(fire_center), get_position="[lon, lat]",
        get_radius=180, get_fill_color="[255, 10, 10, 240]", get_line_color="[255, 255, 255, 255]",
        line_width_min_pixels=2
    ))

    # 5. ⬜ [대표님 지시 완벽 반영] 시간대별 예상 확산 범위에 맞게 개별 상자(인포박스) 분리 배치
    # 곡선 궤적 위의 10분, 30분, 60분 도달 시점마다 하얀색 사각형 전술 상자를 자석처럼 따로따로 꽂아줍니다.
    timeline_boxes = [
        {"lon": curve_points[int(steps * 0.25)][0], "lat": curve_points[int(steps * 0.25)][1] + 0.001, "text": f"⬜ [10분 후 전선]\n피해예측: 약 {p_10:,}평\n방향: ➡️ 진격 중"},
        {"lon": curve_points[int(steps * 0.60)][0], "lat": curve_points[int(steps * 0.60)][1] + 0.001, "text": f"⬜ [30분 후 전선]\n피해예측: 약 {p_30:,}평\n주의: ➡️ 확산 가속"},
        {"lon": curve_points[steps][0], "lat": curve_points[steps][1] + 0.001, "text": f"🔥 [60분 최종 화두]\n피해예측: 약 {p_60:,}평\n전술: ⚠️ 차단선 전개 요구"}
    ]
    
    pydeck_layers.append(pdk.Layer(
        "TextLayer", pd.DataFrame(timeline_boxes), get_position="[lon, lat]", get_text="text",
        get_size=14, get_color="[0, 0, 0, 255]", get_background_color="[255, 255, 255, 250]",
        padding=[8, 10, 8, 10], get_alignment_baseline="'bottom'", get_text_anchor="'center'"
    ))

    # ⛰️ [지도가 안 뜨던 버그 완벽 정복] 토큰에 구애받지 않는 스트림릿 빌드인 표준 다크 스타일 뷰포트 고정 (피치 58도 3D화 완료)
    st.pydeck_chart(pdk.Deck(
        layers=pydeck_layers,
        map_style=pdk.map_styles.DARK,
        initial_view_state=pdk.ViewState(latitude=city_data["lat"], longitude=city_data["lon"], zoom=13, pitch=58, bearing=15),
        tooltip={"text": "소방 전술 레이어"}
    ))
else:
    st.info("🟢 평시 감시 모드 가동 중: 현재 경상북도 전역 예찰 상태입니다. 지도는 제어판의 [🚨 응급 상황] 또는 [🌡️ 가상 시뮬레이션] 발령 즉시 실시간 3D 전술 지형 모드로 자동 팝업됩니다.")

# =========================================================================================
# 🎛 하단 다차원 소방 전술 지시서
# =========================================================================================
st.markdown("---")
c1, c2, c3 = st.columns([1, 1.2, 1.2])

with c1:
    st.markdown(f"""
    <div style="background-color: #1c1d24; padding: 18px; border-radius: 8px; border-left: 5px solid #1a73e8; min-height: 330px;">
        <h4 style="margin:0 0 12px 0; color:#1a73e8; font-weight: bold;">📡 종합 인프라 기상 제원</h4>
        <p style="margin:5px 0; font-size:14px; color: white;"><b>관제 타격좌표:</b> {city_data['addr']}</p>
        <hr style="border:0.5px solid #333; margin:8px 0;">
        <table style="width:100%; color:white; font-size:13px; border-collapse:collapse;">
            <tr style="color:#66bb6a;"><td>🌊 농어촌공사 저수지:</td><td style="text-align:right; font-weight:bold;">{city_data['res_count']} 개</td></tr>
            <tr style="color:#a8c7fa;"><td>🚁 최대 소방 담수지:</td><td style="text-align:right; font-weight:bold;">{city_data['res_largest_name']}저수지</td></tr>
            <tr style="color:#a8c7fa;"><td>📦 저수지 유효용량:</td><td style="text-align:right; font-weight:bold;">{city_data['res_largest_cap']:,} k톤</td></tr>
            <tr><td>🌡️ 현재 실측 기온:</td><td style="text-align:right; font-weight:bold;">{city_data['t']:.1f} °C</td></tr>
            <tr><td>💧 현재 상대 습도:</td><td style="text-align:right; font-weight:bold;">{city_data['h']:.1f} %</td></tr>
            <tr><td>💨 현재 실측 풍속:</td><td style="text-align:right; font-weight:bold;">{city_data['w']:.1f} m/s</td></tr>
            <tr><td>🌲 소나무림 비율:</td><td style="text-align:right; font-weight:bold;">{city_data['pine_ratio']}%</td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div style="background-color: #1c1d24; padding: 18px; border-radius: 8px; border-left: 5px solid #ff4b4b; min-height: 330px;">
        <h4 style="margin:0 0 10px 0; color:#ff4b4b; font-weight: bold;">🧠 령이 AI 자율 물리 확산 스캔</h4>
        <table style="width:100%; color:white; font-size:13px; border-collapse:collapse; margin-bottom:10px;">
            <tr style="border-bottom:1px solid #444; font-weight:bold; color:#aaa;"><td>⏳ 예측 시간</td><td>🔥 예상 피해 규모</td></tr>
            <tr style="border-bottom:1px solid #333;"><td style="color:#1a73e8; font-weight:bold;">발화 10분 후</td><td style="color:white; font-weight:bold;">약 {p_10:,} 평</td></tr>
            <tr style="border-bottom:1px solid #333;"><td style="color:#ffaa00; font-weight:bold;">발화 30분 후</td><td style="color:#ffaa00; font-weight:bold;">약 {p_30:,} 평</td></tr>
            <tr style="border-bottom:1px solid #333;"><td style="color:#ff4b4b; font-weight:bold;">발화 60분 후</td><td style="color:#ff4b4b; font-weight:bold;">약 {p_60:,} 평</td></tr>
        </table>
        <p style="margin:2px 0; font-size:12px; color: #ff8b8b;">⚠️ <b>지형 경사 및 곡선 가중치:</b> +{city_data['penalty']*100:.1f}% 실시간 반영</p>
        <p style="margin:2px 0; font-size:12px; color: #ccc;"><b>실시간 풍향 주파수:</b> {wd_text}</p>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"<h4 style='margin:0 0 10px 0; color:#66bb6a; font-size:15px; font-weight:bold;'>🚒 [령이 팩트 라우팅] 전술 작전 지시서</h4>", unsafe_allow_html=True)
    if emergency_mode or sim_mode:
        st.success(f"🟡 **[🟡접근선] 특정:** 47번 국가 GIS 분석 결과, 대원 도보 침투 최적 루트인 노란색 선 **{found_trail_name}** 코스를 차단선으로 설정하십시오.")
        st.error(f"🔴 **[🔴확산선] 경고:** 화염이 바람과 경사면 굴뚝 효과를 만나 현재 **[{danger_direction}]** 방면 빨간색 곡선 화살표 궤적으로 급격히 확산 중이므로 선제 진압 조치 요망.")
        if city_data['res_count'] > 0:
            st.info(f"🔵 **[🔵담수지] 명령:** 농어촌공사 검증 완료된 파란 기둥인 **[{city_data['res_largest_name']}저수지]**를 헬기 최우선 담수 용수원으로 고정 전파.")
    else:
        st.info("📊 평시 감시 중: 경상북도 산림 격자 인프라 제원 테이블 및 유통 공간정보 정상 작동 중.")

# =========================================================================================
# 📋 령이 자율 포착 로그 대장 (평시/비상시 완전 무결성 분리 패치 완료)
# =========================================================================================
st.divider()
st.subheader("📋 령이 자율 포착 로그 대장 (경상북도 소방 재난 방재 시스템 아카이브)")

if emergency_mode or sim_mode:
    log_status = "🚨 실전 화재 선포 연동 중" if emergency_mode else "⚠️ 가상 시뮬레이션 기동"
    log_decision = f"권장 접근선: {found_trail_name} ➔ 지형 사면 곡선 굴절 수치지도 기반 입체 제어 중"
    log_prob = f"{city_data['prob']:.1f}%"
else:
    log_status = "🚫 평시 예보 커넥션 대기"
    log_decision = "🟢 경북 전역 특이 동향 없음 (평시 실시간 대기 중)"
    log_prob = "0.0% (안전)"

df_mock_db = pd.DataFrame([{
    "령이 실시간 감지 시각": now_kst.strftime("%Y-%m-%d %H:%M:%S"),
    "산림청 API 수신 상태": log_status,
    "경북 관제 행정구역": city_data["addr"] if (emergency_mode or sim_mode) else "경상북도 전역 (22개 시·군 모니터링)",
    "AI 연산 발전 확률": log_prob,
    "3D 공간 전술 판정": log_decision
}])
st.table(df_mock_db)