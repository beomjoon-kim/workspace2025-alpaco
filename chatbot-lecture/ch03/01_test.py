# 01_test.py  — Streamlit 기본 문법을 "상호작용" 중심으로 익히는 예제
# 포인트: 텍스트/마크다운/수식/코드/레이아웃/입력 위젯을 한 화면에서 체험

import time
import numpy as np
import pandas as pd
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# 페이지 메타 & 사이드바
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Streamlit Quick Tour", page_icon="🧭", layout="centered")

with st.sidebar:
    st.header("🔧 실습 옵션")
    username = st.text_input("이름(선택)", placeholder="홍길동")
    demo_speed = st.slider("애니메이션 속도", 0.05, 0.5, 0.15, 0.05)
    show_tips = st.checkbox("학습 팁 표시", value=True)
    st.caption("※ 사이드바 값이 본문 구성에 반영됩니다.")

# ──────────────────────────────────────────────────────────────────────────────
# 헤더 & 인삿말
# ──────────────────────────────────────────────────────────────────────────────
title = "Streamlit 핵심 기능 맛보기"
st.title(f"🧪 {title}")
st.caption("한 파일로 인터랙티브 웹앱을 만드는 법을 5분 만에 익혀봅시다!")

hello = f"{username}님, 환영합니다 👋" if username else "학습자님, 환영합니다 👋"
st.success(hello)

# ──────────────────────────────────────────────────────────────────────────────
# 1) 텍스트 & 마크다운 & 코드 & 수식
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("1) 텍스트 · 마크다운 · 코드 · 수식 보기", expanded=True):
    st.markdown("""
- **굵게**, *기울임*, `인라인 코드`를 섞어 쓸 수 있습니다.
- 체크리스트: 
  - [x] 텍스트
  - [x] 마크다운
  - [x] 코드
  - [x] 수식
""")
    # 예제 코드(문자열 → 하이라이트)
    sample = """\
def greet(name: str) -> str:
    return f"Hello, {name or 'Stranger'}!"

print(greet("Streamlit"))"""
    st.code(sample, language="python")

    st.markdown("---")
    st.markdown("수식(LaTeX) 예시 — **이차방정식 해 공식**:")
    st.latex(r"x=\frac{-b\pm\sqrt{b^2-4ac}}{2a}")

    if show_tips:
        st.info("TIP) 문서형 안내는 `st.markdown`, 코드 하이라이트는 `st.code`, 수식은 `st.latex`를 사용합니다.")

# ──────────────────────────────────────────────────────────────────────────────
# 2) 입력 위젯 → 즉시 반영
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("2) 입력 위젯과 즉시 반영", expanded=True):
    col1, col2, col3 = st.columns(3)

    with col1:
        n = st.number_input("피보나치 길이", min_value=2, max_value=30, value=8, step=1)
    with col2:
        highlight = st.selectbox("강조 색상", ["blue", "green", "red", "violet"], index=0)
    with col3:
        show_code = st.toggle("생성 코드 보기", value=False)

    # 간단한 피보나치 생성
    fib = [0, 1]
    for _ in range(int(n) - 2):
        fib.append(fib[-1] + fib[-2])

    st.markdown(f"**피보나치({n})**: :{highlight}[{fib}]")

    if show_code:
        st.code(
            "fib=[0,1]\nfor _ in range(n-2):\n    fib.append(fib[-1]+fib[-2])\n",
            language="python",
        )

# ──────────────────────────────────────────────────────────────────────────────
# 3) 탭: 표 · 차트 · 상태표시
# ──────────────────────────────────────────────────────────────────────────────
tab_table, tab_chart, tab_status = st.tabs(["📋 표", "📈 차트", "⏳ 상태표시"])

with tab_table:
    df = pd.DataFrame({
        "index": np.arange(len(fib)),
        "value": fib
    })
    st.dataframe(df, use_container_width=True)
    st.metric("마지막 값", value=fib[-1], delta=fib[-1]-fib[-2])
    if show_tips:
        st.caption("`st.dataframe`은 정렬/스크롤 등 인터랙션을 지원합니다.")

with tab_chart:
    st.line_chart(df, x="index", y="value")
    st.caption("간단한 선형 차트 — 데이터가 바뀌면 즉시 갱신됩니다.")

with tab_status:
    st.write("프로그레스/상태 업데이트 예시:")
    prog = st.progress(0, text="준비 중…")
    for i in range(1, 101):
        time.sleep(demo_speed)
        prog.progress(i, text=f"실행 중… {i}%")
    st.success("완료!")

# ──────────────────────────────────────────────────────────────────────────────
# 4) 요약 & 다음 단계
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("다음 단계 제안")
st.markdown("""
1. 사이드바에서 옵션을 바꿔보며 UI 반응을 관찰하세요.
2. 입력 위젯 값을 이용해 **프롬프트**(지시문)를 동적으로 구성해 보세요.
3. 이 파일을 기반으로 OpenAI API를 호출하는 함수만 추가하면,
   간단한 챗 UI까지 빠르게 확장할 수 있습니다.
""")

if show_tips:
    st.warning("TIP) 실제 프로젝트에서는 `.streamlit/secrets.toml` 또는 환경변수로 API Key를 관리하세요.")
