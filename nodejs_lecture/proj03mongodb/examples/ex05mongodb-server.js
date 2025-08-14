const express = require('express');
const app = express();
const http = require('http');
const path = require('path');

const { MongoClient } = require('mongodb');

app.set('port', 3000);
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, "../views") );

// MongoDB 연결 문자열
const uri = "mongodb://localhost:27017";
const client = new MongoClient(uri);

app.get('/car', async (req, res) => {
    try {
        await client.connect();
        const database = client.db('vehicle');
        const cars = database.collection('car');

        // MongoDB에서 데이터를 조회합니다.
        const carList = await cars.find({}).toArray();
        res.render('CarList', { carList });
    } catch (e) {
        console.error(e);
        res.send("Error fetching cars");
    } finally {
        await client.close();
    }
});

const server = http.createServer(app);
server.listen(app.get('port'), () => {
    console.log(`서버 실행 중 >>> http://localhost:${app.get('port')}/car`);
});
