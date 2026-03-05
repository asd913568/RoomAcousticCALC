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

st.set_page_config(page_title="Room Mode & SBIR 계산기", layout="wide")

# --- Session State 초기화 ---
if "ui_L" not in st.session_state: st.session_state.ui_L = 5.0
if "ui_W" not in st.session_state: st.session_state.ui_W = 4.0
if "ui_H" not in st.session_state: st.session_state.ui_H = 2.5
if "ui_d_floor" not in st.session_state: st.session_state.ui_d_floor = 1.0
if "ui_d_back" not in st.session_state: st.session_state.ui_d_back = 0.8
if "ui_d_side" not in st.session_state: st.session_state.ui_d_side = 0.8
if "scan_done" not in st.session_state: st.session_state.scan_done = False
if "prev_unit_room" not in st.session_state: st.session_state.prev_unit_room = "m (미터)"

st.title("🏠 홈 스튜디오를 위한 Room Mode & SBIR 계산기")
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

if st.session_state.prev_unit_room != unit_room:
    keys_to_convert = ["ui_L", "ui_W", "ui_H", "ui_d_floor", "ui_d_back", "ui_d_side"]
    if is_m: 
        for k in keys_to_convert: st.session_state[k] = round(st.session_state[k] / 100.0, 2)
    else: 
        for k in keys_to_convert: st.session_state[k] = round(st.session_state[k] * 100.0, 0)
    st.session_state.prev_unit_room = unit_room

# --- 사이드바: 데이터 입력 (방어적 프로그래밍: min_value 강제) ---
st.sidebar.divider()
st.sidebar.header(f"📏 방 규격 데이터 ({disp_u_room})")
step_r = 0.01 if is_m else 1.0
fmt_r = "%.2f" if is_m else "%.0f"
min_room_size = 1.0 if is_m else 100.0 # 방 최소 크기 제한

L_in = st.sidebar.number_input(f"방 길이 (세로, L)", min_value=min_room_size, step=step_r, format=fmt_r, key="ui_L")
W_in = st.sidebar.number_input(f"방 너비 (가로, W)", min_value=min_room_size, step=step_r, format=fmt_r, key="ui_W")
H_in = st.sidebar.number_input(f"방 높이 (H)", min_value=min_room_size, step=step_r, format=fmt_r, key="ui_H")
L, W, H = (L_in, W_in, H_in) if is_m else (L_in/100.0, W_in/100.0, H_in/100.0)

st.sidebar.divider()
st.sidebar.header(f"🎛️ 스피커 물리적 규격 ({disp_u_spk})")
step_s = 1.0 if is_mm else 0.1
fmt_s = "%.0f" if is_mm else "%.1f"
min_spk_size = 50.0 if is_mm else 2.0 # 스피커 최소 크기 제한

spk_w_in = st.sidebar.number_input(f"스피커 너비", min_value=min_spk_size, value=200.0 if is_mm else 8.0, step=step_s, format=fmt_s)
spk_d_in = st.sidebar.number_input(f"스피커 깊이", min_value=min_spk_size, value=300.0 if is_mm else 12.0, step=step_s, format=fmt_s)
spk_h_in = st.sidebar.number_input(f"스피커 높이", min_value=min_spk_size, value=350.0 if is_mm else 14.0, step=step_s, format=fmt_s)

spk_width = spk_w_in/1000.0 if is_mm else spk_w_in * 0.0254
spk_depth = spk_d_in/1000.0 if is_mm else spk_d_in * 0.0254
spk_height = spk_h_in/1000.0 if is_mm else spk_h_in * 0.0254

st.sidebar.divider()
st.sidebar.header("🎯 스피커 모니터링 용도")
st.sidebar.caption("스캐너가 목표로 할 정삼각형(청취) 거리를 결정합니다.")
spk_type = st.sidebar.radio("스피커 체급 선택", ["Nearfield (1.0m ~ 1.5m)", "Midfield (1.5m ~ 2.5m)", "Farfield (2.5m 이상)"], index=0)

st.sidebar.divider()
st.sidebar.header(f"🔊 스피커 드라이버 중심 거리 ({disp_u_room})")
min_dist = 0.05 if is_m else 5.0 # 최소 거리 제한 (0 나눗셈 완벽 차단)

d_back_in = st.sidebar.number_input(f"뒷벽과의 거리", min_value=min_dist, step=step_r, format=fmt_r, key="ui_d_back")
d_side_in = st.sidebar.number_input(f"옆벽과의 거리", min_value=min_dist, step=step_r, format=fmt_r, key="ui_d_side")
d_floor_in = st.sidebar.number_input(f"바닥과의 거리 (귀 높이)", min_value=min_dist, step=step_r, format=fmt_r, key="ui_d_floor")
d_back, d_side, d_floor = (d_back_in, d_side_in, d_floor_in) if is_m else (d_back_in/100.0, d_side_in/100.0, d_floor_in/100.0)

