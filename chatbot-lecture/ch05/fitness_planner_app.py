# fitness_planner_app.py
# Streamlit x OpenAI - 운동 목표/부위 선택 위젯을 포함한 "운동 플래너 챗봇" (완성 코드)

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

st.set_page_config(page_title="운동 플래너 챗봇", page_icon="🏋️", layout="centered")
st.title("🏋️ 운동 플래너 챗봇")
st.caption("목표·부위·시간·레벨을 반영해 홈트/헬스 루틴을 추천합니다.")

# ──────────────────────────────────────────────────────────────────────────────
# 1) 사이드바 옵션 (운동 목표/부위 선택 위젯 포함)
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("⚙️ 추천 옵션")
    model = st.selectbox(
        "모델 선택",
        options=["gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-3.5-turbo"],
        index=0,
        help="가성비는 gpt-4o-mini 권장"
    )
    goal = st.radio(
        "운동 목표",
        ["체중감량(다이어트)", "근력 강화", "체형 교정/자세", "유산소 체력", "유연성/재활"],
        index=0, horizontal=False
    )
    body_parts = st.multiselect(
        "집중 부위(복수 선택)",
        ["전신", "하체", "상체", "코어", "등", "가슴", "어깨", "팔", "둔근(엉덩이)"],
        default=["하체", "코어"]
    )
    minutes = st.slider("운동 시간(분)", min_value=10, max_value=90, value=30, step=5)
    days_per_week = st.slider("주당 횟수(회)", min_value=1, max_value=7, value=3, step=1)
    level = st.selectbox("난도(레벨)", ["초급", "중급", "상급"], index=0)
    place = st.selectbox("장소", ["홈트(맨몸/소도구)", "헬스장"], index=0)
    equipment = st.multiselect(
        "사용 가능 장비(선택)",
        ["없음", "덤벨", "저항밴드", "케틀벨", "스텝박스", "폼롤러", "풀업바", "머신"],
        default=["없음"] if place.startswith("홈트") else ["덤벨", "머신"]
    )
    injuries = st.text_input("주의/통증/부상 이력", placeholder="예: 무릎 통증, 허리 디스크")
    include_warmup = st.toggle("워밍업 포함", value=True)
    include_cooldown = st.toggle("쿨다운/스트레칭 포함", value=True)
    rpe_guide = st.toggle("RPE(자각 난이도) 안내 포함", value=True)
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

# 시스템 가이드(프롬프트) 생성
SYSTEM_GUIDE = textwrap.dedent(f"""
너는 운동 플랜을 제공하는 피트니스 트레이너야.
아래 조건을 반영하여 안전하고 구체적인 루틴을 제시해줘.

[사용자 조건]
- 목표: {goal}
- 집중 부위: {", ".join(body_parts) if body_parts else "특정 부위 없음"}
- 1회 운동 시간: 약 {minutes}분
- 주당 횟수: {days_per_week}회
- 난도: {level}
- 장소/장비: {place}, 사용 가능 장비: {", ".join(equipment) if equipment else "없음"}
- 주의사항/부상: {injuries or "없음"}

[제시 형식]
- 표제: 오늘의 루틴 (또는 1주 플랜 요약)
- (선택) 워밍업: { "간단한 동적 스트레칭 3~5분" if include_warmup else "생략" }
- 본운동: 동작명 · 세트×반복 · 휴식(초) · 대체 동작(부상 고려)
- (선택) 쿨다운: { "정적 스트레칭 3~5분" if include_cooldown else "생략" }
- 안전/자세 팁 3가지
{ "- RPE(자각 난이도) 가이드 포함" if rpe_guide else "" }

[원칙]
- 레벨과 부상 이력을 고려하여 동작/볼륨을 조절.
- 분 단위 총 소요시간이 {minutes}±5분을 크게 벗어나지 않도록 구성.
- 하체/코어 등 집중 부위가 요청되면 그 비중을 높이고, 균형도 일정 수준 유지.
- 초보자는 폼 안정·범위 제한을 강조, 상급자에게는 진행/피로 누적 관리 팁 제공.
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
default_hint = "예) 하체 위주 홈트 루틴 알려줘 / 상체+코어 40분 / 주 4회 프로그램"
user_prompt = st.chat_input(default_hint)
if user_prompt:
    # 사용자 메시지 표시/저장
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # 단일 문자열 합성 (Responses API는 문자열 input 가능)
    composed = f"[SYSTEM]\n{SYSTEM_GUIDE}\n\n[USER]\n{user_prompt}"

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

        # 부가 정보
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        with st.expander("Ⓘ 시스템 가이드(프롬프트)", expanded=False):
            st.code(SYSTEM_GUIDE, language="markdown")
        st.caption(f"⏱️ 응답 시간: {elapsed_ms} ms")

        # 다운로드(마크다운 텍스트)
        st.download_button(
            label="📥 이번 루틴 텍스트 다운로드 (.md)",
            data=answer.encode("utf-8"),
            file_name="fitness_plan.md",
            mime="text/markdown",
            use_container_width=True,
        )

    except Exception as e:
        with st.chat_message("assistant"):
            st.error(f"OpenAI 호출 실패: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# 5) 안전 안내
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "⚠️ 본 내용은 참고용 가이드이며, 통증·질환이 있거나 초보자는 전문가와 상의하세요. "
    "과사용/부상 방지를 위해 적절한 휴식과 점진적 과부하 원칙을 지키세요."
)
