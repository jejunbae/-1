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

# 🧠 GeoPandas 자율 예외처리 및 무결성 안전망 빌드
gpd = None
try:
    import geopandas as gpd
except ImportError:
    pass

# 🖥 Presets: 웹페이지 상단 세팅 및 플랫폼 아이덴티티 동기화
st.set_page_config(page_title="경북 산불 통합 관제 AI 령이", page_icon="⚠️", layout="wide")

API_KEY = "69309efd849de167a2a68e2fc27331c01eb67888d72dd4a740419a33cf7d292e"
tz_kst = timezone(timedelta(hours=9))
now_kst = datetime.now(tz_kst)

st.title("🚨 경상북도 실시간 산불 소방 작전 지휘 플랫폼 '령이'")
st.markdown(f"**Core Engine v47.0:** 🏹 3D 지형 해제 및 화살표 전술선 벡터 전개 & 🔒 평시/시뮬레이션 UI 무결성 격리 버전")
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
    "구미시": {"stn": 279, "lat": 36.0842, "lon": 128.3214, "slope": 20.0, "addr": "경북 구미시 금오산 등선 배후 사면", "water_dist": 1.8, "road_density": 45, "pine_ratio": 55, "prefix": "gumi", "search_kw": "구미"},
    "포항시": {"stn": 138, "lat": 36.2314, "lon": 129.2845, "slope": 15.0, "addr": "경북 포항시 북구 내연산 군립공원 구역", "water_dist": 1.2, "road_density": 50, "pine_ratio": 40, "prefix": "pohang", "search_kw": "포항"},
    "경산시": {"stn": 281, "lat": 35.8845, "lon": 128.8412, "slope": 14.0, "addr": "경북 경산시 팔공산 남측 갓바위 사면", "water_dist": 2.0, "road_density": 58, "pine_ratio": 35, "prefix": "gyeongsan", "search_kw": "경산"},
    "영천시": {"stn": 281, "lat": 36.1421, "lon": 128.9845, "slope": 22.0, "addr": "경북 영천시 화북면 보현산 천문대 구역", "water_dist": 4.0, "road_density": 28, "pine_ratio": 60, "prefix": "yeongcheon", "search_kw": "영천"},
    "경주시": {"stn": 138, "lat": 35.8124, "lon": 129.3412, "slope": 19.0, "addr": "경북 경주시 양북면 토함산 국립공원 지대", "water_dist": 2.7, "road_density": 38, "pine_ratio": 62, "prefix": "gyeongju", "search_kw": "경주"},
    "김천시": {"stn": 279, "lat": 36.1124, "lon": 128.0124, "slope": 24.0, "addr": "경북 김천시 대항면 황악산 직지사 배후령", "water_dist": 3.5, "road_density": 30, "pine_ratio": 58, "prefix": "gimcheon", "search_kw": "김천"},
    "상주시": {"stn": 273, "lat": 36.5412, "lon": 127.9845, "slope": 23.0, "addr": "경북 상주시 화북면 속리산 문장대 사면", "water_dist": 4.2, "road_density": 26, "prefix": "sangju", "search_kw": "상주"},
    "영주시": {"stn": 272, "lat": 36.9412, "lon": 128.5214, "slope": 27.0, "addr": "경북 영주시 풍기읍 소백산 희방사 계곡지대", "water_dist": 5.0, "road_density": 20, "pine_ratio": 72, "prefix": "yeongju", "search_kw": "영주"},
    "청송군": {"stn": 272, "lat": 36.3942, "lon": 129.1242, "slope": 26.0, "addr": "경북 청송군 주왕산면 주왕산 국립공원 사면", "water_dist": 4.8, "road_density": 22, "pine_ratio": 76, "prefix": "cheongsong", "search_kw": "주왕산"},
    "봉화군": {"stn": 272, "lat": 36.9124, "lon": 128.9412, "slope": 30.0, "addr": "경북 봉화군 명호면 청량산 도립공원 사면", "water_dist": 5.8, "road_density": 14, "pine_ratio": 84, "prefix": "bonghwa", "search_kw": "봉화"},
    "영양군": {"stn": 130, "lat": 36.7142, "lon": 129.1845, "slope": 29.0, "addr": "경북 영양군 일월산 용화리 격오지 야산", "water_dist": 6.2, "road_density": 11, "pine_ratio": 80, "prefix": "yeongyang", "search_kw": "영양"},
    "영덕군": {"stn": 130, "lat": 36.4842, "lon": 129.3142, "slope": 23.0, "addr": "경북 영덕군 지품면 팔각산 암벽 산림지대", "water_dist": 4.5, "road_density": 18, "pine_ratio": 85, "prefix": "yeongdeok", "search_kw": "영덕"},
    "청도군": {"stn": 281, "lat": 35.6124, "lon": 128.9412, "slope": 21.0, "addr": "경북 청도군 운문면 운문사 지룡산 기슭", "water_dist": 3.4, "road_density": 32, "pine_ratio": 54, "prefix": "cheongdo", "search_kw": "청도"},
    "고령군": {"stn": 279, "lat": 35.6842, "lon": 128.2142, "slope": 16.0, "addr": "경북 고령군 쌍림면 미숭산 자연휴양림 배후", "water_dist": 2.2, "road_density": 46, "pine_ratio": 42, "prefix": "goryeong", "search_kw": "고령"},
    "성주군": {"stn": 279, "lat": 35.8142, "lon": 128.1124, "slope": 25.0, "addr": "경북 성주군 수륜면 가야산 백운동 사면", "water_dist": 3.8, "road_density": 24, "pine_ratio": 66, "prefix": "seongju", "search_kw": "성주"},
    "칠곡군": {"stn": 279, "lat": 36.0421, "lon": 128.4845, "slope": 18.0, "addr": "경북 칠곡군 가산면 가산산성 성곽 산림 격자", "water_dist": 1.9, "road_density": 52, "pine_ratio": 50, "prefix": "chilgok", "search_kw": "칠곡"},
    "예천군": {"stn": 272, "lat": 36.6542, "lon": 128.4524, "slope": 14.0, "addr": "경북 예천군 효자면 도효자길 일대 산림", "water_dist": 2.8, "road_density": 44, "pine_ratio": 47, "prefix": "yecheon", "search_kw": "예천"},
    "울릉군": {"stn": 130, "lat": 37.5024, "lon": 130.8412, "slope": 35.0, "addr": "경북 울릉군 서면 성인봉 칼데라 산악 요충", "water_dist": 8.0, "road_density": 5, "pine_ratio": 40, "prefix": "ulleung", "search_kw": "울릉"}
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

