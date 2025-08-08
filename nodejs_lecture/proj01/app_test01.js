const http = require('http');
const express = require('express');
const app = express();

// app에서 라우팅 기능 기본 제공
// 요청 메서드별로 처리하는 라우팅함수가 미리 준비되어 있다.
// RESTApi 방식: get(), post() ... put(), delete(), fetch() ...
// app.get('패스', 콜백함수)
// 예. app.get('/profile', (req, res) => { ... });
// app.get(); // 조회
// app.post(); // 생성, 입력
// app.put(); // 수정
// app.delete();// 삭제
// 입력, 출력, 검색, 수정, 삭제...

// app.get('/', (req, res) => {
//     res.writeHead(200, {'Content-Type':"text/html; charset=UTF-8"});
//     res.write('<h1>길동이의 홈페이지</h1>');
//     res.end();
// });

// serv-static 미들웨어 설정
// GET /style.css etc
// 정적 파일 홈 디렉토리 설정
app.use(express.static('public'));


app.get('/profile', (req, res) => {
    res.writeHead(200, {'Content-Type':"text/html; charset=UTF-8"});
    res.write('<h1>길동이의 프로필</h1>');
    res.end();
});

app.get('/gallery', (req, res) => {
    res.writeHead(200, {'Content-Type':"text/html; charset=UTF-8"});
    res.write('<h1>길동이의 갤러리</h1>');
    res.end();
});

const server = http.createServer(app);
server.listen(3000, () => {
    // 브라우저 콘솔이 아니다. 서버쪽 터미널에서 출력.
    console.log("run on server http://localhost:3000");
});



// const http = require('http');

// const server = http.createServer(function(req, res) {
//     res.writeHead(200, {"Content-Type":"text/html; charset=UTF-8"});
//     res.end("<h1>안녕 노드 세계!</h1>");
// });

// server.listen(3000, function() {
//     console.log("서버실행중 http://localhost:3000");
// });