const { MongoClient } = require("mongodb");
const client = new MongoClient("mongodb://127.0.0.1");
const dbName = "vehicle";
const collectionName = "car";

async function run() {
  try {
    // 클라이언트를 서버에 연결합니다(v4.7부터 선택 사항).
    await client.connect();
    // 연결 설정 및 확인
    const db = client.db(dbName);
    const car = db.collection(collectionName);
    const cursor = car.find({}, { projection: { _id: 0 } });
    await cursor.forEach(console.log);
    console.log("Connected successfully to server");
  } finally {
    // 완료/오류 발생 시 클라이언트가 닫힘.
    await client.close();
  }
}

run().catch(console.dir);