# 물리적 에러 차단 로직 보강
error_flags = False

if d_floor >= H - 0.1:
    st.sidebar.error("⚠️ 오류: 바닥과의 거리가 방 높이와 같거나 큽니다.")
    d_ceil = 0.1 
    error_flags = True
else:
    d_ceil = H - d_floor
    c_disp = d_ceil if is_m else d_ceil * 100.0
    st.sidebar.info(f"💡 천장과의 거리 (자동 계산): {fmt_r % c_disp} {disp_u_room}")

if d_back < spk_depth: 
    st.sidebar.error(f"⚠️ 오류: 뒷벽 거리가 스피커 깊이보다 짧습니다.")
    error_flags = True
if d_side < (spk_width / 2): 
    st.sidebar.error(f"⚠️ 오류: 옆벽 거리가 스피커 너비의 절반보다 짧습니다.")
    error_flags = True
if W - (2 * d_side) <= 0.1:
    st.sidebar.error(f"⚠️ 오류: 스피커 간격이 물리적으로 성립하지 않습니다. 옆벽 거리를 줄이거나 방 너비를 늘려주세요.")
    error_flags = True

st.sidebar.divider()
st.sidebar.markdown("👨‍💻 Made by **Chandler.J 정찬영**")
st.sidebar.markdown("[📸 Instagram](https://www.instagram.com/chanyoung_3863/)")

if error_flags:
    st.error("🚨 **입력된 수치에 물리적인 모순이 있습니다. 좌측 사이드바의 오류 메시지를 확인하고 수치를 수정해 주세요.**")
    st.stop()

# --- 계산 로직 ---
C = 344
modes = []
for n in range(1, 4):
    modes.append({"유형": "세로(L)", "차수": f"{n}차", "주파수 (Hz)": round((C * n) / (2 * L), 1)})
    modes.append({"유형": "가로(W)", "차수": f"{n}차", "주파수 (Hz)": round((C * n) / (2 * W), 1)})
    modes.append({"유형": "높이(H)", "차수": f"{n}차", "주파수 (Hz)": round((C * n) / (2 * H), 1)})
df_modes = pd.DataFrame(modes).sort_values("주파수 (Hz)").reset_index(drop=True)

sbir_data = {
    "뒷벽": round(C / (4 * d_back), 1),
    "옆벽": round(C / (4 * d_side), 1),
    "바닥": round(C / (4 * d_floor), 1),
    "천장": round(C / (4 * d_ceil), 1)
}

warnings_mode, sbir_table, overlap_freqs = [], [], []

for wall, f_sbir in sbir_data.items():
    overlap_sbir = False
    for f_mode in df_modes["주파수 (Hz)"]:
        if abs(f_mode - f_sbir) < 10:
            warnings_mode.append(f"- **{wall} SBIR({f_sbir}Hz)**과 **룸모드({f_mode}Hz)** 중첩.")
            overlap_freqs.append(f_sbir)
            
    for ow, of in sbir_data.items():
        if wall != ow and abs(f_sbir - of) < 10:
            overlap_sbir = True
            overlap_freqs.append(f_sbir)
            
    status = "🔴 위험 (중첩)" if (overlap_sbir or f_sbir in overlap_freqs) else "🟢 양호"
    sbir_table.append({"반사면": wall, "딥 주파수 (Hz)": f_sbir, "상태": status})
df_sbir = pd.DataFrame(sbir_table)

# --- 결과 화면 1: 계산 데이터 ---
st.subheader("📊 Room Mode & SBIR 계산 결과")
col1, col2 = st.columns(2)
with col1:
    st.write("**룸모드 분포 (축방향)**")
    st.dataframe(df_modes, use_container_width=True, hide_index=True)
with col2:
    st.write("**현재 배치별 SBIR 딥(Dip)**")
    st.dataframe(df_sbir, use_container_width=True, hide_index=True)

# --- 결과 화면 2: 시각화 ---
st.divider()
st.subheader("📈 주파수 간섭 시각화 (Log Scale)")
fig, ax = plt.subplots(figsize=(14, 3)) 

for i, freq in enumerate(df_modes["주파수 (Hz)"]):
    ax.axvline(x=freq, color='red', linestyle='--', alpha=0.4, linewidth=2, label='룸모드' if i==0 else "")

