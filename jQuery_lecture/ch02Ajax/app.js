const http = require('http');
const express = require('express');
const app = express();
const port = 3000;

// static 미들웨어
app.use(express.static('public'));

app.get('/hello', (req, res) => {
    res.end('<h1>Hello world</h1>');
}); 

// http와 express 함께 사용.
const server = http.createServer(app);
server.listen(port, () =>  {
    console.log(`Run on Server: http://localhost:${port}`);
});
