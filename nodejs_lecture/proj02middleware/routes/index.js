const express = require('express');
const router = express.Router();

router.route('/calc').get((req, res) => {
    // res.writeHead(200, {"Conent-Type":"text/html; charset=UTF-8"});
    // res.end("<h2>계산기</h2>");

    req.app.render('calc', {}, (err, htmlData)=>{
        if (err) throw err;
        res.end(htmlData);
    });
});

router.route('/todos').get((req, res) => {
    res.writeHead(200, {"Conent-Type":"text/html; charset=UTF-8"});
    res.end("<h2>TodoList</h2>");
});

module.exports = router;