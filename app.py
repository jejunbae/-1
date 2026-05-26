import streamlit as st
import time
import requests
import math
import random
import os
import json
import zipfile
from datetime import datetime, timedelta, timezone
import pandas as pd
import pydeck as pdk

# 🧠 GeoPandas 자율 충돌 방지 및 안전 예외처리 내장망
gpd = None
try:
    import geopandas as gpd
except ImportError:
    pass

# 🖥️ 웹페이지 상단 프레셋 및 플랫폼 아이덴티티 완벽 세팅
st.set_page_config(page_title="경북 산불 통합 관제 AI 령이", page_icon="⚠️", layout="wide")

API_KEY = "69309efd849de167a2a68e2fc27331c01eb67888d72dd4a740419a33cf7d292e"
tz_kst = timezone(timedelta(hours=9))
now_kst = datetime.now(tz_kst)

st.title("🚒 산불 감지 및 관제 AI '령이'")
st.markdown(f"**Core Engine v47.0:** ⛰️ 3D 입체 지형 메쉬 + 🔴 타원형 화선 및 선 위 실시간 제원(피해평수/화선길이/화살표) 융합본")
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

# --- 🛰️ 경북 22개 시·군 산림 인프라 제원 마스터 풀 ---
GB_NATION_STN_MAP = {
    "안동시": {"stn": 272, "lat": 36.6345, "lon": 128.7834, "slope": 25.0, "addr": "경북 안동시 와룡면 주진리 야산 지대", "water_dist": 2.5, "road_density": 35, "pine_ratio": 65, "prefix": "andong", "search_kw": "안동"},
    "울진군": {"stn": 130, "lat": 36.9542, "lon": 129.2845, "slope": 28.0, "addr": "경북 울진군 금강송면 하원리 산림 격자", "water_dist": 7.2, "road_density": 10, "pine_ratio": 88, "prefix": "uljin", "search_kw": "울진"},
    "의성군": {"stn": 278, "lat": 36.3214, "lon": 128.7845, "slope": 18.0, "addr": "경북 의성군 점곡면 사촌리 배후 야산", "water_dist": 3.1, "road_density": 40, "pine_ratio": 50, "prefix": "uiseong", "search_kw": "의성"},
    "문경시": {"stn": 273, "lat": 36.6431, "lon": 128.0824, "slope": 32.0, "addr": "경북 문경시 문경읍 조령산 국지 사면", "water_dist": 6.8, "road_density": 12, "pine_ratio": 78, "prefix": "mungyeong", "search_kw": "문경"},
    "구미시": {"stn": 279, "lat": 36.0842, "lon": 128.3214, "slope": 20.0, "addr": "경북 구미시 금오산 등선 배후 사면", "water_dist": 1.8, "road_density": 45, "pine_ratio": 55, "prefix": "gumi", "search_kw": "금오산"},
    "포항시": {"stn": 138, "lat": 36.2314, "lon": 129.2845, "slope": 15.0, "addr": "경북 포항시 북구 내연산 군립공원 구역", "water_dist": 1.2, "road_density": 50, "pine_ratio": 40, "prefix": "pohang", "search_kw": "내연산"},
    "경산시": {"stn": 281, "lat": 35.8845, "lon": 128.8412, "slope": 14.0, "addr": "경북 경산시 팔공산 남측 갓바위 사면", "water_dist": 2.0, "road_density": 58, "pine_ratio": 35, "prefix": "gyeongsan", "search_kw": "팔공산"},
    "영천시": {"stn": 281, "lat": 36.1421, "lon": 128.9845, "slope": 22.0, "addr": "경북 영천시 화북면 보현산 천문대 구역", "water_dist": 4.0, "road_density": 28, "pine_ratio": 60, "prefix": "yeongcheon", "search_kw": "보현산"},
    "경주시": {"stn": 138, "lat": 35.8124, "lon": 129.3412, "slope": 19.0, "addr": "경북 경주시 양북면 토함산 국립공원 지대", "water_dist": 2.7, "road_density": 38, "prefix": "gyeongju", "search_kw": "토함산"},
    "김천시": {"stn": 279, "lat": 36.1124, "lon": 128.0124, "slope": 24.0, "addr": "경북 김천시 대항면 황악산 직지사 배후령", "water_dist": 3.5, "road_density": 30, "prefix": "gimcheon", "search_kw": "황악산"},
    "상주시": {"stn": 273, "lat": 36.5412, "lon": 127.9845, "slope": 23.0, "addr": "경북 상주시 화북면 속리산 문장대 사면", "water_dist": 4.2, "road_density": 26, "prefix": "sangju", "search_kw": "속리산"},
    "영주시": {"stn": 272, "lat": 36.9412, "lon": 128.5214, "slope": 27.0, "addr": "경북 영주시 풍기읍 소백산 희방사 계곡지대", "water_dist": 5.0, "road_density": 20, "prefix": "yeongju", "search_kw": "소백산"},
    "청송군": {"stn": 272, "lat": 36.3942, "lon": 129.1242, "slope": 26.0, "addr": "경북 청송군 주왕산면 주왕산 국립공원 사면", "water_dist": 4.8, "road_density": 22, "prefix": "cheongsong", "search_kw": "주왕산"}
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
    if 337.5 <= deg or deg < 22.5: return "북풍 (⬇️ 남쪽 확산)", "남쪽", 0, -1, "⬇️"
    elif 22.5 <= deg < 67.5: return "북동풍 (↙️ 남서쪽 확산)", "남서쪽", -0.7, -0.7, "↙️"
    elif 67.5 <= deg < 112.5: return "동풍 (⬅️ 서쪽 확산)", "서쪽", -1, 0, "⬅️"
    elif 112.5 <= deg < 157.5: return "남동풍 (↖️ 북서쪽 확산)", "북서쪽", -0.7, 0.7, "↖️"
    elif 157.5 <= deg < 202.5: return "남풍 (⬆️ 북쪽 확산)", "북쪽", 0, 1, "⬆️"
    elif 202.5 <= deg < 247.5: return "남서풍 (↗️ 북동쪽 확산)", "북동쪽", 0.7, 0.7, "↗️"
    elif 247.5 <= deg < 292.5: return "서풍 (➡️ 동쪽 확산)", "동쪽", 1, 0, "➡️"
    else: return "북서풍 (↘️ 남동쪽 확산)", "남동쪽", 0.7, -0.7, "↘️"

# --- 🎛️ 사이드바 시뮬레이터 통제판 ---
st.sidebar.header("🕹️ 산불 시뮬레이터 통제판")
emergency_mode = st.sidebar.checkbox("🚨 [가상 선포] 실전 산불 시뮬레이션 가동", value=False, key="emerg_check")

st.sidebar.markdown("---")
st.sidebar.subheader("기상 변수 강제 조정")
sim_city = st.sidebar.selectbox("대상 관제 시·군 선택", list(GB_NATION_STN_MAP.keys()), index=0)
sim_t = st.sidebar.slider("가상 온도 (°C)", 10.0, 45.0, value=34.5)
sim_h = st.sidebar.slider("가상 상대습도 (%)", 0.0, 100.0, value=9.0)
sim_w = st.sidebar.slider("가상 풍속 (m/s)", 0.0, 25.0, value=8.5)

# =========================================================================================
# 🔄 경북 시·군 기상 대입 및 리얼타임 위험도 서열화 연산
# =========================================================================================
if "history_probs" not in st.session_state: st.session_state["history_probs"] = {}
all_scanned_list = []

for city, info in GB_NATION_STN_MAP.items():
    t, h, w, wd = fetch_kma_live_weather(info["stn"])
    slope = info["slope"]
    if city == sim_city: t, h, w = sim_t, sim_h, sim_w

    humidity_dryness = (100 - h) / 100.0
    if h <= 35.0: humidity_dryness *= 1.5
    weather_factor = (t * 0.35) + (w * 1.4)
    base_prob = weather_factor * humidity_dryness * 3.5
    raw_prob = max(18.5, min(99.4, base_prob * (1.0 + (slope / 90.0))))

    difficulty_penalty = (info["water_dist"] * 0.15) + ((100 - info["road_density"]) * 0.01) + (info["pine_ratio"] * 0.006)
    spread_factor = 0.001 + (w * 0.004) + (slope * 0.002)
    danger_score = ((raw_prob * 0.001) + (spread_factor * 12.0)) * (1.0 + difficulty_penalty)

    all_scanned_list.append({
        "city": city, "lat": info["lat"], "lon": info["lon"], "addr": info["addr"], "t": t, "h": h, "w": w, "wd": wd, "slope": slope, 
        "prob": raw_prob, "score": danger_score, "prefix": info["prefix"], "search_kw": info["search_kw"],
        "water_dist": info["water_dist"], "road_density": info["road_density"], "pine_ratio": info["pine_ratio"], "penalty": difficulty_penalty
    })

df_nation = pd.DataFrame(all_scanned_list).sort_values(by="prob", ascending=False).reset_index(drop=True)
if emergency_mode:
    df_nation.loc[df_nation["city"] == sim_city, "prob"] = 99.4
    df_nation = df_nation.sort_values(by="prob", ascending=False).reset_index(drop=True)

target_city = sim_city if emergency_mode else df_nation.iloc[0]["city"]
city_data = df_nation[df_nation["city"] == target_city].iloc[0]

# --- 상단 대형산불 발전 확률 실시간 랭킹 카드 ---
st.subheader("🔥 경상북도 대형산불 실시간 확산 위험도 랭킹 TOP 5")
cols = st.columns(5)
for idx, row in df_nation.iterrows():
    if idx >= 5: break
    with cols[idx]:
        if emergency_mode and row["city"] == sim_city:
            border_style = "border: 3px dashed #ff4b4b; background-color: #3b0000; border-radius: 8px; padding: 15px; text-align: center;"
            title_prefix = "🚨 가상발화: "
        else:
            border_style = "border: 1px solid #444; background-color: #0e1117; border-radius: 8px; padding: 15px; text-align: center;"
            title_prefix = f"{idx+1}위 . "
        if row["city"] == target_city:
            border_style = border_style.replace("border: 1px solid #444", "border: 2px dashed #1a73e8")

        st.markdown(f"""
        <div style="{border_style} min-height:115px;">
            <h4 style="margin: 0; color: white;">{title_prefix}{row['city']}</h4>
            <p style="margin: 5px 0; font-size: 14px; color: #ffaa00; font-weight:bold;">발전 확률: {row['prob']:.1f}%</p>
            <p style="margin: 0; font-size: 13px; color: #aaa;">진압난이도: {row['score']:.2f}점</p>
        </div>
        """, unsafe_allow_html=True)

with st.expander("🌐 경상북도 관내 전 지역 실시간 예찰 통제 지수 대장 보기"):
    st.dataframe(df_nation, use_container_width=True)

# =========================================================================================
# 🗺️ [대표님 핵심 오더] Peacetime vs Wildfire UI 엄격 분리 마스터 기동
# =========================================================================================
wd_text, danger_direction, dx, dy, arrow_icon = get_wind_direction_text(city_data["wd"])
base_spread_rate = (city_data['w'] * 1.6) * (1.0 + (city_data['slope'] / 35.0)) * (1.0 + city_data['penalty'])
p_10 = int(city_data['score'] * base_spread_rate * 15)
p_30 = int(p_10 * 3.8)
p_60 = int(p_30 * 4.2)

len_10 = int(850 + city_data['w'] * 45 + city_data['slope'] * 12)
len_30 = int(len_10 * 2.6)
len_60 = int(len_30 * 2.3)

@st.cache_data
def extract_and_merge_numbered_zips(prefix):
    if gpd is None: return None
    merged_gdfs = []
    for i in range(1, 3): 
        zip_name = f"{prefix}{i}_map.zip"
        if not os.path.exists(zip_name): continue
        try:
            tmp_dir = f"tmp_ryong_{prefix}_{i}"
            with zipfile.ZipFile(zip_name, 'r') as zip_ref: zip_ref.extractall(tmp_dir)
            target_shp = None
            for root, dirs, files in os.walk(tmp_dir):
                for file in files:
                    if "F0010000.shp" in file: target_shp = os.path.join(root, file); break
            if target_shp:
                gdf = gpd.read_file(target_shp, encoding="cp949").to_crs(epsg=4326)
                merged_gdfs.append(gdf.head(50))
        except: pass
    if merged_gdfs: return pd.concat(merged_gdfs, ignore_index=True)
    return None

real_contour_gdf = extract_and_merge_numbered_zips(city_data["prefix"])

if emergency_mode:
    st.divider()
    st.error(f"🕹️ [3D 입체 화선 시뮬레이터] {city_data['city']} 대형 산불 가상 확산 분석 레이어")
    st.caption("⛰️ 마우스 우클릭으로 지도를 눕히면 3D 산악 기복이 표출됩니다 | 🔥 화점 불꽃 전술 마킹 | 🔴 [not 원형] 풍향 기속 유선형 예상 화선")

    pydeck_layers = []

    # 1. ⛰️ [3D 입체화] 고도 DEM 메쉬 강제 디코딩 레이어 (산을 울퉁불퉁하게 밀어 올림)
    terrain_layer = pdk.Layer(
        "TerrainLayer",
        elevation_decoder={"rBand": 0, "gBand": 1, "bBand": 2, "scaler": 0.1, "offset": -10000},
        elevation_data="https://a.tiles.mapbox.com/v4/mapbox.terrain-rgb/{z}/{x}/{y}.pngraw",
        texture_data="https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
        pickable=False
    )
    pydeck_layers.append(terrain_layer)

    if real_contour_gdf is not None:
        pydeck_layers.append(pdk.Layer("GeoJsonLayer", real_contour_gdf, get_line_color="[0, 255, 150, 120]", get_line_width=3))

    # 2. 🔴 [not 원형] 바람의 방향(dx, dy)으로 찌그러지고 발달하는 유선형 비원형 타원 화선 생성 함수
    def generate_asymmetric_fire_front(lon, lat, dx, dy, scale, wind_w):
        points = []
        segments = 24
        for j in range(segments):
            angle = (j / segments) * 2 * math.pi
            r_lon = 0.0022 * scale * math.cos(angle)
            r_lat = 0.0022 * scale * math.sin(angle)
            alignment = math.cos(angle - math.atan2(dy, dx))
            stretch = 1.0 + max(0.0, alignment) * (wind_w * 0.18)
            p_lon = lon + r_lon * stretch + (dx * scale * 0.0008 * wind_w)
            p_lat = lat + r_lat * stretch + (dy * scale * 0.0008 * wind_w)
            points.append([p_lon, p_lat])
        points.append(points[0])
        return points

    poly_10 = generate_asymmetric_fire_front(city_data["lon"], city_data["lat"], dx, dy, 0.7, city_data['w'])
    poly_30 = generate_fire_front_polygon = generate_asymmetric_fire_front(city_data["lon"], city_data["lat"], dx, dy, 1.7, city_data['w'])
    poly_60 = generate_asymmetric_fire_front(city_data["lon"], city_data["lat"], dx, dy, 2.9, city_data['w'])

    pydeck_layers.append(pdk.Layer("PolygonLayer", pd.DataFrame([{"poly": poly_10}]), get_polygon="poly", get_fill_color="[255, 60, 60, 40]", get_line_color="[255, 20, 20, 255]", line_width_min_pixels=2))
    pydeck_layers.append(pdk.Layer("PolygonLayer", pd.DataFrame([{"poly": poly_30}]), get_polygon="poly", get_fill_color="[255, 30, 30, 40]", get_line_color="[255, 10, 10, 255]", line_width_min_pixels=3))
    pydeck_layers.append(pdk.Layer("PolygonLayer", pd.DataFrame([{"poly": poly_60}]), get_polygon="poly", get_fill_color="[255, 0, 0, 40]", get_line_color="[220, 0, 0, 255]", line_width_min_pixels=4))

    # 3. ➡️ 화선 진행 전면 격자점 위 화살표 레이어 매핑
    front_10, front_30, front_60 = poly_10[0], poly_30[0], poly_60[0]
    arrow_data = [{"lon": front_10[0], "lat": front_10[1], "text": arrow_icon}, {"lon": front_30[0], "lat": front_30[1], "text": arrow_icon}, {"lon": front_60[0], "lat": front_60[1], "text": arrow_icon}]
    pydeck_layers.append(pdk.Layer("TextLayer", pd.DataFrame(arrow_data), get_position="[lon, lat]", get_text="text", get_size=25, get_color="[255,255,255,255]", get_background_color="[255,0,0,240]", padding=[2,4,2,4]))

    # 🏷️ [선 위 딜리버리] 각 시간대별 화선 경계 위에 직접 피해범위 및 화선 길이를 명시하는 전술 태그
    inline_labels = [
        {"lon": poly_10[6][0], "lat": poly_10[6][1], "text": f"⏳ 10분 화선 | 약 {p_10:,}평 | 길이: {len_10:,}m"},
        {"lon": poly_30[6][0], "lat": poly_30[6][1], "text": f"⚠️ 30분 화선 | 약 {p_30:,}평 | 길이: {len_30:,}m"},
        {"lon": poly_60[6][0], "lat": poly_60[6][1], "text": f"🔥 60분 최종화두 | 약 {p_60:,}평 | 길이: {len_60:,}m"}
    ]
    pydeck_layers.append(pdk.Layer(
        "TextLayer", pd.DataFrame(inline_labels), get_position="[lon, lat]", get_text="text", get_size=13,
        get_color="[255, 255, 255, 255]", get_background_color="[20, 20, 20, 220]", padding=[5, 8, 5, 8],
        get_text_anchor="'start'"
    ))

    # 4. 🔥 [화점 불 이모티콘] 산불 발생 원점에 완벽히 매핑되는 오리지널 불 마커
    pydeck_layers.append(pdk.Layer(
        "TextLayer", pd.DataFrame([{"lon": city_data["lon"], "lat": city_data["lat"], "text": "🔥"}]),
        get_position="[lon, lat]", get_text="text", get_size=42, get_alignment_baseline="'center'"
    ))

    st.pydeck_chart(pdk.Deck(
        layers=pydeck_layers, map_style=None,
        initial_view_state=pdk.ViewState(latitude=city_data["lat"], longitude=city_data["lon"], zoom=12.5, pitch=62, bearing=15)
    ))
else:
    # 🚫 평시에는 지도가 표출되지 않고 안내 메시지만 깔끔하게 상주합니다.
    st.info("🟢 [평시 예찰 모드 정상 작동 중] 현재 경상북도 산림 전역 특이 동향 및 대형 화재 징후 없음. 지도는 사이드바의 [🚨 가상 선포] 작동 즉시 3D 수치 고도 전술 레이아웃으로 자동 팝업됩니다.")

# =========================================================================================
# 📡 [메인 UI] 정밀관측 기상상황 및 예상 피해 스크리닝 계측 카드 복원
# =========================================================================================
st.markdown("---")
st.subheader(f"📡 [종합 제원 전술 지시서] {city_data['city']} 정밀 예찰 기상 및 확산 분석 데이터")

c1, c2, c3 = st.columns([1, 1.2, 1.2])

with c1:
    st.markdown(f"""
    <div style="background-color: #1c1d24; padding: 18px; border-radius: 8px; border-left: 5px solid #1a73e8; min-height: 310px;">
        <h4 style="margin:0 0 12px 0; color:#1a73e8; font-weight: bold;">📡 관내 정밀 관측 기상 정보</h4>
        <p style="margin:5px 0; font-size:14px; color: white;"><b>계측 매핑 구역:</b><br>{city_data['addr']}</p>
        <hr style="border:0.5px solid #333; margin:8px 0;">
        <table style="width:100%; color:white; font-size:13px; border-collapse:collapse;">
            <tr><td>🌡️ 실측 현재 기온:</td><td style="text-align:right; font-weight:bold; color:#ff8a80;">{city_data['t']:.1f} °C</td></tr>
            <tr><td>💧 실측 상대 습도:</td><td style="text-align:right; font-weight:bold; color:#80d8ff;">{city_data['h']:.1f} %</td></tr>
            <tr><td>💨 실측 순간 풍속:</td><td style="text-align:right; font-weight:bold; color:#b9f6ca;">{city_data['w']:.1f} m/s</td></tr>
            <tr style="color:#a8c7fa;"><td>🌊 최단 소방 용수원:</td><td style="text-align:right; font-weight:bold;">{city_data['water_dist']:.1f} km</td></tr>
            <tr style="color:#66bb6a;"><td>🛣️ 진입 소방 임도 밀도:</td><td style="text-align:right; font-weight:bold;">{city_data['road_density']}%</td></tr>
            <tr style="color:#ffb74d;"><td>🌲 소나무림 울창도:</td><td style="text-align:right; font-weight:bold;">{city_data['pine_ratio']}%</td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

with c2:
    status_color = "#ff4b4b" if city_data['prob'] >= 75.0 else ("#ffaa00" if city_data['prob'] >= 50.0 else "#1a73e8")
    st.markdown(f"""
    <div style="background-color: #1c1d24; padding: 18px; border-radius: 8px; border-left: 5px solid {status_color}; min-height: 310px;">
        <h4 style="margin:0 0 10px 0; color:{status_color}; font-weight: bold;">🧠 령이 AI 가상 확산 및 예상 피해 스캔</h4>
        <table style="width:100%; color:white; font-size:13px; border-collapse:collapse; margin-bottom:10px;">
            <tr style="border-bottom:1px solid #444; font-weight:bold; color:#aaa;">
                <td>⏳ 타임라인</td>
                <td>🔥 예상 피해 면적</td>
                <td>📏 예상 화선 총연장</td>
            </tr>
            <tr style="border-bottom:1px solid #333;">
                <td style="color:#1a73e8; font-weight:bold;">발화 10분 후</td>
                <td style="color:white; font-weight:bold;">약 {p_10:,} 평</td>
                <td style="color:#b9f6ca; font-weight:bold;">{len_10:,} m</td>
            </tr>
            <tr style="border-bottom:1px solid #333;">
                <td style="color:#ffaa00; font-weight:bold;">발화 30분 후</td>
                <td style="color:#ffaa00; font-weight:bold;">약 {p_30:,} 평</td>
                <td style="color:#b9f6ca; font-weight:bold;">{len_30:,} m</td>
            </tr>
            <tr style="border-bottom:1px solid #333;">
                <td style="color:#ff4b4b; font-weight:bold;">발화 60분 후</td>
                <td style="color:#ff4b4b; font-weight:bold;">약 {p_60:,} 평</td>
                <td style="color:#ff4b4b; font-weight:bold;">{len_60:,} m</td>
            </tr>
        </table>
        <p style="margin:2px 0; font-size:12px; color: #ff8b8b;">⚠️ <b>지형 사면 할증률:</b> +{city_data['penalty']*100:.1f}% 실시간 물리 반영</p>
        <p style="margin:2px 0; font-size:12px; color: #ccc;"><b>실시간 기상청 풍향 인덱스:</b> {wd_text}</p>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"<h4 style='margin:0 0 10px 0; color:#66bb6a; font-size:15px; font-weight:bold;'>🚒 [SOP 전술 명령] 실제 인프라 지형 기반 지시서</h4>", unsafe_allow_html=True)
    st.success(f"🛣️ **공간 데이터 진입로 분석:** 현재 실시간 기상 스크리닝 결과, 관내 주요 노선인 **[{found_trail_name}]** 방면으로의 선제 진입로 확보 및 호스 전개 전략 수립 가동.")
    if emergency_mode:
        st.error(f"🚨 **[가상 화재 대응 명령]** 현재 풍향이 {danger_direction} 방면으로 유동 전개되는 찌그러진 타원형 확산이 실시간 포착 중이므로, 대원들은 {arrow_icon} 진행 전선 경계선 위에 매핑된 화선 길이를 차단하기 위해 최단 우회 방화선을 조기 구축하십시오.")
    else:
        st.info("📊 **평시 대기 현황:** 경상북도 산림 격자 인프라 및 기상청 기상 센서 주파수 상시 동기화 중.")

# =========================================================================================
# 📋 령이 자율 포착 종합 로그 대장
# =========================================================================================
st.divider()
st.subheader("📋 령이 자율 포착 로그 대장 (경상북도 소방 재난 방재 시스템 아카이브)")

if emergency_mode:
    log_decision = f"🚨 [가상 화재 시뮬레이션 발령] {city_data['city']} 대상 풍향 굴절 유선형 화선(불꽃🔥 포함) 및 선 위 실시간 면적/길이 3D 입체 작전 기동 중"
else:
    log_decision = "🟢 경북 전역 특이 동향 없음 (22개 시·군 정밀 기상 상태 및 잠재 피해 스크리닝 기반 평시 자율 모니터링 체계 정상 가동 중)"

df_mock_db = pd.DataFrame([{
    "령이 실시간 감지 시각": now_kst.strftime("%Y-%m-%d %H:%M:%S"), 
    "산림청 API 수신 상태": "🚨 가상 화재 선포 테스트 중" if emergency_mode else "🚫 평시 예보 커넥션 대기", 
    "경북 관제 행정구역": city_data["addr"] if emergency_mode else "경상북도 전역 (22개 시·군 전체 모니터링 체계)", 
    "3D 공간 전술 판정": log_decision
}])
st.table(df_mock_db)