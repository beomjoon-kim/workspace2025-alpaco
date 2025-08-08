const http = require('http');
const express = require('express');
const app = express();

app.use(express.static('public'))

// request, req
// respons, res
app.get('/add/:num1/:num2', (req, res) => {
    let x = Number(req.params.num1);
    let y = Number(req.params.num2);
    let result = x + y;
    res.send({x:x, y:y, result:result});
});

app.get('/min/:num1/:num2', (req, res) => {
    let x = Number(req.params.num1);
    let y = Number(req.params.num2);
    let result = x - y;
    res.send({x:x, y:y, result:result});
});

app.get('/mul/um1/:num2', (req, res) => {
    let x = Number(req.params.num1);
    let y = Number(req.params.num2);
    let result = x / y;
    res.send({x:x, y:y, result:result});
});

app.get('/div/:num1/:num2', (req, res) => {
    let x = Number(req.params.num1);
    let y = Number(req.params.num2);
    let result = x * y;
    res.send({x:x, y:y, result:result});
});

const server = http.createServer(app);
server.listen(3000, () => {
    console.log("run on server http://localhost:3000");
});
