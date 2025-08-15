// index.js
const http = require('http');
const express = require('express');
const app = express();
const path = require('path');
const { ObjectId, MongoClient, ServerApiVersion } = require('mongodb');

// ──────────────────────────────────────────────────────────────
// MongoDB 연결 설정 (로컬)
const uri = "mongodb://localhost:27017";
const dbName = "local";
const collectionName = "todolist";

// 최신 드라이버 기준: 별도 useUnifiedTopology 옵션 불필요
const client = new MongoClient(uri, {
  serverApi: { version: ServerApiVersion.v1, strict: false, deprecationErrors: true },
});

// 전역 재사용을 위한 locals (앱 전체에서 공유)
app.locals.db = null;
app.locals.todoCollection = null;
// ──────────────────────────────────────────────────────────────

app.set('PORT', process.env.PORT || 3000);
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

app.get('/home', (req, res) => {
  req.app.render('home', {}, (err, html) => {
    if (err) throw err;
    res.end(html);
  });
});

app.get('/todos', (req, res) => {
  // 샘플 데이터 (뷰 점검용)
  let todoList = [
    { _id: ObjectId.createFromHexString('689d8ca73fcaefd98ceec4af'), title: '밥먹기2', done: false },
    { _id: ObjectId.createFromHexString('689d8ca73fcaefd98ceec4b0'), title: '잠자기2', done: false },
    { _id: ObjectId.createFromHexString('689d8ca73fcaefd98ceec4b1'), title: '공부하기2', done: true  },
    { _id: ObjectId.createFromHexString('689d8ca73fcaefd98ceec4b2'), title: '친구랑 놀기2', done: false },
  ];
  req.app.render('todolist', { todoList }, (err, html) => {
    if (err) throw err;
    res.end(html);
  });
});

app.get("/todo/list", async (req, res) => {
  try {
    const todoCollection = req.app.locals.todoCollection;
    const todoList = await todoCollection.find({}).sort({ _id: -1 }).toArray();
    if (!todoList.length) console.log("No documents found!");
    res.render("todolist", { todoList });
  } catch (err) {
    console.error(err);
    res.status(500).send("Internal Server Error");
  }
});

app.get("/todo/detail", async (req, res) => {
  try {
    const todoCollection = req.app.locals.todoCollection;
    const QUERY = { _id: new ObjectId(req.query._id) };
    const findedTodo = await todoCollection.findOne(QUERY);
    res.render("todoDetail", { todo: findedTodo });
  } catch (err) {
    console.error(err);
    res.status(500).send("Internal Server Error");
  }
});

app.get("/todo/modify", async (req, res) => {
  try {
    const todoCollection = req.app.locals.todoCollection;
    const QUERY = { _id: new ObjectId(req.query._id) };
    const findedTodo = await todoCollection.findOne(QUERY);
    res.render("todoModify", { todo: findedTodo });
  } catch (err) {
    console.error(err);
    res.status(500).send("Internal Server Error");
  }
});

app.post("/todo/modify", async (req, res) => {
  try {
    const todoCollection = req.app.locals.todoCollection;
    const filter = { _id: new ObjectId(req.body._id) };
    const updateDoc = {
      $set: {
        title: req.body.title,
        done: (req.body.done == "true" ? true : false),
      },
    };
    const result = await todoCollection.updateOne(filter, updateDoc, { upsert: false });
    console.log(`matched: ${result.matchedCount}, modified: ${result.modifiedCount}`);
    res.redirect("/todo/detail?_id="+req.body._id);
  } catch (err) {
    console.error(err);
    res.status(500).send("Internal Server Error");
  }
});

app.get("/todo/input", (req, res) => res.render("todoInput", {}));

app.post("/todo/input", async (req, res) => {
  try {
    const todoCollection = req.app.locals.todoCollection;

    const title = (req.body.title || "").trim();
    // checkbox 값 처리: true / "true" / "on" / "1" 는 true로 간주
    const doneRaw = req.body.done;
    const done = doneRaw === true || doneRaw === "true" || doneRaw === "on" || doneRaw === "1";

    if (!title) return res.status(400).send("title is required");

    const result = await todoCollection.insertOne({
      title,
      done,
      createdAt: new Date(),
    });

    console.log("insertedId:", result.insertedId);
    res.redirect("/todo/list");
  } catch (err) {
    console.error(err);
    res.status(500).send("Internal Server Error");
  }
});


app.get("/todo/delete", async (req, res) => {
  try {
    const todoCollection = req.app.locals.todoCollection;
    const query = { _id: new ObjectId(req.query._id) };
    const result = await todoCollection.deleteOne(query);
    console.log(`deleted: ${result.deletedCount}`);
    res.redirect("/todo/list");
  } catch (err) {
    console.error(err);
    res.status(500).send("Internal Server Error");
  }
});

// ──────────────────────────────────────────────────────────────
// 서버 & DB 부팅 시퀀스: DB 연결 성공 후 서버 리슨
const server = http.createServer(app);

(async () => {
  try {
    await client.connect();
    // 연결 확인 (선택)
    await client.db('admin').command({ ping: 1 });
    console.log("✅ MongoDB connected");

    app.locals.db = client.db(dbName);
    app.locals.todoCollection = app.locals.db.collection(collectionName);

    server.listen(app.get('PORT'), () => {
      console.log(`Run on server: http://localhost:${app.get('PORT')}`);
    });
  } catch (e) {
    console.error("❌ DB 연결 실패:", e);
    process.exit(1);
  }
})();

// 종료 훅: 프로세스 종료 시 커넥션 정리
async function gracefulShutdown() {
  try {
    await client.close();
    console.log("🔻 MongoDB connection closed");
  } catch (e) {
    console.error("MongoDB close error:", e);
  } finally {
    process.exit(0);
  }
}
process.on('SIGINT', gracefulShutdown);
process.on('SIGTERM', gracefulShutdown);
// ──────────────────────────────────────────────────────────────