# --- 🎛️ 사이드바 종합 시뮬레이터 통제판 ---
st.sidebar.header("🕹️ 산불 시뮬레이터 통제판")
emergency_mode = st.sidebar.checkbox("🚨 [가상 선포] 실전 산불 시뮬레이션 가동", value=False, key="emerg_check")

st.sidebar.markdown("---")
st.sidebar.subheader("기상 변수 강제 조정")
sim_city = st.sidebar.selectbox("대상 관제 시·군 선택", list(GB_NATION_STN_MAP.keys()), index=0)
sim_t = st.sidebar.slider("가상 온도 (°C)", 10.0, 45.0, value=34.5)
sim_h = st.sidebar.slider("가상 상대습도 (%)", 0.0, 100.0, value=9.0)
sim_w = st.sidebar.slider("가상 풍속 (m/s)", 0.0, 25.0, value=8.5)

# =========================================================================================
# 🔄 경북 22개 시·군 실시간 기상 연산 루프
# =========================================================================================
all_scanned_list = []
for city, info in GB_NATION_STN_MAP.items():
    t, h, w, wd = fetch_kma_live_weather(info["stn"])
    slope = info["slope"]
    if city == sim_city: t, h, w = sim_t, sim_h, sim_w

    humidity_dryness = (100 - h) / 100.0
    if h <= 35.0: humidity_dryness *= 1.5
    weather_factor = (t * 0.35) + (w * 1.4)
    raw_prob = max(18.5, min(99.4, weather_factor * humidity_dryness * 3.5 * (1.0 + (slope / 90.0))))

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

