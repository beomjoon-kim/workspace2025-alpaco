# diet_chatbot.py
# Streamlit x OpenAI Responses API - 식단 추천 챗봇 (단일 파일)
import os
import time
import textwrap
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ──────────────────────────────────────────────────────────────────────────────
# 0) 환경 설정
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv()
API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY가 설정되어 있지 않습니다. .env를 확인하세요.")

client = OpenAI(api_key=API_KEY)

st.set_page_config(page_title="식단 추천 챗봇", page_icon="🥗", layout="centered")
st.title("🥗 식단 추천 챗봇")
st.caption("건강 목표·선호를 반영해 식단을 제안합니다.")

# ──────────────────────────────────────────────────────────────────────────────
# 1) Sidebar: 옵션
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("⚙️ 추천 옵션")
    model = st.selectbox(
        "모델 선택",
        options=["gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-3.5-turbo"],
        index=0,
        help="가성비는 gpt-4o-mini 권장"
    )
    meal_type = st.radio("식사 유형", ["아침", "점심", "저녁"], index=1, horizontal=True)
    target_kcal = st.slider("목표 칼로리 (kcal)", min_value=300, max_value=1200, value=600, step=50)
    diet_pref = st.multiselect(
        "식단 선호/제약",
        ["고단백", "저탄고지", "지중해식", "채식(락토/오보 포함)", "비건", "글루텐 프리", "저염"],
        default=["고단백"]
    )
    allergies = st.text_input("알레르기/기피 식재료 (쉼표로 구분)", placeholder="예: 땅콩, 새우, 우유")
    cuisine = st.selectbox("선호하는 스타일", ["아시아", "한식", "서양", "지중해", "무관"], index=0)
    servings = st.number_input("인분(명)", min_value=1, max_value=6, value=1, step=1)
    show_nutri = st.toggle("영양소 요약 포함", value=True)
    streaming = st.toggle("스트리밍 응답", value=True, help="실시간으로 토큰이 표시됩니다.")
    st.divider()
    if st.button("🧹 대화 초기화"):
        st.session_state.clear()
        st.experimental_rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 2) 세션 상태
# ──────────────────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

SYSTEM_GUIDE = textwrap.dedent(f"""
너는 건강한 식단을 추천해주는 AI 영양 코치야.
원칙:
- {meal_type} 기준으로 {servings}인분을 제안할 것.
- 1인분 기준 목표 칼로리는 약 {target_kcal} kcal 전후로 맞출 것(±15% 허용).
- 선호/제약: {", ".join(diet_pref) if diet_pref else "특이사항 없음"}.
- 알레르기/기피: {allergies or "없음"}.
- 선호 스타일: {cuisine}.
- 가능하면 손쉽게 준비 가능한 재료 중심, 조리법 간단 요약 포함.
- 항목 형식: 메뉴 구성 → 재료/분량 → 간단 레시피 → 예상 칼로리 및 영양 포인트{(" → 탄/단/지/식이섬유 표" if show_nutri else "")}.
""").strip()

# ──────────────────────────────────────────────────────────────────────────────
# 3) 과거 대화 렌더링
# ──────────────────────────────────────────────────────────────────────────────
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ──────────────────────────────────────────────────────────────────────────────
# 4) 사용자 입력 & 모델 호출
# ──────────────────────────────────────────────────────────────────────────────
prompt = st.chat_input(f"{meal_type} 식단을 추천해줘 (예: 현미밥+단백질+야채 위주)")
if prompt:
    # 사용자 메시지 표시/저장
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 단일 문자열로 합성 (Responses API는 자유 형식 input 허용)
    composed = f"[SYSTEM]\n{SYSTEM_GUIDE}\n\n[USER]\n{prompt}"

    # 호출
    t0 = time.perf_counter()
    try:
        if streaming:
            with st.chat_message("assistant"):
                placeholder = st.empty()
                chunks = []
                with client.responses.stream(
                    model=model,
                    input=composed,
                    temperature=0.4,
                ) as stream:
                    for event in stream:
                        if event.type == "response.output_text.delta":
                            chunks.append(event.delta)
                            placeholder.markdown("".join(chunks))
                    stream.until_done()
                answer = "".join(chunks) if chunks else "(응답 없음)"
        else:
            resp = client.responses.create(
                model=model,
                input=composed,
                temperature=0.4,
            )
            answer = getattr(resp, "output_text", None) or str(resp)
            with st.chat_message("assistant"):
                st.markdown(answer)

        # 응답 저장
        st.session_state.messages.append({"role": "assistant", "content": answer})

        # 부가 안내(간단 KPI)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        with st.expander("Ⓘ 요청 컨텍스트(시스템 가이드)", expanded=False):
            st.code(SYSTEM_GUIDE, language="markdown")
        st.caption(f"⏱️ 응답 시간: {elapsed_ms} ms")

    except Exception as e:
        with st.chat_message("assistant"):
            st.error(f"OpenAI 호출 실패: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# 5) 푸터
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("🔒 API Key는 .env로 관리하세요. | ⚠️ 건강 관련 정보는 참고용이며, 개인 상황에 따라 전문가와 상담하세요.")