colors = {'뒷벽': 'blue', '옆벽': 'green', '바닥': 'orange', '천장': 'purple'}
for wall, freq in sbir_data.items():
    ax.axvline(x=freq, color=colors[wall], linewidth=3, label=f'SBIR ({wall})')

for f in set(overlap_freqs):
    ax.axvspan(f - 5, f + 5, color='red', alpha=0.15)
    ax.text(f, 0.5, '중첩 위험', color='red', rotation=90, va='center', ha='center', 
            transform=ax.get_xaxis_transform(), fontweight='bold', alpha=0.8)

ax.set_xscale('log'); ax.set_xlim(20, 350)
ticks = [20, 30, 40, 50, 60, 80, 100, 150, 200, 300]
ax.set_xticks(ticks); ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
ax.set_yticks([]); ax.grid(True, which='both', axis='x', linestyle=':', alpha=0.4) 
ax.legend(loc='upper right', bbox_to_anchor=(1, 1.15), ncol=5) 
st.pyplot(fig)

# --- 도면 렌더링 1: 스피커 배치 전용 도면 ---
st.divider()
st.subheader("📐 룸 레이아웃 및 리스닝 스팟 도면")
dist_speakers = W - (2 * d_side)

scale = 1.0 if is_m else 100.0
grid_step = 1.0 if is_m else 100.0 

p_W, p_L, p_H = W * scale, L * scale, H * scale
p_ds, p_db = d_side * scale, d_back * scale
p_sw, p_sd, p_sh = spk_width * scale, spk_depth * scale, spk_height * scale
p_dfl, p_dcl = d_floor * scale, d_ceil * scale
pad = 0.5 * scale

h_tri = dist_speakers * (np.sqrt(3) / 2)
y_ref_side_real = d_back + (h_tri * d_side) / (W/2 + d_side)
y_ref_ceil_real = d_back + (h_tri) / 2

lp_y, lp_x = d_back + h_tri, W / 2 
p_lpx, p_lpy = lp_x * scale, lp_y * scale

disp_lp_x = lp_x if is_m else lp_x * 100.0
disp_lp_y = lp_y if is_m else lp_y * 100.0

if lp_y > L: st.warning("⚠️ 물리적 한계 경고: 리스닝 스팟이 방의 뒷벽을 벗어납니다.")

fig_map, (at, aside) = plt.subplots(1, 2, figsize=(14, 6))

# Top View
at.set_aspect('equal', adjustable='box') 
at.xaxis.set_major_locator(ticker.MultipleLocator(grid_step)) 
at.yaxis.set_major_locator(ticker.MultipleLocator(grid_step))

at.add_patch(patches.Rectangle((0, 0), p_W, p_L, fill=False, edgecolor='black', lw=3))
at.axhline(y=p_L * 0.38, color='magenta', linestyle='-.', lw=1.5, alpha=0.5)
at.text(p_W / 2, p_L * 0.38 + pad/4, "38% 룰 (전면 기준)", color='magenta', ha='center', va='bottom', fontsize=9, alpha=0.8)
at.axhline(y=p_L * 0.62, color='magenta', linestyle=':', lw=1.0, alpha=0.3)
at.text(p_W / 2, p_L * 0.62 + pad/4, "38% 룰 (후면 기준)", color='magenta', ha='center', va='bottom', fontsize=8, alpha=0.5)

at.add_patch(patches.Rectangle((p_ds-p_sw/2, p_db-p_sd), p_sw, p_sd, color='gray', alpha=0.5))
at.add_patch(patches.Rectangle((p_W-p_ds-p_sw/2, p_db-p_sd), p_sw, p_sd, color='gray', alpha=0.5))
at.plot(p_ds, p_db, 's', color='black', markersize=8, label='Driver Center')
at.plot(p_W-p_ds, p_db, 's', color='black', markersize=8)
at.plot([p_ds, p_W - p_ds, p_lpx, p_ds], [p_db, p_db, p_lpy, p_db], 'r--', alpha=0.6)

at.plot(p_lpx, p_lpy, 'o', color='red', markersize=10, label='LP')
at.annotate(f"LP (가로 {fmt_r % disp_lp_x}{disp_u_room}, 세로 {fmt_r % disp_lp_y}{disp_u_room})", 
            xy=(p_lpx, p_lpy), xytext=(0, 12), textcoords="offset points",
            ha='center', va='bottom', color='red', fontsize=9, fontweight='bold')

at.plot([0, p_ds], [p_db, p_db], color='green', linestyle=':', lw=2)
at.plot([p_ds, p_ds], [0, p_db], color='blue', linestyle=':', lw=2)