# =========================================================================================
# 🎛️ [대표님 오더 반영 1] 가상 시뮬레이션 돌릴 땐 메인 UI 순위 카드들 다 지우기
# =========================================================================================
if not emergency_mode:
    st.subheader("🛰️ [순위별 정밀관측] 경상북도 산불 발생 실시간 징후 스크리닝 TOP 5")
    cols = st.columns(5)
    for idx, row in df_nation.iterrows():
        if idx >= 5: break
        with cols[idx]:
            border_style = "border: 1px solid #444; background-color: #0e1117; border-radius: 8px; padding: 15px; text-align: center;"
            if row["city"] == target_city:
                border_style = "border: 2px dashed #1a73e8; background-color: #0b132b; border-radius: 8px; padding: 15px; text-align: center;"
            
            st.markdown(f"""
            <div style="{border_style} min-height:115px;">
                <h4 style="margin: 0; color: white;">{idx+1}위 . {row['city']}</h4>
                <p style="margin: 5px 0; font-size: 14px; color: #ffaa00; font-weight:bold;">발전 확률: {row['prob']:.1f}%</p>
                <p style="margin: 0; font-size: 13px; color: #aaa;">정밀풍속: {row['w']:.1f} m/s</p>
            </div>
            """, unsafe_allow_html=True)
else:
    # 🚨 시뮬레이션 모드 가동 시 순위 카드 전량 증발 및 Pure 화재 분석 체계 구축 알림
    st.error(f"🔥 [가상 산불 시뮬레이션 가동] 순위 통제 보드 차단 ➔ 오직 [{sim_city}] 관내 실전 AI 피드백 및 화살표선 확산 벡터 스캔 집중")

# =========================================================================================
# 📐 제원 및 확산 예측 벡터 굴절 계산식
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
                merged_gdfs.append(gdf.head(40))
        except: pass
    if merged_gdfs: return pd.concat(merged_gdfs, ignore_index=True)
    return None

real_contour_gdf = extract_and_merge_numbered_zips(city_data["prefix"])

