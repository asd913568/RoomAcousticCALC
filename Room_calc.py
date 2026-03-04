import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.ticker as ticker
import platform

# --- OS별 폰트 자동 설정 ---
system_os = platform.system()
if system_os == 'Darwin':
    plt.rc('font', family='AppleGothic')
elif system_os == 'Windows':
    plt.rc('font', family='Malgun Gothic')
else:
    plt.rc('font', family='NanumGothic')

plt.rcParams['axes.unicode_minus'] = False

st.set_page_config(page_title="Room Mode & SBIR 분석기", layout="wide")

st.title("🏠 홈 스튜디오를 위한 Room Mode & SBIR 분석기")
st.markdown("""
방의 물리적 규격과 스피커 배치 데이터를 기반으로 **저역대 에너지 불균형**을 분석합니다.  
⚠️ **필수 주의사항**: 본 도구의 모든 계산은 이상적인 직육면체를 가정한 시뮬레이션입니다. 방의 비대칭 구조, 창문, 가구 등의 변수를 모두 대변할 수 없으므로, **반드시 측정용 마이크와 REW(Room EQ Wizard)를 활용한 실측 배치가 동반되어야 합니다.**
""")

# --- 사이드바: 단위 선택 ---
st.sidebar.header("⚙️ 측정 단위 설정")
unit_room = st.sidebar.radio("방 및 스피커 거리 단위", ["m (미터)", "cm (센티미터)"], horizontal=True)
unit_spk = st.sidebar.radio("스피커 인클로저 단위", ["mm (밀리미터)", "inch (인치)"], horizontal=True)

is_m = (unit_room == "m (미터)")
is_mm = (unit_spk == "mm (밀리미터)")
disp_u_room = "m" if is_m else "cm"
disp_u_spk = "mm" if is_mm else "inch"

# --- Session State 초기화 및 단위 변경 동기화 ---
if "ui_d_back" not in st.session_state: 
    st.session_state.ui_d_back = 0.8 if is_m else 80.0
if "ui_d_side" not in st.session_state: 
    st.session_state.ui_d_side = 0.8 if is_m else 80.0
if "prev_unit_room" not in st.session_state:
    st.session_state.prev_unit_room = unit_room
if "scan_done" not in st.session_state:
    st.session_state.scan_done = False

# 방 단위가 변경되었을 때 기존 입력값 자동 변환
if st.session_state.prev_unit_room != unit_room:
    if is_m: # cm -> m
        st.session_state.ui_d_back = round(st.session_state.ui_d_back / 100.0, 2)
        st.session_state.ui_d_side = round(st.session_state.ui_d_side / 100.0, 2)
    else: # m -> cm
        st.session_state.ui_d_back = round(st.session_state.ui_d_back * 100.0, 0)
        st.session_state.ui_d_side = round(st.session_state.ui_d_side * 100.0, 0)
    st.session_state.prev_unit_room = unit_room

# --- 사이드바: 데이터 입력 ---
st.sidebar.divider()
st.sidebar.header(f"📏 방 규격 데이터 ({disp_u_room})")
step_r = 0.01 if is_m else 1.0
fmt_r = "%.2f" if is_m else "%.0f"

L_in = st.sidebar.number_input(f"방 길이 (L)", value=5.0 if is_m else 500.0, step=step_r, format=fmt_r)
W_in = st.sidebar.number_input(f"방 너비 (W)", value=4.0 if is_m else 400.0, step=step_r, format=fmt_r)
H_in = st.sidebar.number_input(f"방 높이 (H)", value=2.5 if is_m else 250.0, step=step_r, format=fmt_r)

# 내부 연산을 위해 모두 미터(m)로 변환
L = L_in if is_m else L_in / 100.0
W = W_in if is_m else W_in / 100.0
H = H_in if is_m else H_in / 100.0

st.sidebar.divider()
st.sidebar.header(f"🎛️ 스피커 물리적 규격 ({disp_u_spk})")
step_s = 1.0 if is_mm else 0.1
fmt_s = "%.0f" if is_mm else "%.1f"

spk_w_in = st.sidebar.number_input(f"스피커 너비", value=200.0 if is_mm else 8.0, step=step_s, format=fmt_s)
spk_d_in = st.sidebar.number_input(f"스피커 깊이", value=300.0 if is_mm else 12.0, step=step_s, format=fmt_s)
spk_h_in = st.sidebar.number_input(f"스피커 높이", value=350.0 if is_mm else 14.0, step=step_s, format=fmt_s)

