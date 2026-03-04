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

# --- Session State 초기화 (자동 입력 기능을 위함) ---
if "ui_d_back" not in st.session_state: 
    st.session_state.ui_d_back = 0.8
if "ui_d_side" not in st.session_state: 
    st.session_state.ui_d_side = 0.8
if "scan_done" not in st.session_state:
    st.session_state.scan_done = False

st.title("🏠 홈 스튜디오를 위한 Room Mode & SBIR 분석기")
st.markdown("""
방의 물리적 규격과 스피커 배치 데이터를 기반으로 **저역대 에너지 불균형**을 분석합니다.  
⚠️ **필수 주의사항**: 본 도구의 모든 계산은 이상적인 직육면체를 가정한 시뮬레이션입니다. 방의 비대칭 구조, 창문, 가구 등의 변수를 모두 대변할 수 없으므로, **반드시 측정용 마이크와 REW(Room EQ Wizard)를 활용한 실측 배치가 동반되어야 합니다.**
""")

# --- 사이드바: 단위 및 데이터 입력 ---
st.sidebar.header("⚙️ 측정 단위 설정")
unit_room = st.sidebar.radio("방 및 스피커 거리 단위", ["m (미터)", "cm (센티미터)"], horizontal=True)
unit_spk = st.sidebar.radio("스피커 인클로저 단위", ["mm (밀리미터)", "inch (인치)"], horizontal=True)

is_m = (unit_room == "m (미터)")
is_mm = (unit_spk == "mm (밀리미터)")
disp_u_room = "m" if is_m else "cm"
disp_u_spk = "mm" if is_mm else "inch"

st.sidebar.divider()
st.sidebar.header(f"📏 방 규격 데이터 ({disp_u_room})")
step_r = 0.01 if is_m else 1.0
fmt_r = "%.2f" if is_m else "%.0f"

L_in = st.sidebar.number_input(f"방 길이 (L)", value=5.0 if is_m else 500.0, step=step_r, format=fmt_r)
W_in = st.sidebar.number_input(f"방 너비 (W)", value=4.0 if is_m else 400.0, step=step_r, format=fmt_r)
H_in = st.sidebar.number_input(f"방 높이 (H)", value=2.5 if is_m else 250.0, step=step_r, format=fmt_r)

L, W, H = (L_in, W_in, H_in) if is_m else (L_in/100, W_in/100, H_in/100)

st.sidebar.divider()
st.sidebar.header(f"🎛️ 스피커 물리적 규격 ({disp_u_spk})")
step_s = 1.0 if is_mm else 0.1
fmt_s = "%.0f" if is_mm else "%.1f"

spk_w_in = st.sidebar.number_input(f"스피커 너비", value=200.0 if is_mm else 8.0, step=step_s, format=fmt_s)
spk_d_in = st.sidebar.number_input(f"스피커 깊이", value=300.0 if is_mm else 12.0, step=step_s, format=fmt_s)
spk_h_in = st.sidebar.number_input(f"스피커 높이", value=350.0 if is_mm else 14.0, step=step_s, format=fmt_s)

spk_width = spk_w_in/1000 if is_mm else spk_w_in*0.0254
spk_depth = spk_d_in/1000 if is_mm else spk_d_in*0.0254
spk_height = spk_h_in/1000 if is_mm else spk_h_in*0.0254

st.sidebar.divider()
st.sidebar.header(f"🔊 스피커 드라이버 중심 거리 ({disp_u_room})")
d_back_in = st.sidebar.number_input(f"뒷벽과의 거리", step=step_r, format=fmt_r, key="ui_d_back")
d_side_in = st.sidebar.number_input(f"옆벽과의 거리", step=step_r, format=fmt_r, key="ui_d_side")
d_floor_in = st.sidebar.number_input(f"바닥과의 거리", value=1.0 if is_m else 100.0, step=step_r, format=fmt_r)
d_ceil_in = st.sidebar.number_input(f"천장과의 거리", value=1.5 if is_m else 150.0, step=step_r, format=fmt_r)

d_back, d_side, d_floor, d_ceil = (d_back_in, d_side_in, d_floor_in, d_ceil_in) if is_m else (d_back_in/100, d_side_in/100, d_floor_in/100, d_ceil_in/100)

if d_back < spk_depth:
    st.sidebar.error(f"⚠️ 물리적 오류: 뒷벽 거리가 스피커 깊이보다 짧습니다.")
if d_side < (spk_width / 2):
    st.sidebar.error(f"⚠️ 물리적 오류: 옆벽 거리가 스피커 너비 절반보다 짧습니다.")

# --- 제작자 크레딧 및 인스타그램 링크 (수정된 부분) ---
st.sidebar.divider()
st.sidebar.markdown("👨‍💻 Made by **Chandler.J 정찬영**")
st.sidebar.markdown("[📸 Instagram](https://www.instagram.com/chanyoung_3863/)")

# --- 연산 로직 ---
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

sbir_table = []
warnings_mode = []
for wall, f_sbir in sbir_data.items():
    overlap_sbir = any(wall != ow and abs(f_sbir - of) < 10 for ow, of in sbir_data.items())
    for f_mode in df_modes["주파수 (Hz)"]:
        if abs(f_mode - f_sbir) < 10:
            warnings_mode.append(f"- **{wall} SBIR({f_sbir}Hz)**과 **룸모드({f_mode}Hz)** 중첩. (위상 왜곡 극심)")
    status = "🔴 위험 (SBIR간 중첩)" if overlap_sbir else "🟢 양호"
    sbir_table.append({"반사면": wall, "딥 주파수 (Hz)": f_sbir, "상태": status})
