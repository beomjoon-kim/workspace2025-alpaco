# message_writer_app.py
# Streamlit x OpenAI - 문구/메시지 추천 챗봇 (톤/길이/언어/이모지/여러 개 생성 + 다운로드)
# 필요 패키지: streamlit, openai, python-dotenv

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

st.set_page_config(page_title="문구/메시지 추천 챗봇", page_icon="✉️", layout="centered")
st.title("✉️ 문구/메시지 추천 챗봇")
st.caption("행사/대상/톤/길이/언어를 선택해 감동적인 메시지를 만들어 보세요.")

# ──────────────────────────────────────────────────────────────────────────────
# 1) 사이드바: 생성 옵션
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("⚙️ 생성 옵션")
    model = st.selectbox(
        "모델 선택",
        options=["gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-3.5-turbo"],
        index=0,
        help="가성비는 gpt-4o-mini 권장"
    )
    occasion = st.selectbox(
        "행사(테마)",
        ["졸업", "입학", "생일", "결혼", "출산", "집들이", "새해/명절", "감사/격려", "사과", "위로/응원", "퇴사/이직 축하", "기타"],
        index=0
    )
    recipient = st.text_input("받는 사람(대상)", placeholder="예: 친구 민수, 선생님, 동료, 자녀")
    tone = st.selectbox("톤(문체)", ["감동적", "격려", "진지", "유머", "격식", "따뜻함", "담백함"], index=0)
    length = st.selectbox("길이", ["짧게(한두 문장)", "보통(3~4문장)", "길게(문단)"], index=1)
    language = st.selectbox("언어", ["한국어", "영어", "일본어", "중국어", "스페인어", "독일어"], index=0)
    emoji = st.toggle("이모지 포함", value=True)
    variants = st.slider("문구 개수", min_value=1, max_value=10, value=5, step=1)
    include_signoff = st.toggle("끝인사/서명 포함", value=False, help="예: 마지막에 이름/호칭 추가")
    streaming = st.toggle("스트리밍 응답", value=True)
    st.divider()
    if st.button("🧹 화면 초기화"):
        st.session_state.clear()
        st.experimental_rerun()

# ──────────────────────────────────────────────────────────────────────────────
# 2) 시스템 가이드(프롬프트) 구성
# ──────────────────────────────────────────────────────────────────────────────
# 길이 가이드라인
length_rule = {
    "짧게(한두 문장)": "한두 문장으로 간결하게 작성",
    "보통(3~4문장)": "3~4문장 내로 명확하게 작성",
    "길게(문단)": "짧은 문단 1개 분량으로 풍부하게 작성",
}[length]

# 언어 코드 힌트
lang_hint = {
    "한국어": "ko",
    "영어": "en",
    "일본어": "ja",
    "중국어": "zh",
    "스페인어": "es",
    "독일어": "de",
}[language]

SYSTEM_PROMPT = textwrap.dedent(f"""
너는 감동적이고 상황에 맞는 축하/격려/사과/감사 메시지를 만들어주는 전문 문장 작가야.
요청에 맞춰 다음 원칙을 지켜주세요.

[원칙]
- 톤: "{tone}"의 분위기를 유지.
- 길이: {length_rule}.
- 언어: {language}(코드: {lang_hint}).
- 대상: 요청에 명시된 대상과 관계에 맞춤.
- 금지: 비속어/차별/개인정보/과도한 사적 추측/민감한 정치·의학적 조언.
- 문장 매끄럽게, 맞춤법/띄어쓰기 정확하게.
- { "적절한 이모지를 1~2개선에서 활용" if emoji else "이모지 사용 금지" }.
- { "끝인사/서명 한 줄을 마지막에 추가" if include_signoff else "끝인사/서명은 포함하지 않음" }.
- 변형(variants) 수만큼 서로 다른 문구를 각각 별도 항목으로 제공.

[출력 형식]
- 각 문구는 번호 목록으로 제공 (1., 2., 3. …).
- 불필요한 프리앰블/해설 없이 결과만 출력.
""").strip()

# ──────────────────────────────────────────────────────────────────────────────
# 3) 입력 영역
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("### ✍️ 요청 내용")
user_topic = st.text_input(
    "상세 요청(상황/키워드)",
    placeholder="예) 졸업식 축하 카드인데, 열심히 노력한 점을 칭찬하고 앞으로의 시작을 응원해줘."
)
extra_info = st.text_area(
    "조건(선택)",
    placeholder="예) 과장되지 않게, 유머는 아주 약하게, 문장 길이 짧게, 선생님께 드릴 카드 등"
)

default_hint = "예) 졸업식 축하 카드에 쓸 좋은 말 알려줘"
user_prompt = st.chat_input(default_hint)

