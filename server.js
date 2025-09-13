const express = require("express");
const path = require("path");

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));

let currentTime = 0;
let timerInterval = null;
let activeOrders = [];
let scores = {};

const BURGER_RECIPES = {
    "ハンバーガー": ["🫓", "🥩:cooked", "🥬:cut"],
    "ベジバーガー": ["🫓", "🥬:cut", "🍅:cut"],
    "ミートサンド": ["🫓", "🥩:cooked"]
};

// ===== ルーティング =====
app.get("/", (req, res) => {
    res.render("index"); // views/index.ejs
});

app.get("/hamburger", (req, res) => {
    resetGame();
    // EJS で初期画面描画
    res.render("hamburger", { title: "ハンバーガーゲーム" });
});

// ===== ゲーム制御 =====
app.post("/start", (req, res) => {
    const seconds = req.body.seconds || 120;
    if (!timerInterval) {
        currentTime = seconds;
        addRandomOrder(); // 開始時に即注文

        let tickCount = 0;
        timerInterval = setInterval(() => {
            currentTime--;
            tickCount++;

            if (tickCount % 10 === 0 && activeOrders.length < 7) {
                addRandomOrder();
            }

            activeOrders.forEach(o => o.remain--);
            activeOrders = activeOrders.filter(o => o.remain > 0);

            if (currentTime <= 0) {
                clearInterval(timerInterval);
                timerInterval = null;
                currentTime = 0;
            }
        }, 1000);
    }
    res.json({ status: "started", currentTime });
});

app.get("/status", (req, res) => {
    const displayTime = timerInterval ? currentTime : 120;
    res.json({ currentTime: displayTime, activeOrders });
});

app.post("/score_update", (req, res) => {
    const sessionId = req.body.sessionId || "anon";
    scores[sessionId] = req.body.score || 0;
    res.json({ status: "ok" });
});

app.post("/end", (req, res) => {
    clearInterval(timerInterval);
    timerInterval = null;
    currentTime = 0;
    activeOrders = [];
    res.json({ status: "ended" });
});

// ===== ユーティリティ =====
function addRandomOrder() {
    const keys = Object.keys(BURGER_RECIPES);
    const name = keys[Math.floor(Math.random() * keys.length)];
    activeOrders.push({
        name,
        items: BURGER_RECIPES[name].join(" + "),
        remain: 40
    });
}

function resetGame() {
    clearInterval(timerInterval);
    timerInterval = null;
    currentTime = 0;
    activeOrders = [];
}

app.listen(3000, () => console.log("Server running on http://localhost:3000"));
