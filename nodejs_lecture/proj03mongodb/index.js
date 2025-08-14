const http = require("http");
const express = require("express");
const app = express();
const { MongoClient } = require("mongodb");
const path = require("path");
const bodyParser = require("body-parser");

app.set('port', 3000);
app.set("views", path.join(__dirname, "views"));
app.set("view engine", "ejs");

app.use(bodyParser.urlencoded({extended: false}));
app.use(bodyParser.json());
app.use("/", express.static(path.join(__dirname, "public")) );

const uri = "mongodb://localhost:27017";
const client = new MongoClient(uri);
const dbName = "vehicle";
const collectionName = "car";

app.get("/car", async (req, res) => {
    try {
        await client.connect();
        const database = client.db(dbName);
        const cars = database.collection(collectionName);
        const query = {};
        const options = {
            sort: { name: 1 },
            //projection: { _id:true, name:1, company:1, price:1, year:1 }
            projection: {}
        };
        const cursor = cars.find(query, options);
        if ((await cars.countDocuments(query)) === 0) {
            console.log("No documents found!");
    　　}
        const carList = [];
        for await (const doc of cursor) {
            carList.push(doc);
            console.dir(doc);
        }
        req.app.render("CarList", {carList}, (err, html)=>{
            // console.log(html);
            res.end(html);
        });
    } finally {
        await client.close();
    }
});

app.post("/car", async (req, res)=> {
    res.end("POST - /car");
});

const server = http.createServer(app);
server.listen(app.get('port'), ()=>{
  console.log(`서버 실행 중 >>> http://localhost:${app.get('port')}/car`);
});