# =========================================================================================
# 🗺️ [대표님 핵심 오더] 지도는 오직 산불 났을 때만 노출 (Peacetime 시 100% 가림)
# =========================================================================================
if emergency_mode:
    st.divider()
    st.error(f"🕹️ [가상 시뮬레이션 화선 확산 맵] {city_data['city']} 전술 방향 및 확산 화살표선 분석")
    st.caption("⛰️ 3D 왜곡을 완전히 배제한 고대비 소방 2D 전술 도면 | 🔥 화점 중심 불꽃 이모티콘 마킹 | 🔴 바람 벡터 반영 유선형 비원형 화선")

    pydeck_layers = []

    # 1. 🟡 47.shp 경북 진짜 산길 레이어 투사
    if gpd_gb_trails := load_gyeongbuk_gis_lines():
        local_trails = gpd_gb_trails[gpd_gb_trails['MNTN_NM'].str.contains(city_data['search_kw'], na=False)]
        if not local_trails.empty:
            plot_gdf = local_trails.head(25).copy()
            def extract_path_coords(geom):
                if geom.geom_type == 'LineString': return [[coord[0], coord[1]] for coord in geom.coords]
                elif geom.geom_type == 'MultiLineString': return [[coord[0], coord[1]] for line in geom.geoms for coord in line.coords]
                return []
            plot_gdf['path'] = plot_gdf['geometry'].apply(extract_path_coords)
            if 'PMNTN_NM' in plot_gdf.columns and not plot_gdf.iloc[0]['PMNTN_NM'] is None:
                found_trail_name = f"[{plot_gdf.iloc[0]['MNTN_NM']}] {plot_gdf.iloc[0]['PMNTN_NM']}"
            else: found_trail_name = "관내 간선 등산로 1호선"
            pydeck_layers.append(pdk.Layer("PathLayer", plot_gdf, get_path="path", width_scale=15, width_min_pixels=2.5, get_color="[0, 255, 150, 180]"))
    else: found_trail_name = "관내 간선 등산로 1호선"

    if real_contour_gdf is not None:
        pydeck_layers.append(pdk.Layer("GeoJsonLayer", real_contour_gdf, get_line_color="[255, 255, 255, 60]", get_line_width=1.5))

    # 2. 🔴 [not 원형] 바람의 벡터(dx, dy) 방향으로 기속 굴절되는 타원형 유선형 가상 화선 다각형 생성
    def generate_asymmetric_fire_front(lon, lat, dx, dy, scale, wind_w):
        points = []
        segments = 32
        for j in range(segments):
            angle = (j / segments) * 2 * math.pi
            r_lon = 0.0022 * scale * math.cos(angle)
            r_lat = 0.0022 * scale * math.sin(angle)
            alignment = math.cos(angle) * dx + math.sin(angle) * dy
            stretch = 1.0 + max(0.0, alignment) * (wind_w * 0.16)
            p_lon = lon + r_lon * stretch + (dx * scale * 0.0006 * wind_w)
            p_lat = lat + r_lat * stretch + (dy * scale * 0.0006 * wind_w)
            points.append([p_lon, p_lat])
        points.append(points[0])
        return points

    poly_10 = generate_asymmetric_fire_front(city_data["lon"], city_data["lat"], dx, dy, 0.7, city_data['w'])
    poly_30 = generate_asymmetric_fire_front(city_data["lon"], city_data["lat"], dx, dy, 1.7, city_data['w'])
    poly_60 = generate_asymmetric_fire_front(city_data["lon"], city_data["lat"], dx, dy, 2.9, city_data['w'])

    # ⛰️ [대표님 오더] 3D 강제 해제: extruded=False 평면 외곽선 형태로 정밀 도면화
    pydeck_layers.append(pdk.Layer("PolygonLayer", pd.DataFrame([{"poly": poly_10}]), get_polygon="poly", get_fill_color="[255, 60, 60, 30]", get_line_color="[255, 20, 20, 255]", line_width_min_pixels=2))
    pydeck_layers.append(pdk.Layer("PolygonLayer", pd.DataFrame([{"poly": poly_30}]), get_polygon="poly", get_fill_color="[255, 30, 30, 30]", get_line_color="[255, 10, 10, 255]", line_width_min_pixels=2.5))
    pydeck_layers.append(pdk.Layer("PolygonLayer", pd.DataFrame([{"poly": poly_60}]), get_polygon="poly", get_fill_color="[200, 0, 0, 25],", get_line_color="[220, 0, 0, 255]", line_width_min_pixels=3))

    # 3. 🏹 [대표님 핵심 역점 오더] 화살표선 (Line Vector) 전술 레이어 장착!
    # 발화 원점(Center)에서 화두 최전방(Front Point)까지 어디로 뿜어져 나가는지 굵은 지휘 화살표선을 쫙 그어버립니다.
    front_10, front_30, front_60 = poly_10[0], poly_30[0], poly_60[0]
    
    arrow_lines_data = [
        {"slon": city_data["lon"], "slat": city_data["lat"], "elon": front_10[0], "elat": front_10[1], "color": [255, 100, 100], "width": 4},
        {"slon": city_data["lon"], "slat": city_data["lat"], "elon": front_30[0], "elat": front_30[1], "color": [255, 50, 50], "width": 5},
        {"slon": city_data["lon"], "slat": city_data["lat"], "elon": front_60[0], "elat": front_60[1], "color": [220, 0, 0], "width": 6}
    ]
    pydeck_layers.append(pdk.Layer(
        "LineLayer", pd.DataFrame(arrow_lines_data), get_source_position="[slon, slat]", get_target_position="[elon, elat]",
        get_color="color", get_width="width"
    ))

    # 화살표 전술선 끝단(화두 최전면)에 확산 방향 화살표 매핑
    arrow_heads = [{"lon": front_10[0], "lat": front_10[1], "text": arrow_icon}, {"lon": front_30[0], "lat": front_30[1], "text": arrow_icon}, {"lon": front_60[0], "lat": front_60[1], "text": arrow_icon}]
    pydeck_layers.append(pdk.Layer("TextLayer", pd.DataFrame(arrow_heads), get_position="[lon, lat]", get_text="text", get_size=24, get_color="[255,255,255,255]", get_background_color="[255,10,10,240]", padding=[2,4,2,4]))

    # 🏷️ [선 위 실시간 제원 매핑] 화선선 및 전술선 위에 직접 피해범위 및 화선 길이를 완벽히 얹어 출력하는 텍스트 가이드
    inline_labels = [
        {"lon": poly_10[8][0], "lat": poly_10[8][1], "text": f"⏳ 10분 화선 | 약 {p_10:,}평 | 화선길이: {len_10:,}m"},
        {"lon": poly_30[8][0], "lat": poly_30[8][1], "text": f"⚠️ 30분 위험선 | 약 {p_30:,}평 | 화선길이: {len_30:,}m"},
        {"lon": poly_60[8][0], "lat": poly_60[8][1], "text": f"🔥 60분 최종화두 | 약 {p_60:,}평 | 화선길이: {len_60:,}m"}
    ]
    pydeck_layers.append(pdk.Layer(
        "TextLayer", pd.DataFrame(inline_labels), get_position="[lon, lat]", get_text="text", get_size=13,
        get_color="[255, 255, 255, 255]", get_background_color="[15, 15, 15, 240]", padding=[5, 8, 5, 8], get_text_anchor="'start'"
    ))

    # 4. 🔥 [화점 불 이모티콘 마킹] 산불 발생 원점 중심 좌표에 정확히 장착되는 오리지널 불꽃 마커
    pydeck_layers.append(pdk.Layer(
        "TextLayer", pd.DataFrame([{"lon": city_data["lon"], "lat": city_data["lat"], "text": "🔥"}]),
        get_position="[lon, lat]", get_text="text", get_size=45, get_alignment_baseline="'center'"
    ))

    st.pydeck_chart(pdk.Deck(
        layers=pydeck_layers, map_style=pdk.map_styles.DARK,
        initial_view_state=pdk.ViewState(latitude=city_data["lat"], longitude=city_data["lon"], zoom=12.5, pitch=0, bearing=0) # 2D 작전 도면 뷰 고정
    ))
