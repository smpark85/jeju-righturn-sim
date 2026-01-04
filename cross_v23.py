import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import random
import time
import os
import numpy as np
from collections import deque

# 1. 페이지 설정
st.set_page_config(page_title="Jeju Univ. Stop Line Sim", layout="wide")
st.title("🍊 [제주대학교 공개강의] 교차로 우회전 알고리즘: 정지선 일시정지 및 보행자 보호 시스템")

# 자산 로드
def load_asset(path):
    if os.path.exists(path):
        return mpimg.imread(path), True
    return None, False

logo_img, logo_ok = load_asset('jeju_logo.png')
car_img, car_ok = load_asset('car_image.png')

# 2. [DB & 자료구조] 교육용 로그 시스템
class EducationalDriveDB:
    def __init__(self):
        self.records = deque()
        self.last_status = None
        self.last_log_time = 0

    def insert_log(self, status, current_time, is_accident=False):
        if status != self.last_status or (current_time - self.last_log_time >= 3.0) or is_accident:
            t_str = time.strftime('%H:%M:%S')
            self.records.append({"Time": t_str, "Decision": status})
            
            if is_accident:
                self.records.append({"Time": t_str, "Decision": "⚖️ [법규위반] 도로교통법 제27조 1항 위반 (보행자 보호 의무)"})
                self.records.append({"Time": t_str, "Decision": "💸 [페널티] 범칙금 6만 원 (승용차 기준)"})
                self.records.append({"Time": t_str, "Decision": "⚠ [벌점] 벌점 10점 부과"})
                self.records.append({"Time": t_str, "Decision": "📈 [할증] 자동차 보험료 5~10% 할증 대상"})
            
            self.last_status = status
            self.last_log_time = current_time

    def get_final_report(self):
        return list(self.records)

if 'edu_db' not in st.session_state:
    st.session_state.edu_db = EducationalDriveDB()
if 'is_running' not in st.session_state:
    st.session_state.is_running = False

# 3. 사이드바 제어
st.sidebar.header("🕹️ 시뮬레이션 환경 설정")
init_c_sig = st.sidebar.selectbox("초기 차량 신호", ["GREEN", "RED"], index=1)
init_p_sig_6 = st.sidebar.selectbox("초기 6시 보행자 신호", ["RED", "GREEN"], index=0)
init_p_sig_3 = st.sidebar.selectbox("초기 3시 보행자 신호", ["GREEN", "RED"], index=0)
n_peds = st.sidebar.slider("5초당 생성될 보행자 수(n)", 1, 5, 2)

col1, col2 = st.sidebar.columns(2)
if col1.button("▶ 시작"): st.session_state.is_running = True
if col2.button("⏹ 강제 중단"): st.session_state.is_running = False

# 4. 그래픽 엔진
def draw_scene(car_pos, car_rot, peds, c_sig, p6, p3, countdown):
    fig, ax = plt.subplots(figsize=(10, 10))
    fig.patch.set_facecolor('white')
    ax.add_patch(plt.Rectangle((-10, -3.5), 20, 7, color='#D3D3D3', zorder=0))
    ax.add_patch(plt.Rectangle((-3.5, -10), 7, 20, color='#D3D3D3', zorder=0))
    ax.axhline(0, color='#FFD700', lw=2); ax.axvline(0, color='#FFD700', lw=2)

    # 횡단보도 및 정지선
    def draw_cw(x, y, v=True):
        for i in range(10):
            if v: ax.add_patch(plt.Rectangle((x + i*0.7 - 3.5, y), 0.4, 3, color='white', zorder=2))
            else: ax.add_patch(plt.Rectangle((x, y + i*0.7 - 3.5), 3, 0.4, color='white', zorder=2))
    
    draw_cw(0, -6.5, True); draw_cw(3.5, 0, False)
    
    # [수정] 6시 방향 주황색 정지선 추가 (횡단보도 진입 전)
    ax.add_patch(plt.Rectangle((-3.5, -6.8), 7, 0.3, color='orange', zorder=3))
    ax.text(-3.4, -7.3, "STOP LINE", color='orange', fontweight='bold', fontsize=10)

    # 신호등 및 카운트다운
    ax.add_patch(plt.Rectangle((0.2, 4.5), 3, 1, color='black', zorder=5))
    c_col = 'green' if c_sig == 'GREEN' else 'red'
    ax.add_patch(plt.Circle((0.8 if c_col=='red' else 2.6, 5.0), 0.35, color=c_col, ec='white', zorder=6))

    def draw_p_unit(x, y, sig, cd):
        ax.add_patch(plt.Rectangle((x, y), 1, 2, color='black', zorder=5))
        p_c = 'red' if sig == 'RED' else 'green'
        ax.add_patch(plt.Circle((x+0.5, y+1.4 if p_c=='red' else y+0.6), 0.4, color=p_c, ec='white', zorder=6))
        ax.text(x+1.2, y+0.5, f"{int(cd)}s", color=p_c, fontsize=15, fontweight='bold', bbox=dict(facecolor='white', alpha=0.8))

    draw_p_unit(7.0, 4.5, p3, countdown)
    draw_p_unit(-6.5, -6.5, p6, countdown)

    car_w, car_h = 1.89, 2.5
    if car_ok:
        from matplotlib.transforms import Affine2D
        tr = Affine2D().rotate_deg_around(car_pos[0], car_pos[1], car_rot) + ax.transData
        ax.imshow(car_img, extent=(car_pos[0]-car_w/2, car_pos[0]+car_w/2, car_pos[1]-car_h/2, car_pos[1]+car_h/2), transform=tr, zorder=10)
    else:
        ax.add_patch(plt.Rectangle((car_pos[0]-car_w/2, car_pos[1]-car_h/2), car_w, car_h, color='red', angle=car_rot, rotation_point='center', zorder=10))

    for p in peds:
        size = 2.1
        if logo_ok: ax.imshow(logo_img, extent=(p['x']-size/2, p['x']+size/2, p['y']-size/2, p['y']+size/2), zorder=11)
        else: ax.add_patch(plt.Circle((p['x'], p['y']), size/2, color='blue', zorder=11))

    ax.set_xlim(-10, 10); ax.set_ylim(-10, 10); ax.axis('off')
    return fig