at.annotate(f"{fmt_r % d_side_in}{disp_u_room}", xy=(p_ds/2, p_db), ha='center', va='bottom', color='green')
at.annotate(f"{fmt_r % d_back_in}{disp_u_room}", xy=(p_ds, p_db/2), ha='left', va='center', color='blue')

max_y_limit = max(p_L, p_lpy) + pad
at.set_xlim(-pad, p_W + pad); at.set_ylim(-pad, max_y_limit)
at.set_title(f"Top View (배치 Layout)"); at.grid(True, linestyle=':', alpha=0.5); at.legend(loc='lower right')

# Side View
aside.set_aspect('equal', adjustable='box') 
aside.xaxis.set_major_locator(ticker.MultipleLocator(grid_step))
aside.yaxis.set_major_locator(ticker.MultipleLocator(grid_step))

aside.add_patch(patches.Rectangle((0, 0), p_L, p_H, fill=False, edgecolor='black', lw=3))
aside.axvline(x=p_L * 0.38, color='magenta', linestyle='-.', lw=1.5, alpha=0.5)

aside.add_patch(patches.Rectangle((p_db-p_sd, p_dfl-p_sh/2), p_sd, p_sh, color='gray', alpha=0.5))
aside.plot(p_db, p_dfl, 's', color='black', markersize=8)

aside.plot(p_lpy, p_dfl, 'o', color='red', markersize=10)
aside.annotate(f"LP (세로 {fmt_r % disp_lp_y}{disp_u_room}, 높이 {fmt_r % d_floor_in}{disp_u_room})", 
               xy=(p_lpy, p_dfl), xytext=(0, 12), textcoords="offset points",
               ha='center', va='bottom', color='red', fontsize=9, fontweight='bold')

aside.plot([p_db, p_lpy], [p_dfl, p_dfl], 'r--', alpha=0.6)
aside.plot([p_db, p_db], [0, p_dfl], color='orange', linestyle=':', lw=2)
aside.plot([p_db, p_db], [p_dfl, p_H], color='purple', linestyle=':', lw=2)

aside.annotate(f"{fmt_r % d_floor_in}{disp_u_room}", xy=(p_db, p_dfl/2), ha='left', va='center', color='orange')
aside.annotate(f"{fmt_r % c_disp}{disp_u_room}", xy=(p_db, p_dfl + p_dcl/2), ha='left', va='center', color='purple')

max_x_limit = max(p_L, p_lpy) + pad
aside.set_xlim(-pad, max_x_limit); aside.set_ylim(-pad, p_H + pad)
aside.set_title(f"Side View (배치 Layout)"); aside.grid(True, linestyle=':', alpha=0.5)

st.pyplot(fig_map)

# --- 튜토리얼 및 2분할 스캐너 ---
st.divider()
st.subheader("🎯 스피커 배치 최적화 스캐너 (Hybrid Workflow)")

with st.expander("📖 [필독] 완벽한 배치를 위한 하이브리드 워크플로우 가이드"):
    st.markdown("""
    음향 세팅에서 완벽한 배치는 없으며, **룸모드(방의 울림)**와 **SBIR(위상 상쇄)** 사이의 타협점을 찾는 교차 검증(Iteration) 과정입니다.  
    
    1. **스텝 1 (LP 우선)**: 먼저 `[Mode A]` 탭을 열어 청취 위치(LP)를 방 길이의 38% 근처 안정 지대에 놓습니다.
    2. **스텝 2 (검증)**: 도출된 스피커 거리를 적용한 뒤, 도면 아래의 흡음 솔루션 표에서 **100Hz 이하에 심각한 딥(Dip)**이 생기는지 확인합니다. (이 대역의 SBIR은 서브우퍼가 없다면 흡음이나 EQ로 해결 불가합니다.)
    3. **스텝 3 (타협)**: SBIR 딥이 너무 심각하다면, `[Mode B]` 탭으로 넘어가 SBIR을 피하는 스피커 좌표를 찾습니다.
    4. **스텝 4 (최종 조정)**: 추천값을 적용한 후, 도면 상의 빨간 점(LP)이 방의 50%나 25% 같은 '데드스팟'에 들어가지 않도록 미세 조정하며 REW로 최종 실측합니다.
    
    > **💡 서브우퍼 사용자의 경우**: 메인 스피커의 80Hz 이하 SBIR 딥은 서브우퍼가 담당하므로 무시해도 좋습니다. 이 경우 `[Mode A]` 방식이 더 유리할 수 있습니다.
    """)

tab_A, tab_B = st.tabs(["🎯 Mode A: 리스닝 스팟 (38% Rule) 최우선", "🎯 Mode B: SBIR 간섭 최소화 최우선"])

