# app_chat_dashboard_stream.py
# Chat / Logs / Charts 대시보드 + Responses API 스트리밍(.stream) + 파일 업로드(텍스트 컨텍스트) 통합 예제

import os, time, textwrap, datetime as dt
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

st.set_page_config(page_title="Chat + Logs + Charts (Streaming)", page_icon="💬", layout="wide")
st.title("💬 Chat Dashboard (Streamlit x OpenAI, Streaming)")

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
    st.session_state.logs = []       # [{ts, model, domain, temp, chars_in, chars_out, t_ms, tok_in, tok_out, answer, question}]
if "sys_prompt" not in st.session_state:
    st.session_state.sys_prompt = textwrap.dedent("""
    You are a helpful assistant.
    - 답을 모르면 모른다고 말합니다.
    - 불확실한 정보는 추측하지 않습니다.
    - 간결하고 단계적으로 설명합니다.
    """)
if "upload_text" not in st.session_state:
    st.session_state.upload_text = ""   # 업로드된 텍스트(.txt) 내용을 저장

# ──────────────────────────────────────────────────────────────────────────────
# 2) 사이드바 (모델/온도/도메인 + Streaming 토글)
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("⚙️ Settings")
    model = st.selectbox(
        "Model",
        options=["gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-3.5-turbo"],
        index=0,
    )
    temperature = st.slider("Temperature", 0.0, 1.0, 0.3, 0.1)
    domain = st.radio("Domain(역할 프리셋)", ["일반", "여행추천", "식단코치", "학습튜터"], index=0)
    streaming = st.toggle("🔴 Streaming 모드", value=True, help="켜면 실시간으로 토큰이 표시됩니다.")
    use_uploaded = st.checkbox("업로드한 텍스트를 컨텍스트로 사용", value=True, help="업로드된 .txt 내용을 프롬프트에 포함")
    st.divider()
    st.caption("🔒 API Key: 환경변수(.env) 로드됨 (화면 비노출)")

DOMAIN_GUIDE = {
    "일반": "",
    "여행추천": "여행플래너 역할로, 2~3개 후보 일정과 장단점을 제시합니다.",
    "식단코치": "영양 코치 역할로, 알레르기/선호를 질문하고 1일 식단을 제시합니다.",
    "학습튜터": "학습 튜터 역할로, 예제→설명→퀴즈→요약 순서로 가르칩니다.",
}
sys_prompt = st.session_state.sys_prompt + ("\n" + DOMAIN_GUIDE.get(domain, ""))

# ──────────────────────────────────────────────────────────────────────────────
# 3) 상단 안내(01_text 응용)
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("📘 시스템 가이드 & 샘플 표시", expanded=False):
    st.markdown("""
- **역할(System Prompt)**은 좌측 Domain 선택에 따라 보강됩니다.
- 아래는 코드/수식 예시입니다.
""")
    st.code(
        "def few_shot_rule():\n    return '간결하게, 단계별로, 예시와 함께 설명'\n",
        language="python",
    )
    st.latex(r"x=\frac{-b\pm\sqrt{b^2-4ac}}{2a}")

# ──────────────────────────────────────────────────────────────────────────────
# 4) 탭 구성: Chat / Logs / Charts
# ──────────────────────────────────────────────────────────────────────────────
tab_chat, tab_logs, tab_charts = st.tabs(["💬 Chat", "🧾 Logs", "📈 Charts"])

