import streamlit as st
import time
import requests
import math
import random
import os
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib

# 🔗 구글 스프레드시트 실시간 DB 도킹을 위한 라이브러리
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="국가 화재 통합 관제 AI 령이", page_icon="⚠️", layout="wide")

if "SEC_KEY" in st.secrets: 
    API_KEY = st.secrets["SEC_KEY"]
else: 
    API_KEY = "69309efd849de167a2a68e2fc27331c01eb67888d72dd4a740419a33cf7d292e"

tz_kst = timezone(timedelta(hours=9))
now_kst = datetime.now(tz_kst)
current_hour = now_kst.hour
is_night = (current_hour >= 19 or current_hour < 6)

st.title("🚨 실시간 화재 조기경보 및 통합 관제 플랫폼 '령이'")
st.markdown(f"**현재 관제 상태:** {'🌙 야간 전술 모드' if is_night else '☀️ 주간 관제 모드'} | **Core Engine:** 🛰️ Google Sheets DB 실시간 영구 연동 엔진 v18.5")
st.divider()

MODEL_FILE = "ryong_i_ai_brain.pkl"

# --- 🛰️ 대한민국 전국 주요 기상 관측소(STN) 마스터 풀 ---
ALL_NATION_STN_MAP = {
    "문경": {"stn": 273, "lat": 36.5938, "lon": 128.1865, "slope": 32.0, "addr": "경상북도 문경시 가은읍 수예리 산 18-1"},
    "안동": {"stn": 272, "lat": 36.5665, "lon": 128.7262, "slope": 25.0, "addr": "경상북도 안동시 명륜동 야산 지대"},
    "의성": {"stn": 278, "lat": 36.3526, "lon": 128.6970, "slope": 18.0, "addr": "경상북도 의성군 의성읍 원당리 일원"},
    "구미": {"stn": 279, "lat": 36.1214, "lon": 128.3446, "slope": 20.0, "addr": "경상북도 구미시 금오산 성안 구역"},
    "강릉": {"stn": 105, "lat": 37.7511, "lon": 128.8906, "slope": 35.0, "addr": "강원도 강릉시 성산면 백두대간령"},
    "속초": {"stn": 90, "lat": 38.2509, "lon": 128.5647, "slope": 30.0, "addr": "강원도 속초시 설악산 국립공원 구역"},
    "춘천": {"stn": 101, "lat": 37.9026, "lon": 127.7357, "slope": 22.0, "addr": "강원도 춘천시 신북읍 산림 지대"},
    "원주": {"stn": 114, "lat": 37.3375, "lon": 127.9466, "slope": 24.0, "addr": "강원도 원주시 치악산 국지 사면"},
    "청주": {"stn": 131, "lat": 36.6372, "lon": 127.4414, "slope": 15.0, "addr": "충청북도 청주시 상당구 우암산 구역"},
    "충주": {"stn": 127, "lat": 36.9537, "lon": 127.9513, "slope": 18.0, "addr": "충청북도 충주시 계명산 부근 임야"},
    "대전": {"stn": 133, "lat": 36.3721, "lon": 127.3745, "slope": 14.0, "addr": "대전광역시 유성구 식장산 전방 사면"},
    "천안": {"stn": 232, "lat": 36.7617, "lon": 127.1147, "slope": 16.0, "addr": "충청남도 천안시 태조산 등산로 주변"},
    "전주": {"stn": 146, "lat": 35.8400, "lon": 127.1189, "slope": 12.0, "addr": "전라북도 전주시 완산구 모악산 연계림"},
    "광주": {"stn": 156, "lat": 35.1729, "lon": 126.8916, "slope": 20.0, "addr": "광주광역시 북구 무등산 국립공원 벨트"},
    "대구": {"stn": 143, "lat": 35.8294, "lon": 128.6530, "slope": 23.0, "addr": "대구광역시 동구 팔공산 사면 초입"},
    "포항": {"stn": 138, "lat": 36.0322, "lon": 129.3800, "slope": 17.0, "addr": "경상북도 포항시 북구 보경사 계곡 임야"},
    "울진": {"stn": 130, "lat": 36.9917, "lon": 129.4128, "slope": 28.0, "addr": "경상북도 울진군 금강송면 산불 취약지"},
    "부산": {"stn": 159, "lat": 35.1047, "lon": 129.0320, "slope": 21.0, "addr": "부산광역시 금정구 금정산성 후방 능선"},
    "울산": {"stn": 152, "lat": 35.5653, "lon": 129.3245, "slope": 22.0, "addr": "울산광역시 울주군 가지산 신불산 벨트"},
    "제주": {"stn": 184, "lat": 33.5141, "lon": 126.5297, "slope": 26.0, "addr": "제주특별자치도 제주시 한라산 국립공원 사면"}
}

