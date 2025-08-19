# fitness_planner_media_app.py
# Streamlit x OpenAI - "운동 플래너 챗봇"
# 확장: 동작별 YouTube 임베드 + GIF/이미지 검색 링크 포함

import os
import re
import time
import textwrap
import urllib.parse
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

st.set_page_config(page_title="운동 플래너 챗봇 (미디어 포함)", page_icon="🏋️", layout="centered")
st.title("🏋️ 운동 플래너 챗봇")
st.caption("목표·부위·시간·레벨을 반영해 루틴을 제안하고, 동작별 학습용 미디어(YouTube/GIF)를 제공합니다.")

# ──────────────────────────────────────────────────────────────────────────────
# 1) 사이드바 옵션
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
        index=0
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

    st.divider()
    st.subheader("🎞 미디어 표시")
    show_media = st.toggle("동작별 미디어 섹션 표시", value=True)
    max_media = st.slider("표시할 동작 개수 (상단부터)", 1, 10, 6)

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

# ──────────────────────────────────────────────────────────────────────────────
# 3) 시스템 가이드(프롬프트)
# ──────────────────────────────────────────────────────────────────────────────
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
- 본운동: 동작명 · 세트×반복(또는 시간) · 휴식(초) · 대체 동작(부상 고려)
- (선택) 쿨다운: { "정적 스트레칭 3~5분" if include_cooldown else "생략" }
- 안전/자세 팁 3가지
{ "- RPE(자각 난이도) 가이드 포함" if rpe_guide else "" }