# 내부 연산을 위해 모두 미터(m)로 변환
spk_width = spk_w_in / 1000.0 if is_mm else spk_w_in * 0.0254
spk_depth = spk_d_in / 1000.0 if is_mm else spk_d_in * 0.0254
spk_height = spk_h_in / 1000.0 if is_mm else spk_h_in * 0.0254

st.sidebar.divider()
st.sidebar.header(f"🔊 스피커 드라이버 중심 거리 ({disp_u_room})")
st.sidebar.caption("※ 전면 배플(드라이버)에서 벽까지의 거리")

d_back_in = st.sidebar.number_input(f"뒷벽과의 거리", step=step_r, format=fmt_r, key="ui_d_back")
d_side_in = st.sidebar.number_input(f"옆벽과의 거리", step=step_r, format=fmt_r, key="ui_d_side")
d_floor_in = st.sidebar.number_input(f"바닥과의 거리", value=1.0 if is_m else 100.0, step=step_r, format=fmt_r)
d_ceil_in = st.sidebar.number_input(f"천장과의 거리", value=1.5 if is_m else 150.0, step=step_r, format=fmt_r)

# 내부 연산을 위해 모두 미터(m)로 변환
d_back = d_back_in if is_m else d_back_in / 100.0
d_side = d_side_in if is_m else d_side_in / 100.0
d_floor = d_floor_in if is_m else d_floor_in / 100.0
d_ceil = d_ceil_in if is_m else d_ceil_in / 100.0

# --- 물리적 충돌 검사 ---
if d_back < spk_depth:
    st.sidebar.error(f"⚠️ 물리적 오류: 뒷벽 거리({d_back:.2f}m)가 스피커 깊이({spk_depth:.2f}m)보다 짧습니다.")
if d_side < (spk_width / 2):
    st.sidebar.error(f"⚠️ 물리적 오류: 옆벽 거리가 스피커 너비의 절반보다 짧습니다.")

# --- 제작자 크레딧 ---
st.sidebar.divider()
st.sidebar.caption("👨‍💻 Made by **Chandler.J 정찬영**")

# --- 연산 로직 (모두 m 단위 기준) ---
C = 344

modes = []
for n in range(1, 4):
    modes.append({"유형": "길이", "차수": f"{n}차", "주파수 (Hz)": round((C * n) / (2 * L), 1)})
    modes.append({"유형": "너비", "차수": f"{n}차", "주파수 (Hz)": round((C * n) / (2 * W), 1)})
    modes.append({"유형": "높이", "차수": f"{n}차", "주파수 (Hz)": round((C * n) / (2 * H), 1)})
df_modes = pd.DataFrame(modes).sort_values("주파수 (Hz)").reset_index(drop=True)

sbir_data = {
    "뒷벽": round(C / (4 * max(d_back, 0.01)), 1),
    "옆벽": round(C / (4 * max(d_side, 0.01)), 1),
    "바닥": round(C / (4 * max(d_floor, 0.01)), 1),
    "천장": round(C / (4 * max(d_ceil, 0.01)), 1)
}

warnings_mode = [] 
sbir_table = []
for wall, f_sbir in sbir_data.items():
    overlap_sbir = False
    for f_mode in df_modes["주파수 (Hz)"]:
        if abs(f_mode - f_sbir) < 10:
            warnings_mode.append(f"- **{wall} SBIR({f_sbir}Hz)**과 **룸모드({f_mode}Hz)** 중첩. (위상 왜곡 극심)")
            
    for other_wall, other_f in sbir_data.items():
        if wall != other_wall and abs(f_sbir - other_f) < 10:
            overlap_sbir = True

    status = "🔴 위험 (SBIR간 중첩)" if overlap_sbir else "🟢 양호"
    sbir_table.append({"반사면": wall, "딥 주파수 (Hz)": f_sbir, "상태": status})

df_sbir = pd.DataFrame(sbir_table)

# --- 결과 화면 구성 ---
col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("📊 핵심 계산 데이터")
    st.write("**룸모드 분포 (축방향)**")
    st.dataframe(df_modes, use_container_width=True, hide_index=True)
    
    st.write("**현재 배치별 SBIR 딥(Dip)**")
    st.dataframe(df_sbir, use_container_width=True, hide_index=True)