# ──────────────────────────────────────────────────────────────────────────────
# 4-1) Chat 탭 (좌: 대화, 우: KPI/원시응답 + 파일 업로드)
# ──────────────────────────────────────────────────────────────────────────────
with tab_chat:
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("대화")
        # 이전 메시지 출력
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        # 입력
        if prompt := st.chat_input("메시지를 입력하세요"):
            # 사용자 메시지
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            start = time.perf_counter()
            try:
                # 시스템+사용자 프롬프트 합성 (업로드 텍스트가 있으면 컨텍스트로 추가)
                context_block = ""
                if use_uploaded and st.session_state.upload_text.strip():
                    # 너무 길면 절단 (모델 토큰 보호)
                    ctx = st.session_state.upload_text.strip()
                    if len(ctx) > 4000:
                        ctx = ctx[:4000] + "\n...[truncated]"
                    context_block = f"\n[CONTEXT]\n{ctx}\n"

                composed = f"[SYSTEM]\n{sys_prompt}{context_block}\n[USER]\n{prompt}"

                if streaming:
                    # ── 스트리밍 모드 ───────────────────────────────────────────
                    with st.chat_message("assistant"):
                        placeholder = st.empty()
                        chunks = []

                        with client.responses.stream(
                            model=model,
                            input=composed,
                            temperature=temperature,
                        ) as stream:
                            for event in stream:
                                if event.type == "response.output_text.delta":
                                    chunks.append(event.delta)
                                    placeholder.markdown("".join(chunks))
                            stream.until_done()

                        answer = "".join(chunks) or "(응답 없음)"
                else:
                    # ── 비-스트리밍 모드 ───────────────────────────────────────
                    resp = client.responses.create(
                        model=model,
                        input=composed,
                        temperature=temperature,
                    )
                    answer = getattr(resp, "output_text", None) or str(resp)
                    with st.chat_message("assistant"):
                        st.markdown(answer)

                dur_ms = int((time.perf_counter() - start) * 1000)

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
                    "tok_in": None,
                    "tok_out": None,
                    "answer": answer,
                    "question": prompt,
                })

            except Exception as e:
                with st.chat_message("assistant"):
                    st.error(f"OpenAI 호출 실패: {e}")

    with col_right:
        st.subheader("통계 / 원시 응답 / 업로드")

        # ── KPI (02_data: metric)
        df = pd.DataFrame(st.session_state.logs)
        turns = len(df)
        avg_ms = int(df["t_ms"].mean()) if turns else 0
        total_chars = int(df["chars_out"].sum()) if turns else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Turns", turns)
        c2.metric("Avg Latency(ms)", avg_ms)
        c3.metric("Out Chars", total_chars)

        # ── 최근 응답 원시(간단) (02_data: json)
        if turns:
            st.caption("최근 응답 요약(JSON 느낌)")
            st.json({
                "answer": df.iloc[-1]["answer"],
                "elapsed_ms": df.iloc[-1]["t_ms"],
                "model": df.iloc[-1]["model"],
                "domain": df.iloc[-1]["domain"],
            })

        st.divider()
        # ── 파일 업로드 (요청하신 코드 포함) ───────────────────────────────────
        st.markdown("**📎 파일 업로드**")
        uploaded_file = st.file_uploader("파일을 업로드하세요", type=["txt", "pdf", "png", "jpg"])
        if uploaded_file is not None:
            st.write("파일 이름:", uploaded_file.name)
            st.write("파일 크기:", uploaded_file.size, "bytes")

            # 텍스트 파일 → 미리보기 + 컨텍스트 저장
            if uploaded_file.type == "text/plain":
                # 파일 포인터 주의: 여러 번 읽을 수 있도록 필요 시 seek(0)
                content = uploaded_file.read().decode("utf-8", errors="ignore")
                st.text_area("텍스트 미리보기", content, height=200)
                st.session_state.upload_text = content  # 컨텍스트로 사용
                st.success("이 텍스트는 컨텍스트로 사용됩니다. (사이드바 '업로드 텍스트 사용' 체크 상태)")
            # 이미지 파일 → 미리보기
            elif uploaded_file.type in ("image/png", "image/jpeg"):
                st.image(uploaded_file, caption=uploaded_file.name, use_column_width=True)
                st.info("이미지는 현재 컨텍스트에 자동 주입하지 않습니다.")
            # PDF → 메타 정보만
            elif uploaded_file.type == "application/pdf":
                st.info("PDF 텍스트 추출은 이 예제에 포함되어 있지 않습니다. (RAG 실습에서 확장 가능)")
            else:
                st.warning("지원하지 않는 파일 형식입니다.")

        st.divider()
        st.info("도움말: Domain/Temperature/Streaming, 업로드 텍스트 사용을 바꿔가며 응답 변화를 관찰하세요.")

# ──────────────────────────────────────────────────────────────────────────────
# 4-2) Logs 탭: 누적 로그 테이블 + CSV 다운로드
# ──────────────────────────────────────────────────────────────────────────────
with tab_logs:
    st.subheader("대화 로그")
    df = pd.DataFrame(st.session_state.logs)
    if df.empty:
        st.warning("아직 로그가 없습니다. Chat 탭에서 대화를 시작하세요.")
    else:
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("CSV로 다운로드", data=csv, file_name="chat_logs.csv", mime="text/csv")

# ──────────────────────────────────────────────────────────────────────────────
# 4-3) Charts 탭: Plotly로 지표 시각화
# ──────────────────────────────────────────────────────────────────────────────
with tab_charts:
    st.subheader("세션 지표 시각화 (Plotly)")
    df = pd.DataFrame(st.session_state.logs)
    if df.empty:
        st.info("시각화할 로그가 없습니다.")
    else:
        x = list(range(1, len(df) + 1))

        fig1 = go.Figure(data=go.Scatter(x=x, y=df["t_ms"], mode="lines+markers"))
        fig1.update_layout(title="응답 시간(ms) 추이", xaxis_title="Turn", yaxis_title="ms")
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = go.Figure(data=go.Scatter(x=x, y=df["chars_out"], mode="markers"))
        fig2.update_layout(title="출력 길이(문자 수)", xaxis_title="Turn", yaxis_title="chars_out")
        st.plotly_chart(fig2, use_container_width=True)

        if "tok_out" in df.columns and df["tok_out"].notna().any():
            fig3 = go.Figure(data=go.Bar(x=x, y=df["tok_out"]))
            fig3.update_layout(title="출력 토큰 수(있을 때)", xaxis_title="Turn", yaxis_title="tok_out")
            st.plotly_chart(fig3, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# 5) 보안/배포 메모
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("🔒 보안/배포 체크리스트", expanded=False):
    st.markdown("""
- API Key는 코드에 직접 넣지 말고 **.env** 또는 배포 환경 변수로 관리
- Git 커밋 금지(.gitignore)
- Streamlit Cloud 사용 시 **Secrets** UI에 등록 가능
- 인증이 필요하면 OIDC/프록시 앞단 고려
""")
