import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# ─────────────────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────────────────
st.set_page_config(page_title="AgGrid + Plotly Demo", page_icon="📊", layout="wide")
st.title("📊 AgGrid로 데이터 테이블 예쁘게 + 선택 연동 Plotly 차트")

# ─────────────────────────────────────────────────────────
# 1) 데모 데이터 준비
# ─────────────────────────────────────────────────────────
np.random.seed(42)
df = pd.DataFrame({
    "category": np.random.choice(["A","B","C"], size=50),
    "x": np.random.randint(1, 10, size=50),
    "y": np.random.randint(10, 100, size=50),
    "value": np.random.randn(50).round(2),
})
df["size"] = (np.abs(df["value"]) * 20 + 10).astype(int)

# ─────────────────────────────────────────────────────────
# 상단: 액션 바
# ─────────────────────────────────────────────────────────
left, right = st.columns([3,1])
with left:
    st.subheader("데이터 테이블")
with right:
    st.download_button("⬇️ CSV 다운로드", data=df.to_csv(index=False).encode("utf-8"),
                       file_name="demo_data.csv", mime="text/csv")

# ─────────────────────────────────────────────────────────
# 2) AgGrid 옵션 구성
# ─────────────────────────────────────────────────────────
gb = GridOptionsBuilder.from_dataframe(df)

# 기본 컬럼 기능
gb.configure_default_column(
    sortable=True, filter=True, resizable=True, editable=False
)

# 페이지네이션 & 선택 모드(체크박스)
gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=10)
gb.configure_selection(selection_mode="multiple", use_checkbox=True)

# 사이드바(열 보이기/그룹/피벗/집계)
gb.configure_side_bar()

# 열별 추가 설정(예: 숫자 포맷, 집계 가능)
gb.configure_column("x", type=["numericColumn"], enableValue=True, header_name="X 값")
gb.configure_column("y", type=["numericColumn"], enableValue=True, header_name="Y 값")
gb.configure_column("value", type=["numericColumn"], enableValue=True, header_name="가중치")
gb.configure_column("size", type=["numericColumn"], enableValue=True, header_name="마커 크기")
gb.configure_column("category", enableRowGroup=True, header_name="카테고리")

grid_options = gb.build()

# ─────────────────────────────────────────────────────────
# 3) AgGrid 렌더링
# ─────────────────────────────────────────────────────────
grid = AgGrid(
    df,
    gridOptions=grid_options,
    theme="balham",  # "streamlit", "balham", "material", "alpine" 등
    height=420,
    fit_columns_on_grid_load=True,
    update_mode=GridUpdateMode.SELECTION_CHANGED  # 선택 시 반응
)

selected = pd.DataFrame(grid["selected_rows"])
st.caption(f"선택된 행: {len(selected)}개")

# ─────────────────────────────────────────────────────────
# 4) 선택 결과 → Plotly 차트로 반영
# ─────────────────────────────────────────────────────────
plot_df = selected if not selected.empty else df  # 선택 없으면 전체 데이터

fig = go.Figure(
    data=go.Scatter(
        x=plot_df["x"],
        y=plot_df["y"],
        mode="markers",
        marker=dict(
            size=plot_df["size"],
            # 색상은 카테고리별 인덱스로 단순 매핑
            color=pd.factorize(plot_df["category"])[0]
        ),
        text=[f"cat={c}, value={v}" for c, v in zip(plot_df["category"], plot_df["value"])]
    )
)
fig.update_layout(
    title="선택한 데이터로 그리는 산점도",
    xaxis_title="X",
    yaxis_title="Y",
    margin=dict(l=10, r=10, t=50, b=10)
)

st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────────
# 5) 선택 요약 카드
# ─────────────────────────────────────────────────────────
st.subheader("선택 요약")
c1, c2, c3, c4 = st.columns(4)
def safe_mean(series):
    return float(series.mean()) if not series.empty else 0.0

with c1:
    st.metric("선택 수", len(plot_df))
with c2:
    st.metric("x 평균", f"{safe_mean(plot_df['x']):.2f}")
with c3:
    st.metric("y 평균", f"{safe_mean(plot_df['y']):.2f}")
with c4:
    st.metric("value 평균", f"{safe_mean(plot_df['value']):.2f}")
