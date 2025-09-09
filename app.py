from flask import Flask, render_template, request, session, redirect, url_for, jsonify, make_response
import random
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = "your_secret_key"

# 表示用の材料リスト（状態なし）
INGREDIENTS = ["パン", "肉", "レタス", "トマト"]

# 状態付きレシピ定義（絵文字＋状態）
BURGER_RECIPES = {
    "ハンバーガー": ["🫓:plain", "🥩:cooked", "🥬:cut"],
    "ベジバーガー": ["🫓:plain", "🥬:cut", "🍅:cut"],
    "ミートサンド": ["🫓:plain", "🥩:cooked"]
}

RECIPES = BURGER_RECIPES

# ゲーム状態を保持するグローバル変数
game_state = {
    "player": {"x": 0, "y": 0, "carrying": None},
    "score": 0,
    "fieldItems": [],
    "turn": 0
}

@app.route("/reset", methods=["POST"])
def reset_game():
    global game_state
    # 全状態をリセット
    game_state = {
        "player": {"x": 0, "y": 0, "carrying": None},
        "score": 0,
        "fieldItems": [],
        "turn": 0
    }
    # ホームにリダイレクト
    return redirect(url_for("home"))

# 🕒 食材に応じた制限時間を計算
def calculate_time_limit(ingredients):
    base = 10
    extra = 0
    for item in ingredients:
        emoji = item.split(":")[0]
        if emoji == "🥩":
            extra += 10
        elif emoji in ["🥬", "🍅"]:
            extra += 5
    return base + extra

@app.route("/")

def game():
    if "score" not in session or "start_time" not in session:
        return redirect(url_for("start"))

    now = datetime.now()
    elapsed = (now - datetime.fromisoformat(session["start_time"])).seconds
    remaining = max(0, 120 - elapsed)
    if remaining <= 0:
        return redirect(url_for("result"))

    orders = session.get("orders", [])
    if "last_order_time" not in session:
        session["last_order_time"] = session["start_time"]

    # 注文期限チェック
    valid_orders = []
    for order in orders:
        age = (now - datetime.fromisoformat(order["created"])).seconds
        recipe = RECIPES[order["name"]]
        time_limit = calculate_time_limit(recipe)
        if age <= time_limit:
            valid_orders.append(order)
        else:
            session["score"] -= 5

    # 注文追加
    last_order_time = datetime.fromisoformat(session["last_order_time"])
    if (now - last_order_time).seconds >= 15 or len(valid_orders) == 0:
        new_order = random.choice(list(RECIPES.keys()))
        valid_orders.append({"name": new_order, "created": now.isoformat()})
        session["last_order_time"] = now.isoformat()

    session["orders"] = valid_orders

    # 表示用注文データ
    emoji_orders = []
    for order in valid_orders:
        recipe = RECIPES[order["name"]]
        emoji_list = [i.split(":")[0] for i in recipe]
        created_time = datetime.fromisoformat(order["created"])
        age = (now - created_time).seconds
        time_limit = calculate_time_limit(recipe)
        time_left = max(0, time_limit - age)
        emoji_orders.append({
            "name": order["name"],
            "emojis": emoji_list,
            "remaining": time_left,
            "time_limit": time_limit,
            "created": order["created"]
        })

    # 🍳 食材状態の取得
    field_items = session.get("field_items", [])

    return render_template("game.html",
        ingredients=INGREDIENTS,
        recipes=RECIPES,
        orders=emoji_orders,
        score=session["score"],
        time=remaining,
        field_items=field_items
    )

@app.route("/start")
def start():
    now = datetime.now()
    session["score"] = 0
    session["start_time"] = now.isoformat()
    session["last_order_time"] = now.isoformat()
    first_order = random.choice(list(RECIPES.keys()))
    session["orders"] = [{"name": first_order, "created": now.isoformat()}]
    return redirect(url_for("game"))

@app.route("/result")
def result():
    score = session.get("score", 0)
    return render_template("result.html", score=score)

@app.route("/serve", methods=["POST"])
def serve():
    if "score" not in session or "orders" not in session:
        return {"status": "error", "message": "セッションが無効です"}, 400

    burger = [b.strip() for b in request.json.get("ingredients", [])]
    orders = session["orders"]
    matched = None

    for order in orders:
        correct = RECIPES.get(order["name"], [])
        if sorted(burger) == sorted(correct):
            matched = order
            break

    if matched:
        session["orders"].remove(matched)
        session["score"] += 10
        result = f"{matched['name']} 提供成功！+10点"
    else:
        session["score"] -= 5
        result = "注文に一致しません！-5点"

    return {"status": "ok", "result": result, "score": session["score"]}

@app.route("/update_field", methods=["POST"])
def update_field():
    session["field_items"] = request.json.get("fieldItems", [])
    return {"status": "ok"}

# ✅ クッキー保存ルート追加
@app.route("/save_state", methods=["POST"])
def save_state():
    data = request.json or {}
    resp = make_response(jsonify({"status": "ok"}))

    # x, y を保存
    resp.set_cookie("player_x", str(data.get("x", 0)))
    resp.set_cookie("player_y", str(data.get("y", 0)))

    # carrying を保存
    carrying = data.get("carrying")
    if carrying:
        resp.set_cookie("carrying", json.dumps(carrying))
    else:
        resp.set_cookie("carrying", "", expires=0)

    return resp


def safe_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

@app.route("/load_state")
def load_state():
    def safe_int(val):
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0

    x = safe_int(request.cookies.get("player_x"))
    y = safe_int(request.cookies.get("player_y"))
    carrying_raw = request.cookies.get("carrying")

    return jsonify({
        "x": x,
        "y": y,
        "carrying": json.loads(carrying_raw) if carrying_raw else None
    })

