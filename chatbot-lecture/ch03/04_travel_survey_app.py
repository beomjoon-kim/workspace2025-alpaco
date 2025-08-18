import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="여행 설문 미니 앱", page_icon="🧳", layout="centered")
st.title("🧳 여행 설문 미니 앱")
st.caption("간단 설문을 제출하면 결과 요약과 CSV 다운로드를 제공합니다.")

# ──────────────────────────────────────────────────────────────────────────────
# Session State 초기화: 설문 응답 누적/초기화용
# ──────────────────────────────────────────────────────────────────────────────
if "responses" not in st.session_state:
    st.session_state.responses = []  # 각 응답: dict로 저장

# ──────────────────────────────────────────────────────────────────────────────
# 1) 설문 폼
# - form을 쓰면 입력 도중에는 앱이 재실행되지 않고, submit 시점에만 제출/검증됩니다.
# ──────────────────────────────────────────────────────────────────────────────
with st.form(key="travel_survey"):
    st.subheader("1. 기본 정보")
    name = st.text_input("이름 (선택)", placeholder="홍길동")
    mbti = st.radio(
        "MBTI",
        ("ISTJ", "ENFP", "선택지 없음"),
        horizontal=True,
        index=2
    )

    st.divider()
    st.subheader("2. 여행 선호")
    destination = st.text_input("가고 싶은 여행지*", placeholder="예: 오키나와 / 파리 / 부산")
    travel_dates = st.date_input("여행 날짜(단일 또는 범위)", value=[date.today()])
    companions = st.multiselect("함께 가는 사람", ["혼자", "가족", "친구", "연인", "동료"])
    activities = st.multiselect(
        "관심 활동",
        ["맛집탐방", "자연/트레킹", "해변/휴양", "박물관/전시", "쇼핑", "액티비티"]
    )

    st.divider()
    st.subheader("3. 기타")
    budget = st.slider("1인 예상 예산(만원)", min_value=10, max_value=500, value=80, step=10)
    fruits = st.multiselect(
        "좋아하는 과일(선택)",
        ["망고", "오렌지", "사과", "바나나"],
        default=["망고", "오렌지"]
    )
    agree = st.checkbox("개인정보 수집·이용에 동의합니다.*")

    submitted = st.form_submit_button("설문 제출", use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# 2) 검증 & 제출 처리
# ──────────────────────────────────────────────────────────────────────────────
def normalize_dates(value):
    """date_input가 단일/범위 모두 가능하므로 문자열로 일관되게 정리"""
    if isinstance(value, list) and len(value) == 2:
        return f"{value[0]} ~ {value[1]}"
    elif isinstance(value, list) and len(value) == 1:
        return str(value[0])
    elif isinstance(value, date):
        return str(value)
    return ""

if submitted:
    errors = []
    if not destination.strip():
        errors.append("여행지는 필수입니다.")
    if not agree:
        errors.append("개인정보 수집·이용에 동의가 필요합니다.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        record = {
            "이름": name or "(미입력)",
            "MBTI": mbti,
            "여행지": destination.strip(),
            "여행날짜": normalize_dates(travel_dates),
            "동행": ", ".join(companions) if companions else "(없음)",
            "활동": ", ".join(activities) if activities else "(미선택)",
            "예산(만원)": budget,
            "좋아하는 과일": ", ".join(fruits) if fruits else "(미선택)",
        }
        st.session_state.responses.append(record)
        st.success("설문이 정상적으로 제출되었습니다! 아래에서 결과 요약을 확인하세요.")

# ──────────────────────────────────────────────────────────────────────────────
# 3) 결과 요약(개별 제출 + 누적 통계) & CSV 다운로드
# ──────────────────────────────────────────────────────────────────────────────
if len(st.session_state.responses) == 0:
    st.info("아직 제출된 설문이 없습니다. 폼을 작성하고 **설문 제출** 버튼을 눌러주세요.")
else:
    st.markdown("---")
    st.subheader("🧾 최신 제출 요약")

    latest = st.session_state.responses[-1]
    col1, col2 = st.columns(2)
    with col1:
        st.metric("여행지", latest["여행지"])
        st.metric("MBTI", latest["MBTI"])
        st.metric("예산(만원)", latest["예산(만원)"])
    with col2:
        st.markdown(f"**여행 날짜**: `{latest['여행날짜']}`")
        st.markdown(f"**동행**: `{latest['동행']}`")
        st.markdown(f"**관심 활동**: `{latest['활동']}`")
        st.markdown(f"**좋아하는 과일**: `{latest['좋아하는 과일']}`")

    # 누적 응답 테이블
    st.markdown("### 📋 누적 응답")
    df = pd.DataFrame(st.session_state.responses)
    st.dataframe(df, use_container_width=True)

    # 간단 통계(Top 여행지/활동)
    st.markdown("### 📈 간단 통계")
    c1, c2 = st.columns(2)
    with c1:
        top_dest = (
            df["여행지"].value_counts()
            .rename_axis("여행지")
            .reset_index(name="응답수")
        )
        st.caption("Top 여행지")
        st.table(top_dest.head(5))
    with c2:
        # 활동은 콤마 문자열 → explode
        if df["활동"].notna().any():
            acts = (
                df.assign(활동=df["활동"].str.split(", "))
                  .explode("활동")
            )
            acts = acts[acts["활동"].notna() & (acts["활동"] != "(미선택)")]
            if not acts.empty:
                top_act = acts["활동"].value_counts().rename_axis("활동").reset_index(name="응답수")
                st.caption("Top 활동")
                st.table(top_act.head(5))
            else:
                st.info("활동 통계를 계산할 데이터가 없습니다.")
        else:
            st.info("활동 통계를 계산할 데이터가 없습니다.")

    # CSV 다운로드
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 누적 응답 CSV 다운로드",
        data=csv,
        file_name="travel_survey_responses.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # 초기화 버튼
    st.markdown("### ⚙️ 관리")
    if st.button("응답 초기화(모두 삭제)"):
        st.session_state.responses = []
        st.warning("응답이 초기화되었습니다. 상단 폼에서 다시 제출해 주세요.")
        st.rerun()

