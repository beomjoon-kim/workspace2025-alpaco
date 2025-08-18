# app_chat_dashboard_rag.py
# Chat / Logs / Charts 대시보드 + 업로드 컨텍스트
# + PDF 제목/구역 Chunking → Embedding Index → Query-time Retrieval(RAG)
# + 이미지 OCR, TXT/PDF 텍스트 추출 그대로도 사용 가능
import os, io, time, textwrap, hashlib, json, datetime as dt, re, pathlib
from typing import List, Dict, Any
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI

# ──────────────────────────────────────────────────────────────────────────────
# 추가: PDF / 이미지 OCR 유틸
# ──────────────────────────────────────────────────────────────────────────────
try:
    import pdfplumber  # PDF 텍스트 추출
except Exception:
    pdfplumber = None

try:
    from PIL import Image
    import pytesseract  # 이미지 OCR (시스템에 Tesseract 설치 필요)
except Exception:
    Image = None
    pytesseract = None

# ──────────────────────────────────────────────────────────────────────────────
# 0) 환경설정
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv(find_dotenv())
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
EMBED_MODEL = "text-embedding-3-small"   # 비용↓, 1536-d
GEN_MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-3.5-turbo"]

st.set_page_config(page_title="RAG Chat Dashboard", page_icon="📚", layout="wide")
st.title("📚 PDF 섹션 RAG + Chat Dashboard (Streamlit x OpenAI)")

if not OPENAI_API_KEY or not OPENAI_API_KEY.startswith("sk-"):
    st.error("OPENAI_API_KEY가 설정되어 있지 않습니다. .env 파일을 확인하세요.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# ──────────────────────────────────────────────────────────────────────────────
# 1) Session State
# ──────────────────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "logs" not in st.session_state:
    st.session_state.logs = []
if "sys_prompt" not in st.session_state:
    st.session_state.sys_prompt = textwrap.dedent("""
    You are a helpful assistant.
    - 답을 모르면 모른다고 말합니다.
    - 불확실한 정보는 추측하지 않습니다.
    - 간결하고 단계적으로 설명합니다.
    """)
if "upload_text" not in st.session_state:
    st.session_state.upload_text = ""      # 일반 컨텍스트(텍스트/ocr/pdf full)
if "rag_sections" not in st.session_state:
    st.session_state.rag_sections = []     # [{title, content, page, section_id}]
if "rag_index" not in st.session_state:
    st.session_state.rag_index = None      # {"emb": np.ndarray, "meta": [...]}
if "rag_file_sig" not in st.session_state:
    st.session_state.rag_file_sig = None   # 업로드 PDF 파일 해시(캐시 무결성용)

# ──────────────────────────────────────────────────────────────────────────────
# 2) 사이드바
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("⚙️ Settings")
    model = st.selectbox("Model", options=GEN_MODELS, index=0)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.3, 0.1)
    domain = st.radio("Domain(역할 프리셋)", ["일반", "여행추천", "식단코치", "학습튜터"], index=0)
    streaming = st.toggle("🔴 Streaming 모드", value=True)
    st.divider()

    st.markdown("**컨텍스트 옵션**")
    use_uploaded = st.checkbox("업로드 텍스트 단순 주입(원본)", value=True)
    ctx_limit = st.number_input("단순 컨텍스트 최대 길이(문자)", min_value=500, max_value=20000, value=4000, step=500)

    st.markdown("**RAG 옵션(PDF)**")
    use_rag = st.checkbox("PDF 섹션 RAG 사용", value=True)
    top_k = st.number_input("RAG Top-K", min_value=1, max_value=10, value=4, step=1)
    rag_ctx_limit = st.number_input("RAG 컨텍스트 최대 길이(문자)", min_value=500, max_value=20000, value=5000, step=500)

    st.caption("RAG와 단순 주입은 함께 사용할 수 있습니다. (프롬프트에 [RAG] 블록, [CONTEXT] 블록 순으로 추가)")

DOMAIN_GUIDE = {
    "일반": "",
    "여행추천": "여행플래너 역할로, 2~3개 후보 일정과 장단점을 제시합니다.",
    "식단코치": "영양 코치 역할로, 알레르기/선호를 질문하고 1일 식단을 제시합니다.",
    "학습튜터": "학습 튜터 역할로, 예제→설명→퀴즈→요약 순서로 가르칩니다.",
}
sys_prompt = st.session_state.sys_prompt + ("\n" + DOMAIN_GUIDE.get(domain, ""))