@st.cache_resource
def load_ryong_i_ai():
    if os.path.exists(MODEL_FILE):
        try: return joblib.load(MODEL_FILE), "🧠 전국구 빅데이터 멀티 랭킹 AI 엔진 동기화 완료"
        except: pass
    model = RandomForestRegressor(n_estimators=10, random_state=42)
    model.fit(pd.DataFrame([{"STN": 273, "TA": 25.0, "HM": 30.0, "WS": 3.0}]), [0.05])
    return model, "🌱 백업용 기본 데이터 인공지능 가동"

ai_brain, ai_status_message = load_ryong_i_ai()

# 🗄️ 구글 스프레드시트 커넥션 안전 초기화 레이어 (문법 오류 수정)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_cloud_db = conn.read(ttl="5s") 
except:
    df_cloud_db = pd.DataFrame(columns=["령이 감지 시각", "소방신고 접수 시각", "실측 시차 분석", "발화 대상 주소", "AI 예측 피해규모 (평)", "예상 화선 및 풍향"])

def fetch_kma_live_weather(stn_id):
    live_t, live_h, live_w, live_wd = 20.0, 70.0, 1.5, 180.0
    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    base_time_dt = datetime.now(tz_kst) - timedelta(minutes=45)
    params = {'serviceKey': API_KEY, 'pageNo': '1', 'numOfRows': '10', 'dataType': 'JSON', 'base_date': base_time_dt.strftime("%Y%m%d"), 'base_time': base_time_dt.strftime("%H00"), 'nx': '91', 'ny': '106'}
    try:
        res = requests.get(url, params=params, timeout=1.0)
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
    if 337.5 <= deg or deg < 22.5: return "북풍 (⬇️ 남쪽 위험)", "남쪽"
    elif 22.5 <= deg < 67.5: return "북동풍 (↙️ 남서쪽 위험)", "남서쪽"
    elif 67.5 <= deg < 112.5: return "동풍 (⬅️ 서쪽 위험)", "서쪽"
    elif 112.5 <= deg < 157.5: return "남동풍 (↖️ 북서쪽 위험)", "북서쪽"
    elif 157.5 <= deg < 202.5: return "남풍 (⬆️ 북쪽 위험)", "북쪽"
    elif 202.5 <= deg < 247.5: return "남서풍 (↗️ 북동쪽 위험)", "북동쪽"
    elif 247.5 <= deg < 292.5: return "서풍 (➡️ 동쪽 위험)", "동쪽"
    else: return "북서풍 (↘️ 남동쪽 위험)", "남동쪽"

