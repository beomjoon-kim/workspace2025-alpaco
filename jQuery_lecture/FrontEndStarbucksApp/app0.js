// app.js
const express = require('express');
const path = require('path');
const fs = require('fs');
const multer = require('multer');
const session = require('express-session');

const app = express();
const PORT = 3000;

// 1) View 엔진 & 정적 파일
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));
// /upload 경로로 업로드 폴더 정적 서빙
app.use('/upload', express.static(path.join(__dirname, 'public', 'upload')));

// 2) 세션
app.use(
  session({
    secret: 'secret-for-shop-admin',
    resave: false,
    saveUninitialized: true,
    cookie: { maxAge: 1000 * 60 * 10 }, // 10분
  })
);

// 3) 업로드 디렉터리 준비
const uploadDir = path.join(__dirname, 'public', 'upload');
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}

// 4) Multer 설정 (JSP의 DefaultFileRenamePolicy 대체: 파일명 중복 방지)
const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, uploadDir),
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname);           // .png
    const base = path.basename(file.originalname, ext);    // image
    const safeBase = base.replace(/[^\w\-]+/g, '_');       // 특수문자 정리
    cb(null, `${safeBase}_${Date.now()}${ext}`);           // image_169... .png
  },
});
const upload = multer({
  storage,
  limits: { fileSize: 5 * 1024 * 1024 }, // 5MB
});

// 5) 라우팅
// GET: 등록 페이지
app.get('/', (req, res) => {
  res.render('product_fileupload'); // form 페이지
});

// POST: 업로드 처리 (JSP의 viewpage.jsp 역할)
app.post('/upload', upload.single('filename'), (req, res) => {
  try {
    const { name, price, content } = req.body;
    const filename = req.file ? req.file.filename : null;

    // JSP처럼 세션에 보관 후 페이지 이동
    req.session.product = { name, price, content, filename };

    // JSP의 response.sendRedirect("viewpage2.jsp")와 동일한 흐름
    return res.redirect('/view');
  } catch (err) {
    console.error(err);
    return res.status(500).send('파일 업로드 중 오류가 발생했습니다.');
  }
});

// GET: 결과 보기 (JSP의 viewpage2.jsp 역할)
app.get('/view', (req, res) => {
  const product = req.session.product;
  if (!product) {
    return res.redirect('/'); // 세션이 없으면 처음으로
  }
  res.render('viewpage2', product);
});

// 서버 시작
app.listen(PORT, () => {
  console.log(`http://localhost:${PORT}`);
});
