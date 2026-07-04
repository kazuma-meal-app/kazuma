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

# 目標入力欄
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

# タブ切り替えUI
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
                    
                    # エラー原因だった1行書きを、きれいに複数行に分けて安全化！
                    if raw_text.startswith("```json"):
                        raw_text = raw_text[7:]
                    if raw_text.endswith("```"):
                        raw_text = raw_text[:-3]
                    
                    parsed_data = json.loads(raw_text.strip())
                except Exception as e:
                    st.error(f"画像解析エラー: {e}")

# --- タブ2: 文字入力 ---
with tab2:
    st.write("写真がない時や、プロテイン・サプリ・外食メニューを文字でパッと足したい時はここ！")
    text_input = st.text_area("食べたものやメニューを入力（例:「マイプロテイン1スクープ」「セブンのサラダチキン1個と塩おにぎり1個」）", placeholder="ここに細かく書くほど正確に計算されるよ！")

    if st.button("AI文章解析スタート"):
        if text_input.strip() == "":
            st.warning("何か文字を入力してね！")
        else:
            with st.spinner("AI文章解析中..."):
                try:
                    prompt = f"以下のテキストで入力された食事内容を解析してください。\n入力内容: {text_input}\n" + base_instruction
                    response = model.generate_content(prompt)
                    raw_text = response.text.strip()
                    
                    # ここもきれいに複数行に分けて安全化！
                    if raw_text.startswith("```json"):
                        raw_text = raw_text[7:]
                    if raw_text.endswith("```"):
                        raw_text = raw_text[:-3]
                    
                    parsed_data = json.loads(raw_text.strip())
                except Exception as e:
                    st.error(f"文章解析エラー: {e}")

# 📊 両方のタブ共通の表示処理
if parsed_data is not None:
    st.header(f"🍳 {parsed_data.get('food_name', '分析された食事')}")
    st.metric(label="🔥 推定総カロリー", value=f"{parsed_data.get('estimated_calories_kcal', 0)} kcal")
    
    col1, col2, col3 = st.columns(3)
    with col1: st.metric(label="💪 タンパク質", value=f"{parsed_data.get('protein_g', 0)} g")
    with col2: st.metric(label="🥑 脂質", value=f"{parsed_data.get('fat_g', 0)} g")
    with col3: st.metric(label="🌾 炭水化物", value=f"{parsed_data.get('carbohydrates_g', 0)} g")
    
    # 円グラフ表示
    p = parsed_data.get('protein_g', 0)
    f = parsed_data.get('fat_g', 0)
    c = parsed_data.get('carbohydrates_g', 0)
    if p + f + c > 0:
        st.write("### 📈 PFC割合（バランス）")
        labels = ['Protein (P)', 'Fat (F)', 'Carbs (C)']
        sizes = [p, f, c]
        colors = ['#ff9999','#66b3ff','#99ff99']
        fig, ax = plt.subplots(figsize=(5, 5))
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)
        ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, textprops=dict(color="white"))
        ax.axis('equal')
        st.pyplot(fig)
    
    # 内訳表示
    st.write("### 🥗 内訳と基準値")
    breakdown_list = parsed_data.get("breakdown", [])
    if breakdown_list:
        for b in breakdown_list:
            st.write(f"・**{b.get('item', '不明')}**: {b.get('calories', '0kcal')}  *(基準: {b.get('base_rate', 'なし')})*")
    
    st.write("### 🏃‍♂️ 俺専用コーチのアドバイス")
    st.write(parsed_data.get("reason", "なし"))
    
    # 💾 データを加算
    st.session_state.total_cal += parsed_data.get('estimated_calories_kcal', 0)
    st.session_state.total_p += parsed_data.get('protein_g', 0)
    st.session_state.total_f += parsed_data.get('fat_g', 0)
    st.session_state.total_c += parsed_data.get('carbohydrates_g', 0)
    st.session_state.history.append(parsed_data.get('food_name', '不明な料理'))
    
    st.success("今日の合計データに追加したよ！")
    
    # 自動リロードでメーターを即時更新！
    st.rerun()
