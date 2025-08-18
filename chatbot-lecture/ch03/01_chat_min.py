# 01_chat_min.py
import os
import streamlit as st
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI

# ── 환경 변수(.env) 로드 & OpenAI 클라이언트 준비 ─────────────────────────────
load_dotenv(find_dotenv())  # 앱 시작 시 1회만 호출
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

print("Key 길이:", len(OPENAI_API_KEY), "앞:", OPENAI_API_KEY[:5])

st.set_page_config(page_title="Minimal Chat", page_icon="💬")
st.title("💬 Minimal OpenAI Chat")

if not OPENAI_API_KEY  or not OPENAI_API_KEY.startswith("sk-"):
    st.error("환경변수 OPENAI_API_KEY가 없습니다. .env 파일을 확인하세요.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

st.write("키 로드됨:", bool(OPENAI_API_KEY), "길이:", len(OPENAI_API_KEY or ""))
st.write("첫 3글자:", (OPENAI_API_KEY[:3] + "***") if OPENAI_API_KEY else "없음")

# ── 대화 상태 초기화 ───────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

# ── 기존 대화 렌더 ─────────────────────────────────────────────────────────────
for m in st.session_state.messages:
    if m["role"] == "system":
        continue
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ── 입력 & 응답 ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("메시지를 입력하세요"):
    # 사용자 메시지 저장/출력
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # OpenAI 호출 (Responses API, 단문 입력)
    user_text = "\n".join(
        m["content"] for m in st.session_state.messages if m["role"] == "user"
    )

    with st.chat_message("assistant"):
        thinking = st.status("생각 중...")
        try:
            resp = client.responses.create(
                model="gpt-4.1-nano",    # 예: 가성비 모델(환경에 맞게 변경 가능)
                input=user_text,
                temperature=0.3,
            )
            # SDK 버전에 따라 안전하게 텍스트 추출
            answer = getattr(resp, "output_text", None) or str(resp)
            thinking.update(label="완료", state="complete")
            st.markdown(answer)
            st.session_state.messages.append(
                {"role": "assistant", "content": answer}
            )
        except Exception as e:
            thinking.update(label="오류 발생", state="error")
            st.error(f"OpenAI 호출 중 오류: {e}")
            st.error("OpenAI 호출 실패(키/네트워크/모델 설정 확인).")
            st.caption(f"기술 로그: {getattr(e, 'status_code', '')} {str(e)[:200]} ...")
