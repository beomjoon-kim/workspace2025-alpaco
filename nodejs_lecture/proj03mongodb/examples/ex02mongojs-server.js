// node.js 프로젝트와 mongodb 연동 테스트
// 결과를 웹 브라우저에서 출력
const http = require('http');
const express = require('express');
const app = express();
const mongojs = require("mongojs");
const db = mongojs('vehicle', ['car']);

app.set('port', 3000);

app.get('/', (req, res) => {
    console.log("GET - / 요청 ...")
    if(db) {
        // mongojs는 옛날 기술 - 콜백 함수로 처리.
        db.car.find((err, result) => {
            if(err) throw err;
            let html = '<table border="1">';
            result.forEach((car, i)=>{
                html += `<tr><td>${car.name}</td><td>${car.price}</td>
                <td>${car.company}</td><td>${car.year}</td></tr>`;
            });
            html += "</table>";
            res.end(html);
        });
    } else {
        res.end("db가 연결되지 않았습니다!");
    }
});

const server = http.createServer(app);
server.listen(app.get('port'), ()=>{
    console.log(`서버 실행 중>>> http://localhost:${app.get('port')}`);
});
