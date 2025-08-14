const http = require('http');
const express = require('express');
const app = express();
const path = require('path');

app.set('PORT', process.env.PORT || 3000);
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

app.use(express.static(path.join(__dirname, 'public')));
app.use('/api', require("./routes/index") );

app.use((req, res, next) => {
    res.writeHead(200, {"Content-Type":"text/html; charset=UTF-8"});
    console.log("첫번째 미들웨어 실행 ...");
    res.write('<p>hi!</p>');
    // 다음 미들웨어 체인 실행
    next();
});

app.use((req, res, next) => {
    console.log("두번째 미들웨어 실행 ...");
    res.write('<p>hi2!</p>');
    // 다음 미들웨어 체인 실행
    next();
});

app.get('/home', (req, res) => {
    res.end("<h1>Hello world</h1>");
})

const server = http.createServer(app);
server.listen(app.get('PORT'), () => {
    console.log(`Run on server: http://localhost:${app.get('PORT')}`)
});
