from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import threading
import json
import websocket
import requests
import time
import os
import logging

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Ensure this is secure in production
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # Session expires in 30 minutes
socketio = SocketIO(app)

# API Key and WebSocket symbols
COINMARKETCAP_API_KEY = "d2731549-19f8-405a-8017-6df613de03dd"
allowed_symbols = ["dogeusdt", "btcusdt", "ethusdt", "bnbusdt", "xrpusdt", "solusdt"]

# Caching for API rates
cache = {}
cache_expiry = 300

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Latest prices storage
latest_prices = {}


# --- Helper Functions ---
def get_conversion_rate(from_currency, to_currency):
    key = f"{from_currency}_{to_currency}"
    if key in cache and time.time() - cache[key]["timestamp"] < cache_expiry:
        return cache[key]["rate"]

    url = "https://pro-api.coinmarketcap.com/v1/tools/price-conversion"
    headers = {"X-CMC_PRO_API_KEY": COINMARKETCAP_API_KEY}
    params = {"amount": 1, "symbol": from_currency, "convert": to_currency}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        rate = response.json()["data"]["quote"][to_currency]["price"]
        cache[key] = {"rate": rate, "timestamp": time.time()}
        return rate
    else:
        raise Exception(f"API Error: {response.text}")


# --- WebSocket Functions ---
def on_message(ws, message):
    try:
        data = json.loads(message)
        symbol = data["s"].lower()
        price = float(data["c"])  # Current price
        volume = float(data["v"])  # Volume
        price_change = float(data["P"])  # Percent change
        latest_prices[symbol.upper()] = {
            "price": price,
            "volume": volume,
            "change": price_change,
        }

        socketio.emit(
            "price_update",
            {"symbol": symbol.upper(), "price": price, "volume": volume, "change": price_change},
        )
    except Exception as e:
        logger.error(f"Error processing message: {e}, message: {message}")


def on_error(ws, error):
    logger.error(f"WebSocket Error: {error}")


def on_close(ws):
    logger.info("### WebSocket closed ###")


def on_open(ws):
    logger.info("### WebSocket opened ###")
    params = [f"{symbol}@ticker" for symbol in allowed_symbols]
    subscribe_message = {"method": "SUBSCRIBE", "params": params, "id": 1}
    ws.send(json.dumps(subscribe_message))


def start_websocket():
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp(
        "wss://stream.binance.com:9443/ws",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    ws.on_open = on_open
    ws.run_forever()


# Start WebSocket in a separate thread
ws_thread = threading.Thread(target=start_websocket)
ws_thread.daemon = True
ws_thread.start()


# --- Routes ---
@app.route("/convert", methods=["GET"])
def convert_currency():
    try:
        amount = float(request.args.get("amount"))
        from_currency = request.args.get("from", "USD")
        to_currency = request.args.get("to", "USD")

        if from_currency == to_currency:
            return jsonify({"converted": amount})

        rate = get_conversion_rate(from_currency, to_currency)
        converted_amount = amount * rate
        return jsonify({"converted": converted_amount})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/candlestick/<symbol>")
def candlestick(symbol):
    if symbol.lower() not in allowed_symbols:
        return "Invalid coin symbol", 404
    return render_template("candlestick.html", symbol=symbol.upper())


@app.route("/get-candlestick-data", methods=["GET"])
def get_candlestick_data():
    symbol = request.args.get("symbol", "").upper()
    interval = request.args.get("interval", "1h")
    start = request.args.get("start")
    end = request.args.get("end")

    if symbol.lower() not in allowed_symbols:
        return jsonify({"error": "Invalid coin symbol"}), 400

    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol.upper(), "interval": interval, "limit": 1000}

    if start:
        params["startTime"] = int(time.mktime(time.strptime(start, "%Y-%m-%d"))) * 1000
    if end:
        params["endTime"] = int(time.mktime(time.strptime(end, "%Y-%m-%d"))) * 1000

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        candlestick_data = [
            {
                "time": int(item[0] / 1000),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
            }
            for item in data
        ]
        return jsonify(candlestick_data)
    else:
        return jsonify({"error": "Failed to fetch candlestick data"}), 500


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        with sqlite3.connect("users.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()

        if not user:
            return render_template("login.html", error="Username does not exist")
        elif not check_password_hash(user[0], password):
            logger.info(f"Failed login attempt for username: {username}")
            return render_template("login.html", error="Incorrect password")
        else:
            session["username"] = username
            return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        hashed_password = generate_password_hash(password)

        try:
            with sqlite3.connect("users.db") as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
                conn.commit()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Username already exists. Please use a different email.")
        except Exception as e:
            return render_template("register.html", error=f"An unexpected error occurred: {str(e)}")

    return render_template("register.html")


@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", allowed_symbols=allowed_symbols, username=session["username"])


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
