import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import matplotlib.pyplot as plt

# ネット上の秘密の金庫からAPIキーを読み込む設定
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("APIキーが設定されていません。StreamlitのAdvanced settingsで設定してください。")

# モデルは2.5-flash
model = genai.GenerativeModel('gemini-2.5-flash')

# 💾 飯ログ用：データを記憶しておく設定
if "total_cal" not in st.session_state:
    st.session_state.total_cal = 0
    st.session_state.total_p = 0
    st.session_state.total_f = 0
    st.session_state.total_c = 0
    st.session_state.history = []

# 📅 サイドバー設定（目標入力）
st.sidebar.header("🎯 俺の目標設定")
cal_target = st.sidebar.number_input("🔥 目標カロリー (kcal)", value=2500, step=50)
p_target = st.sidebar.number_input("💪 目標タンパク質 (g)", value=146, step=5)
f_target = st.sidebar.number_input("🥑 目標脂質 (g)", value=60, step=5)
c_target = st.sidebar.number_input("🌾 目標炭水化物 (g)", value=340, step=10)

# 復活させた目標入力欄！
run_goal = st.sidebar.text_input("🏃‍♂️ ランニング目標", value="現状維持・体力向上")
body_goal = st.sidebar.text_input("💪 体づくりの目標", value="フィジーク系ボディメイク（消費カロリー維持・タンパク質146g死守）")

st.sidebar.write("---")
st.sidebar.header("📅 今日の摂取状況と残り")

# 各種メーターと「あと何g/kcal」の計算
cal_current = st.session_state.total_cal
cal_left = max(cal_target - cal_current, 0)
cal_progress = min(cal_current / cal_target, 1.0) if cal_target > 0 else 0.0
st.sidebar.metric(label="🔥 カロリー", value=f"{cal_current} / {cal_target} kcal", delta=f"あと {cal_left} kcal", delta_color="inverse")
st.sidebar.progress(cal_progress)

p_current = st.session_state.total_p
p_left = max(p_target - p_current, 0.0)
p_progress = min(p_current / p_target, 1.0) if p_target > 0 else 0.0
st.sidebar.metric(label="💪 タンパク質(P)", value=f"{p_current:.1f} / {p_target:.1f} g", delta=f"あと {p_left:.1f} g", delta_color="inverse")
st.sidebar.progress(p_progress)

f_current = st.session_state.total_f
f_left = max(f_target - f_current, 0.0)
f_progress = min(f_current / f_target, 1.0) if f_target > 0 else 0.0
st.sidebar.metric(label="🥑 脂質(F)", value=f"{f_current:.1f} / {f_target:.1f} g", delta=f"あと {f_left:.1f} g", delta_color="inverse")
st.sidebar.progress(f_progress)

c_current = st.session_state.total_c
c_left = max(c_target - c_current, 0.0)
c_progress = min(c_current / c_target, 1.0) if c_target > 0 else 0.0
st.sidebar.metric(label="🌾 炭水化物(C)", value=f"{c_current:.1f} / {c_target:.1f} g", delta=f"あと {c_left:.1f} g", delta_color="inverse")
st.sidebar.progress(c_progress)

if st.sidebar.button("今日のデータをリセット"):
    st.session_state.total_cal = 0
    st.session_state.total_p = 0
    st.session_state.total_f = 0
    st.session_state.total_c = 0
    st.session_state.history = []
    st.rerun()

if st.session_state.history:
    st.sidebar.write("---")
    st.sidebar.write("📋 今日食べたもの:")
    for meal in st.session_state.history:
        st.sidebar.write(f"・{meal}")


st.title("📸 俺専用・最強ボディメイクAI (究極完全体)")

# プロっぽいタブ切り替えUIを搭載
tab1, tab2 = st.tabs(["📸 画像から解析", "✍️ 文字入力で追加"])

# 共通のプロンプトの土台
base_instruction = f"""
提供された情報から、カロリー、PFCバランス、各具材ごとのカロリー内訳を分析し、必ず以下のJSONフォーマットのみで返答してください。余計な解説テキストは含めず、純粋なJSONデータだけを出力してください。

【ユーザーのボディメイク方針】
・目的: フィジーク選手のような、引き締まった筋肉質な体作り
・カロリー方針: 1日の総摂取カロリーターゲットは {cal_target} kcal です。消費カロリー付近を維持するクリーンゲインズを狙います。
・タンパク質目標: 1日あたり {p_target}g を確実に摂取する。
・その他の目標設定: {run_goal} / {body_goal}

breakdownの中の「base_rate」には、その具材のカロリー計算の基準となった数値（例:「168kcal/100g」や「90kcal/1個」など）を記載してください。

{{
  "food_name": "料理名または入力された食事",
  "estimated_calories_kcal": 合計カロリー(数値),
  "protein_g": タンパク質(数値),
  "fat_g": 脂質(数値),
  "carbohydrates_g": 炭水化物(数値),
  "breakdown": [
    {{
      "item": "具材や食品名1", 
      "calories": "〇〇kcal",
      "base_rate": "〇〇kcal / 100g あたり(または1個あたり)"
    }}
  ],
  "reason": "計算の根拠と、フィジーク系ボディメイク方針に合わせた具体的なアドバイス"
}}
"""

parsed_data = None

# --- タブ1: 画像解析 ---
with tab1:
    st.write("食事の写真をアップロードするか、スマホのカメラで撮ってね。")
    uploaded_file = st.file_uploader("画像を選択...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption='選択された画像', use_container_width=True)

        if st.button("AI画像解析スタート"):
            with st.spinner("AI画像解析中..."):
                try:
                    prompt = "画像の料理を解析してください。\n" + base_instruction
                    response = model.generate_content([prompt, image])
                    raw_text = response.text.strip()
                    if raw_text.startswith("