# ──────────────────────────────────────────────────────────────────────────────
# 3) 업로드 파일 텍스트 추출
# ──────────────────────────────────────────────────────────────────────────────
def extract_text_from_upload(uploaded_file) -> str:
    """
    업로드된 파일에서 텍스트 추출
    - text/plain: UTF-8 디코드
    - application/pdf: pdfplumber로 텍스트 추출
    - image/*: pytesseract로 OCR (기본 en, 한국어 kor 옵션)
    """
    if uploaded_file is None:
        return ""

    mime = uploaded_file.type or ""
    name = getattr(uploaded_file, "name", "uploaded")

    try:
        if mime == "text/plain":
            uploaded_file.seek(0)
            return uploaded_file.read().decode("utf-8", errors="ignore")

        if mime == "application/pdf":
            if not pdfplumber:
                st.warning("pdfplumber가 설치되어 있지 않아 PDF 텍스트를 추출하지 못했습니다.")
                return ""
            uploaded_file.seek(0)
            text_chunks = []
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    if text.strip():
                        text_chunks.append(text)
            return "\n\n".join(text_chunks).strip()

        if mime in ("image/png", "image/jpeg"):
            if not (Image and pytesseract):
                st.warning("Pillow/pytesseract가 없어서 이미지 OCR을 수행할 수 없습니다.")
                return ""
            uploaded_file.seek(0)
            img = Image.open(uploaded_file)

            # OCR 언어 선택
            # 한국어 데이터(kor.traineddata)가 설치되어 있으면 한국어 OCR 시도
            try:
                text = pytesseract.image_to_string(img, lang="kor+eng")
            except Exception:
                text = pytesseract.image_to_string(img)  # fallback: 영어만
            return text

    except Exception as e:
        st.warning(f"파일 텍스트 추출 중 오류: {e}")

    st.info(f"미지원 파일 형식 또는 텍스트를 찾지 못함: {name} ({mime})")
    return ""

# ──────────────────────────────────────────────────────────────────────────────
# 4) PDF → 섹션 Chunking (제목/구역 단위)
#    - 단순 텍스트 기반 규칙: 번호형 제목, 대문자/Title Case, 빈줄 기준 등
#    - 실패 시 문장 단위 슬라이딩 윈도우로 보수적으로 분할
# ──────────────────────────────────────────────────────────────────────────────
HEADING_PATTERNS = [
    r"^\s*\d+(\.\d+)*\s+.+",          # 1 / 1.1 / 2.3.4 형태
    r"^\s*[IVXLCM]+\.\s+.+",          # 로마숫자. Title
    r"^\s*[A-Z][A-Z\s\-:]{4,}$",      # 전부 대문자 계열 제목
]

def naive_split_sections(full_text: str) -> List[Dict[str, Any]]:
    lines = full_text.splitlines()
    sections = []
    cur_title = "Introduction"
    cur_buf = []
    cur_start_page = None  # 텍스트 추출 방식에선 정확 페이지 매핑 어려움 → None 처리

    def flush():
        if cur_buf:
            sections.append({
                "title": cur_title.strip(),
                "content": "\n".join(cur_buf).strip(),
                "page": cur_start_page,
            })

    heading_regex = re.compile("|".join(HEADING_PATTERNS), flags=re.IGNORECASE)

    for ln in lines:
        if heading_regex.match(ln.strip()):
            # 새 섹션 시작
            if cur_buf:
                flush()
                cur_buf = []
            cur_title = ln.strip()
        else:
            cur_buf.append(ln)
    # 마지막 섹션 flush
    flush()

    # 섹션이 너무 적거나 제목 감지가 실패하면, 문장 슬라이딩 윈도우로 분할
    if len(sections) <= 1:
        sections = []
        sents = re.split(r"(?<=[\.\?\!])\s+", full_text)
        win = 8              # 문장 8개 정도씩
        stride = 6           # 겹치게
        for i in range(0, len(sents), stride):
            chunk = " ".join(sents[i:i+win]).strip()
            if len(chunk) > 100:
                sections.append({
                    "title": f"Chunk {i//stride+1}",
                    "content": chunk,
                    "page": None,
                })
    # section_id 부여
    for idx, s in enumerate(sections, start=1):
        s["section_id"] = idx
    return sections