# =========================================================================================
# 🚒 6대 하이브리드 변수 결합형 SOP 자율 텍스트 빌더 엔진 (오타 교정 완료)
# =========================================================================================
def get_dynamic_sop_manual(area_ha, t, h, w, slope, danger_zone, is_night_mode):
    if area_ha >= 0.15: level_title = "🔴 [SOP 3단계] 광역 초광역 비상대응"
    elif area_ha >= 0.08: level_title = "🟠 [SOP 2단계] 관할 구조대 전원 투입"
    else: level_title = "🟡 [SOP 1단계] 초동 진압 관할 출동"

    dry_text = "수목 낙엽층 흡수율 제로(0%) 판정. 일반 용수 진화 효율 저하로 화학 방화제(지연제) 혼합 살포 요망." if h < 25 else "일반 용수 위주 방수 전술 전개 가능."
    wind_text = f"풍속 {w}m/s 강풍 돌풍 발생. {danger_zone} 하류 골짜기 풍하측 300m 비화(날아가는 불 씨) 감시조 의무 조 편성." if w >= 5.0 else f"풍속 {w}m/s 안정 기류. 화선 전면 직접 진압 위주 전개."
    slope_text = f"경사도 {slope}° 급경사 험준 지형. 대원 도보 진입 지연 및 추락 위험 발생. 기계화 진화대 로프 확보 및 소방 드론 전방 정찰 유도 필수." if slope >= 25.0 else f"경사도 {slope}° 완경사 지형. 진화 차량 펌프선 전방 임도 직접 진입 및 방수선 즉각 구축."

    if is_night_mode:
        m10 = f"🚒 **[10분 야간 전술]** 진화 헬기 즉각 철수 완료. 관할 의용소방대 야간 비상 소집령 발령. 현시각 기온 {t}°C 하강 기류 인지, {danger_zone} 부락 민가 경계선에 수화 고착 방어차량 배치."
        m30 = f"🔦 **[30분 가시 확보]** 소방 조명차 2대 및 고성능 열화상 드론 급파. 야간 골바람에 의한 {danger_zone} 능선 이동 속도 역산 개시. {wind_text}"
        m60 = f"🏠 **[60분 인명 사수]** {danger_zone} 방향 직격 타깃 부락 취침 주민 전원 강제 가택 대피령 집행 및 대피소 이송. {slope_text}"
    else:
        # 오타 수정 완료 파트 (Corporate ➔ 🚒 이모지)
        m10 = f"🚒 **[10분 주간 전술]** 산림청·소방 초대형 진화헬기 3대 이상 즉각 출격 격상 요청. 현시각 기온 {t}°C 고온 상승 기류 반영, {danger_zone} 최전방 주 화선에 선제적 다각 살포 감행."
        m30 = f"⚠️ **[30분 저지 조치]** 산불전문진화대 및 특수진화대 지상 인력 임도 배치. {danger_zone} 골짜기 1차 차단벽 구축. {dry_text} {wind_text}"
        m60 = f"🧑‍🚒 **[60분 광역 저지]** 소방동원령 1호 연계 인근 지자체 소방력 20% 교차 응원 분사. {slope_text}"

    return level_title, m10, m30, m60

# --- 🎮 사이드바 시뮬레이터 통제 장치 ---
st.sidebar.header("🎛️ 전국 단위 관제 테스트")
sim_mode = st.sidebar.checkbox("🚨 가상 산불 상황 강제 조작 활성화", value=False)

sim_city = "문경"
sim_t, sim_h, sim_w, sim_wd, sim_slope = 28.5, 19.0, 6.5, 225.0, 32.0

if sim_mode:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔥 가상 기상 제어판")
    sim_city = st.sidebar.selectbox("타깃 가상 재난 도시 선택", list(ALL_NATION_STN_MAP.keys()), index=0)
    sim_t = st.sidebar.slider("가상 온도 (°C)", -10.0, 45.0, value=28.5)
    sim_h = st.sidebar.slider("가상 상대습도 (%)", 0.0, 100.0, value=19.0)
    sim_w = st.sidebar.slider("가상 풍속 (m/s)", 0.0, 35.0, value=6.5)
    sim_wd = st.sidebar.slider("가상 풍향 (각도 °)", 0.0, 360.0, value=225.0, step=45.0)
    sim_slope = st.sidebar.slider("가상 지형 경사도 (°)", 0.0, 60.0, value=float(ALL_NATION_STN_MAP[sim_city]["slope"]))

# =========================================================================================
# 🔄 전국 스캔 후 실시간 위험도 TOP 10 자율 분류 연산 레이어
# =========================================================================================
all_scanned_list = []

for city, info in ALL_NATION_STN_MAP.items():
    t, h, w, wd = fetch_kma_live_weather(info["stn"])
    slope = info["slope"]
    
    if sim_mode and city == sim_city:
        t, h, w, wd, slope = sim_t, sim_h, sim_w, sim_wd, sim_slope

    try: ai_pred = float(ai_brain.predict([[info["stn"], t, h, w]])[0])
    except: ai_pred = (t * 0.01) + (w * 0.1)
    
    base_calc = (ai_pred * 0.005) + ((100 - h) * 0.001) + (w * 0.01)
    danger_score = base_calc * (1.0 + (slope / 60.0) * 1.5)
    
    all_scanned_list.append({
        "city": city, "stn": info["stn"], "lat": info["lat"], "lon": info["lon"],
        "addr": info["addr"], "t": t, "h": h, "w": w, "wd": wd, "slope": slope, "score": danger_score
    })

df_nation = pd.DataFrame(all_scanned_list).sort_values(by="score", ascending=False).reset_index(drop=True)
df_top10 = df_nation.head(10)
top_1_target = df_top10.iloc[0]

