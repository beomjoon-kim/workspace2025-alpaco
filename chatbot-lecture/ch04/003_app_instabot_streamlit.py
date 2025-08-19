# 003_app_instabot_streamlit.py
# Streamlit: Instagram 캡션 생성 + 이미지 생성(DALL·E 2 기본) + 업로드(instagrapi)

import os, io, time, urllib
from pathlib import Path

import streamlit as st
from PIL import Image
from instagrapi import Client

import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI 최신 SDK 사용을 권장합니다.
# pip install -U openai
try:
    from openai import OpenAI
except Exception:
    st.error("OpenAI SDK 불일치: 'pip install -U openai'로 1.x 이상 설치하세요.")
    st.stop()

# googletrans는 충돌이 잦아 폴백 처리
try:
    from googletrans import Translator
    _translator = Translator()
except Exception:
    _translator = None


# ─────────────────────────────────────────────────────────
# 유틸: 한국어 → 영어 번역 (googletrans 없거나 실패 시 원문 반환)
# ─────────────────────────────────────────────────────────
def google_trans(text: str) -> str:
    if not text:
        return ""
    if _translator is None:
        return text  # 폴백
    try:
        return _translator.translate(text, dest="en").text
    except Exception:
        return text  # 폴백


# ─────────────────────────────────────────────────────────
# 캡션 생성 (Chat Completions)
# ─────────────────────────────────────────────────────────
def gen_caption(topic: str, mood: str, apikey: str) -> str:
    client = OpenAI(api_key=apikey)
    prompt = f"""Write a Korean Instagram caption.
- topic: {topic}
- mood: {mood}
Include emojis and good hashtags. Break lines for readability."""

    # 최신 SDK에서도 chat.completions.create 사용 가능
    res = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"system","content":prompt}],
        temperature=0.7,
    )
    return res.choices[0].message.content.strip()


# ─────────────────────────────────────────────────────────
# 이미지 생성 (기본: DALL·E 2)  — DALL·E 3(gpt-image-1)은 조직 인증 필요할 수 있음
# ─────────────────────────────────────────────────────────
def gen_image(topic: str, mood: str, apikey: str, size: str = "1024x1024",
              try_gpt_image_1: bool = False) -> str:
    """
    반환: 저장된 로컬 파일 경로 (instaimg.jpg)
    """
    
    # client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    client = OpenAI(api_key=apikey)

    t_topic, t_mood = google_trans(topic), google_trans(mood)
    prompt = f"Draw picture about {t_topic}. Picture mood is {t_mood}."

    def _call(model_name: str):
        return client.images.generate(model=model_name, prompt=prompt, size=size, n=1)

    # 우선순위: 사용자가 원하면 gpt-image-1 시도 → 실패 시 dall-e-2
    resp = None
    if try_gpt_image_1:
        try:
            resp = _call("gpt-image-1")
        except Exception as e:
            # 권한 문제(403) 등 → DALL·E 2로 폴백
            print("gpt-image-1 실패 → dall-e-2로 폴백:", e)

    if resp is None:
        resp = _call("dall-e-2")

    url = resp.data[0].url
    out_path = "instaimg.jpg"
    urllib.request.urlretrieve(url, out_path)
    return out_path


# ─────────────────────────────────────────────────────────
# 인스타 업로드
# ─────────────────────────────────────────────────────────
def ig_upload(image_path: str, caption: str, user: str, pwd: str,
              session_json: str = "ig_session.json") -> dict:
    """
    이미지 1080x1080 RGB로 변환 후 업로드
    반환: 업로드 media 객체의 dict
    """
    # 1080 정사각 변환
    im = Image.open(image_path).convert("RGB").resize((1080, 1080))
    resized = "instaimg_resize.jpg"
    im.save(resized, quality=95)

    cl = Client()

    # 세션 재사용
    sess = Path(session_json)
    if sess.exists():
        try:
            cl.load_settings(str(sess))
        except Exception:
            pass

    try:
        cl.login(user, pwd)
    except Exception:
        # 세션 깨졌을 때 재로그인
        cl.set_settings({})
        cl.login(user, pwd)

    # 세션 저장
    try:
        sess.write_text(str(cl.get_settings()))
    except Exception:
        pass

    media = cl.photo_upload(Path(resized), caption)
    return media.dict()


