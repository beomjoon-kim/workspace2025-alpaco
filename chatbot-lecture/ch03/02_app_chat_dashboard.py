# app_chat_dashboard.py
# 업로드 예제(01~05)의 포인트를 하나의 Streamlit 앱으로 통합한 실습 코드
# - dotenv로 키 관리, Responses API(비-스트리밍), 탭/사이드바/차트/로그/다운로드 포함

import os, time, io, textwrap, datetime as dt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI

# ──────────────────────────────────────────────────────────────────────────────
# 0) 환경설정: dotenv → OPENAI_API_KEY
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv(find_dotenv())
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()

st.set_page_config(page_title="Chat + Logs + Charts", page_icon="💬", layout="wide")
st.title("💬 Chat Dashboard (Streamlit x OpenAI)")

if not OPENAI_API_KEY or not OPENAI_API_KEY.startswith("sk-"):
    st.error("OPENAI_API_KEY가 설정되어 있지 않습니다. .env 파일을 확인하세요.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# ──────────────────────────────────────────────────────────────────────────────
# 1) Session State 초기화
# ──────────────────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []   # 채팅 말풍선 표시용(간단)
if "logs" not in st.session_state:
    # 대화/측정치 누적 로그(DataFrame용)
    st.session_state.logs = []       # [{ts, model, domain, temp, chars_in, chars_out, t_ms, tok_in, tok_out, answer}]
if "sys_prompt" not in st.session_state:
    st.session_state.sys_prompt = textwrap.dedent("""
    You are a helpful assistant.
    - 답을 모르면 모른다고 말합니다.
    - 불확실한 정보는 추측하지 않습니다.
    - 간결하고 단계적으로 설명합니다.
    """)

# ──────────────────────────────────────────────────────────────────────────────
# 2) 사이드바(05_layout / 04_input widget)
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("⚙️ Settings")
    # 모델은 실제 사용 가능한 것만 노출
    model = st.selectbox(
        "Model",
        options=["gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-3.5-turbo"],
        index=0,
    )
    temperature = st.slider("Temperature", 0.0, 1.0, 0.3, 0.1)
    domain = st.radio("Domain(역할 프리셋)", ["일반", "여행추천", "식단코치", "학습튜터"], index=0, horizontal=False)
    st.divider()
    st.caption("🔒 API Key: 환경변수(.env) 로드됨")
    st.caption("※ 키 값은 화면에 노출하지 않습니다.")

# 도메인 프리셋 → 시스템 프롬프트에 반영
DOMAIN_GUIDE = {
    "일반": "",
    "여행추천": "여행플래너 역할로, 2~3개 후보 일정과 장단점을 제시합니다.",
    "식단코치": "영양 코치 역할로, 알레르기/선호를 질문하고 1일 식단을 제시합니다.",
    "학습튜터": "학습 튜터 역할로, 예제→설명→퀴즈→요약 순서로 가르칩니다.",
}
sys_prompt = st.session_state.sys_prompt + ("\n" + DOMAIN_GUIDE.get(domain, ""))

# ──────────────────────────────────────────────────────────────────────────────
# 3) 상단 안내(01_text: 마크다운/코드/수식 → 가이드/샘플)
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("📘 시스템 가이드 & 샘플 표시 (01_text 응용)", expanded=False):
    st.markdown("""
    - **역할(System Prompt)**은 좌측 Domain 선택에 따라 보강됩니다.
    - `st.markdown`, `st.code`, `st.latex` 사용 예시를 아래에 배치했습니다.
    """)
    st.code(
        "def few_shot_rule():\n    return '간결하게, 단계별로, 예시와 함께 설명'\n",
        language="python",
    )
    st.latex(r"x=\frac{-b\pm\sqrt{b^2-4ac}}{2a}")

# ──────────────────────────────────────────────────────────────────────────────
# 4) 탭 구성(05_layout): Chat / Logs / Charts
# ──────────────────────────────────────────────────────────────────────────────
tab_chat, tab_logs, tab_charts = st.tabs(["💬 Chat", "🧾 Logs", "📈 Charts"])

# ──────────────────────────────────────────────────────────────────────────────
# 4-1) Chat 탭
#   - 좌: 대화창(03: 없음), 우: 통계/도움말 컬럼(02_data의 metric/json 응용)
# ──────────────────────────────────────────────────────────────────────────────
with tab_chat:
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("대화")
        # 이전 메시지 출력
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        # 입력창
        if prompt := st.chat_input("메시지를 입력하세요"):
            # 사용자 메시지 표시
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # OpenAI 호출 (Responses API, 비-스트리밍)
            start = time.perf_counter()
            try:
                # 간단 문자열 합성 입력(Responses는 문자열 input 허용)
                composed = f"[SYSTEM]\n{sys_prompt}\n\n[USER]\n{prompt}"
                resp = client.responses.create(
                    model=model,
                    input=composed,
                    temperature=temperature,
                )
                # 텍스트/사용량 안전 추출
                answer = getattr(resp, "output_text", None) or str(resp)
                usage = getattr(resp, "usage", None)

                dur_ms = int((time.perf_counter() - start) * 1000)
                tokens_in = tokens_out = None
                if usage:
                    # 객체/딕셔너리 호환 처리
                    tokens_in = getattr(usage, "input_tokens", None) or (usage.get("input_tokens") if isinstance(usage, dict) else None)
                    tokens_out = getattr(usage, "output_tokens", None) or (usage.get("output_tokens") if isinstance(usage, dict) else None)

                # 어시스턴트 말풍선
                with st.chat_message("assistant"):
                    st.markdown(answer)

                # 메시지/로그 적재
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.session_state.logs.append({
                    "ts": dt.datetime.now().isoformat(timespec="seconds"),
                    "model": model,
                    "domain": domain,
                    "temp": temperature,
                    "chars_in": len(prompt),
                    "chars_out": len(answer),
                    "t_ms": dur_ms,
                    "tok_in": tokens_in,
                    "tok_out": tokens_out,
                    "answer": answer,
                    "question": prompt,
                })

            except Exception as e:
                with st.chat_message("assistant"):
                    st.error(f"OpenAI 호출 실패: {e}")

    with col_right:
        st.subheader("통계 / 원시 응답 보기")
        # KPI (02_data: metric)
        df = pd.DataFrame(st.session_state.logs)
        turns = len(df)
        avg_ms = int(df["t_ms"].mean()) if turns else 0
        total_chars = int(df["chars_out"].sum()) if turns else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Turns", turns)
        c2.metric("Avg Latency(ms)", avg_ms)
        c3.metric("Out Chars", total_chars)

        # 원시 응답 보기 (02_data: json)
        if turns:
            st.caption("최근 응답 원문(JSON 비슷하게 보기)")
            st.json({
                "answer": df.iloc[-1]["answer"],
                "usage": {"tok_in": df.iloc[-1]["tok_in"], "tok_out": df.iloc[-1]["tok_out"]},
                "elapsed_ms": df.iloc[-1]["t_ms"],
                "model": df.iloc[-1]["model"],
            })

        st.divider()
        st.info("도움말: 좌측 Domain과 Temperature를 바꿔가며 응답 변화를 관찰하세요.")

# ──────────────────────────────────────────────────────────────────────────────
# 4-2) Logs 탭 (02_data: dataframe, download / 04_input widget: 다운로드)
# ──────────────────────────────────────────────────────────────────────────────
with tab_logs:
    st.subheader("대화 로그")
    df = pd.DataFrame(st.session_state.logs)
    if df.empty:
        st.warning("아직 로그가 없습니다. Chat 탭에서 대화를 시작하세요.")
    else:
        st.dataframe(df, use_container_width=True)
        # CSV 다운로드
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="CSV로 다운로드",
            data=csv,
            file_name="chat_logs.csv",
            mime="text/csv",
        )

