# 00_hello.py

import streamlit as st
import pandas as pd
from numpy.random import default_rng as rng

# 이모지? 사용하자
st.title("👋 Hello, Streamlit 😩")

st.write("이 앱은 Streamlit으로 만든 첫 번째 웹 앱입니다!")

if st.button("버튼 클릭") :
    st.success("버튼이 눌러졌습니다!😩")


df = pd.DataFrame(rng(0).standard_normal((20, 3)), columns=["a", "b", "c"])

st.area_chart(df)