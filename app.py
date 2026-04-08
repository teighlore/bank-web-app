from flask import Flask, render_template, request, redirect, session
import mysql.connector
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secretkey123"

# ===== DATABASE =====
import os
import mysql.connector

conn = mysql.connector.connect(
    host=os.getenv("MYSQLHOST"),
    user=os.getenv("MYSQLUSER"),
    password=os.getenv("MYSQLPASSWORD"),
    database=os.getenv("MYSQLDATABASE"),
    port=int(os.getenv("MYSQLPORT", "3306"))
)

cursor = conn.cursor()

# ===== UTIL =====
def generate_account_number():
    while True:
        num = str(random.randint(100000, 999999))
        cursor.execute("SELECT account_number FROM accounts WHERE account_number=%s", (num,))
        if not cursor.fetchone():
            return num

def log_transaction(acc, ttype, acct_type, amount):
    cursor.execute(
        "INSERT INTO transactions (account_number,type,account_type,amount,timestamp) VALUES (%s,%s,%s,%s,%s)",
        (acc, ttype, acct_type, amount, datetime.now())
    )
    conn.commit()

# ===== ROUTES =====

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        last = request.form["last"]
        acc = request.form["acc"]

        cursor.execute("SELECT * FROM accounts WHERE last_name=%s AND account_number=%s", (last, acc))
        r = cursor.fetchone()

        if r:
            session["acc"] = r[8]
            session["name"] = f"{r[1]} {r[3]}"
            return redirect("/dashboard")

    return render_template("login.html")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    acc = session.get("acc")

    cursor.execute("SELECT checking_balance, savings_balance FROM accounts WHERE account_number=%s", (acc,))
    r = cursor.fetchone()

    checking, savings = float(r[0]), float(r[1])

    if request.method == "POST":
        amount = float(request.form["amount"])
        ttype = request.form["type"]
        acct_type = request.form["acct"]

        bal = checking if acct_type == "Checking" else savings

        if ttype == "Withdraw" and amount > bal:
            return "Insufficient funds"

        bal = bal - amount if ttype == "Withdraw" else bal + amount

        if acct_type == "Checking":
            cursor.execute("UPDATE accounts SET checking_balance=%s WHERE account_number=%s", (bal, acc))
        else:
            cursor.execute("UPDATE accounts SET savings_balance=%s WHERE account_number=%s", (bal, acc))

        conn.commit()
        log_transaction(acc, ttype, acct_type, amount)

        return redirect("/dashboard")

    return render_template("dashboard.html", checking=checking, savings=savings, name=session["name"])


@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        data = request.form
        acc = generate_account_number()

        cursor.execute("""
        INSERT INTO accounts (
        first_name,middle_name,last_name,
        street,city,state,zipcode,
        account_number,checking_balance,savings_balance)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data["first"], data["middle"], data["last"],
            data["street"], data["city"], data["state"], data["zip"],
            acc, float(data["checking"]), float(data["savings"])
        ))

        conn.commit()
        return f"Account created! Number: {acc}"

    return render_template("create.html")


@app.route("/history")
def history():
    acc = session.get("acc")

    cursor.execute("SELECT type,account_type,amount,timestamp FROM transactions WHERE account_number=%s", (acc,))
    rows = cursor.fetchall()

    return render_template("history.html", rows=rows)


# ===== TELLER =====

@app.route("/teller", methods=["GET", "POST"])
def teller():
    if request.method == "POST":
        if request.form["user"] == "Admin" and request.form["pw"] == "Password1234":
            return redirect("/teller_tools")
    return render_template("teller_login.html")


@app.route("/teller_tools")
def teller_tools():
    return render_template("teller_tools.html")


@app.route("/search_name", methods=["GET", "POST"])
def search_name():
    results = []
    if request.method == "POST":
        name = request.form["name"]
        cursor.execute("SELECT * FROM accounts WHERE first_name=%s OR last_name=%s", (name, name))
        results = cursor.fetchall()
    return render_template("search_name.html", results=results)


@app.route("/search_account", methods=["GET", "POST"])
def search_account():
    results = []
    if request.method == "POST":
        acc = request.form["acc"]
        cursor.execute("SELECT * FROM accounts WHERE account_number=%s", (acc,))
        results = cursor.fetchall()
    return render_template("search_account.html", results=results)


@app.route("/delete", methods=["GET", "POST"])
def delete():
    if request.method == "POST":
        acc = request.form["acc"]
        cursor.execute("DELETE FROM accounts WHERE account_number=%s", (acc,))
        conn.commit()
    return render_template("delete.html")


if __name__ == "__main__":
    app.run()