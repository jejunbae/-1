import streamlit as st
import time
import requests
import math
import random
import os
import json
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib

st.set_page_config(page_title="국가 화재 통합 관제 AI 령이", page_icon="⚠️", layout="wide")

# --- 🕒 실시간 시간대(Day/Night) 인지 ---
tz_kst = timezone(timedelta(hours=9))
now_kst = datetime.now(tz_kst)
current_hour = now_kst.hour
is_night = (current_hour >= 19 or current_hour < 6)

st.title("🚨 실시간 화재 조기경보 및 통합 관제 플랫폼 '령이'")
st.markdown(f"**현재 관제 상태:** {'🌙 야간 전술 모드' if is_night else '☀️ 주간 관제 모드'} | **Core Engine:** ⏱️ v13.0 AI 브레인 학습 & 시계열 동적 예측")
st.divider()

DB_FILE = "ryong_i_annual_db.json"
MODEL_FILE = "ryong_i_ai_brain.pkl"

# 령이의 뇌(AI) 로드 (학습된 모델이 있으면 불러오고, 없으면 기본값 사용)
if os.path.exists(MODEL_FILE):
    ai_brain = joblib.load(MODEL_FILE)
    ai_status_message = "✅ [각성 모드] 학습된 AI 브레인 적용 완료!"
else:
    ai_brain = None
    ai_status_message = "⚠️ [기본 모드] 학습된 뇌 파일을 찾을 수 없습니다. (train_ai.py 실행 필요)"

st.sidebar.info(ai_status_message)

# --- 🌟 세션 상태 설정 ---
if 't_val' not in st.session_state: st.session_state['t_val'] = 18.0
if 'h_val' not in st.session_state: st.session_state['h_val'] = 50.0
if 'w_val' not in st.session_state: st.session_state['w_val'] = 1.5
if 'wd_val' not in st.session_state: st.session_state['wd_val'] = 180.0
if 'slope_val' not in st.session_state: st.session_state['slope_val'] = 20.0
if 'pty_val' not in st.session_state: st.session_state['pty_val'] = 0
if 'fire_blackbox' not in st.session_state: st.session_state['fire_blackbox'] = []
if 'current_target' not in st.session_state: st.session_state['current_target'] = "대한민국 전역"

# --- [기상청 & 브이월드 API 함수들 (생략... 기존과 동일)] ---
# (이 부분은 기존에 잘 작동하던 코드를 그대로 유지하세요)
def fetch_kma_live_weather():
    # ... 기존 코드 내용 동일 ...
    return 18.0, 50.0, 1.5, 180.0, 0.0, 0

def fetch_vworld_live_slope():
    return 20.0

def get_wind_direction_text(deg):
    # ... 기존 코드 내용 동일 ...
    return "북풍", "남쪽"

# --- 🧠 AI 물리 연산 및 학습 결과 적용 ---
if ai_brain:
    # 🌟 [중요] AI 브레인의 예측값을 받아옴
    ai_base = float(ai_brain.predict([[st.session_state['t_val'], st.session_state['h_val'], st.session_state['w_val']]])[0])
else:
    # 뇌가 없으면 기본 연산
    ai_base = (st.session_state['t_val'] * 0.001) + ((100 - st.session_state['h_val']) * 0.0002)

# 지형 경사도 반영
slope_multiplier = 1.0 + (st.session_state['slope_val'] / 60.0) * 0.5
final_area_ha = ai_base * slope_multiplier

is_raining = (st.session_state['pty_val'] > 0)
current_pyeong = 10.0
current_fireline = 15.0

if is_raining:
    spread_rate_pyeong_per_min = 0.0
    spread_rate_line_per_min = 0.0
    status_msg = "🌧️ [자연 진화] 우천 감지로 확산 억제 중"
    bg_color = "#005b96"
else:
    # 🌟 AI가 예측한 확산속도를 반영
    spread_rate_pyeong_per_min = min(final_area_ha * 3000 * 0.1, 500.0)
    spread_rate_line_per_min = spread_rate_pyeong_per_min * 0.15
    if spread_rate_pyeong_per_min > 50:
        status_msg = "🔥 [🚨 AI 심각] 대형 산불 급속 확산 중"
        bg_color = "#ff0000"
    else:
        status_msg = "🔥 [⚠️ AI 경계] 중소형 산불 확산 중"
        bg_color = "#d9381e"

# 시계열 계산 및 UI 출력 (기존과 동일)
# ... (중략) ...