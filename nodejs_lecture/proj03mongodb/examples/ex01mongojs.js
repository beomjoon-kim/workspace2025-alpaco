// node.js 프로젝트와 mongodb 연동 테스트
const mongojs = require("mongojs");
const db = mongojs('vehicle', ['car']);

db.car.find(function(err, data) {
    console.log(data);
});
