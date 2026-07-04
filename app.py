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

# モデルは一真くんが見つけた大正解の2.5-flash！
model = genai.GenerativeModel('gemini-2.5-flash')

# 💾 飯ログ用：データを記憶しておく設定
if "total_cal" not in st.session_state:
    st.session_state.total_cal = 0
    st.session_state.total_p = 0
    st.session_state.total_f = 0
    st.session_state.total_c = 0
    st.session_state.history = []

# 📅 サイドバーに今日の合計を表示
st.sidebar.header("📅 今日の合計栄養素")
st.sidebar.metric(label="🔥 総摂取カロリー", value=f"{st.session_state.total_cal} kcal")
st.sidebar.write(f"💪 タンパク質(P): {st.session_state.total_p:.1f} g")
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


st.title("📸 俺専用・カロリーPFC判定 (基準値つき最強版)")
st.write("食事の写真をアップロードするか、スマホのカメラで撮ってね。")

uploaded_file = st.file_uploader("画像を選択...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='選択された画像', use_container_width=True)

    if st.button("AIで解析スタート"):
        # 💡 【アップデート】「base_rate」という基準値の項目をプロンプトに追加したよ！
        prompt = """
        提供された料理の画像から、カロリー、PFCバランス、各具材ごとのカロリー内訳を分析し、必ず以下のJSONフォーマットのみで返答してください。余計な解説テキストは含めず、純粋なJSONデータだけを出力してください。

        なお、ユーザーは現在「10kmを45分切りするための長距離ランニングのトレーニング」と「引き締まった体作り（筋肉維持と脂肪燃焼）」を両立しています。この目標を踏まえて、この食事がトレーニングのエネルギー補給や筋肉のリカバリーにどう影響するか、具体的なアドバイスや改善提案を必ず「reason」の後半に含めてください。

        breakdownの中の「base_rate」には、その具材のカロリー計算の基準となった数値（例:「168kcal/100g」や「90kcal/1個」など）を記載してください。

        {
          "food_name": "料理名",
          "estimated_calories_kcal": 合計カロリー(数値),
          "protein_g": タンパク質(数値),
          "fat_g": 脂質(数値),
          "carbohydrates_g": 炭水化物(数値),
          "breakdown": [
            {
              "item": "具材や調味料1", 
              "calories": "〇〇kcal",
              "base_rate": "〇〇kcal / 100g あたり(または1個あたり)"
            }
          ],
          "reason": "計算の根拠と、長距離ランナー・体作り視点での具体的なアドバイス"
        }
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
                
                # 🥗 【アップデート】具材ごとのカロリー内訳＋基準値を表示！
                st.write("### 🥗 具材ごとのカロリー内訳")
                breakdown_list = data.get("breakdown", [])
                if breakdown_list:
                    for b in breakdown_list:
                        item_name = b.get('item', '不明')
                        cals = b.get('calories', '0kcal')
                        rate = b.get('base_rate', '基準データなし')
                        # 画面に「具材名: 〇〇kcal (基準: 〇〇kcal/100g)」の形で出すよ
                        st.write(f"・**{item_name}**: {cals}  *(基準: {rate})*")
                
                # 📝 アドバイス
                st.write("### 🏃‍♂️ アスリート向けアドバイス・根拠")
                st.write(data.get("reason", "なし"))
                
                # 💾 データを今日の合計に自動加算
                st.session_state.total_cal += data.get('estimated_calories_kcal', 0)
                st.session_state.total_p += data.get('protein_g', 0)
                st.session_state.total_f += data.get('fat_g', 0)
                st.session_state.total_c += data.get('carbohydrates_g', 0)
                st.session_state.history.append(data.get('food_name', '不明な料理'))
                
                st.success("今日の合計データに追加したよ！")
                
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