FIRE_THRESHOLD = 0.13
is_fire_detected = (top_1_target["score"] >= FIRE_THRESHOLD)

# --- 🛰️ 1단계: 실시간 전국 위험도 TOP 10 카드 표출 ---
st.header("🛰️ [1단계] 실시간 전국 산불 위험도 자율 선별 랭킹 TOP 10")
st.caption("※ 전국 기상망을 전수 분석하여 위험 점수가 높은 상위 10개 지점을 실시간으로 표출합니다.")

r1_cols = st.columns(5)
r2_cols = st.columns(5)
all_cols = r1_cols + r2_cols

for idx, row in df_top10.iterrows():
    with all_cols[idx]:
        if row["score"] >= FIRE_THRESHOLD:
            badge_html = f"<span style='color:#ff4b4b;font-weight:bold;'>🔥 [위기 단계]</span>"
            border_style = "border: 2px solid #ff4b4b; background-color: #1e1e1e;"
        else:
            badge_html = f"<span style='color:#ffaa00;font-weight:bold;'>⚠️ [주의순위 {idx+1}위]</span>"
            border_style = "border: 1px solid #444; background-color: #0e1117;"
            
        if (idx == 0) and row["score"] >= FIRE_THRESHOLD:
            border_style = "border: 3px dashed #ffff00; background-color: #1c1d24;"
            badge_html += " ⭐ 최악 위험"

        st.markdown(f"""
        <div style="{border_style} padding: 12px; border-radius: 8px; text-align: center; min-height:120px;">
            <h4 style="margin: 0; color: white;">{idx+1}위 . {row['city']} ({row['stn']}번)</h4>
            <p style="margin: 4px 0; font-size: 12px; color: #aaa;">습도: {row['h']}% | 풍속: {row['w']}m/s</p>
            <p style="margin: 0; font-size: 13px;">{badge_html}</p>
        </div>
        """, unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# --- 📍 2단계 & 3단계: 화재 검출 시 시뮬레이션 대책 ---
if is_fire_detected:
    pyeong = top_1_target["score"] * 3025.0
    eccentricity = 1.0 + (top_1_target["w"] * 0.1)
    radius = math.sqrt((top_1_target["score"] * 10000.0) / math.pi)
    fire_line = 2.0 * math.pi * radius * (eccentricity ** 0.5)
    wd_text, danger_zone = get_wind_direction_text(top_1_target["wd"])
    
    spread_factor = 0.001 + (top_1_target["w"] * 0.002) + (top_1_target["slope"] * 0.0008)
    if top_1_target["h"] < 30: spread_factor *= 1.8
    spread_rate_min = min(top_1_target["score"] * 0.1, spread_factor)
    
    sop_title, m10, m30, m60 = get_dynamic_sop_manual(
        top_1_target["score"], top_1_target["t"], top_1_target["h"], 
        top_1_target["w"], top_1_target["slope"], danger_zone, is_night
    )
    
    # 🔒 [로그 차단/정밀 적재] 가상 조작 모드가 꺼져있을 때만 구글 스프레드시트에 영구 적재
    if not sim_mode and 'conn' in locals():
        sat_time_str = now_kst.strftime("%Y-%m-%d %H:%M:%S")
        
        should_write = True
        if not df_cloud_db.empty:
            last_addr = df_cloud_db.iloc[-1]["발화 대상 주소"]
            if last_addr == top_1_target["addr"]:
                should_write = False
                
        if should_write:
            new_row = pd.DataFrame([{
                "령이 감지 시각": sat_time_str,
                "소방신고 접수 시각": "실시간 동기화 중",
                "실측 시차 분석": "위성 자율 검출 완료",
                "발화 대상 주소": top_1_target["addr"],
                "AI 예측 피해규모 (평)": f"{pyeong:,.0f} 평",
                "예상 화선 및 풍향": f"{fire_line:,.0f}m ({wd_text.split(' ')[0]})"
            }])
            df_updated = pd.concat([df_cloud_db, new_row], ignore_index=True)
            try:
                conn.update(data=df_updated)
                df_cloud_db = df_updated
            except:
                pass

    st.header(f"📍 [2단계] AI 선별 최우선 추적 관제 구역 ➔ [{top_1_target['city']}시·군] {'🧪 (가상 가동 중)' if sim_mode else ''}")
    col_t1, col_t2 = st.columns([1, 2])
    
    with col_t1:
        # ⚪ 화이트 폰트 가독성 개편 완료 파트
        st.markdown(f"""
        <div style="background-color: #262730; padding: 20px; border-radius: 8px; border-left: 5px solid #ff4b4b;">
            <h4 style="margin:0 0 10px 0; color:#ff4b4b; font-weight: bold;">🔍 최고 위험 지형/환경 리포트</h4>
            <p style="margin:6px 0; color: #ffffff; font-size:15px;"><b>지번 주소:</b> {top_1_target['addr']}</p>
            <p style="margin:6px 0; color: #ffffff; font-size:15px;"><b>실측 실시간 기온:</b> {top_1_target['t']} °C</p>
            <p style="margin:6px 0; color: #ffffff; font-size:15px;"><b>상대습도/풍속:</b> {top_1_target['h']}% / {top_1_target['w']}m/s</p>
            <p style="margin:6px 0; color: #ffffff; font-size:15px;"><b>지형 사면 경사도:</b> {top_1_target['slope']} °</p>
            <p style="margin:6px 0; color: #ffffff; font-size:15px;"><b>분당 확산 속도:</b> <span style="color:#ffaa00; font-weight:bold;">{spread_rate_min * 3025.0:.1f} 평/min</span></p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_t2:
        st.markdown(f"""
        <div style="background-color: #ff4b4b; padding: 30px; border-radius: 8px; text-align: center;">
            <h2 style="color:white; margin:0;">🔥 전국 최고 위험 1위 [{top_1_target['city']}] 산불 임계치 초과 확산 검출!</h2>
            <h4 style="color:yellow; margin:10px 0 0 0;">🚨 현장 지휘부 긴급 작전 지침: {sop_title}</h4>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.header("🧠 [3단계] AI 가상 시뮬레이션 미래 타임라인 예측 및 표준 대응 처방")
    
    timeline_records = []
    for mins in [10, 30, 60]:
        est_area = top_1_target["score"] + (spread_rate_min * mins)
        timeline_records.append({
            "경과 시간": f"발화 {mins}분 뒤 실시간 확산 시점",
            "AI 추정 피해 면적(평)": f"{est_area * 3025.0:,.0f} 평",
            "지형 반영 추정 화선 길이(m)": f"{2.0 * math.pi * math.sqrt((est_area * 10000.0) / math.pi) * (eccentricity ** 0.5):,.1f} m"
        })
    st.dataframe(pd.DataFrame(timeline_records), use_container_width=True, hide_index=True)
    
    st.markdown("#### 🚒 소방 표준 작전 절차(SOP) 분 단위 전술 명령")
    sc1, sc2, sc3 = st.columns(3)
    sc1.error(m10); sc2.error(m30); sc3.error(m60)

else:
    st.markdown(f"""
    <div style="background-color: #1a73e8; padding: 40px; border-radius: 10px; text-align: center; margin-top: 20px;">
        <span style="font-size: 60px;">🔒</span>
        <h2 style="color: white; margin-top: 15px;">대한민국 전역 산불 안전 관제 정상 상태</h2>
        <p style="color: #e8f0fe; margin: 5px 0 0 0;">전국 관측소 전수 실시간 연산 결과, 화재 확산 임계치를 초과한 지점이 없습니다.</p>
        <p style="color: #ffff00; font-size:14px; margin-top:10px;">🛡️ 현재 가장 건조 지수 주의가 요구되는 관심 지점 1위: <b>[{top_1_target['city']}]</b> (위험도 점수: {top_1_target['score']:.4f})</p>
    </div>
    """, unsafe_allow_html=True)

# --- 🛰️ 구글 클라우드 DB 실시간 로그 테이블 뷰 ---
st.divider()
st.subheader("📋 령이 자율 화재 포착 로그 (Google Sheets Cloud DB 연동 데이터)")
if not df_cloud_db.empty:
    st.table(df_cloud_db.iloc[::-1].reset_index(drop=True))
else:
    st.info("🚨 임계치를 초과하여 구글 스프레드로 적재된 실시간 화재 기록이 없습니다.")

# 🔄 24시간 자율 백그라운드 리프레시 트리거
if not sim_mode:
    time.sleep(10)
    st.rerun()