with col2:
    st.subheader("📈 주파수 간섭 시각화 (Log Scale)")
    fig, ax = plt.subplots(figsize=(10, 2.5)) 
    
    for i, freq in enumerate(df_modes["주파수 (Hz)"]):
        ax.axvline(x=freq, color='red', linestyle='--', alpha=0.4, linewidth=2, label='룸모드' if i==0 else "")
    
    colors = {'뒷벽': 'blue', '옆벽': 'green', '바닥': 'orange', '천장': 'purple'}
    for wall, freq in sbir_data.items():
        ax.axvline(x=freq, color=colors[wall], linewidth=3, label=f'SBIR ({wall})')
    
    ax.set_xscale('log')
    ax.set_xlim(20, 350)
    ticks = [20, 30, 40, 50, 60, 80, 100, 150, 200, 300]
    ax.set_xticks(ticks)
    ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
    
    ax.set_yticks([]) 
    ax.set_ylabel("") 
    ax.set_xlabel("주파수 (Hz)")
    ax.set_title("Room Mode (Red) vs SBIR Dips")
    ax.grid(True, which='both', axis='x', linestyle=':', alpha=0.4) 
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1)) 
    st.pyplot(fig)

# --- 스피커 배치 최적화 스캐너 ---
st.divider()
st.subheader("🎯 최적 스피커 배치 스캐너 (물리적 한계 반영)")
st.markdown("입력된 방 규격과 **스피커의 인클로저 크기**를 고려하여, 물리적으로 설치 가능하면서 간섭 페널티가 가장 적은 좌표를 역산합니다.")

if st.button("🚀 최적 배치 스캔 시작"):
    best_score = float('inf')
    best_d_back = d_back
    best_d_side = d_side
    best_sbirs = {}
    
    min_db = spk_depth + 0.05 
    min_ds = (spk_width / 2) + 0.05
    
    db_range = np.arange(min_db, min(L/2, 1.5), 0.05)
    ds_range = np.arange(min_ds, W/2 - 0.4, 0.05) 
    
    progress_bar = st.progress(0)
    total_iters = len(db_range) * len(ds_range)
    iter_count = 0
    
    for db in db_range:
        for ds in ds_range:
            temp_sbir = {
                "뒷벽": C / (4 * db),
                "옆벽": C / (4 * ds),
                "바닥": C / (4 * d_floor),
                "천장": C / (4 * d_ceil)
            }
            penalty = 0
            
            for f_sbir in temp_sbir.values():
                for f_mode in df_modes["주파수 (Hz)"]:
                    if abs(f_mode - f_sbir) < 10: penalty += 50
            
            sbir_vals = list(temp_sbir.values())
            for i in range(len(sbir_vals)):
                for j in range(i+1, len(sbir_vals)):
                    if abs(sbir_vals[i] - sbir_vals[j]) < 10: penalty += 30
                        
            for f_sbir in temp_sbir.values():
                if f_sbir < 100: penalty += 15
                    
            if penalty < best_score:
                best_score = penalty
                best_d_back = round(db, 2)
                best_d_side = round(ds, 2)
                best_sbirs = {k: round(v, 1) for k, v in temp_sbir.items()}
                
            iter_count += 1
            progress_bar.progress(iter_count / total_iters)
            
    progress_bar.empty()
    
    st.session_state.best_d_back = best_d_back
    st.session_state.best_d_side = best_d_side
    st.session_state.best_sbirs = best_sbirs
    st.session_state.scan_done = True

# 스캔 완료 후 추천값 출력 및 적용 버튼
if st.session_state.scan_done:
    st.success(f"**추천 좌표 도출 완료!** (최소 간섭 페널티 + 물리적 설치 가능 조건 달성)")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        # 단위에 맞게 출력 변환
        out_db = st.session_state.best_d_back if is_m else round(st.session_state.best_d_back * 100, 0)
        out_ds = st.session_state.best_d_side if is_m else round(st.session_state.best_d_side * 100, 0)
        
        st.metric(label=f"💡 추천 뒷벽 거리 ({disp_u_room})", value=f"{out_db} {disp_u_room}")
        st.metric(label=f"💡 추천 옆벽 거리 ({disp_u_room})", value=f"{out_ds} {disp_u_room}")
        
        def apply_recommendation():
            st.session_state.ui_d_back = out_db
            st.session_state.ui_d_side = out_ds
            st.session_state.scan_done = False 
            
        st.button("✨ 이 추천값으로 자동 입력 및 레이아웃 갱신", on_click=apply_recommendation, type="primary")

    with col_r2:
        st.write(f"- **예상 뒷벽 딥**: {st.session_state.best_sbirs['뒷벽']} Hz")
        st.write(f"- **예상 옆벽 딥**: {st.session_state.best_sbirs['옆벽']} Hz")
        st.write(f"- **바닥/천장 딥**: {st.session_state.best_sbirs['바닥']} Hz / {st.session_state.best_sbirs['천장']} Hz")