# ──────────────────────────────────────────────────────────────────────────────
# 4-3) Charts 탭 (03_chart: Plotly로 시각화)
#   - 발화 길이 / 응답 시간 / (옵션) 간단 피드백
# ──────────────────────────────────────────────────────────────────────────────
with tab_charts:
    st.subheader("세션 지표 시각화 (Plotly)")

    df = pd.DataFrame(st.session_state.logs)
    if df.empty:
        st.info("시각화할 로그가 없습니다.")
    else:
        x = list(range(1, len(df) + 1))

        # 응답 시간 라인
        fig1 = go.Figure(data=go.Scatter(x=x, y=df["t_ms"], mode="lines+markers"))
        fig1.update_layout(title="응답 시간(ms) 추이", xaxis_title="Turn", yaxis_title="ms")
        st.plotly_chart(fig1, use_container_width=True)

        # 출력 글자 수 산점
        fig2 = go.Figure(data=go.Scatter(x=x, y=df["chars_out"], mode="markers"))
        fig2.update_layout(title="출력 길이(문자 수)", xaxis_title="Turn", yaxis_title="chars_out")
        st.plotly_chart(fig2, use_container_width=True)

        # (토큰 사용량이 있으면) 막대
        if "tok_out" in df.columns and df["tok_out"].notna().any():
            fig3 = go.Figure(data=go.Bar(x=x, y=df["tok_out"]))
            fig3.update_layout(title="출력 토큰 수(있을 때)", xaxis_title="Turn", yaxis_title="tok_out")
            st.plotly_chart(fig3, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# 5) 보안/배포 체크(메모)
#  - 로컬: dotenv(.env) 사용
#  - Streamlit Cloud 배포 시에는 Secrets UI 사용 가능(st.secrets) — 여기선 화면 노출만 막음
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("🔒 보안/배포 체크리스트 (메모)", expanded=False):
    st.markdown("""
- API Key는 코드에 직접 넣지 말고 **.env** 또는 배포 환경 변수로 관리
- Git 커밋 금지(.gitignore)
- Streamlit Cloud 사용 시 **Secrets** UI에 등록 가능
- 인증이 필요하면 OIDC/프록시 앞단 고려
""")
