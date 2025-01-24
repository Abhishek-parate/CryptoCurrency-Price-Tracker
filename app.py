import os
import sqlite3
import time
import json
import threading
import requests
import websocket
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Set a secret key for session management
socketio = SocketIO(app)

COINMARKETCAP_API_KEY = "d2731549-19f8-405a-8017-6df613de03dd"
allowed_symbols = ["dogeusdt", "btcusdt", "ethusdt", "bnbusdt", "xrpusdt", "solusdt"]
latest_prices = {}
cache = {}
cache_expiry = 300  # Cache expiry time in seconds


def get_conversion_rate(from_currency, to_currency):
    """Fetch conversion rate between two currencies."""
    key = f"{from_currency}_{to_currency}"
    if key in cache and time.time() - cache[key]["timestamp"] < cache_expiry:
        return cache[key]["rate"]

    url = "https://pro-api.coinmarketcap.com/v1/tools/price-conversion"
    headers = {"X-CMC_PRO_API_KEY": COINMARKETCAP_API_KEY}
    params = {"amount": 1, "symbol": from_currency, "convert": to_currency}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        rate = response.json()["data"]["quote"][to_currency]["price"]
        cache[key] = {"rate": rate, "timestamp": time.time()}
        return rate
    except requests.exceptions.RequestException as e:
        raise Exception(f"API Error: {e}")


def on_message(ws, message):
    """Handle incoming WebSocket messages."""
    try:
        data = json.loads(message)
        symbol = data["s"].lower()
        price = float(data["c"])  # Current price
        volume = float(data["v"])  # Volume
        price_change = float(data["P"])  # Price change
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
        print(f"Error processing message: {e}")


def on_error(ws, error):
    """Handle WebSocket errors."""
    print(f"WebSocket Error: {error}")


def on_close(ws):
    """Handle WebSocket closure."""
    print("### WebSocket closed ###")


def on_open(ws):
    """Subscribe to relevant WebSocket streams."""
    print("### WebSocket opened ###")
    params = [f"{symbol}@ticker" for symbol in allowed_symbols]
    subscribe_message = {"method": "SUBSCRIBE", "params": params, "id": 1}
    ws.send(json.dumps(subscribe_message))


def start_websocket():
    """Start the WebSocket connection to receive live updates."""
    websocket.enableTrace(True)
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


@app.route("/convert", methods=["GET"])
def convert_currency():
    """Convert between currencies."""
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
    """Render candlestick chart for a specific symbol."""
    if symbol.lower() not in allowed_symbols:
        return "Invalid coin symbol", 404
    return render_template("candlestick.html", symbol=symbol.upper())


@app.route("/get-candlestick-data", methods=["GET"])
def get_candlestick_data():
    """Fetch candlestick data for a specific symbol and time range."""
    symbol = request.args.get("symbol", "").upper()
    interval = request.args.get("interval", "1h")
    start = request.args.get("start")
    end = request.args.get("end")

    if symbol.lower() not in allowed_symbols:
        return jsonify({"error": "Invalid coin symbol"}), 400

    url = f"https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": 1000,  # Binance max is 1000 per request
    }

    # Add date range if provided
    if start:
        params["startTime"] = int(time.mktime(time.strptime(start, "%Y-%m-%d"))) * 1000
    if end:
        params["endTime"] = int(time.mktime(time.strptime(end, "%Y-%m-%d"))) * 1000

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        candlestick_data = [
            {
                "time": int(item[0] / 1000),  # Convert milliseconds to seconds
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
    """Handle login functionality."""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        try:
            with sqlite3.connect("users.db") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
                user = cursor.fetchone()

            if user and check_password_hash(user[0], password):
                session["username"] = username
                return redirect(url_for("index"))
            else:
                return render_template("login.html", error="Invalid credentials")
        except Exception as e:
            return render_template("login.html", error=f"Error: {str(e)}")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Handle user registration."""
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
            return render_template("register.html", error="Username already exists")
        except Exception as e:
            return render_template("register.html", error=f"Error: {str(e)}")

    return render_template("register.html")


@app.route("/")
def index():
    """Render homepage with user data."""
    if "username" not in session:
        return redirect(url_for("login"))

    return render_template("index.html", allowed_symbols=allowed_symbols, username=session["username"])


@app.route("/logout")
def logout():
    """Handle user logout."""
    session.pop("username", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