# --- 팩트 체크 상시 고정 (스캔 여부와 무관하게 표시) ---
st.info("""
**비판적 팩트 체크**: 자동 입력 기능은 편리하지만, 이 수학적 최적점이 항상 귀로 듣기에 좋은 것은 아닙니다. 벽에 가까워질수록 위상 상쇄(Null)는 해결될지 모르나, **경계면 효과(Boundary Gain)**에 의해 저역 에너지가 기형적으로 증폭됩니다. 자동 입력 후 도면을 확인하셨다면, **반드시 실제 환경에서 측정 후 부풀어 오른 저음역대를 깎아내는 DSP EQ(쉘빙 필터) 작업이 수반되어야 함**을 명심하십시오.
""")

# --- 기하학적 룸 시뮬레이션 (Top & Side View) ---
st.divider()
st.subheader("📐 룸 레이아웃 및 리스닝 스팟 도면")

dist_between_speakers = W - (2 * d_side)
if dist_between_speakers <= 0:
    st.error("⚠️ 에러: 스피커 간의 거리가 0 이하입니다. 옆벽과의 거리를 방 너비에 맞게 줄여주세요.")
else:
    triangle_height = dist_between_speakers * (np.sqrt(3) / 2)
    lp_y = d_back + triangle_height 
    lp_x = W / 2 
    
    if lp_y > L:
        st.warning(f"⚠️ **물리적 한계 경고**: 현재 스피커 간격({dist_between_speakers:.2f}m)으로 정삼각형 배치를 구성할 경우, 리스닝 스팟이 방의 뒷벽(길이 {L}m)을 벗어납니다.")

    fig_map, (ax_top, ax_side) = plt.subplots(1, 2, figsize=(14, 6))

    ax_top.add_patch(patches.Rectangle((0, 0), W, L, fill=False, edgecolor='black', lw=3))
    ax_top.add_patch(patches.Rectangle((d_side - spk_width/2, d_back - spk_depth), spk_width, spk_depth, fill=True, color='gray', alpha=0.5))
    ax_top.add_patch(patches.Rectangle((W - d_side - spk_width/2, d_back - spk_depth), spk_width, spk_depth, fill=True, color='gray', alpha=0.5))
    
    ax_top.plot(d_side, d_back, 's', color='black', markersize=6)
    ax_top.plot(W - d_side, d_back, 's', color='black', markersize=6)
    ax_top.plot(lp_x, lp_y, 'o', color='red', markersize=10, label='리스닝 스팟 (LP)')
    
    ax_top.plot([d_side, W - d_side, lp_x, d_side], [d_back, d_back, lp_y, d_back], 'r--', alpha=0.6)
    
    ax_top.annotate(f"{d_side:.2f}m", xy=(d_side/2, d_back), ha='center', va='bottom', color='green')
    ax_top.annotate(f"{d_back:.2f}m", xy=(d_side, d_back/2), ha='left', va='center', color='blue')
    
    ax_top.set_xlim(-0.5, W + 0.5)
    ax_top.set_ylim(-0.5, L + 0.5)
    ax_top.set_title("Top View (실제 스피커 부피 반영)")
    ax_top.set_xlabel("방 너비 (W, m)")
    ax_top.set_ylabel("방 길이 (L, m)")
    ax_top.grid(True, linestyle=':', alpha=0.5)
    ax_top.legend(loc="upper right")

    ax_side.add_patch(patches.Rectangle((0, 0), L, H, fill=False, edgecolor='black', lw=3))
    ax_side.add_patch(patches.Rectangle((d_back - spk_depth, d_floor - spk_height/2), spk_depth, spk_height, fill=True, color='gray', alpha=0.5))
    
    ax_side.plot(d_back, d_floor, 's', color='black', markersize=6)
    ax_side.plot(lp_y, d_floor, 'o', color='red', markersize=10, label='리스닝 스팟 (귀 높이)')
    
    ax_side.plot([d_back, lp_y], [d_floor, d_floor], 'r--', alpha=0.6)
    
    ax_side.annotate(f"{d_floor:.2f}m", xy=(d_back, d_floor/2), ha='left', va='center', color='orange')
    ax_side.annotate(f"{d_ceil:.2f}m", xy=(d_back, d_floor + (H - d_floor)/2), ha='left', va='center', color='purple')
    
    ax_side.set_xlim(-0.5, L + 0.5)
    ax_side.set_ylim(-0.5, H + 0.5)
    ax_side.set_title("Side View (실제 스피커 부피 반영)")
    ax_side.set_xlabel("방 길이 (L, m)")
    ax_side.set_ylabel("방 높이 (H, m)")
    ax_side.grid(True, linestyle=':', alpha=0.5)
    ax_side.legend(loc="upper right")

    st.pyplot(fig_map)

