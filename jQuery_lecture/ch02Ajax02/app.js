const http = require('http');
const express = require('express');
const app = express();
const port = 3000;

app.use(express.static('public'));

// /data에 대한 처리
app.get('/data', (req, res) => {
    let objData = req.query;
    let current = new Date();
    objData.date = `${current.getFullYear()}-${current.getMonth()+1}-${current.getDate()}`

    // 문자열로 변환
    res.end(JSON.stringify(objData));
});

const server = http.createServer(app);
server.listen(port, ()=>{
    console.log(`http://localhost:${port}`);
});