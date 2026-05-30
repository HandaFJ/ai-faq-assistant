import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Dynamic AI FAQ Assistant", layout="wide")

st.title("AI問い合わせアシスタント")
st.caption("最新モデル自動取得・保守フリー設計")

# ==========================================
# 🔐 サイドバー：APIキーの入力と安全性の説明
# ==========================================
st.sidebar.title("🔐 セキュリティと設定")

user_api_key = st.sidebar.text_input(
    "あなたの Gemini API Key を入力してください", 
    type="password",
    help="Google AI Studioで取得した無料のAPIキーをご利用いただけます。"
)

st.sidebar.info(
    "安全への取り組み\n\n"
    "入力されたAPIキーは、このブラウザのメモリ内でのみ一時的に使用され、"
    "サーバーやデータベースには一切保存されません。"
)

# APIキーのチェック
if not user_api_key:
    st.warning("アプリを利用するには、サイドバーにGeminiのAPIキーを入力してください。")
    st.stop()

# ==========================================
# 🔄 技2：Google APIからモデルリストを動的取得
# ==========================================
genai.configure(api_key=user_api_key)

@st.cache_data(show_spinner="最新のAIモデルリストを取得中...")
def get_available_gemini_models():
    """GoogleのAPIから現在利用可能なモデルを動的に取得する関数"""
    try:
        # 利用可能なモデル一覧を取得
        model_list = genai.list_models()
        
        valid_models = []
        for m in model_list:
            if "generateContent" in m.supported_generation_methods:
                clean_name = m.name.replace("models/", "")
                # プレビュー版やテキスト埋め込み用を除外（実用モデルのみに絞り込み）
                if "flash" in clean_name or "pro" in clean_name:
                    if "text-" not in clean_name and "embedding" not in clean_name:
                        valid_models.append(clean_name)
        
        # 新しいモデルが下（末尾）に来ることが多いため、リストを反転して最新順にする
        valid_models.reverse()
        return valid_models
    except Exception as e:
        # 万が一APIエラーが起きた場合のフォールバック（予備）リスト
        return ["gemini-2.0-flash", "gemini-2.0-pro", "gemini-1.5-flash"]

# 動的にモデルリストを取得
available_models = get_available_gemini_models()

# ==========================================
# サイドバー：動的パラメーター設定
# ==========================================
st.sidebar.markdown("---")
st.sidebar.title("LLM Tuning Panel")

# 【自動取得されたリスト】からユーザーにモデルを選ばせる
selected_model_name = st.sidebar.selectbox(
    "使用するLLMモデル（Googleから自動取得中）",
    options=available_models,
    help="Googleのサーバーから現在利用可能な最新モデルをリアルタイムに取得しています。将来新モデルが出た際も自動でここに追加されます。"
)

# ペルソナ（システムプロンプト）の動的切り替え
persona_option = st.sidebar.selectbox(
    "AIアシスタントのキャラクター設定",
    [
        "親切な社内ヘルプデスク（マニュアル丁寧解説）",
        "プロのカスタマーサポート（丁寧・敬語徹底）",
        "辛口ITコンサルタント（問題点と改善策のハッキリ提示）"
    ]
)

SYSTEM_PROMPTS = {
    "親切な社内ヘルプデスク（マニュアル丁寧解説）": "あなたは企業の社内ヘルプデスク担当です。社内マニュアルに基づき、分かりやすく親切に回答してください。",
    "プロのカスタマーサポート（丁寧・敬語徹底）": "あなたは大手企業のカスタマーサポート責任者です。完璧なビジネス敬語を用いて、非の打ち所がない丁寧な回答を徹底してください。",
    "辛口ITコンサルタント（問題点と改善策のハッキリ提示）": "あなたは経験豊富な辛口ITコンサルタントです。質問の裏にある本質的な課題を厳しく指摘し、具体的な改善策を提示してください。"
}
current_system_prompt = SYSTEM_PROMPTS[persona_option]

# ハイパーパラメータの調整
temperature = st.sidebar.slider("Temperature (温度値)", 0.0, 2.0, 0.2, 0.1)
max_tokens = st.sidebar.slider("最大出力トークン数", 100, 2000, 800, 50)

# ==========================================
# 💬 メインエリア：チャットUIと履歴管理
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []

# 過去の会話履歴を描画
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ユーザー入力
if user_input := st.chat_input("質問を入力してください..."):
    
    st.chat_message("user").markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        try:
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
            
            # ユーザーがセレクトボックスで選んだ最新モデルをそのまま指定
            model = genai.GenerativeModel(
                model_name=f"models/{selected_model_name}",
                generation_config=generation_config,
                system_instruction=current_system_prompt
            )
            
            # 文脈維持のための履歴結合（直近3件）
            full_prompt = ""
            for msg in st.session_state.messages[-3:]:
                full_prompt += f"{msg['role']}: {msg['content']}\n"
            
            # 応答生成
            response = model.generate_content(full_prompt)
            ai_response = response.text
            
            response_placeholder.markdown(ai_response)
            st.session_state.messages.append({"role": "assistant", "content": ai_response})
            
        except Exception as e:
            st.error(f"エラーが発生しました。選択したモデルがAPIキーの権限に対応していないか、パラメータが不正な可能性があります。 (詳細: {e})")