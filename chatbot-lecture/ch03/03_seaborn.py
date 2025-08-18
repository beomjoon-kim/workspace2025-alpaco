# 03_chat.py
# Streamlit + Matplotlib + Plotly + Seaborn + AgGrid 통합 예제
# -----------------------------------------------------------------------------
# 설치 (가상환경 권장):
# pip install streamlit pandas numpy matplotlib plotly seaborn streamlit-aggrid python-dotenv
# 실행:
# streamlit run 03_chat.py
# -----------------------------------------------------------------------------

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import plotly.graph_objects as go
import seaborn as sns

from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# ─────────────────────────────────────────────────────────────────────────────
# 0) 페이지 & 테마 설정
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="03: Streamlit + Matplotlib + Plotly + Seaborn + AgGrid",
                   page_icon="📊", layout="wide")
st.title("📊 통합 대시보드: Streamlit × Matplotlib × Plotly × Seaborn × AgGrid")

st.caption("좌측 사이드바에서 데이터셋과 시각화 옵션을 조정해 보세요. "
           "표(AgGrid)에서 행을 선택하면 우측 Plotly 차트에 반영됩니다.")

# ─────────────────────────────────────────────────────────────────────────────
# 1) 데이터셋 로더
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data
def load_dataset(name: str) -> pd.DataFrame:
    if name == "tips (seaborn)":
        df = sns.load_dataset("tips")
        # 범주형 alias 통일
        if "day" in df.columns:
            df.rename(columns={"day": "category"}, inplace=True)
        # 숫자열 추출
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if len(num_cols) >= 1:
            base = df[num_cols[0]].to_numpy()
        else:
            base = np.zeros(len(df))
        size = (np.abs((base - np.nanmean(base)) / (np.nanstd(base) + 1e-9)) * 20 + 10).astype(int)
        df["size"] = size
        return df

    if name == "iris (seaborn)":
        df = sns.load_dataset("iris")
        # species → category
        if "species" in df.columns:
            df.rename(columns={"species": "category"}, inplace=True)
        # size 계산
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        base = df[num_cols[0]].to_numpy()
        size = (np.abs((base - np.nanmean(base)) / (np.nanstd(base) + 1e-9)) * 20 + 10).astype(int)
        df["size"] = size
        return df

    # random
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "category": rng.choice(["A", "B", "C"], size=200),
        "x": rng.integers(1, 50, size=200),
        "y": rng.integers(10, 100, size=200),
        "value": np.round(rng.normal(0, 1, size=200), 2),
    })
    df["size"] = (np.abs(df["value"]) * 20 + 10).astype(int)
    return df

# ─────────────────────────────────────────────────────────────────────────────
# 2) 사이드바: 데이터/옵션
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 옵션")

    dataset_name = st.selectbox("데이터셋 선택", ["tips (seaborn)", "iris (seaborn)", "random"])
    df = load_dataset(dataset_name)

    # 샘플링 (원하는 행 수만큼 사용)
    max_rows = len(df)
    sample_n = st.slider("표시할 행 수", min_value=50 if max_rows >= 50 else 10,
                         max_value=max_rows, value=min(200, max_rows), step=10)
    if sample_n < max_rows:
        df = df.sample(n=sample_n, random_state=42).reset_index(drop=True)

    # 컬럼 목록
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()

    # x/y 컬럼 선택 (수치형)
    default_x = numeric_cols[0] if numeric_cols else None
    default_y = numeric_cols[1] if len(numeric_cols) > 1 else (numeric_cols[0] if numeric_cols else None)
    x_col = st.selectbox("X 축(수치)", numeric_cols, index=numeric_cols.index(default_x) if default_x in numeric_cols else 0)
    y_col = st.selectbox("Y 축(수치)", numeric_cols, index=numeric_cols.index(default_y) if default_y in numeric_cols else 0)

    # hue(색상) 기준
    hue_col = None
    if "category" in df.columns:
        hue_col = "category"
    elif categorical_cols:
        hue_col = st.selectbox("색상 그룹(범주형)", ["(없음)"] + categorical_cols)
        if hue_col == "(없음)":
            hue_col = None

    st.divider()
    st.subheader("AgGrid 설정")
    grid_theme = st.selectbox("테마", ["balham", "alpine", "material", "streamlit"], index=0)
    selection_mode = st.radio("선택 모드", ["multiple", "single"], horizontal=True)
    page_size = st.slider("페이지 크기", 5, 50, 10, 5)

    st.divider()
    st.subheader("보이기/숨기기")
    show_table = st.checkbox("표 (AgGrid)", value=True)
    show_plotly = st.checkbox("Plotly 산점도", value=True)
    show_seaborn = st.checkbox("Seaborn 차트 묶음", value=True)
    show_matplotlib = st.checkbox("Matplotlib 히스토그램", value=True)

# ─────────────────────────────────────────────────────────────────────────────
# 3) 상단 지표
# ─────────────────────────────────────────────────────────────────────────────
top1, top2, top3, top4 = st.columns(4)
with top1:
    st.metric("행 수", len(df))
with top2:
    st.metric("열 수", len(df.columns))
with top3:
    st.metric("수치형 컬럼 수", len(numeric_cols))
with top4:
    st.metric("범주형 컬럼 수", len(categorical_cols))

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# 4) 레이아웃: (좌) 표 - (우) Plotly
# ─────────────────────────────────────────────────────────────────────────────
left_col, right_col = st.columns([7, 8])

selected_df = pd.DataFrame()

