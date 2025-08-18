# app_chat.py
import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv, find_dotenv

# ── 환경 변수(.env) 로드 & OpenAI 클라이언트 준비 ─────────────────────────────
load_dotenv(find_dotenv())  # 앱 시작 시 1회만 호출
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

print("Key 길이:", len(OPENAI_API_KEY), "앞:", OPENAI_API_KEY[:5])

st.set_page_config(page_title="OpenAI Chatbot", layout="wide")
st.title("OpenAI Chatbot (Streamlit)")

# client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
client = OpenAI(api_key=OPENAI_API_KEY)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role":"system", "content":"You are a helpful assistant."}]

# 좌측: 옵션
with st.sidebar:
    st.subheader("설정")
    model = st.selectbox("Model", ["gpt-5", "gpt-5-mini", "gpt-4o"], index=0)
    temperature = st.slider("temperature", 0.0, 1.0, 0.3, 0.1)

# 본문: 이전 대화 렌더
for m in st.session_state.messages:
    if m["role"] == "system":
        continue
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# 입력창
if prompt := st.chat_input("메시지를 입력하세요"):
    # 사용자 메시지 저장/출력
    st.session_state.messages.append({"role":"user", "content":prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 어시스턴트 응답
    with st.chat_message("assistant"):
        thinking = st.status("OpenAI 호출 중...", expanded=False)
        try:
            # Responses API: 단문 입력 흐름
            # (역할별 messages를 그대로 넣고 싶다면 Chat Completions로 호출하거나
            # Responses 멀티파트 입력 가이드에 맞춰 구성)
            user_text = "\n".join([m["content"] for m in st.session_state.messages if m["role"]=="user"])
            resp = client.responses.create(
                model=model,
                input=user_text,
                temperature=temperature
            )
            answer = resp.output_text
            thinking.update(label="완료", state="complete")
            st.markdown(answer)
            st.session_state.messages.append({"role":"assistant", "content":answer})
        except Exception as e:
            thinking.update(label=f"에러: {e}", state="error")
            