# 5. 시뮬레이션 메인 엔진
if st.session_state.is_running:
    car_x, car_y, car_rot = 1.7, -9.5, 0
    peds = []; is_stopped_at_line = False; accident = False
    start_time = time.time()
    last_spawn_time = 0
    
    plot_area = st.empty(); log_area = st.empty()
    db = st.session_state.edu_db

    while -11 <= car_x <= 11 and -11 <= car_y <= 11 and st.session_state.is_running:
        curr_elapsed = time.time() - start_time
        countdown = 20 - (curr_elapsed % 20)
        cycle = int(curr_elapsed / 20)
        
        def toggle(val): return "RED" if val=="GREEN" else "GREEN"
        curr_c_sig = init_c_sig if cycle % 2 == 0 else toggle(init_c_sig)
        curr_p6 = init_p_sig_6 if cycle % 2 == 0 else toggle(init_p_sig_6)
        curr_p3 = init_p_sig_3 if cycle % 2 == 0 else toggle(init_p_sig_3)

        if curr_elapsed - last_spawn_time >= 5.0:
            if curr_p6 == "GREEN":
                for _ in range(n_peds): peds.append({'x': 6, 'y': random.uniform(-5.5, -4.5), 'dir': -1, 'type': 'H'})
            if curr_p3 == "GREEN":
                for _ in range(n_peds): peds.append({'x': random.uniform(4.5, 5.5), 'y': -5, 'dir': 1, 'type': 'V'})
            last_spawn_time = curr_elapsed

        for p in peds[:]:
            speed = 0.25
            if countdown <= 4: speed *= 3.0
            p['x'] += p['dir']*speed if p['type']=='H' else 0
            p['y'] += p['dir']*speed if p['type']=='V' else 0
            if abs(p['x']) > 9.5 or abs(p['y']) > 9.5: peds.remove(p)
            if np.sqrt((car_x - p['x'])**2 + (car_y - p['y'])**2) < 1.1: accident = True

        decision = "서행 주행 중"
        v_speed = 0.4 
        
        ped_ahead_6 = any(p for p in peds if p['type']=='H' and -3.0 < p['x'] < 3.0)
        ped_ahead_3 = any(p for p in peds if p['type']=='V' and -3.0 < p['y'] < 3.0)

        # [수정] 정지선(Stop Line) 기반 알고리즘 적용
        if curr_c_sig == "RED" and -7.5 < car_y < -6.5 and not is_stopped_at_line:
            if ped_ahead_6:
                decision = "🚶 [보행자보호] 정지선 대기 중 (보행자 감지)"
                v_speed = 0
            else:
                decision = "🛑 [일시정지] 정지선 준수 (2초 정지)"
                fig_stop = draw_scene((car_x, -6.8), car_rot, peds, curr_c_sig, curr_p6, curr_p3, countdown)
                plot_area.pyplot(fig_stop); plt.close(fig_stop)
                log_area.info(f"운행 상태: {decision}")
                db.insert_log(decision, curr_elapsed)
                
                time.sleep(2.0) # 정지선 앞 2초 정지
                is_stopped_at_line = True
                car_y = -6.5

        if accident:
            decision = "🚨 [중대사고] 보행자 충돌!"; v_speed = 0
        elif car_y < -3.5 and ped_ahead_6:
            decision = "🚶 [보행자보호] 횡단보도 대기"; v_speed = 0
        elif car_y >= -1.5 and car_x < 3.5 and ped_ahead_3:
            decision = "🚶 [보행자보호] 우회전 후 횡단보도 대기"; v_speed = 0
        elif not (curr_c_sig == "RED" and -7.5 < car_y < -6.5 and not is_stopped_at_line):
            if car_y > -1.5:
                car_x += v_speed * 1.5; car_rot = -90; car_y = -1.5
            else:
                car_y += v_speed

        db.insert_log(decision, curr_elapsed, is_accident=accident)
        fig = draw_scene((car_x, car_y), car_rot, peds, curr_c_sig, curr_p6, curr_p3, countdown)
        plot_area.pyplot(fig); plt.close(fig)
        log_area.info(f"운행 상태: {decision}")
        time.sleep(0.05)
        if accident: break

    if accident:
        st.error("❗ 사고가 발생했습니다. 법규 위반 로그를 확인하십시오.")
    else:
        st.success("안전하게 주행을 마쳤습니다.")
        st.session_state.is_running = False

    st.divider()
    st.subheader("📊 주행 분석 및 법규 교육 리포트")
    st.table(db.get_final_report())