# ──────────────────────────────────────────────────────────────────────────────
# 4) 모델 호출 유틸
# ──────────────────────────────────────────────────────────────────────────────
def build_user_message():
    lines = []
    lines.append(f"행사/테마: {occasion}")
    if recipient.strip():
        lines.append(f"대상: {recipient.strip()}")
    if user_topic.strip():
        lines.append(f"요청 상세: {user_topic.strip()}")
    if extra_info.strip():
        lines.append(f"추가 조건: {extra_info.strip()}")
    lines.append(f"서로 다른 문구 {variants}개 생성")
    return "\n".join(lines)

def call_model(prompt_text: str) -> str:
    composed = f"[SYSTEM]\n{SYSTEM_PROMPT}\n\n[USER]\n{prompt_text}"
    if streaming:
        with st.chat_message("assistant"):
            placeholder = st.empty()
            chunks = []
            with client.responses.stream(
                model=model,
                input=composed,
                temperature=0.6,  # 창의성 조금 높임
            ) as stream:
                for event in stream:
                    if event.type == "response.output_text.delta":
                        chunks.append(event.delta)
                        placeholder.markdown("".join(chunks))
                stream.until_done()
            return "".join(chunks) if chunks else "(응답 없음)"
    else:
        resp = client.responses.create(model=model, input=composed, temperature=0.6)
        answer = getattr(resp, "output_text", None) or str(resp)
        with st.chat_message("assistant"):
            st.markdown(answer)
        return answer

# ──────────────────────────────────────────────────────────────────────────────
# 5) 대화 & 생성 트리거
# ──────────────────────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []  # [(role, content), ...]

# 과거 대화 렌더링
for role, content in st.session_state.history:
    with st.chat_message(role):
        st.markdown(content)

# 채팅 입력이 들어오면 즉시 생성
if user_prompt:
    st.session_state.history.append(("user", user_prompt))
    with st.chat_message("user"):
        st.markdown(user_prompt)

    final_user_message = build_user_message()
    t0 = time.perf_counter()
    try:
        answer = call_model(final_user_message)
        st.session_state.history.append(("assistant", answer))
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        with st.expander("Ⓘ 시스템 프롬프트", expanded=False):
            st.code(SYSTEM_PROMPT, language="markdown")
        with st.expander("Ⓘ 사용자 메시지(모델 입력)", expanded=False):
            st.code(final_user_message, language="markdown")
        st.caption(f"⏱️ 응답 시간: {elapsed_ms} ms")
    except Exception as e:
        with st.chat_message("assistant"):
            st.error(f"OpenAI 호출 실패: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# 6) 결과 활용: 개별 선택/다운로드
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📥 결과 저장/활용")

# 최신 어시스턴트 응답에서 번호 목록 추출
latest_answer = None
for role, content in reversed(st.session_state.history):
    if role == "assistant":
        latest_answer = content
        break

def split_numbered_items(text: str):
    # "1. ...\n2. ...\n" 형식 분리
    import re
    items = []
    current = []
    for line in text.splitlines():
        if re.match(r"^\s*\d+\.\s+", line):
            if current:
                items.append("\n".join(current).strip())
                current = []
            current.append(re.sub(r"^\s*(\d+)\.\s+", "", line))
        else:
            if current:
                current.append(line)
    if current:
        items.append("\n".join(current).strip())
    return [i for i in items if i]

selected = []
if latest_answer:
    st.caption("가장 최근 생성 결과에서 문구를 선택해 저장할 수 있어요.")
    items = split_numbered_items(latest_answer)
    if items:
        cols = st.columns(2)
        for idx, msg in enumerate(items, start=1):
            with cols[(idx-1) % 2]:
                st.text_area(f"{idx}번 문구", msg, height=120, key=f"msg_{idx}")
                if st.checkbox(f"{idx}번 선택", key=f"sel_{idx}"):
                    selected.append((idx, msg))
    else:
        st.info("번호 목록 형식의 문구를 찾지 못했습니다. (프롬프트 규칙을 확인하세요)")

    # 다운로드
    if selected:
        content = "\n\n".join([f"{i}. {m}" for i, m in selected])
        st.download_button(
            "선택 문구 TXT 다운로드",
            data=content.encode("utf-8"),
            file_name="messages_selected.txt",
            mime="text/plain",
            use_container_width=True,
        )

# 전체 결과 다운로드
if latest_answer:
    st.download_button(
        "전체 결과 TXT 다운로드",
        data=latest_answer.encode("utf-8"),
        file_name="messages_full.txt",
        mime="text/plain",
        use_container_width=True,
    )

# ──────────────────────────────────────────────────────────────────────────────
# 7) 가이드/주의
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "💡 팁: 상황·대상·톤·길이·언어를 구체적으로 지정할수록 만족도가 높습니다. "
    "⚠️ 민감한 정보, 명예훼손, 차별 표현은 생성/사용하지 마세요."
)