[원칙]
- 레벨과 부상 이력을 고려하여 동작/볼륨을 조절.
- 분 단위 총 소요시간이 {minutes}±5분을 크게 벗어나지 않도록 구성.
- 요청된 부위 비중을 높이되, 균형도 일정 수준 유지.
- 초보자는 폼 안정·범위 제한 강조, 상급자에게는 진행/피로 누적 관리 팁 제공.
""").strip()

# ──────────────────────────────────────────────────────────────────────────────
# 4) 과거 대화 렌더링
# ──────────────────────────────────────────────────────────────────────────────
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ──────────────────────────────────────────────────────────────────────────────
# 5) 사용자 입력 & 모델 호출
# ──────────────────────────────────────────────────────────────────────────────
default_hint = "예) 하체 위주 홈트 루틴 / 상체+코어 40분 / 주 4회 프로그램"
user_prompt = st.chat_input(default_hint)

def call_model(prompt_text: str) -> str:
    """Responses API or Chat Completions 호출(여기선 Responses 스트리밍 기본)"""
    composed = f"[SYSTEM]\n{SYSTEM_GUIDE}\n\n[USER]\n{prompt_text}"
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
            return "".join(chunks) if chunks else "(응답 없음)"
    else:
        resp = client.responses.create(model=model, input=composed, temperature=0.4)
        answer = getattr(resp, "output_text", None) or str(resp)
        with st.chat_message("assistant"):
            st.markdown(answer)
        return answer

if user_prompt:
    # 사용자 메시지
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    t0 = time.perf_counter()
    try:
        answer = call_model(user_prompt)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        with st.expander("Ⓘ 시스템 가이드(프롬프트)", expanded=False):
            st.code(SYSTEM_GUIDE, language="markdown")
        st.caption(f"⏱️ 응답 시간: {elapsed_ms} ms")

    except Exception as e:
        with st.chat_message("assistant"):
            st.error(f"OpenAI 호출 실패: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# 6) 동작 추출 → 미디어 패널
# ──────────────────────────────────────────────────────────────────────────────
# 간단 추출 규칙: "1. 스쿼트 15회 x 3세트" 같은 라인에서 선행 텍스트(숫자/불릿 제거 후) 첫 단어/구 절을 동작명으로 추정
EXERCISE_VOCAB = {
    # 한글 ↔ 영어 키를 모두 포함해 약간의 변형에 대응
    "스쿼트": "squat",
    "런지": "lunge",
    "브릿지": "glute bridge",
    "플랭크": "plank",
    "푸시업": "push up",
    "푸쉬업": "push up",
    "벤치프레스": "bench press",
    "데드리프트": "deadlift",
    "바벨로우": "barbell row",
    "로우": "row",
    "숄더프레스": "shoulder press",
    "힙쓰러스트": "hip thrust",
    "버드독": "bird dog",
    "사이드 플랭크": "side plank",
    "크런치": "crunch",
    "레그레이즈": "leg raise",
    "카프레이즈": "calf raise",
}

# 신뢰 가능한 튜토리얼 단일 영상 맵(일부 대표 동작만 수록)
YOUTUBE_MAP = {
    "squat": "https://www.youtube.com/watch?v=U3HlEF_E9fo",         # ATHLEAN-X Perfect Squat
    "lunge": "https://www.youtube.com/watch?v=QOVaHwm-Q6U",
    "glute bridge": "https://www.youtube.com/watch?v=m2Zx-57cSok",
    "plank": "https://www.youtube.com/watch?v=pSHjTRCQxIw",
    "push up": "https://www.youtube.com/watch?v=IODxDxX7oi4",
    "deadlift": "https://www.youtube.com/watch?v=1ZXobu7JvvE",
    "barbell row": "https://www.youtube.com/watch?v=vT2GjY_Umpw",
    "shoulder press": "https://www.youtube.com/watch?v=B-aVuyhvLHU",
    "hip thrust": "https://www.youtube.com/watch?v=LM8XHLYJoYs",
    "bird dog": "https://www.youtube.com/watch?v=v6ZCgP4g3sQ",
    "side plank": "https://www.youtube.com/watch?v=K2VljzCC16g",
    "crunch": "https://www.youtube.com/watch?v=Xyd_fa5zoEU",
    "leg raise": "https://www.youtube.com/watch?v=JB2oyawG9KI",
    "calf raise": "https://www.youtube.com/watch?v=YMmgqO8Jo-k",
}

def parse_exercises_from_messages(messages_text: str):
    # 줄 단위 스캔: 번호/불릿 제거 후 첫 구절에서 동작명 후보 추출
    names = []
    for raw in messages_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if re.match(r"^(\*|\-|\d+[\.\)]|\•)\s+", line):
            line = re.sub(r"^(\*|\-|\d+[\.\)]|\•)\s+", "", line)
        # "스쿼트 15회 × 3세트" → "스쿼트"
        cand = re.split(r"[\d\(\)xX×*~\-:|/]", line)[0].strip()
        cand = re.sub(r"[•\.\,]+$", "", cand)
        # 너무 짧거나 문장형이면 스킵
        if 1 <= len(cand) <= 30:
            names.append(cand)
    # 중복 제거, 상위 몇 개만
    seen, uniq = set(), []
    for n in names:
        if n not in seen:
            uniq.append(n)
            seen.add(n)
    return uniq

def to_english_key(name: str) -> str:
    # 한글 매핑 → 영어 키, 없으면 영문 소문자화
    for ko, en in EXERCISE_VOCAB.items():
        if ko in name:
            return en
    return name.lower()

def youtube_for(name: str) -> str | None:
    key = to_english_key(name)
    return YOUTUBE_MAP.get(key)

def youtube_search_url(name: str) -> str:
    q = urllib.parse.quote_plus(f"{name} exercise tutorial")
    return f"https://www.youtube.com/results?search_query={q}"

def gif_search_url(name: str) -> str:
    # Google Images animated filter
    q = urllib.parse.quote_plus(f"{name} exercise gif")
    return f"https://www.google.com/search?q={q}&tbm=isch&tbs=itp:animated"

# 최신 어시스턴트 답변 텍스트 가져오기
latest_answer = None
for m in reversed(st.session_state.messages):
    if m["role"] == "assistant":
        latest_answer = m["content"]
        break

if show_media and latest_answer:
    st.markdown("---")
    st.subheader("🎥 동작별 미디어 가이드")

    ex_names = parse_exercises_from_messages(latest_answer)
    if not ex_names:
        st.info("루틴에서 동작명을 찾지 못했습니다. 번호/불릿으로 나열된 동작이 있어야 추출됩니다.")
    else:
        # 상단부터 N개만 표시
        ex_names = ex_names[:max_media]
        for idx, name in enumerate(ex_names, start=1):
            st.markdown(f"**{idx}. {name}**")
            yt = youtube_for(name)
            cols = st.columns([2, 1, 1])
            with cols[0]:
                if yt:
                    # YouTube 직접 임베드
                    st.video(yt)
                else:
                    st.info("직접 임베드 가능한 추천 영상이 없어 검색 링크를 제공합니다.")
            with cols[1]:
                st.link_button("🔎 YouTube 검색", youtube_search_url(name), use_container_width=True)
            with cols[2]:
                st.link_button("🖼 GIF 검색", gif_search_url(name), use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# 7) 푸터
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "⚠️ 본 내용은 참고용 가이드입니다. 통증/질환이 있거나 초보자는 전문가와 상의하세요. "
    "동작 학습 시 낮은 강도로 연습하고, 안전 범위와 올바른 자세를 우선하세요."
)
