# import openai
# import urllib
# from dotenv import load_dotenv

# # API_KEY = "api key"
# # client = openai.OpenAI(api_key = API_KEY)

# # .env 불러오기
# load_dotenv()
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# response = client.images.generate(
#   model="dall-e-2",
#   prompt="a white siamese cat",
#   size="1024x1024",
#   quality="standard",
#   n=1,
# )
# # size : "256x256", "512x512","1024x1024" 
# # price : 0.016$, 0.018$,0.02$

# image_url = response.data[0].url
# urllib.request.urlretrieve(image_url, "test.jpg")
# print(image_url)


import os, urllib
from dotenv import load_dotenv
from openai import OpenAI

# .env 불러오기
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 프롬프트 작성
prompt = "A futuristic cyberpunk city at night, neon lights, flying cars"

# 이미지 생성 (DALL·E 3)
resp = client.images.generate(
    model="gpt-image-1",   # 최신 DALL·E 3 모델
    prompt=prompt,
    size="1024x1024"
)

# 결과 URL 추출 & 저장
image_url = resp.data[0].url
urllib.request.urlretrieve(image_url, "dalle3_test.jpg")

print("✅ DALL·E 3 이미지 저장 완료:", image_url)