with tab_A:
    t_min, t_max = 1.0, 1.5
    if "Midfield" in spk_type: t_min, t_max = 1.5, 2.5
    elif "Farfield" in spk_type: t_min, t_max = 2.5, float('inf')
    
    if st.button("🚀 Mode A 스캔 시작 (38% 룰 기반)", key="btn_mode_a"):
        best_score_A, best_db_A, best_ds_A, best_sbirs_A = float('inf'), d_back, d_side, {}
        min_db = spk_depth + 0.05
        min_ds = (spk_width / 2) + 0.05
        ds_range = np.arange(min_ds, W/2 - 0.4, 0.01)
        
        valid_found = False
        for target_y in [L * 0.38, L * 0.62]: 
            for ds in ds_range:
                tri_dist = W - (2 * ds)
                if not (t_min <= tri_dist <= t_max): continue
                
                tri_height = tri_dist * (np.sqrt(3) / 2)
                db = target_y - tri_height
                
                if db >= min_db: 
                    valid_found = True
                    ts = {"뒷벽": C/(4*db), "옆벽": C/(4*ds), "바닥": C/(4*d_floor), "천장": C/(4*d_ceil)}
                    penalty = sum(50 for f in ts.values() for m in df_modes["주파수 (Hz)"] if abs(m-f) < 10)
                    vs = list(ts.values()); penalty += sum(30 for i in range(4) for j in range(i+1, 4) if abs(vs[i]-vs[j]) < 10)
                    penalty += sum(15 for f in ts.values() if f < 100)
                    if penalty < best_score_A: best_score_A, best_db_A, best_ds_A, best_sbirs_A = penalty, db, ds, {k: round(v, 1) for k, v in ts.items()}

        if not valid_found: st.error(f"⚠️ **계산 불가**: 방 너비({W_in}{disp_u_room})와 '{spk_type}' 조건으로는 38% 지점에 LP를 두는 배치가 물리적으로 불가능합니다. Mode B를 사용하세요.")
        else:
            st.session_state.best_d_back, st.session_state.best_d_side, st.session_state.best_sbirs = best_db_A, best_ds_A, best_sbirs_A
            st.session_state.scan_done = True
            st.success("**Mode A 기반 추천 좌표 도출 완료!**")

with tab_B:
    if st.button("🚀 Mode B 스캔 시작 (SBIR 최소화)", key="btn_mode_b"):
        best_score_B, best_db_B, best_ds_B, best_sbirs_B = float('inf'), d_back, d_side, {}
        min_db = spk_depth + 0.05
        min_ds = (spk_width / 2) + 0.05
        db_range = np.arange(min_db, min(L/2, 1.5), 0.05)
        ds_range = np.arange(min_ds, W/2 - 0.4, 0.05) 
        
        progress_bar = st.progress(0); total = len(db_range) * len(ds_range); count = 0
        valid_found = False
        for db in db_range:
            for ds in ds_range:
                count += 1
                tri_dist = W - (2 * ds)
                if not (t_min <= tri_dist <= t_max):
                    progress_bar.progress(count / total)
                    continue
                valid_found = True
                ts = {"뒷벽": C/(4*db), "옆벽": C/(4*ds), "바닥": C/(4*d_floor), "천장": C/(4*d_ceil)}
                penalty = sum(50 for f in ts.values() for m in df_modes["주파수 (Hz)"] if abs(m-f) < 10)
                vs = list(ts.values()); penalty += sum(30 for i in range(4) for j in range(i+1, 4) if abs(vs[i]-vs[j]) < 10)
                penalty += sum(15 for f in ts.values() if f < 100)
                if penalty < best_score_B: best_score_B, best_db_B, best_ds_B, best_sbirs_B = penalty, db, ds, {k: round(v, 1) for k, v in ts.items()}
                progress_bar.progress(count / total)
        progress_bar.empty()
        if not valid_found: st.error(f"⚠️ **스캔 실패**: 현재 입력된 방 너비로는 선택하신 타겟 청취 거리를 확보할 수 없습니다.")
        else:
            st.session_state.best_d_back, st.session_state.best_d_side, st.session_state.best_sbirs = best_db_B, best_ds_B, best_sbirs_B
            st.session_state.scan_done = True
            st.success("**Mode B 기반 추천 좌표 도출 완료!**")

