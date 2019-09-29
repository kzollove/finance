import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime as dt
from helpers import apology, login_required, lookup, usd

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

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("postgres://baewqmlznuckhs:8c14518e3d4748129b33d9f9a20d6784cb398f0801586bf41d50c091b67609c8@ec2-23-23-182-18.compute-1.amazonaws.com:5432/d6kjpfs837okbf")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    ID=session['user_id']
    sharesList = db.execute("SELECT shares, name, symbol FROM holdings JOIN stocks ON holdings.stock_id=stocks.id WHERE user_id=:ID GROUP BY name",
                            ID=ID)

    username = db.execute("SELECT username FROM users WHERE id=:user_id", user_id=ID)[0]['username']
    #return f"{sharesList}"
    for share in sharesList:
        share['current'] = usd(lookup(share['symbol'])['price'])
        share['val'] = usd(lookup(share['symbol'])['price'] * share['shares'])

    return render_template("index.html", shares=sharesList, username=username)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "GET":
        return render_template("buy.html")

    if request.method == "POST":

        #ensure that symbol is valid number of letters
        if not request.form.get("symbol"):
            return apology("must provide valid symbol", 403)

        #ensure that shares is an integer
        try:
            if int(request.form.get("shares")) < 1:
                return apology("must provide valid number of shares", 403)
        except ValueError:
                return apology("must provide valid number of shares", 403)

        user_id=session["user_id"]
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))
        stockObj = lookup(symbol)
        price = stockObj['price']
        cost = price * shares
        funds = db.execute("SELECT cash FROM users WHERE id=:ID",
                            ID=user_id)[0]['cash']

        #make sure the user has enough cash for requested funds
        if cost > funds:
            return apology("insufficient funds", 403)

        #if stock is not listed in db, add it. Get stock_id from stocks
        stock = db.execute("SELECT * FROM stocks WHERE symbol=:symbol",
                            symbol=stockObj['symbol'])
        if not stock:
            db.execute("INSERT INTO stocks (name, symbol) VALUES (:name, :symbol)",
                        name=stockObj['name'], symbol=stockObj['symbol'])
        stock_id = db.execute("SELECT id FROM stocks WHERE symbol=:symbol",
                            symbol=stockObj['symbol'])[0]['id']

        #Add record of purchase, add stock to holdings  subtract cash from users profile
        print(f"{user_id},{stock_id},{shares},{price}")
        db.execute("INSERT INTO purchases (user_id, stock_id, shares, price) VALUES (:user_id, :stock_id, :shares, :price)",
                    user_id=user_id, stock_id=stock_id, shares=shares, price=price)
        #Check if user already owns this stock
        current = db.execute("SELECT shares FROM holdings WHERE stock_id=:stock_id AND user_id=:user_id",
                            stock_id=stock_id, user_id=user_id)

        #new holding if none of stock owned
        if not current:
            db.execute("INSERT INTO holdings (user_id, stock_id, shares) VALUES (:user_id, :stock_id, :shares)",
                        user_id=user_id, stock_id=stock_id, shares=shares)
        #update holding record if owned
        else:
            db.execute("UPDATE holdings SET shares=:current WHERE stock_id=:stock_id AND user_id=:user_id",
                        current=current[0]['shares']+shares,  stock_id=stock_id, user_id=user_id)

        db.execute("UPDATE users SET cash=:newCash WHERE id=:user_id", newCash=funds-cost, user_id=user_id)

    return redirect("/")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""

    username=request.args.get('username')
    checker = db.execute("SELECT username FROM users WHERE username=:username", username=username)
    if checker:
        return jsonify(True)
    else:
        return jsonify(False)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    ID=session['user_id']

    #This SQL call combines the rows from liquidations and purchases, ordered by date.
    #It then joins the wh
    hist = db.execute("SELECT * FROM stocks JOIN (SELECT stock_id, shares, date, price,'Purchase' AS Type FROM purchases WHERE user_id=:ID UNION ALL SELECT stock_id, shares, date, price, 'Sale' FROM liquidations WHERE user_id=:ID ORDER BY date) foo ON stocks.id=foo.stock_id",
                        ID=ID)

    for row in hist:
        row['tp']=usd(float(row['price']*int(row['shares'])))
        row['date']=dt.strptime(row['date'], "%Y-%m-%d %H:%M:%S").strftime("%B %d, %Y at %H:%M")

    return render_template("history.html", hist=hist)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("must provide symbol", 403)
        else:
            symbol = request.form.getlist("symbol")
            qList = []
            for s in symbol:
                qList.append(lookup(s.upper()))
            for p in qList:
                try:
                    p['price']=usd(p['price'])
                except TypeError:
                    pass

            return render_template("quoted.html", quote=qList)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    #User reached route via post (submitted registration form)
    if request.method == "POST":

        #ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        #ensure password was submitted
        if not request.form.get("password"):
            return apology("must provide password", 403)

        #ensure password and confirmation match
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("password must match confirmation", 403)

        #query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                            username=request.form.get("username"))
        #ensure username is unique
        if len(rows):
            return apology("username already in use", 403)

        #hash password
        newHash = generate_password_hash(password=request.form.get("password"))

        #insert username into db
        db.execute("INSERT INTO users ('username', 'hash') VALUES (:username, :newHash)",
                                            username=request.form.get("username"), newHash=newHash)

        return redirect("/login")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    ID=session["user_id"]
    stocks=db.execute("SELECT shares, name, symbol FROM holdings JOIN stocks ON holdings.stock_id=stocks.id WHERE user_id=:ID GROUP BY name", ID=ID)

    if request.method == "GET":
        return render_template("sell.html", stocks=stocks)

    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("must provide valid symbol", 403)
        symbol = request.form.get("symbol")
        stockObj=lookup(symbol)
        shares = int(request.form.get("shares"))
        held = 0
        for stock in stocks:
            if symbol in stock['symbol']:
                held=int(stock['shares'])
        cost = lookup(symbol)['price']
        current=held-shares


        funds = db.execute("SELECT cash FROM users WHERE id=:ID",
                            ID=ID)[0]['cash']
        try:
            if shares < 1 or shares > held:
                return apology("must provide valid number of shares", 403)
        except ValueError:
                return apology("must provide valid number of shares", 403)

        stock_id = db.execute("SELECT id FROM stocks WHERE symbol=:symbol",
                            symbol=stockObj['symbol'])[0]['id']
        #add to liquidations
        db.execute("INSERT INTO liquidations (user_id, stock_id, shares, price) VALUES (:ID, :stock_id, :shares, :cost)",
                    ID=ID, stock_id=stock_id, shares=shares, cost=cost)


        #if all stocks were sold remove from holdings
        if not current:
            db.execute("DELETE FROM holdings WHERE stock_id=:stock_id", stock_id=stock_id)

        #remove from holdings
        db.execute("UPDATE holdings SET shares=:current WHERE stock_id=:stock_id AND user_id=:user_id",
                        current=current, stock_id=stock_id, user_id=ID)
        #update cash
        db.execute("UPDATE users SET cash=:newCash WHERE id=:ID", newCash=funds+cost, ID=ID)

    return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