# ─────────────────────────────────────────────────────────
# Streamlit App
# ─────────────────────────────────────────────────────────
st.set_page_config(page_title="📸 AI Instagram Bot", page_icon="📸", layout="centered")
st.title("📸 AI Instagram Bot")

with st.sidebar:
    st.subheader("🔑 Keys / 로그인")
    # OpenAI Key: st.secrets 또는 환경변수 → 없으면 입력받기
    # openai_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        openai_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")

    # ig_user = st.secrets.get("IG_USER", os.getenv("IG_USER", ""))
    # ig_pass = st.secrets.get("IG_PASS", os.getenv("IG_PASS", ""))
    ig_user = os.getenv("IG_USER")
    ig_pass = os.getenv("IG_PASS")
    ig_user = st.text_input("Instagram ID", value=ig_user or "")
    ig_pass = st.text_input("Instagram Password", value=ig_pass or "", type="password")

    st.divider()
    st.subheader("⚙️ 옵션")
    size = st.selectbox("이미지 크기", ["512x512", "1024x1024"], index=1)
    try_gpt_image_1 = st.checkbox("DALL·E 3 (gpt-image-1) 시도", value=False,
                                  help="조직 인증이 안 되어 있으면 자동으로 DALL·E 2로 폴백합니다.")

# 입력 UI
st.markdown("### 📝 게시글 정보")
col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("포스팅 주제", placeholder="예: 부산 야경, 바다, 야외 카페")
with col2:
    mood = st.text_input("분위기/톤", placeholder="예: 따뜻한, 감성적인, 레트로")

gen_btn = st.button("1) 캡션 + 이미지 생성")
st.markdown("---")

# 세션 상태
if "caption" not in st.session_state:
    st.session_state.caption = ""
if "image_path" not in st.session_state:
    st.session_state.image_path = ""

# 생성 버튼
if gen_btn:
    if not (openai_key and openai_key.startswith("sk-")):
        st.error("OpenAI API Key가 필요합니다.")
    elif not topic:
        st.error("포스팅 주제를 입력하세요.")
    else:
        with st.spinner("캡션 생성 중..."):
            try:
                cap = gen_caption(topic, mood, openai_key)
                st.session_state.caption = cap
            except Exception as e:
                st.error(f"캡션 생성 실패: {e}")

        with st.spinner("이미지 생성 중..."):
            try:
                img_path = gen_image(topic, mood, openai_key, size=size, try_gpt_image_1=try_gpt_image_1)
                st.session_state.image_path = img_path
            except Exception as e:
                st.error(f"이미지 생성 실패: {e}")

# 미리보기 & 수정
if st.session_state.image_path or st.session_state.caption:
    st.markdown("### 👀 미리보기 / 수정")
    if st.session_state.image_path and Path(st.session_state.image_path).exists():
        st.image(st.session_state.image_path, caption="Generated Image", use_column_width=True)
    st.session_state.caption = st.text_area("캡션(수정 가능)", value=st.session_state.caption, height=180)

    # 업로드 버튼
    uploaded = st.button("2) 인스타그램 업로드")
    if uploaded:
        if not ig_user or not ig_pass:
            st.error("Instagram ID/Password를 입력하세요. (사이드바)")
        elif not st.session_state.image_path:
            st.error("이미지가 없습니다. 먼저 이미지를 생성하세요.")
        else:
            with st.spinner("인스타그램 업로드 중... (2FA/보안정책으로 실패할 수 있음)"):
                try:
                    info = ig_upload(st.session_state.image_path, st.session_state.caption, ig_user, ig_pass)
                    st.success("업로드 완료!")
                    st.json(info)
                except Exception as e:
                    st.error(f"업로드 실패: {e}")

st.caption("※ 보안상 Key/계정정보는 코드에 하드코딩하지 말고 st.secrets 또는 환경변수(.env)로 관리하세요.")