if st.session_state.scan_done:
    odb = st.session_state.best_d_back if is_m else round(st.session_state.best_d_back * 100, 0)
    ods = st.session_state.best_d_side if is_m else round(st.session_state.best_d_side * 100, 0)
    cr1, cr2 = st.columns(2)
    with cr1:
        st.metric(label=f"💡 추천 뒷벽 거리 ({disp_u_room})", value=f"{odb} {disp_u_room}")
        st.metric(label=f"💡 추천 옆벽 거리 ({disp_u_room})", value=f"{ods} {disp_u_room}")
        def update_layout():
            st.session_state.ui_d_back = odb
            st.session_state.ui_d_side = ods
            st.session_state.scan_done = False
        st.button("✨ 계산된 추천값으로 자동 입력 및 레이아웃 갱신", type="primary", on_click=update_layout)
    with cr2:
        st.write(f"- **예상 뒷벽 딥**: {st.session_state.best_sbirs.get('뒷벽', 0)} Hz / **옆벽 딥**: {st.session_state.best_sbirs.get('옆벽', 0)} Hz")

# --- 흡음 솔루션 및 데이터 ---
st.divider()
st.subheader("🛠️ SBIR 개선을 위한 흡음 솔루션")
sc1, sc2 = st.columns(2)
with sc1:
    st.markdown("#### 🔍 현재 배치별 SBIR 딥 요약")
    st.dataframe(df_sbir, use_container_width=True, hide_index=True)
with sc2:
    st.markdown("#### 📍 다공성 흡음재 두께별 기대 효과 (100Hz 이상)")
    for wall, freq in sbir_data.items():
        if freq >= 100:
            st.markdown(f"**[{wall} 반사 지점: {freq}Hz]**")
            wav = C/freq; ed = []
            for t in [50, 100, 150, 200, 250]:
                r = (t/1000)/wav
                eff = "매우 효과적 (완전 제어 수준)" if r>=0.25 else "유의미한 완화 (3~5dB 내외)" if r>=0.125 else "미세한 완화" if r>=0.08 else "효과 미미"
                ed.append({"두께": f"{t}T", "기대 효과": eff})
            st.table(pd.DataFrame(ed).set_index("두께"))

st.markdown("---")
st.markdown("#### ⚠️ 제어 한계 대역 및 룸모드 중첩 경고")
uncontrollable = [f"**{w} ({f}Hz)**" for w, f in sbir_data.items() if f < 100]
if uncontrollable:
    st.error("다공성 흡음재로 제어 불가능한 저역대 발견:\n" + ", ".join(uncontrollable))
    st.warning("👉 **스피커 위치 이동, 멤브레인/헬름홀츠 공명기 적용, 혹은 멀티 서브우퍼 및 DSP를 통한 액티브 제어 고려**")
if warnings_mode:
    for w in set(warnings_mode): st.error(w)
else: st.success("🟢 룸모드와 각 벽면의 SBIR 딥 간에 심각한 중첩이 발생하지 않는 양호한 배치입니다.")


# --- 신규 도면 렌더링 2: 룸 트리트먼트 가이드 및 튜토리얼 ---
st.divider()
st.subheader("🛠️ 룸 트리트먼트 가이드 (흡음재 부착 시뮬레이션)")

with st.expander("📖 [필독] 흡음 vs 분산 (RT60 타겟) 및 에어갭(Air Gap) 시공 가이드"):
    st.markdown("""
    #### 1. RT60 잔향 시간에 따른 재질 선택 (Absorber vs Diffuser)
    모든 반사 지점에 흡음재를 바르는 것은 초보적인 실수입니다. REW 측정 결과 룸의 잔향 시간(RT60)이 이미 소규모 룸 타겟인 **0.2초 ~ 0.3초**에 도달했다면 주의해야 합니다.
    * **SBIR 타겟 (파란색/초록색)**: 저음역대 위상 상쇄 방어가 목적이므로, 잔향 시간과 무관하게 **두꺼운 다공성 흡음재(Bass Trap)**가 필수입니다.
    * **1차 반사 타겟 (빨간색/주황색)**: 방이 이미 충분히 건조하다면(데드 룸), 흡음재 대신 소리 에너지를 깎지 않고 방향만 흩뿌려주는 **디퓨저(분산재)**를 시공하는 것이 훨씬 자연스러운 환경을 만듭니다.

    #### 2. 에어갭(Air Gap)의 마법: 천장 클라우드 시공 팁
    다공성 흡음재는 소리 입자의 속도가 최대가 되는 **1/4 파장 지점**에서 가장 뛰어난 마찰 효율을 냅니다.
    * **데이터 팩트 체크**: 100mm 두께의 흡음재를 천장에서 **100mm 띄워서(Air Gap) 시공**하게 되면, 저음 흡수 효율이 두께 200mm짜리 패널을 띄우지 않고 붙였을 때와 거의 동일해집니다. 이를 통해 천장 하중과 자재비를 획기적으로 줄일 수 있습니다.
    
    #### 3. 패널 규격 팩트 체크 (소리는 레이저가 아닙니다)
    * 아래 제공되는 좌표는 소리가 튕기는 **정중앙(Center Point)**입니다. 스피커의 부채꼴 지향각(Dispersion)을 커버하기 위해서는 해당 좌표를 중심으로 국내 기성품 표준 사이즈인 **500mm x 1000mm (50cm x 100cm)** 규격의 패널을 배치하는 것을 권장합니다.
    """)


