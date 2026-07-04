import streamlit as st
import google.generativeai as genai
from PIL import Image
import json

# ネット上の秘密の金庫からAPIキーを読み込む設定（安全！）
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("APIキーが設定されていません。StreamlitのAdvanced settingsで設定してください。")

# 🛠️ 一真くんが成功させた「gemini-2.5-flash」をそのまま使うよ！
model = genai.GenerativeModel('gemini-2.5-flash')

st.title("📸 俺専用・カロリーPFC判定")
st.write("食事の写真をアップロードするか、スマホのカメラで撮ってね。")

uploaded_file = st.file_uploader("画像を選択...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='選択された画像', use_container_width=True)

    if st.button("AIで解析スタート"):
        # 🥗 内訳（breakdown）を出してもらうためのプロンプト
        prompt = """
        提供された料理の画像から、カロリー、PFCバランス、 shadow 各具材ごとのカロリー内訳を分析し、必ず以下のJSONフォーマットのみで返答してください。余計な解説テキストは含めず、純粋なJSONデータだけを出力してください。

        {
          "food_name": "料理名",
          "estimated_calories_kcal": 合計カロリー(数値),
          "protein_g": タンパク質(数値),
          "fat_g": 脂質(数値),
          "carbohydrates_g": 炭水化物(数値),
          "breakdown": [
            {"item": "具材や調味料1", "calories": "〇〇kcal"},
            {"item": "具材や調味料2", "calories": "〇〇kcal"}
          ],
          "reason": "計算の根拠やアドバイス"
        }
        """

        with st.spinner("AIが計算中..."):
            try:
                response = model.generate_content([prompt, image])
                st.success("分析完了！")
                
                # 🛠️ AIが「```json」という文字を付けて返してきたときのための自動カット処理
                raw_text = response.text.strip()
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                raw_text = raw_text.strip()
                
                # 🧠 文字列をアプリで使えるデータ（JSON）に変換
                data = json.loads(raw_text)
                
                # 📊 画面に数字やメーターを綺麗に表示
                st.header(f"🍳 {data.get('food_name', '分析された料理')}")
                st.metric(label="🔥 推定総カロリー", value=f"{data.get('estimated_calories_kcal', 0)} kcal")
                
                # PFCバランスを3列に分けてカッコよく並べる！
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(label="💪 タンパク質", value=f"{data.get('protein_g', 0)} g")
                with col2:
                    st.metric(label="🥑 脂質", value=f"{data.get('fat_g', 0)} g")
                with col3:
                    st.metric(label="🌾 炭水化物", value=f"{data.get('carbohydrates_g', 0)} g")
                
                # 🥗 待望の「具材ごとのカロリー内訳」を表示！
                st.write("### 🥗 具材ごとのカロリー内訳")
                breakdown_list = data.get("breakdown", [])
                if breakdown_list:
                    for b in breakdown_list:
                        st.write(f"・**{b['item']}**: {b['calories']}")
                else:
                    st.write("内訳データが取得できませんでした。")
                
                # 📝 計算根拠やアドバイス
                st.write("### 📝 AIからのアドバイス・計算根拠")
                st.write(data.get("reason", "なし"))
                
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