df_sbir = pd.DataFrame(sbir_table)

# --- 시각화 및 도면 ---
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
        ax.axvline(x=freq, color='red', linestyle='--', alpha=0.4, linewidth=2)
    colors = {'뒷벽': 'blue', '옆벽': 'green', '바닥': 'orange', '천장': 'purple'}
    for wall, freq in sbir_data.items():
        ax.axvline(x=freq, color=colors[wall], linewidth=3, label=f'SBIR ({wall})')
    ax.set_xscale('log')
    ax.set_xlim(20, 350)
    ax.set_xticks([20, 30, 40, 50, 60, 80, 100, 150, 200, 300])
    ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
    ax.set_yticks([]) 
    ax.grid(True, which='both', axis='x', linestyle=':', alpha=0.4) 
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1)) 
    st.pyplot(fig)

# --- 스피커 배치 최적화 스캐너 ---
st.divider()
st.subheader("🎯 최적 스피커 배치 스캐너 (물리적 한계 반영)")
if st.button("🚀 최적 배치 스캔 시작"):
    best_score, best_db, best_ds, best_sbirs = float('inf'), d_back, d_side, {}
    min_db, min_ds = spk_depth + 0.05, (spk_width / 2) + 0.05
    db_range = np.arange(min_db, min(L/2, 1.5), 0.05)
    ds_range = np.arange(min_ds, W/2 - 0.4, 0.05) 
    progress_bar = st.progress(0)
    total = len(db_range) * len(ds_range)
    count = 0
    for db in db_range:
        for ds in ds_range:
            ts = {"뒷벽": C/(4*db), "옆벽": C/(4*ds), "바닥": C/(4*d_floor), "천장": C/(4*d_ceil)}
            p = sum(50 for f in ts.values() for m in df_modes["주파수 (Hz)"] if abs(m-f) < 10)
            vs = list(ts.values())
            p += sum(30 for i in range(4) for j in range(i+1, 4) if abs(vs[i]-vs[j]) < 10)
            p += sum(15 for f in ts.values() if f < 100)
            if p < best_score:
                best_score, best_db, best_ds = p, db, ds
                best_sbirs = {k: round(v, 1) for k, v in ts.items()}
            count += 1
            progress_bar.progress(count / total)
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
        if st.button("✨ 이 추천값으로 자동 입력 및 레이아웃 갱신", type="primary"):
            st.session_state.ui_d_back, st.session_state.ui_d_side, st.session_state.scan_done = odb, ods, False
            st.rerun()
    with cr2:
        st.write(f"- **예상 뒷벽 딥**: {st.session_state.best_sbirs['뒷벽']} Hz / **옆벽 딥**: {st.session_state.best_sbirs['옆벽']} Hz")

st.info("**비판적 팩트 체크**: 자동 입력 기능은 편리하지만, 이 최적점은 위상 상쇄를 피하기 위한 수학적 결과일 뿐입니다. 벽에 가까워질수록 발생하는 **경계면 효과(Boundary Gain)**는 반드시 측정 후 DSP EQ로 보정해야 합니다.")

# --- 도면 렌더링 ---
st.divider()
st.subheader("📐 룸 레이아웃 및 리스닝 스팟 도면")
dw = W - (2 * d_side)
if dw <= 0: st.error("⚠️ 에러: 스피커 간격 오류.")
else:
    th = dw * (np.sqrt(3) / 2)
    lp_y, lp_x = d_back + th, W / 2 
    if lp_y > L: st.warning("⚠️ 물리적 한계: 리스닝 스팟이 방을 벗어납니다.")
    fig_map, (at, aside) = plt.subplots(1, 2, figsize=(14, 6))
    at.add_patch(patches.Rectangle((0, 0), W, L, fill=False, edgecolor='black', lw=3))
    at.add_patch(patches.Rectangle((d_side-spk_width/2, d_back-spk_depth), spk_width, spk_depth, color='gray', alpha=0.5))
    at.add_patch(patches.Rectangle((W-d_side-spk_width/2, d_back-spk_depth), spk_width, spk_depth, color='gray', alpha=0.5))
    at.plot([d_side, W-d_side, lp_x, d_side], [d_back, d_back, lp_y, d_back], 'r--', alpha=0.6)
    at.plot(lp_x, lp_y, 'o', color='red', markersize=10)
    at.set_title("Top View")
    aside.add_patch(patches.Rectangle((0, 0), L, H, fill=False, edgecolor='black', lw=3))
    aside.add_patch(patches.Rectangle((d_back-spk_depth, d_floor-spk_height/2), spk_depth, spk_height, color='gray', alpha=0.5))
    aside.plot(lp_y, d_floor, 'o', color='red', markersize=10)
    aside.set_title("Side View")
    st.pyplot(fig_map)

# --- 분석 노트 ---
st.divider()
st.info("💡 **엔지니어를 위한 데이터 분석 노트**")
st.markdown("""
1. **실측 필수**: 시뮬레이션은 출발점일 뿐입니다. 반드시 **측정용 마이크와 REW**를 통한 실측이 동반되어야 합니다.
2. **흡음재 타겟팅**: SBIR 제어를 위한 흡음재는 우퍼 중심에서 벽면으로의 **최단 거리 지점(수직선)**을 1차적으로 덮어야 합니다.
3. **룸모드 vs SBIR**: 룸모드는 멀티 서브우퍼와 DSP(Dirac ART 등)로 시간 영역까지 제어 가능하지만, SBIR 딥은 물리적 빈공간이므로 배치를 바꾸거나 흡음하는 것이 유일한 해결책입니다.
""")