col_c1, col_c2, col_c3 = st.columns(3)
val_y_side = y_ref_side_real if is_m else y_ref_side_real * 100
val_y_ceil = y_ref_ceil_real if is_m else y_ref_ceil_real * 100

with col_c1:
    st.info(f"📍 **옆벽 1차 반사 패널 중앙점**\n\n앞벽에서 **{fmt_r % val_y_side} {disp_u_room}** 지점")
with col_c2:
    st.info(f"📍 **천장 클라우드 중앙점**\n\n앞벽에서 **{fmt_r % val_y_ceil} {disp_u_room}** 지점")
with col_c3:
    st.success("📏 **국내 기성 패널 규격**\n\n가로 500mm x 세로 1000mm")

fig_trt, (trt_top, trt_side) = plt.subplots(1, 2, figsize=(14, 6))

panel_w, panel_d = 0.5 * scale, 0.1 * scale
p_y_side = y_ref_side_real * scale
p_y_ceil = y_ref_ceil_real * scale

# [Top View: 룸 트리트먼트]
trt_top.set_aspect('equal', adjustable='box') 
trt_top.xaxis.set_major_locator(ticker.MultipleLocator(grid_step)) 
trt_top.yaxis.set_major_locator(ticker.MultipleLocator(grid_step))

trt_top.add_patch(patches.Rectangle((0, 0), p_W, p_L, fill=False, edgecolor='black', lw=3))

trt_top.add_patch(patches.Rectangle((p_ds-p_sw/2, p_db-p_sd), p_sw, p_sd, color='gray', alpha=0.5))
trt_top.add_patch(patches.Rectangle((p_W-p_ds-p_sw/2, p_db-p_sd), p_sw, p_sd, color='gray', alpha=0.5))

trt_top.plot(p_ds, p_db, 's', color='black', markersize=6)
trt_top.plot(p_W-p_ds, p_db, 's', color='black', markersize=6)

trt_top.plot(p_lpx, p_lpy, 'o', color='red', markersize=8)
trt_top.annotate(f"LP (가로 {fmt_r % disp_lp_x}{disp_u_room}, 세로 {fmt_r % disp_lp_y}{disp_u_room})", 
                 xy=(p_lpx, p_lpy), xytext=(0, 12), textcoords="offset points",
                 ha='center', va='bottom', color='red', fontsize=9, fontweight='bold')

# SBIR 패널
trt_top.add_patch(patches.Rectangle((p_ds - panel_w/2, 0), panel_w, panel_d, color='blue', alpha=0.7))
trt_top.add_patch(patches.Rectangle((p_W - p_ds - panel_w/2, 0), panel_w, panel_d, color='blue', alpha=0.7))
trt_top.add_patch(patches.Rectangle((0, p_db - panel_w/2), panel_d, panel_w, color='green', alpha=0.7))
trt_top.add_patch(patches.Rectangle((p_W - panel_d, p_db - panel_w/2), panel_d, panel_w, color='green', alpha=0.7))

# 1차 반사 패널
trt_top.add_patch(patches.Rectangle((0, p_y_side - panel_w/2), panel_d, panel_w, color='red', alpha=0.6))
trt_top.add_patch(patches.Rectangle((p_W - panel_d, p_y_side - panel_w/2), panel_d, panel_w, color='red', alpha=0.6))

trt_top.annotate(f"{fmt_r % val_y_side}{disp_u_room}", xy=(panel_d, p_y_side), ha='left', va='center', color='red', fontsize=10, fontweight='bold')

trt_top.plot([p_ds, 0, p_lpx], [p_db, p_y_side, p_lpy], color='red', linestyle='--', lw=1.5, alpha=0.4)
trt_top.plot([p_W - p_ds, p_W, p_lpx], [p_db, p_y_side, p_lpy], color='red', linestyle='--', lw=1.5, alpha=0.4)

trt_top.set_xlim(-pad, p_W + pad); trt_top.set_ylim(-pad, max_y_limit)
trt_top.set_title(f"Top View (Acoustic Treatment)"); trt_top.grid(True, linestyle=':', alpha=0.5)

