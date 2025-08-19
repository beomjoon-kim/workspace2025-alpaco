import os, urllib
from dotenv import load_dotenv
import openai

print('Dall-E 2 이미지 생성 실습')

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key :
    raise ValueError("❌ OPENAI_API_KEY not found. Please set it in .env file.");
else :
    print("api-key 가져오기 성공!")

# ────────────────────────────────
# 이미지 생성 요청 (DALL·E)
# ────────────────────────────────
response = openai.Image.create(
    prompt="A futuristic city at night",
    n=1,
    size="512x512"
)

# ────────────────────────────────
# 이미지 다운로드 → test.jpg 저장
# ────────────────────────────────
image_url = response['data'][0]['url']
urllib.request.urlretrieve(image_url, "test.jpg")

print("✅ Image saved as test.jpg")