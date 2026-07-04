import streamlit as st
import google.generativeai as genai
from PIL import Image

# ネット上の秘密の金庫からAPIキーを読み込む設定（安全！）
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("APIキーが設定されていません。StreamlitのAdvanced settingsで設定してください。")

model = genai.GenerativeModel('gemini-1.5-flash') # 最新の安定モデルにしておくね

st.title("📸 俺専用・カロリーPFC判定")
st.write("食事の写真をアップロードするか、スマホのカメラで撮ね。")

uploaded_file = st.file_uploader("画像を選択...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption='選択された画像', use_container_width=True)
    
    if st.button("AIで解析スタート"):
        prompt = """
        この食事画像に写っている料理を分析し、おおよその総カロリーとPFCバランス（タンパク質、脂質、炭水化物）を推定してください。
        結果は、必ず以下のJSON形式のみで出力してください。余計な解説テキストは含めないでください。

        {
          "food_name": "分析された料理名",
          "estimated_calories_kcal": 0,
          "protein_g": 0,
          "fat_g": 0,
          "carbohydrates_g": 0,
          "reason": "そのカロリー・PFCだと推定した簡単な理由や内訳"
        }
        """
        with st.spinner("AIが計算中..."):
            try:
                response = model.generate_content([prompt, image])
                st.success("分析完了！")
                st.text(response.text)
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")