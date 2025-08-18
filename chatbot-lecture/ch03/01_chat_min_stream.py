# 01_chat_min_stream.py
import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ── .env 로드 & 클라이언트 준비 ───────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="Streaming Chat", page_icon="🔴")
st.title("🔴 Streaming Chat (OpenAI Responses)")

if not OPENAI_API_KEY:
    st.error("환경변수 OPENAI_API_KEY가 없습니다. .env 파일을 확인하세요.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# ── 대화 상태 ─────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "You are a helpful assistant."}]

# 기존 대화 렌더
for m in st.session_state.messages:
    if m["role"] == "system":
        continue
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ── 입력 & 스트리밍 응답 ──────────────────────────────────────────────────────
if prompt := st.chat_input("메시지를 입력하세요"):
    # 사용자 메시지 표시/저장
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        collected_chunks = []

        try:
            # Responses API 스트리밍
            with client.responses.stream(
                model="gpt-4.1-nano",     # 필요에 따라 모델 변경
                input=prompt,
                temperature=0.3,
            ) as stream:
                for event in stream:
                    # 부분 토큰 델타 수신
                    if event.type == "response.output_text.delta":
                        collected_chunks.append(event.delta)
                        placeholder.markdown("".join(collected_chunks))
                # 모든 이벤트 처리 완료까지 대기
                stream.until_done()

            answer = "".join(collected_chunks) or "(응답 없음)"
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as e:
            placeholder.error(f"OpenAI 스트리밍 중 오류: {e}")
