# 002_instagram_upload.py

from pathlib import Path
from instagrapi import Client
from PIL import Image
import os

from dotenv import load_dotenv
from openai import OpenAI

# .env 불러오기
load_dotenv()

# ─────────────────────────────────────────────
# 1) Instagram 로그인 정보 (보안상 .env 권장)
# ─────────────────────────────────────────────
INSTAGRAM_USER = os.getenv("IG_USER")
INSTAGRAM_PASS = os.getenv("IG_PASS")

if INSTAGRAM_USER.startswith("your_") or INSTAGRAM_PASS.startswith("your_"):
    raise RuntimeError("👉 먼저 IG_USER / IG_PASS 환경변수를 설정하세요!")

# ─────────────────────────────────────────────
# 2) 이미지 규격 변환 (1080x1080, RGB)
# ─────────────────────────────────────────────
src_path = Path("image_out.jpg")       # 원본 파일
dst_path = Path("new_image_out.jpg")    # 업로드용 파일

image = Image.open(src_path).convert("RGB")
image = image.resize((1080, 1080))    # 정사각 1080px
image.save(dst_path)

print(f"✅ 이미지 저장 완료: {dst_path}")

# ─────────────────────────────────────────────
# 3) Instagram 로그인
# ─────────────────────────────────────────────
cl = Client()

# 세션 재사용 (매번 로그인 방지)
session_file = Path("ig_session.json")
if session_file.exists():
    cl.load_settings(str(session_file))

try:
    cl.login(INSTAGRAM_USER, INSTAGRAM_PASS)
except Exception as e:
    print("⚠️ 로그인 실패 → 다시 로그인 시도:", e)
    cl.set_settings({})
    cl.login(INSTAGRAM_USER, INSTAGRAM_PASS)

# 세션 저장 (다음 실행 때 재사용)
session_file.write_text(str(cl.get_settings()))

print("✅ 로그인 성공")

# ─────────────────────────────────────────────
# 4) 사진 업로드
# ─────────────────────────────────────────────
caption = "🌆 Test Upload via Instagrapi\n#python #instabot #automation"
media = cl.photo_upload(dst_path, caption)

print("✅ 업로드 완료:", media.dict())