# [Side View: 룸 트리트먼트]
trt_side.set_aspect('equal', adjustable='box') 
trt_side.xaxis.set_major_locator(ticker.MultipleLocator(grid_step)) 
trt_side.yaxis.set_major_locator(ticker.MultipleLocator(grid_step))

trt_side.add_patch(patches.Rectangle((0, 0), p_L, p_H, fill=False, edgecolor='black', lw=3))

trt_side.add_patch(patches.Rectangle((p_db-p_sd, p_dfl-p_sh/2), p_sd, p_sh, color='gray', alpha=0.5))

trt_side.plot(p_db, p_dfl, 's', color='black', markersize=6)

trt_side.plot(p_lpy, p_dfl, 'o', color='red', markersize=8)
trt_side.annotate(f"LP (세로 {fmt_r % disp_lp_y}{disp_u_room}, 높이 {fmt_r % d_floor_in}{disp_u_room})", 
                  xy=(p_lpy, p_dfl), xytext=(0, 12), textcoords="offset points",
                  ha='center', va='bottom', color='red', fontsize=9, fontweight='bold')

# SBIR 패널
trt_side.add_patch(patches.Rectangle((0, p_dfl - panel_w/2), panel_d, panel_w, color='blue', alpha=0.7))

# 1차 반사 패널
trt_side.add_patch(patches.Rectangle((p_y_ceil - panel_w/2, p_H - panel_d), panel_w, panel_d, color='purple', alpha=0.6))
trt_side.add_patch(patches.Rectangle((p_y_ceil - panel_w/2, 0), panel_w, panel_d, color='orange', alpha=0.5))

trt_side.annotate(f"{fmt_r % val_y_ceil}{disp_u_room}", xy=(p_y_ceil, p_H - panel_d), ha='center', va='top', color='purple', fontsize=10, fontweight='bold')

trt_side.plot([p_db, p_y_ceil, p_lpy], [p_dfl, p_H, p_dfl], color='purple', linestyle='--', lw=1.5, alpha=0.4)
trt_side.plot([p_db, p_y_ceil, p_lpy], [p_dfl, 0, p_dfl], color='orange', linestyle='--', lw=1.5, alpha=0.4)

trt_side.set_xlim(-pad, max_x_limit); trt_side.set_ylim(-pad, p_H + pad)
trt_side.set_title(f"Side View (Acoustic Treatment)"); trt_side.grid(True, linestyle=':', alpha=0.5)

st.pyplot(fig_trt)

# --- 엔지니어를 위한 비판적 분석 노트 (수정 완) ---
st.divider()
st.info("💡 **엔지니어를 위한 데이터 분석 노트 (팩트 체크 및 한계점)**")
st.markdown("""
1. **시뮬레이션의 한계**: 본 시뮬레이션 데이터는 출발점일 뿐입니다. 방 구조(가벽/석고보드 등)에 따른 음파의 회절과 모드 변화를 완벽히 대변할 수 없으므로, **측정용 마이크와 REW(Room EQ Wizard)를 활용한 실측**을 통해 최종 배치를 결정해야 합니다.
2. **SBIR 흡음재의 정확한 타겟팅**: SBIR 딥을 완화하기 위한 다공성 흡음재의 위치는 스피커의 토인(Toe-in) 각도와 무관합니다. 우퍼 드라이버 중심에서 벽면과 만나는 **최단 거리 지점(직각을 이루는 수직선 지점)**을 1차적으로 덮어야 유의미한 에너지를 흡수할 수 있습니다.
3. **룸모드와 SBIR의 분리 접근 (DSP 및 서브우퍼 제어)**: 
    - **룸모드(Room Mode)**: 2개 이상의 멀티 서브우퍼를 배치하고 MSO, Dirac Live ART 등의 DSP를 적용하면 주파수 응답을 넘어 룸모드로 인한 과도한 잔향 링잉(Time Domain)까지 효과적으로 제어할 수 있습니다.
    - **SBIR (Spatial Null)**: SBIR 딥은 위상 상쇄에 의한 물리적 빈공간(Null)이므로, 해당 대역을 **단순히 EQ로 부스트한다고 해서 결코 메워지지 않습니다.** 이를 해결하는 방법은 세 가지입니다. ① 스피커 위치 변경, ② 두꺼운 베이스 트랩 시공, ③ **베이스 매니지먼트 (크로스오버를 설정해 딥이 발생하는 저역대를 벽에 밀착시킨 서브우퍼가 대신 재생하게 하여 원천 회피)**.
""")