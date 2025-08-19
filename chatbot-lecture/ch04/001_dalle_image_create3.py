import os, urllib, base64
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from openai import PermissionDeniedError  # 403 처리용

# 1) 키 로드
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY가 없습니다. .env를 확인하세요.")

client = OpenAI(api_key=api_key)

def save_from_url(url: str, out_path: str):
    urllib.request.urlretrieve(url, out_path)
    return out_path

def save_from_b64(b64_data: str, out_path: str):
    img_bytes = base64.b64decode(b64_data)
    Path(out_path).write_bytes(img_bytes)
    return out_path

def generate_image(prompt: str, size: str = "1024x1024", prefer_b64: bool = False) -> str:
    """
    1) gpt-image-1 시도
    2) 403(권한없음) 발생 시 dall-e-2로 폴백
    반환: 저장된 로컬 파일 경로
    """
    out = "image_out.png"  # 확장자는 임의, b64 저장이면 png 권장

    def _call(model_name: str):
        return client.images.generate(
            model=model_name,
            prompt=prompt,
            size=size,
            # prefer_b64=True면 b64로 받기 (방화벽/직접 저장 시 유용)
            **({"response_format": "b64_json"} if prefer_b64 else {})
        )

    try:
        # 1) DALL·E 3 (조직 인증 필요)
        resp = _call("gpt-image-1")
    except PermissionDeniedError as e:
        # 2) 권한 문제 → DALL·E 2로 폴백
        print("⚠️ gpt-image-1 권한 없음 → dall-e-2로 폴백합니다.")
        resp = _call("dall-e-2")

    # 저장 처리 (URL 또는 b64)
    if prefer_b64:
        b64 = resp.data[0].b64_json
        return save_from_b64(b64, out)
    else:
        url = resp.data[0].url
        # 확장자 jpg로 저장하고 싶다면 아래 라인 수정
        return save_from_url(url, "image_out.jpg")

# 사용 예시
if __name__ == "__main__":
    prompt = "A futuristic cyberpunk city at night, neon lights, flying cars"
    path = generate_image(prompt, size="1024x1024", prefer_b64=False)
    print(f"✅ 이미지 저장 완료: {path}")