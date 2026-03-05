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

# 단위 변경 시 기존 입력값 안전하게 변환
if st.session_state.prev_unit_room != unit_room:
    keys_to_convert = ["ui_L", "ui_W", "ui_H", "ui_d_floor", "ui_d_back", "ui_d_side"]
    if is_m: 
        for k in keys_to_convert: st.session_state[k] = round(st.session_state[k] / 100.0, 2)
    else: 
        for k in keys_to_convert: st.session_state[k] = round(st.session_state[k] * 100.0, 0)
    st.session_state.prev_unit_room = unit_room

# --- 사이드바: 데이터 입력 ---
st.sidebar.divider()
st.sidebar.header(f"📏 방 규격 데이터 ({disp_u_room})")
step_r = 0.01 if is_m else 1.0
fmt_r = "%.2f" if is_m else "%.0f"

L_in = st.sidebar.number_input(f"방 길이 (세로, L)", step=step_r, format=fmt_r, key="ui_L")
W_in = st.sidebar.number_input(f"방 너비 (가로, W)", step=step_r, format=fmt_r, key="ui_W")
H_in = st.sidebar.number_input(f"방 높이 (H)", step=step_r, format=fmt_r, key="ui_H")

L, W, H = (L_in, W_in, H_in) if is_m else (L_in/100.0, W_in/100.0, H_in/100.0)

st.sidebar.divider()
st.sidebar.header(f"🎛️ 스피커 물리적 규격 ({disp_u_spk})")
step_s = 1.0 if is_mm else 0.1
fmt_s = "%.0f" if is_mm else "%.1f"

spk_w_in = st.sidebar.number_input(f"스피커 너비", value=200.0 if is_mm else 8.0, step=step_s, format=fmt_s)
spk_d_in = st.sidebar.number_input(f"스피커 깊이", value=300.0 if is_mm else 12.0, step=step_s, format=fmt_s)
spk_h_in = st.sidebar.number_input(f"스피커 높이", value=350.0 if is_mm else 14.0, step=step_s, format=fmt_s)

spk_width = spk_w_in/1000.0 if is_mm else spk_w_in * 0.0254
spk_depth = spk_d_in/1000.0 if is_mm else spk_d_in * 0.0254
spk_height = spk_h_in/1000.0 if is_mm else spk_h_in * 0.0254

st.sidebar.divider()
st.sidebar.header(f"🔊 스피커 드라이버 중심 거리 ({disp_u_room})")
d_back_in = st.sidebar.number_input(f"뒷벽과의 거리", step=step_r, format=fmt_r, key="ui_d_back")
d_side_in = st.sidebar.number_input(f"옆벽과의 거리", step=step_r, format=fmt_r, key="ui_d_side")
d_floor_in = st.sidebar.number_input(f"바닥과의 거리 (귀 높이)", step=step_r, format=fmt_r, key="ui_d_floor")

d_back, d_side, d_floor = (d_back_in, d_side_in, d_floor_in) if is_m else (d_back_in/100.0, d_side_in/100.0, d_floor_in/100.0)

# 천장 거리 자동 연산
if d_floor >= H:
    st.sidebar.error("⚠️ 오류: 바닥과의 거리가 방 높이보다 크거나 같습니다.")
    d_ceil = 0.01 
else:
    d_ceil = H - d_floor
    c_disp = d_ceil if is_m else d_ceil * 100.0
    st.sidebar.info(f"💡 천장과의 거리 (자동 계산): {fmt_r % c_disp} {disp_u_room}")

if d_back < spk_depth: st.sidebar.error(f"⚠️ 오류: 뒷벽 거리가 스피커 깊이보다 짧습니다.")
if d_side < (spk_width / 2): st.sidebar.error(f"⚠️ 오류: 옆벽 거리가 스피커 너비의 절반보다 짧습니다.")

st.sidebar.divider()
st.sidebar.markdown("👨‍💻 Made by **Chandler.J 정찬영**")
st.sidebar.markdown("[📸 Instagram](https://www.instagram.com/chanyoung_3863/)")

