import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ──────────────────────────────────────────────
# 1) 환경설정
# ──────────────────────────────────────────────
load_dotenv()
API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
client = OpenAI(api_key=API_KEY)

st.set_page_config(page_title="운동 플래너 챗봇", page_icon="🏋️")
st.title("🏋️ 운동 플래너 챗봇")
st.caption("개인 맞춤 홈트/운동 루틴을 추천합니다.")

# ──────────────────────────────────────────────
# 2) 시스템 프롬프트 (AI 역할 정의)
# ──────────────────────────────────────────────
system_prompt = {
    "role": "system",
    "content": "너는 운동 플랜을 제공하는 피트니스 트레이너야. \
    사용자의 목표(체중감량, 근력강화, 부위별 운동 등)에 맞춰 \
    운동 루틴을 세트/횟수/휴식까지 구체적으로 제시해줘."
}

# ──────────────────────────────────────────────
# 3) 세션 상태 초기화
# ──────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state["messages"] = [system_prompt]

# ──────────────────────────────────────────────
# 4) 기존 대화 표시
# ──────────────────────────────────────────────
for msg in st.session_state["messages"]:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# ──────────────────────────────────────────────
# 5) 사용자 입력 → 모델 호출
# ──────────────────────────────────────────────
if user_input := st.chat_input("오늘 운동 루틴을 알려줘!"):
    # 사용자 메시지 저장
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 모델 호출
    with st.chat_message("assistant"):
        with st.spinner("운동 플랜을 구성하는 중..."):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state["messages"]
            )
            answer = response.choices[0].message.content
            st.markdown(answer)

    # AI 응답 저장
    st.session_state["messages"].append({"role": "assistant", "content": answer})