# --- 흡음 솔루션 및 비판적 분석 ---
st.divider()
st.subheader("🛠️ 데이터 기반 흡음 솔루션")

solution_cols = st.columns(2)
with solution_cols[0]:
    st.markdown("#### 📍 다공성 흡음재 두께별 기대 효과 (100Hz 이상)")
    
    thickness_options = [50, 100, 150, 200, 250] 
    for wall, freq in sbir_data.items():
        if freq >= 100:
            st.markdown(f"**[{wall} 반사 지점: {freq}Hz]**")
            wavelength = C / freq
            effect_data = []
            for t in thickness_options:
                t_m = t / 1000
                ratio = t_m / wavelength
                if ratio >= 0.25: effect = "매우 효과적 (완전 제어 수준)"
                elif ratio >= 0.125: effect = "유의미한 완화 (3~5dB 내외)"
                elif ratio >= 0.08: effect = "미세한 완화 (에너지 소폭 감소)"
                else: effect = "효과 미미 (저역 에너지 투과)"
                effect_data.append({"두께": f"{t}T", "기대 효과": effect})
            st.table(pd.DataFrame(effect_data).set_index("두께"))

with solution_cols[1]:
    st.markdown("#### ⚠️ 제어 한계 대역 및 룸모드 중첩 경고")
    
    uncontrollable = [f"**{w} ({f}Hz)**" for w, f in sbir_data.items() if f < 100]
    if uncontrollable:
        st.error("다공성 흡음재로 제어 불가능한 저역대 발견:\n" + ", ".join(uncontrollable))
        st.warning("👉 **스피커 위치 이동, 멤브레인/헬름홀츠 공명기 적용, 혹은 멀티 서브우퍼 및 DSP를 통한 액티브 제어 고려**")
    
    st.markdown("---")
    
    warnings_mode = list(set(warnings_mode)) 
    if warnings_mode:
        for w in warnings_mode:
            st.error(w)
    else:
        st.success("🟢 룸모드와 각 벽면의 SBIR 딥 간에 심각한 중첩(10Hz 이내)이 발생하지 않는 양호한 배치입니다.")

# --- 엔지니어를 위한 비판적 분석 노트 ---
st.divider()
st.info("💡 **엔지니어를 위한 데이터 분석 노트 (팩트 체크 및 한계점)**")
st.markdown("""
1. **시뮬레이션의 한계**: 본 시뮬레이션 데이터는 출발점일 뿐입니다. 방 구조에 따른 음파의 회절과 모드 변화를 완벽히 대변할 수 없으므로, **측정용 마이크와 REW(Room EQ Wizard)를 활용한 실측**을 통해 최종 배치를 결정해야 합니다.
2. **SBIR 흡음재의 정확한 타겟팅**: SBIR 딥을 완화하기 위한 다공성 흡음재의 위치는 스피커의 토인(Toe-in) 각도와 무관합니다. 우퍼 드라이버 중심에서 벽면과 만나는 **최단 거리 지점(직각을 이루는 수직선 지점)**을 1차적으로 덮어야 유의미한 에너지를 흡수할 수 있습니다.
3. **룸모드와 SBIR의 분리 접근 (DSP 제어)**: 
    - **룸모드(Room Mode)**: 2개 이상의 멀티 서브우퍼를 배치하고 MSO(Multi-Sub Optimizer), Dirac Live ART 등의 기술을 적용하면, 단순히 주파수 응답을 넘어 룸모드로 인한 과도한 잔향 링잉(Ringing, Time Domain)까지 효과적으로 캔슬링 및 컨트롤 할 수 있습니다.
    - **SBIR (Spatial Null)**: 반면 SBIR로 인해 발생한 딥은 위상 상쇄에 의한 물리적 빈공간(Null)이므로, 서브우퍼나 EQ로 에너지를 부스트한다고 해서 결코 메워지지 않습니다. 이는 반드시 물리적인 흡음이나 스피커 위치 변경을 통해서만 해결 가능합니다.
""")