# --- 계산 로직 ---
C = 344
modes = []
for n in range(1, 4):
    modes.append({"유형": "세로(L)", "차수": f"{n}차", "주파수 (Hz)": round((C * n) / (2 * L), 1)})
    modes.append({"유형": "가로(W)", "차수": f"{n}차", "주파수 (Hz)": round((C * n) / (2 * W), 1)})
    modes.append({"유형": "높이(H)", "차수": f"{n}차", "주파수 (Hz)": round((C * n) / (2 * H), 1)})
df_modes = pd.DataFrame(modes).sort_values("주파수 (Hz)").reset_index(drop=True)

sbir_data = {
    "뒷벽": round(C / (4 * max(d_back, 0.01)), 1),
    "옆벽": round(C / (4 * max(d_side, 0.01)), 1),
    "바닥": round(C / (4 * max(d_floor, 0.01)), 1),
    "천장": round(C / (4 * max(d_ceil, 0.01)), 1)
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

# --- 도면 렌더링 (포맷 에러 수정 완료) ---
st.divider()
st.subheader("📐 룸 레이아웃 및 리스닝 스팟 도면")
dist_speakers = W - (2 * d_side)
if dist_speakers <= 0: st.error("⚠️ 에러: 스피커 간격 오류.")
else:
    th = dist_speakers * (np.sqrt(3) / 2); lp_y, lp_x = d_back + th, W / 2 
    if lp_y > L: st.warning("⚠️ 물리적 한계 경고: 리스닝 스팟이 방의 뒷벽을 벗어납니다.")
    
    scale = 1.0 if is_m else 100.0
    p_W, p_L, p_H = W * scale, L * scale, H * scale
    p_ds, p_db = d_side * scale, d_back * scale
    p_sw, p_sd, p_sh = spk_width * scale, spk_depth * scale, spk_height * scale
    p_lpx, p_lpy = lp_x * scale, lp_y * scale
    p_dfl, p_dcl = d_floor * scale, d_ceil * scale
    pad = 0.5 * scale

    fig_map, (at, aside) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Top View
    at.add_patch(patches.Rectangle((0, 0), p_W, p_L, fill=False, edgecolor='black', lw=3))
    at.add_patch(patches.Rectangle((p_ds-p_sw/2, p_db-p_sd), p_sw, p_sd, color='gray', alpha=0.5))
    at.add_patch(patches.Rectangle((p_W-p_ds-p_sw/2, p_db-p_sd), p_sw, p_sd, color='gray', alpha=0.5))
    at.plot(p_ds, p_db, 's', color='black', markersize=8, label='Driver Center')
    at.plot(p_W-p_ds, p_db, 's', color='black', markersize=8)
    at.plot([p_ds, p_W - p_ds, p_lpx, p_ds], [p_db, p_db, p_lpy, p_db], 'r--', alpha=0.6)
    at.plot(p_lpx, p_lpy, 'o', color='red', markersize=10, label='LP')
    
    at.plot([0, p_ds], [p_db, p_db], color='green', linestyle=':', lw=2)
    at.plot([p_ds, p_ds], [0, p_db], color='blue', linestyle=':', lw=2)
    
    # 에러 구문(f-string) 수정 파트
    at.annotate(f"{fmt_r % d_side_in}{disp_u_room}", xy=(p_ds/2, p_db), ha='center', va='bottom', color='green')
    at.annotate(f"{fmt_r % d_back_in}{disp_u_room}", xy=(p_ds, p_db/2), ha='left', va='center', color='blue')
    
    at.set_xlim(-pad, p_W + pad); at.set_ylim(-pad, p_L + pad)
    at.set_title(f"Top View ({disp_u_room} 기준)"); at.grid(True, linestyle=':', alpha=0.5); at.legend()
    
    # Side View
    aside.add_patch(patches.Rectangle((0, 0), p_L, p_H, fill=False, edgecolor='black', lw=3))
    aside.add_patch(patches.Rectangle((p_db-p_sd, p_dfl-p_sh/2), p_sd, p_sh, color='gray', alpha=0.5))
    aside.plot(p_db, p_dfl, 's', color='black', markersize=8)
    aside.plot(p_lpy, p_dfl, 'o', color='red', markersize=10)
    
    aside.plot([p_db, p_lpy], [p_dfl, p_dfl], 'r--', alpha=0.6)
    
    aside.plot([p_db, p_db], [0, p_dfl], color='orange', linestyle=':', lw=2)
    aside.plot([p_db, p_db], [p_dfl, p_H], color='purple', linestyle=':', lw=2)
    
    # 에러 구문(f-string) 수정 파트
    aside.annotate(f"{fmt_r % d_floor_in}{disp_u_room}", xy=(p_db, p_dfl/2), ha='left', va='center', color='orange')
    aside.annotate(f"{fmt_r % c_disp}{disp_u_room}", xy=(p_db, p_dfl + p_dcl/2), ha='left', va='center', color='purple')
    
    aside.set_xlim(-pad, p_L + pad); aside.set_ylim(-pad, p_H + pad)
    aside.set_title(f"Side View ({disp_u_room} 기준)"); aside.grid(True, linestyle=':', alpha=0.5)
    
    st.pyplot(fig_map)

# --- 최적화 스캐너 ---
st.divider()
st.subheader("🎯 최적 스피커 배치 스캐너 (물리적 한계 반영)")
st.markdown("현재 도면의 간섭 페널티가 크다면, 시스템이 계산한 아래의 최적 좌표로 변경해 보세요.")
if st.button("🚀 최적 배치 스캔 시작"):
    best_score, best_db, best_ds, best_sbirs = float('inf'), d_back, d_side, {}
    min_db, min_ds = spk_depth + 0.05, (spk_width / 2) + 0.05
    db_range = np.arange(min_db, min(L/2, 1.5), 0.05); ds_range = np.arange(min_ds, W/2 - 0.4, 0.05) 
    progress_bar = st.progress(0); total = len(db_range) * len(ds_range); count = 0
    for db in db_range:
        for ds in ds_range:
            ts = {"뒷벽": C/(4*db), "옆벽": C/(4*ds), "바닥": C/(4*d_floor), "천장": C/(4*d_ceil)}
            penalty = sum(50 for f in ts.values() for m in df_modes["주파수 (Hz)"] if abs(m-f) < 10)
            vs = list(ts.values()); penalty += sum(30 for i in range(4) for j in range(i+1, 4) if abs(vs[i]-vs[j]) < 10)
            penalty += sum(15 for f in ts.values() if f < 100)
            if penalty < best_score: best_score, best_db, best_ds, best_sbirs = penalty, db, ds, {k: round(v, 1) for k, v in ts.items()}
            count += 1; progress_bar.progress(count / total)
    progress_bar.empty()
    st.session_state.best_d_back, st.session_state.best_d_side, st.session_state.best_sbirs, st.session_state.scan_done = best_db, best_ds, best_sbirs, True

if st.session_state.scan_done:
    odb = st.session_state.best_d_back if is_m else round(st.session_state.best_d_back * 100, 0)
    ods = st.session_state.best_d_side if is_m else round(st.session_state.best_d_side * 100, 0)
    st.success(f"**추천 좌표 도출 완료!**")
    cr1, cr2 = st.columns(2)
    with cr1:
        st.metric(label=f"💡 추천 뒷벽 거리 ({disp_u_room})", value=f"{odb} {disp_u_room}")
        st.metric(label=f"💡 추천 옆벽 거리 ({disp_u_room})", value=f"{ods} {disp_u_room}")
        
        def update_layout():
            st.session_state.ui_d_back = odb
            st.session_state.ui_d_side = ods
            st.session_state.scan_done = False

        st.button("✨ 이 추천값으로 자동 입력 및 레이아웃 갱신", type="primary", on_click=update_layout)

    with cr2:
        st.write(f"- **예상 뒷벽 딥**: {st.session_state.best_sbirs['뒷벽']} Hz / **옆벽 딥**: {st.session_state.best_sbirs['옆벽']} Hz")

st.info("""
**비판적 팩트 체크**: 자동 입력 기능은 편리하지만, 이 수학적 최적점이 항상 귀로 듣기에 좋은 것은 아닙니다. 벽에 가까워질수록 위상 상쇄(Null)는 해결될지 모르나, **경계면 효과(Boundary Gain)**에 의해 저역 에너지가 기형적으로 증폭됩니다. 자동 입력 후 도면을 확인하셨다면, **반드시 실제 환경에서 측정 후 부풀어 오른 저음역대를 깎아내는 DSP EQ(쉘빙 필터) 작업이 수반되어야 함**을 명심하십시오.
""")

# --- 흡음 솔루션 및 중첩 경고 ---
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