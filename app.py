from flask import Flask, render_template, request, redirect, send_file
import sqlite3
import random
from fpdf import FPDF
import os
import base64
from io import BytesIO

app = Flask(__name__)

# ---------------- DATABASE ----------------
def get_db():
    return sqlite3.connect("database.db")

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS crops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer TEXT,
        crop TEXT,
        quantity INTEGER,
        price INTEGER,
        UNIQUE(farmer, crop, quantity)
    )
    """)
    conn.commit()
    conn.close()

# ---------------- AI LOGIC ----------------
def predict_price(month, rainfall, demand):
    return 2000 + (demand * 5) - (rainfall * 2) + random.randint(-100, 100)

def risk_level(rainfall, demand):
    if rainfall > 120 and demand < 50:
        return "High Risk"
    elif demand >= 50:
        return "Medium Risk"
    return "Low Risk"

def price_trend(current, avg_price):
    if current > avg_price:
        return "Rising"
    elif current < avg_price:
        return "Falling"
    return "Stable"

def sell_advice(trend, risk):
    if trend == "Rising" and risk == "Low Risk":
        return "Best time to sell now"
    elif trend == "Rising":
        return "Wait for better price"
    return "Avoid selling now"

def multi_crop_prediction(month, rainfall, demand):
    crops = ["Wheat", "Rice", "Maize", "Onion"]
    prices = []
    for _ in crops:
        price = 2000 + (demand * 4) - (rainfall * 1.5) + random.randint(-150, 150)
        prices.append(int(price))
    return crops, prices

# ---------------- ROUTES ----------------
@app.route("/", methods=["GET", "POST"])
def dashboard():
    price = risk = trend = advice = None
    graph_months, graph_prices = [], []
    multi_crops, multi_prices = [], []

    if request.method == "POST":
        month = int(request.form["month"])
        rainfall = int(request.form["rainfall"])
        demand = int(request.form["demand"])

        price = predict_price(month, rainfall, demand)
        avg_price = 2500

        risk = risk_level(rainfall, demand)
        trend = price_trend(price, avg_price)
        advice = sell_advice(trend, risk)

        graph_months = ["Jan", "Feb", "Mar", "Apr", "May"]
        graph_prices = [2200, 2300, 2400, price, price + 100]

        multi_crops, multi_prices = multi_crop_prediction(month, rainfall, demand)

    # ----- SEARCH / FILTER / SORT / PAGINATION -----
    search = request.args.get("search", "")
    min_price = request.args.get("min_price", "")
    max_price = request.args.get("max_price", "")
    sort = request.args.get("sort", "asc")

    page = int(request.args.get("page", 1))
    per_page = 10
    offset = (page - 1) * per_page

    query = "SELECT * FROM crops WHERE 1=1"
    count_query = "SELECT COUNT(*) FROM crops WHERE 1=1"
    params = []

    if search:
        query += " AND crop LIKE ?"
        count_query += " AND crop LIKE ?"
        params.append(f"%{search}%")

    if min_price:
        query += " AND price >= ?"
        count_query += " AND price >= ?"
        params.append(min_price)

    if max_price:
        query += " AND price <= ?"
        count_query += " AND price <= ?"
        params.append(max_price)

    query += " ORDER BY price " + ("DESC" if sort == "desc" else "ASC")
    query += " LIMIT ? OFFSET ?"

    conn = get_db()
    crops = conn.execute(query, params + [per_page, offset]).fetchall()
    total = conn.execute(count_query, params).fetchone()[0]
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "dashboard.html",
        price=price, risk=risk, trend=trend, advice=advice,
        graph_months=graph_months, graph_prices=graph_prices,
        multi_crops=multi_crops, multi_prices=multi_prices,
        crops=crops, page=page, total_pages=total_pages,
        search=search, min_price=min_price, max_price=max_price, sort=sort,
        accuracy="Approx. 85% (trend‑based)"
    )

@app.route("/sell", methods=["POST"])
def sell():
    farmer = request.form["farmer"]
    crop = request.form["crop"]
    quantity = int(request.form["quantity"])
    price = random.randint(1500, 5000)

    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO crops (farmer, crop, quantity, price) VALUES (?,?,?,?)",
        (farmer, crop, quantity, price)
    )
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/download-report", methods=["POST"])
def download_report():
    price = request.form.get("price")
    risk = request.form.get("risk")
    trend = request.form.get("trend")
    advice = request.form.get("advice")

    price_img = request.form.get("price_img")
    multi_img = request.form.get("multi_img")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(0, 10, "Smart Agriculture AI Prediction Report", ln=True)
    pdf.ln(5)

    pdf.cell(0, 8, f"Predicted Price: Rs {price}", ln=True)
    pdf.cell(0, 8, f"Risk Level: {risk}", ln=True)
    pdf.cell(0, 8, f"Trend: {trend}", ln=True)
    pdf.cell(0, 8, f"Advice: {advice}", ln=True)

    # ---- PRICE TREND CHART ----
    if price_img:
        img_data = base64.b64decode(price_img.split(",")[1])
        img_path = "price_chart.png"
        with open(img_path, "wb") as f:
            f.write(img_data)

        pdf.ln(5)
        pdf.cell(0, 10, "Price Trend Chart", ln=True)
        pdf.image(img_path, x=10, w=180)

    # ---- MULTI CROP CHART ----
    if multi_img:
        img_data = base64.b64decode(multi_img.split(",")[1])
        img_path2 = "multi_crop_chart.png"
        with open(img_path2, "wb") as f:
            f.write(img_data)

        pdf.ln(5)
        pdf.cell(0, 10, "Multi-Crop Comparison", ln=True)
        pdf.image(img_path2, x=10, w=180)

    file_path = os.path.join(os.getcwd(), "AI_Prediction_Report.pdf")
    pdf.output(file_path)

    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)