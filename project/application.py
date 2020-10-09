import os

import re
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///words.db")

@app.route("/")
@login_required
def index():
    rows = db.execute("SELECT kanji, SUM(count) as total FROM wordbank WHERE user_id = :user_id GROUP BY kanji ORDER BY total DESC",user_id=session["user_id"])
    index = []
    for row in rows:
        index.append({"kanji" :row["kanji"], "total" : row["total"]})
    return render_template("table.html", index = index)

@app.route("/update", methods=["GET", "POST"])
@login_required
def update():

    if request.method == "GET":
        return render_template("update.html")
    else:
        text = request.form.get("text").upper()
        text = re.sub('[(),!.?]', '', text)
        words = text.split()
        for i in words:
            db.execute("INSERT INTO database (user_id, kanji, count) VALUES(:user_id, :kanji, :count)",
                user_id=session["user_id"], kanji = i, count = 1)

        return redirect("/filter")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Please enter username")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Please enter a password")
            return render_template("login.html")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Invalid username or password")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")

        if not username:
            flash("Please enter a username!")
            return render_template("register.html")


        password = request.form.get("password")
        password2 = request.form.get("password2")

        if password != password2:
            flash("Passwords do not match!")
            return render_template("register.html")
        elif not password or not password2:
            flash("Please provide a password")
            return render_template("register.html")

        if db.execute("SELECT * FROM users WHERE username = :username", username=username):
            flash("Username is already in use")
            return render_template("register.html")

        row = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=username, hash=generate_password_hash(password))
        session["user_id"] = row
        return redirect("/")

@app.route("/remove", methods=["GET", "POST"])
@login_required
def remove():
    if request.method == "GET":
        rows = db.execute("SELECT kanji, SUM(count) as total FROM wordbank WHERE user_id = :user_id GROUP BY kanji  ORDER BY total DESC", user_id=session["user_id"])
        index = []
        for row in rows:
            index.append({"kanji" :row["kanji"]})
        return render_template("remove.html", index=index)

    else:
        kanji = request.form.get("kanji").upper()
        db.execute("DELETE FROM wordbank WHERE user_id = :user_id AND kanji = :kanji", user_id=session["user_id"], kanji=kanji)
        return redirect("/")

@app.route("/filter", methods=["GET", "POST"])
def filter():
    if request.method == "GET":
        rows = db.execute("SELECT kanji, SUM(count) as total FROM database WHERE user_id = :user_id GROUP BY kanji ORDER BY total DESC",user_id=session["user_id"])
        index = []
        for row in rows:
            index.append({"kanji" :row["kanji"], "total" : row["total"]})
        return render_template("filter.html", index=index)

    else:
        kanji = request.form.getlist("kanji")
        for row in kanji:
            db.execute("INSERT INTO wordbank (user_id, kanji, count) VALUES(:user_id, :kanji, :count)",user_id=session["user_id"], kanji = row, count = 1)
        db.execute("DELETE FROM database WHERE user_id = :user_id", user_id=session["user_id"])
        return redirect("/")