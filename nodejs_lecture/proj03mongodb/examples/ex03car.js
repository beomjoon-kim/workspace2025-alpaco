const mongojs = require("mongojs");
const db = mongojs('vehicle', ['car']);

const express = require('express');
const app = express();
const http = require('http');

const path = require('path');

app.set('view engine', 'ejs');
console.log(path.join(__dirname, "../views"));
app.set('views', path.join(__dirname, "../views") );

app.get('/car', (req, res) => {
    db.car.find(function(err, carList) {
        req.app.render('CarList', {carList}, (err, html)=>{
            res.end(html);
        });
    });
});

const server = http.createServer(app);
server.listen(3000, () => {
    console.log('서버 실행 중 ... http://localhost:3000');
});
