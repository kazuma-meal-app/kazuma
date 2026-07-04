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

# 📅 サイドバー設定
st.sidebar.header("🎯 俺の目標設定")
# カロリーの目標値を画面上で自由に変えられるボックス（初期値2500）
cal_target = st.sidebar.number_input("🔥 目標摂取カロリー (kcal)", value=2500, step=50)
run_goal = st.sidebar.text_input("🏃‍♂️ ランニング目標", value="現状維持・体力向上")
body_goal = st.sidebar.text_input("💪 体づくりの目標", value="フィジーク系ボディメイク（消費カロリー維持・タンパク質146g死守）")

st.sidebar.write("---")
st.sidebar.header("📅 今日の合計栄養素")

# 📊 カロリーメーターの計算
cal_current = st.session_state.total_cal
cal_progress = min(cal_current / cal_target, 1.0) if cal_target > 0 else 0.0

st.sidebar.metric(label="🔥 カロリー", value=f"{cal_current} / {cal_target} kcal")
st.sidebar.progress(cal_progress)
st.sidebar.write(f" 📈 カロリー目標 達成度: {cal_progress*100:.1f}%")

# 📊 タンパク質146gメーターの計算
p_target = 146.0
p_current = st.session_state.total_p
p_progress = min(p_current / p_target, 1.0)

st.sidebar.metric(label="💪 タンパク質", value=f"{p_current:.1f} / {p_target:.1f} g")
st.sidebar.progress(p_progress)
st.sidebar.write(f" 📈 タンパク質目標 達成度: {p_progress*100:.1f}%")

st.sidebar.write(f"🥑 脂質(F): {st.session_state.total_f:.1f} g")
st.sidebar.write(f"🌾 炭水化物(C): {st.session_state.total_c:.1f} g")

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


st.title("📸 俺専用・カロリーPFC判定 (Wメーター最強版)")
st.write("食事の写真をアップロードするか、スマホのカメラで撮ってね。")

uploaded_file = st.file_uploader("画像を選択...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='選択された画像', use_container_width=True)

    if st.button("AIで解析スタート"):
        # AIにも一真くんが設定した今日の目標カロリーを共有して、より精密にアドバイスさせるよ！
        prompt = f"""
        提供された料理の画像から、カロリー、PFCバランス、各具材ごとのカロリー内訳を分析し、必ず以下のJSONフォーマットのみで返答してください。余計な解説テキストは含めず、純粋なJSONデータだけを出力してください。

        なお、ユーザーは現在、以下の明確なボディメイク方針を持っています。この方針を踏まえて、この食事がターゲットにどう貢献するか、具体的なアドバイスや改善提案を必ず「reason」の後半に含めてください。

        【ユーザーのボディメイク方針】
        ・目的: フィジーク選手のような、引き締まった筋肉質な体作り
        ・カロリー方針: 1日の総摂取カロリーのターゲットは【 {cal_target} kcal 】です。増量期のように太るわけでも、減量期のように削るわけでもなく、この消費カロリー付近を維持することを目指しています。
        ・タンパク質目標: 1日あたり 146g （体重73kg × 2倍）を確実に摂取する。
        ・その他の設定: {run_goal} / {body_goal}

        breakdownの中の「base_rate」には、その具材のカロリー計算の基準となった数値（例:「168kcal/100g」や「90kcal/1個」など）を記載してください。

        {{
          "food_name": "料理名",
          "estimated_calories_kcal": 合計カロリー(数値),
          "protein_g": タンパク質(数値),
          "fat_g": 脂質(数値),
          "carbohydrates_g": 炭水化物(数値),
          "breakdown": [
            {{
              "item": "具材や調味料1", 
              "calories": "〇〇kcal",
              "base_rate": "〇〇kcal / 100g あたり(または1個あたり)"
            }}
          ],
          "reason": "計算の根拠と、フィジーク系ボディメイク方針（目標カロリー・タンパク質目標）に合わせた具体的なアドバイス"
        }}
        """

        with st.spinner("AIが計算中..."):
            try:
                response = model.generate_content([prompt, image])
                
                raw_text = response.text.strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                raw_text = raw_text.strip()
                
                data = json.loads(raw_text)
                
                # 📊 画面表示
                st.header(f"🍳 {data.get('food_name', '分析された料理')}")
                st.metric(label="🔥 推定総カロリー", value=f"{data.get('estimated_calories_kcal', 0)} kcal")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(label="💪 タンパク質", value=f"{data.get('protein_g', 0)} g")
                with col2:
                    st.metric(label="🥑 脂質", value=f"{data.get('fat_g', 0)} g")
                with col3:
                    st.metric(label="🌾 炭水化物", value=f"{data.get('carbohydrates_g', 0)} g")
                
                # 📊 PFC割合の円グラフ
                p = data.get('protein_g', 0)
                f = data.get('fat_g', 0)
                c = data.get('carbohydrates_g', 0)
                
                if p + f + c > 0:
                    st.write("### 📈 PFC割合（バランス）")
                    labels = ['Protein (P)', 'Fat (F)', 'Carbs (C)']
                    sizes = [p, f, c]
                    colors = ['#ff9999','#66b3ff','#99ff99']
                    
                    fig, ax = plt.subplots(figsize=(5, 5))
                    fig.patch.set_alpha(0.0)
                    ax.patch.set_alpha(0.0)
                    
                    wedges, texts, autotexts = ax.pie(
                        sizes, labels=labels, colors=colors, 
                        autopct='%1.1f%%', startangle=90,
                        textprops=dict(color="white")
                    )
                    ax.axis('equal')
                    st.pyplot(fig)
                
                # 🥗 具材ごとのカロリー内訳＋基準値を表示
                st.write("### 🥗 具材ごとのカロリー内訳")
                breakdown_list = data.get("breakdown", [])
                if breakdown_list:
                    for b in breakdown_list:
                        item_name = b.get('item', '不明')
                        cals = b.get('calories', '0kcal')
                        rate = b.get('base_rate', '基準データなし')
                        st.write(f"・**{item_name}**: {cals}  *(基準: {rate})*")
                
                # 📝 アドバイス
                st.write("### 🏃‍♂️ 俺専用コーチのアドバイス・根拠")
                st.write(data.get("reason", "なし"))
                
                # 💾 データを今日の合計に自動加算
                st.session_state.total_cal += data.get('estimated_calories_kcal', 0)
                st.session_state.total_p += data.get('protein_g', 0)
                st.session_state.total_f += data.get('fat_g', 0)
                st.session_state.total_c += data.get('carbohydrates_g', 0)
                st.session_state.history.append(data.get('food_name', '不明な料理'))
                
                st.success("今日の合計データに追加したよ！")
                st.sidebar.button("画面を更新してメーターに反映", key="refresh_btn")
                
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