# 4-1) AgGrid 표
if show_table:
    with left_col:
        st.subheader("📋 데이터 테이블 (AgGrid)")

        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_default_column(sortable=True, filter=True, resizable=True)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=page_size)
        gb.configure_selection(selection_mode=selection_mode, use_checkbox=(selection_mode=="multiple"))
        gb.configure_side_bar()

        # 컬럼 설정: 수치형은 집계 가능
        for c in numeric_cols:
            gb.configure_column(c, type=["numericColumn"], enableValue=True)

        # 조건부 스타일 예시 (value 음수/양수 색상)
        if "value" in df.columns:
            gb.configure_column(
                "value",
                header_name="value",
                cellStyle={
                    "styleConditions": [
                        {"condition": "params.value < 0", "style": {"color": "white", "backgroundColor": "#d9534f"}},
                        {"condition": "params.value >= 0", "style": {"color": "white", "backgroundColor": "#5cb85c"}},
                    ]
                }
            )

        # category가 있으면 그룹핑 가능
        if "category" in df.columns:
            gb.configure_column("category", enableRowGroup=True)

        grid_options = gb.build()

        grid = AgGrid(
            df,
            gridOptions=grid_options,
            theme=grid_theme,
            height=420,
            fit_columns_on_grid_load=True,
            update_mode=GridUpdateMode.SELECTION_CHANGED
        )
        selected_df = pd.DataFrame(grid.get("selected_rows", []))

        st.caption(f"선택된 행: {len(selected_df)}개")
        # 다운로드
        st.download_button(
            "⬇️ 현재 데이터 CSV 다운로드",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="data.csv",
            mime="text/csv"
        )

# 4-2) Plotly 산점도 (선택 반영)
if show_plotly:
    with right_col:
        st.subheader("📈 Plotly 산점도 (AgGrid 선택 반영)")

        plot_df = selected_df if not selected_df.empty else df

        # 색상 인코딩을 위해 factorize 사용 (범주형 없으면 1색)
        if hue_col and hue_col in plot_df.columns:
            color_vals = pd.factorize(plot_df[hue_col])[0]
            color_text = [f"{hue_col}={v}" for v in plot_df[hue_col].astype(str).tolist()]
        else:
            color_vals = np.zeros(len(plot_df))
            color_text = [""] * len(plot_df)

        # 마커 크기
        size_vals = plot_df["size"].to_numpy() if "size" in plot_df.columns else np.full(len(plot_df), 12)

        fig = go.Figure(
            data=go.Scatter(
                x=plot_df[x_col],
                y=plot_df[y_col],
                mode="markers",
                marker=dict(size=size_vals, color=color_vals),
                text=[f"{x_col}={x}, {y_col}={y} {(' | ' + t) if t else ''}"
                      for x, y, t in zip(plot_df[x_col].tolist(),
                                          plot_df[y_col].tolist(),
                                          color_text)]
            )
        )
        fig.update_layout(
            title=f"Scatter: {x_col} vs {y_col}" + (f" (색상: {hue_col})" if hue_col else ""),
            xaxis_title=x_col,
            yaxis_title=y_col,
            margin=dict(l=10, r=10, t=50, b=10),
        )

        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# 5) Seaborn 차트 묶음
# ─────────────────────────────────────────────────────────────────────────────
if show_seaborn:
    st.subheader("🎨 Seaborn 시각화")

    sns.set_theme(style="whitegrid")

    # 산점도
    st.markdown("**1) 산점도 (scatterplot)**")
    fig1, ax1 = plt.subplots()
    if hue_col and hue_col in df.columns:
        sns.scatterplot(data=df, x=x_col, y=y_col, hue=hue_col, ax=ax1)
    else:
        sns.scatterplot(data=df, x=x_col, y=y_col, ax=ax1)
    st.pyplot(fig1)

    # 박스플롯: category가 있으면 그 기준으로
    st.markdown("**2) 박스플롯 (boxplot)**")
    fig2, ax2 = plt.subplots()
    if "category" in df.columns:
        sns.boxplot(data=df, x="category", y=y_col, ax=ax2)
    else:
        sns.boxplot(data=df[[y_col]], ax=ax2)
        ax2.set_xticklabels([y_col])
    st.pyplot(fig2)

    # 히트맵: 상관행렬
    st.markdown("**3) 히트맵 (상관관계)**")
    fig3, ax3 = plt.subplots()
    corr = df.select_dtypes(include=[np.number]).corr(numeric_only=True)
    sns.heatmap(corr, annot=True, cmap="coolwarm", ax=ax3)
    st.pyplot(fig3)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# 6) Matplotlib 히스토그램
# ─────────────────────────────────────────────────────────────────────────────
if show_matplotlib and numeric_cols:
    st.subheader("📚 Matplotlib 히스토그램")

    col_sel, col_bins = st.columns([2, 1])
    with col_sel:
        hist_col = st.selectbox("히스토그램 대상 컬럼", numeric_cols, index=numeric_cols.index(x_col) if x_col in numeric_cols else 0)
    with col_bins:
        bins = st.slider("bins", min_value=5, max_value=60, value=20, step=5)

    fig_hist, ax_hist = plt.subplots()
    ax_hist.hist(df[hist_col].dropna().to_numpy(), bins=bins)
    ax_hist.set_title(f"Histogram: {hist_col}")
    st.pyplot(fig_hist)

st.caption("© 2025 통합 예제 — Streamlit, Matplotlib, Plotly, Seaborn, AgGrid")