# ──────────────────────────────────────────────────────────────────────────────
# 5) Embedding Index (로컬 캐시)
# ──────────────────────────────────────────────────────────────────────────────
CACHE_DIR = pathlib.Path(".rag_cache")
CACHE_DIR.mkdir(exist_ok=True)

def file_signature(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()

def build_rag_index(sections: List[Dict[str, Any]], cache_key: str):
    """sections → 임베딩 배열(np.float32) + 메타데이터 리스트"""
    texts = [f"{s['title']}\n{s['content']}" for s in sections]
    # 임베딩 호출
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    emb = np.array([e.embedding for e in resp.data], dtype=np.float32)
    meta = [{"title": s["title"], "page": s["page"], "section_id": s["section_id"], "n_chars": len(s["content"])} for s in sections]

    # 캐시 저장
    np.save(CACHE_DIR / f"{cache_key}.npy", emb)
    with open(CACHE_DIR / f"{cache_key}.json", "w", encoding="utf-8") as f:
        json.dump({"meta": meta}, f, ensure_ascii=False)
    return {"emb": emb, "meta": meta}

def load_rag_index(cache_key: str):
    npy = CACHE_DIR / f"{cache_key}.npy"
    jsn = CACHE_DIR / f"{cache_key}.json"
    if npy.exists() and jsn.exists():
        emb = np.load(npy)
        meta = json.loads(jsn.read_text(encoding="utf-8"))["meta"]
        return {"emb": emb, "meta": meta}
    return None

def ensure_rag_index(pdf_bytes: bytes, sections: List[Dict[str, Any]]):
    sig = file_signature(pdf_bytes)
    cached = load_rag_index(sig)
    if cached:
        return sig, cached
    built = build_rag_index(sections, sig)
    return sig, built

def embed_query(q: str) -> np.ndarray:
    v = client.embeddings.create(model=EMBED_MODEL, input=[q]).data[0].embedding
    return np.array(v, dtype=np.float32)

def cosine_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_n = a / (np.linalg.norm(a, axis=-1, keepdims=True) + 1e-8)
    b_n = b / (np.linalg.norm(b, axis=-1, keepdims=True) + 1e-8)
    return np.dot(a_n, b_n.T)

def retrieve_sections(query: str, index: Dict[str, Any], sections: List[Dict[str, Any]], k: int = 4):
    if not index or "emb" not in index:
        return []
    qv = embed_query(query)
    sims = cosine_sim(qv.reshape(1, -1), index["emb"]).ravel()
    top_idx = np.argsort(-sims)[:k]
    items = []
    for i in top_idx:
        meta = index["meta"][i]
        sec = next((s for s in sections if s["section_id"] == meta["section_id"]), None)
        if not sec:
            continue
        items.append({
            "score": float(sims[i]),
            "title": meta["title"],
            "page": meta["page"],
            "content": sec["content"],
            "section_id": meta["section_id"],
        })
    return items

# ──────────────────────────────────────────────────────────────────────────────
# 6) 상단 가이드
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("📘 시스템 가이드 & 샘플 표시", expanded=False):
    st.markdown("""
- **PDF 업로드 후 [RAG 빌드]** 버튼을 누르면 *제목/구역* 단위로 분할→임베딩 색인합니다.
- 질문 시 Top-K 유사 섹션을 찾아 **[RAG]** 블록으로 프롬프트에 자동 삽입합니다.
- 동시에 TXT/PDF/이미지에서 추출한 **원본 텍스트 전체**를 **[CONTEXT]** 블록으로 일부(문자 한도) 덧붙일 수도 있습니다.
""")
    st.code("def few_shot_rule():\n    return '간결하게, 단계별로, 예시와 함께 설명'\n", language="python")
    st.latex(r"x=\frac{-b\pm\sqrt{b^2-4ac}}{2a}")

# ──────────────────────────────────────────────────────────────────────────────
# 7) 탭: Chat / Logs / Charts
# ──────────────────────────────────────────────────────────────────────────────
tab_chat, tab_logs, tab_charts = st.tabs(["💬 Chat", "🧾 Logs", "📈 Charts"])

# ──────────────────────────────────────────────────────────────────────────────
# 7-1) Chat 탭
# ──────────────────────────────────────────────────────────────────────────────
with tab_chat:
    col_left, col_right = st.columns([2, 1])

    with col_right:
        st.subheader("업로드 & RAG")
        uploaded_file = st.file_uploader("📎 TXT/PDF/PNG/JPG 업로드", type=["txt", "pdf", "png", "jpg", "jpeg"])
        pdf_bytes = None

        if uploaded_file is not None:
            st.write("파일:", uploaded_file.name, f"({uploaded_file.type}, {uploaded_file.size} bytes)")
            # 1) 원본 텍스트 추출(단순 컨텍스트 주입용)
            extracted = extract_text_from_upload(uploaded_file).strip()
            if extracted:
                st.text_area("추출 텍스트(미리보기)", extracted[:2000] + ("\n...[more]" if len(extracted) > 2000 else ""), height=180)
                st.session_state.upload_text = extracted
                st.success("단순 컨텍스트 준비 완료")

            # 2) RAG: PDF만 섹션 분할 대상
            if (uploaded_file.type or "") == "application/pdf":
                uploaded_file.seek(0)
                pdf_bytes = uploaded_file.read()
                # 섹션 상태 초기화
                st.session_state.rag_sections = []
                st.session_state.rag_index = None
                st.session_state.rag_file_sig = None

                if st.button("🧩 RAG 빌드 (PDF 섹션 분할 → 임베딩 색인)"):
                    # 텍스트 기반 섹션 분할
                    if not extracted:
                        st.error("PDF 텍스트 추출에 실패했습니다.")
                    else:
                        sections = naive_split_sections(extracted)
                        if not sections:
                            st.error("섹션을 생성하지 못했습니다.")
                        else:
                            sig, index = ensure_rag_index(pdf_bytes, sections)
                            st.session_state.rag_sections = sections
                            st.session_state.rag_index = index
                            st.session_state.rag_file_sig = sig
                            st.success(f"RAG 빌드 완료: {len(sections)}개 섹션, 임베딩 {index['emb'].shape}")

            # 가이드
            if pdfplumber is None:
                st.info("PDF 텍스트 추출을 사용하려면 `pip install pdfplumber` 후 앱을 재시작하세요.")
            if pytesseract is None or Image is None:
                st.info("이미지 OCR을 사용하려면 `pip install pillow pytesseract` + Tesseract 설치 필요")

        st.divider()

        # 최근 응답 KPI/원시 요약
        df = pd.DataFrame(st.session_state.logs)
        turns = len(df)
        avg_ms = int(df["t_ms"].mean()) if turns else 0
        total_chars = int(df["chars_out"].sum()) if turns else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Turns", turns)
        c2.metric("Avg Latency(ms)", avg_ms)
        c3.metric("Out Chars", total_chars)

        if turns:
            st.caption("최근 응답 요약")
            st.json({
                "answer": df.iloc[-1]["answer"],
                "elapsed_ms": df.iloc[-1]["t_ms"],
                "model": df.iloc[-1]["model"],
                "domain": df.iloc[-1]["domain"],
            })

    with col_left:
        st.subheader("대화")

        # 과거 메시지
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        # 입력 및 응답
        if prompt := st.chat_input("질문을 입력하세요 (PDF RAG + 단순 컨텍스트 지원)"):
            # 사용자 메시지 표시/저장
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # ── 프롬프트 합성: [SYSTEM] + [RAG] + [CONTEXT] + [USER] ───────────
            rag_block = ""
            retrieved_items = []
            if use_rag and st.session_state.rag_index is not None and st.session_state.rag_sections:
                retrieved_items = retrieve_sections(prompt, st.session_state.rag_index, st.session_state.rag_sections, k=top_k)
                if retrieved_items:
                    # 길이 제한 내에서 정리
                    pieces = []
                    acc_len = 0
                    limit = int(rag_ctx_limit)
                    for it in retrieved_items:
                        head = f"### {it['title']} (sec:{it['section_id']}{', p.'+str(it['page']) if it['page'] else ''})\n"
                        body = it["content"].strip()
                        chunk_text = head + body + "\n"
                        if acc_len + len(chunk_text) > limit:
                            chunk_text = (head + body)[: max(0, limit-acc_len)] + "\n...[truncated]"
                            pieces.append(chunk_text)
                            break
                        pieces.append(chunk_text)
                        acc_len += len(chunk_text)
                    rag_block = "\n[RAG]\n" + "\n---\n".join(pieces) + "\n"

            context_block = ""
            if use_uploaded and st.session_state.upload_text.strip():
                ctx = st.session_state.upload_text.strip()
                if len(ctx) > ctx_limit:
                    ctx = ctx[:ctx_limit] + "\n...[truncated]"
                context_block = f"\n[CONTEXT]\n{ctx}\n"

            composed = f"[SYSTEM]\n{sys_prompt}{rag_block}{context_block}\n[USER]\n{prompt}"

            # ── 호출
            start = time.perf_counter()
            try:
                if streaming:
                    with st.chat_message("assistant"):
                        placeholder = st.empty()
                        chunks = []
                        with client.responses.stream(
                            model=model,
                            input=composed,
                            temperature=temperature,
                        ) as stream:
                            for event in stream:
                                if event.type == "response.output_text.delta":
                                    chunks.append(event.delta)
                                    placeholder.markdown("".join(chunks))
                            stream.until_done()
                        answer = "".join(chunks) or "(응답 없음)"
                else:
                    resp = client.responses.create(model=model, input=composed, temperature=temperature)
                    answer = getattr(resp, "output_text", None) or str(resp)
                    with st.chat_message("assistant"):
                        st.markdown(answer)

                dur_ms = int((time.perf_counter() - start) * 1000)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.session_state.logs.append({
                    "ts": dt.datetime.now().isoformat(timespec="seconds"),
                    "model": model,
                    "domain": domain,
                    "temp": temperature,
                    "chars_in": len(prompt),
                    "chars_out": len(answer),
                    "t_ms": dur_ms,
                    "tok_in": None,
                    "tok_out": None,
                    "answer": answer,
                    "question": prompt,
                })

                # RAG 매칭 결과 표로 표시
                if retrieved_items:
                    st.markdown("**🔎 RAG 매칭 섹션 (유사도 높은 순)**")
                    show = []
                    for it in retrieved_items:
                        show.append({
                            "score": round(it["score"], 4),
                            "section_id": it["section_id"],
                            "title": it["title"],
                            "page": it["page"],
                            "chars": len(it["content"]),
                        })
                    st.dataframe(pd.DataFrame(show), use_container_width=True)

            except Exception as e:
                with st.chat_message("assistant"):
                    st.error(f"OpenAI 호출 실패: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# 7-2) Logs
# ──────────────────────────────────────────────────────────────────────────────
with tab_logs:
    st.subheader("대화 로그")
    df = pd.DataFrame(st.session_state.logs)
    if df.empty:
        st.warning("아직 로그가 없습니다. Chat 탭에서 대화를 시작하세요.")
    else:
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("CSV로 다운로드", data=csv, file_name="chat_logs.csv", mime="text/csv")

# ──────────────────────────────────────────────────────────────────────────────
# 7-3) Charts
# ──────────────────────────────────────────────────────────────────────────────
with tab_charts:
    st.subheader("세션 지표 시각화 (Plotly)")
    df = pd.DataFrame(st.session_state.logs)
    if df.empty:
        st.info("시각화할 로그가 없습니다.")
    else:
        x = list(range(1, len(df) + 1))
        fig1 = go.Figure(data=go.Scatter(x=x, y=df["t_ms"], mode="lines+markers"))
        fig1.update_layout(title="응답 시간(ms) 추이", xaxis_title="Turn", yaxis_title="ms")
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = go.Figure(data=go.Scatter(x=x, y=df["chars_out"], mode="markers"))
        fig2.update_layout(title="출력 길이(문자 수)", xaxis_title="Turn", yaxis_title="chars_out")
        st.plotly_chart(fig2, use_container_width=True)

# ──────────────────────────────────────────────────────────────────────────────
# 8) 보안/배포 메모
# ──────────────────────────────────────────────────────────────────────────────
with st.expander("🔒 보안/배포 체크리스트", expanded=False):
    st.markdown("""
- API Key는 코드에 직접 넣지 말고 **.env** 또는 배포 환경 변수로 관리
- Git 커밋 금지(.gitignore)
- Streamlit Cloud 사용 시 **Secrets** UI에 등록 가능
- 인증이 필요하면 OIDC/프록시 앞단 고려
""")
