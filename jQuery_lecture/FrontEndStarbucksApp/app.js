// app.js
const express = require('express');
const path = require('path');
const fs = require('fs');
const multer = require('multer');
const session = require('express-session');

const app = express();
const PORT = 3000;

// ===== View & Static =====
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));
app.use('/upload', express.static(path.join(__dirname, 'public', 'upload')));
app.use(express.urlencoded({ extended: true }));

// ===== Session =====
app.use(
  session({
    secret: 'secret-for-shop-admin',
    resave: false,
    saveUninitialized: true,
    cookie: { maxAge: 1000 * 60 * 10 },
  })
);

// ===== In-memory Store (나중에 DB로 교체 가능) =====
/** @type {{id:number,name:string,price:number,content:string,filename:string|null, createdAt:Date}[]} */
const products = [];

// ===== Multer =====
const uploadDir = path.join(__dirname, 'public', 'upload');
if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir, { recursive: true });

const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, uploadDir),
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname);
    const base = path.basename(file.originalname, ext).replace(/[^\w\-]+/g, '_');
    cb(null, `${base}_${Date.now()}${ext}`);
  },
});
const upload = multer({
  storage,
  limits: { fileSize: 5 * 1024 * 1024 },
});

// ===== Routes =====

// 홈: 등록 폼
app.get('/', (req, res) => {
  res.render('product_fileupload');
});

// 목록 페이지
app.get('/products', (req, res) => {
  // 최신 등록이 위로 오도록 정렬
  const list = [...products].sort((a, b) => b.id - a.id);
  res.render('products', { products: list });
});

// 업로드 처리 (등록)
app.post('/upload', upload.single('filename'), (req, res) => {
  try {
    const { name, price, content } = req.body;
    const filename = req.file ? req.file.filename : null;

    // 세션(예전 JSP 흐름 유지)
    req.session.product = { name, price, content, filename };

    // 목록 저장 (메모리)
    const id = Date.now();
    products.push({
      id,
      name,
      price: Number(price),
      content,
      filename,
      createdAt: new Date(),
    });

    // 상세 페이지로 이동
    return res.redirect(`/products/${id}`);
  } catch (err) {
    console.error(err);
    return res.status(500).send('파일 업로드 중 오류가 발생했습니다.');
  }
});

// 상세 페이지 (JSP의 viewpage2.jsp 역할)
app.get('/products/:id', (req, res) => {
  const id = Number(req.params.id);
  const product = products.find(p => p.id === id);
  if (!product) return res.redirect('/products');
  res.render('viewpage2', product);
});

app.listen(PORT, () => {
  console.log(`http://localhost:${PORT}`);
});