else:
    # 🚫 평시 예찰 모드일 때는 지도가 완벽히 보이지 않고 클린 상태 유지
    found_trail_name = "관내 간선 등산로 1호선"
    st.info("🟢 [평시 AI 자율 예찰 시스템] 경상북도 산림 전역 특이 동향 및 대형 화재 징후 없음. 지도는 제어판의 [🚨 가상 선포] 클릭 시 해당 구역을 조준하여 화살표 전술선 맵으로 자동 팝업됩니다.")

# =========================================================================================
# 📡 [순위별 정밀관측 연동 메인 UI] 정밀관측 기상상황 및 예상 피해 스크리닝 패널
# =========================================================================================
st.markdown("---")
st.subheader(f"📡 [종합 AI 피드백 제원] {city_data['city']} 관내 정밀 예찰 기상 및 확산 예측 분석")

c1, c2, c3 = st.columns([1, 1.2, 1.2])

with c1:
    st.markdown(f"""
    <div style="background-color: #1c1d24; padding: 18px; border-radius: 8px; border-left: 5px solid #1a73e8; min-height: 310px;">
        <h4 style="margin:0 0 12px 0; color:#1a73e8; font-weight: bold;">📡 관내 정밀 관측 기상 상황</h4>
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
    st.success(f"🛣️ **공간 데이터 진입로 분석:** 현재 실시간 기상 스크리닝 결과, 관내 주요 산길 루트 방면으로의 선제 진입로 확보 및 호스 전개 전략 수립 가동.")
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
    log_decision = f"🚨 [가상 시뮬레이션 발령] {city_data['city']} 대상 풍향 굴절 유선형 화선(불꽃🔥 포함) 및 선 위 실시간 면적/길이 정밀 작전 가동 중"
else:
    log_decision = "🟢 경북 전역 특이 동향 없음 (22개 시·군 정밀 기상 상태 및 잠재 피해 스크리닝 기반 평시 자율 모니터링 체계 정상 가동 중)"

df_mock_db = pd.DataFrame([{
    "령이 실시간 감지 시각": now_kst.strftime("%Y-%m-%d %H:%M:%S"), 
    "산림청 API 수신 상태": "🚨 가상 화재 선포 테스트 중" if emergency_mode else "🚫 평시 예보 커넥션 대기", 
    "경북 관제 행정구역": city_data["addr"] if emergency_mode else "경상북도 전역 (22개 시·군 전체 모니터링 체계)", 
    "3D 공간 전술 판정": log_decision
}])
st.table(df_mock_db)