from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
import time

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required

def index():
    rows = db.execute("SELECT shares, symbol FROM portfolio WHERE id=:id", id=session["user_id"])
    for row in rows:
        symbol = row["symbol"]
        shares = row["shares"]
        look = lookup(symbol)
        value = shares*look["price"]
        
        db.execute("UPDATE portfolio SET current_price=:price, \
            stock_value=:value \
            WHERE id=:id AND symbol=:symbol", \
            price=look["price"], \
            value=value,\
            id=session["user_id"], symbol=symbol)
    c = db.execute ("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
    cash = usd(c[0]["cash"])
    
    current_rows = db.execute("SELECT * FROM portfolio WHERE id=:id",\
                        id=session["user_id"])
    values = db.execute("SELECT sum(stock_value) FROM portfolio WHERE id=:id", id=session["user_id"])
    total = usd(values[0]["sum(stock_value)"] + c[0]["cash"])

    return render_template("index.html", current_rows = current_rows, cash = cash, total = total) ##, total = total
    
#return render_templace("index.html")

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    c = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
    cash = usd(c[0]["cash"])
    if request.method == "POST":
           
        # look up stock information
        stock = lookup(request.form.get("stock"))
        shares = int(request.form.get("shares"))
        user_id = session["user_id"]
        
        # return error if not a valid stock or valid number of shares
        if not stock:
            return apology("Invalid stock symbol")
        
        if shares < 0:
            return apology("must suppy valid number")
            
        # check to make sure that the user has enough money to purchase the requested stocks
        avail_cash = db.execute ("SELECT cash FROM users WHERE id=:id", id=user_id)
        purchase_price = stock["price"]*shares
        
        if float(avail_cash[0]["cash"]) < purchase_price:
            return apology ("Insufficient funds")
        
        # update cash in user table
        db.execute("UPDATE users SET cash = cash-:purchase WHERE id=:id", purchase = purchase_price, id = user_id)
        
        # insert sale into histories table
        date = time.strftime('%Y-%m-%d %H:%M:%S')
        result = db.execute("INSERT INTO histories (shares, symbol, name, id, price, buyDATE) \
                        VALUES (:shares, :symbol, :name, :id, :price, :buyDATE)", \
                        shares=shares, symbol=stock["symbol"], name=stock["name"], id=user_id, price=purchase_price, buyDATE=date)

        if not result:
            return apology("Share info not in portfolio")
        #select share 
        my_share = db.execute("SELECT shares FROM portfolio WHERE id=:id AND symbol=:symbol", \
                                id=user_id, symbol=stock["symbol"])
        # update shares in portfolio
        if my_share:
            db.execute("UPDATE portfolio SET shares = shares +:shares WHERE id=:id AND symbol=:symbol",\
                        shares=shares, id=user_id, symbol=stock["symbol"])    
        else:

            db.execute("INSERT INTO portfolio (shares, symbol, name, id) \
                        VALUES (:shares, :symbol, :name, :id)", \
                        shares=shares, symbol=stock["symbol"], name=stock["name"], id=user_id)

        return render_template("bought.html", cash = cash, stock = stock)
    else:
        return render_template("buy.html", cash = cash)

@app.route("/history")
@login_required
def history():
    
    c = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
    cash = usd(c[0]["cash"])
    
    """Show history of transactions."""
    rows = db.execute("SELECT * FROM histories WHERE id=:id", id=session["user_id"])
    
    return render_template("history.html", rows=rows, cash=cash)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    
    c = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
    cash = usd(c[0]["cash"])
    """Get stock quote."""

    if request.method == "POST":

        rows = lookup(request.form.get("symbol"))

        if not rows:
            return apology("Invalid stock symbol")
        
        return render_template("quoted.html", quote=rows, cash=cash)
    
    else:
        return render_template("quote.html", cash=cash)
    
    #return apology("TODO")
        

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    if request.method == "POST": 
        # Make sure user provides username, email and password.
        if request.form.get("username") is "":
            return apology("Must provide a username")
        
        elif request.form.get("password") is "":
            return apology("Must provide a password")

        elif request.form.get("password") != request.form.get("password2"):
            return apology("Password and confirmation must match")
        
        elif request.form.get("email") is "":
            return apology("Must provide email")
        
        user = request.form.get("username")
        hashed = pwd_context.hash(request.form.get("password"))
        email = request.form.get("email")
        
        result = db.execute("INSERT INTO users (username, hash, email) VALUES (:username, :hash, :email)", username=user, hash=hashed, email=email)
        
        if not result:
            return apology("You have NOT registered")
        
        user_id = db.execute("SELECT * FROM users WHERE username=:username", username=user)
        session["user_id"] = result 
    
        return redirect(url_for("index"))
    
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    c = db.execute("SELECT cash FROM users WHERE id=:id", id=session["user_id"])
    cash = usd(c[0]["cash"])
    """Sell shares of stock."""

    if request.method == "POST":
           
        # get information from user about what stock to sell
        stock = lookup(request.form.get("stock"))
        shares = int(request.form.get("shares"))
        user_id = session["user_id"]
        
        if not stock:
            return apology("This is not a valid stock symbol")
        sell_stock = db.execute("SELECT symbol FROM portfolio WHERE symbol=:symbol AND id=:id", symbol=stock["symbol"], id=user_id)       
        
        # return error if not a valid stock
        if not sell_stock:
            return apology("You do not have that stock to sell")
        
        # make sure they have enough stocks to sell
        sell_shares = db.execute("SELECT shares FROM portfolio WHERE id=:id AND symbol=:stock",\
                                id=user_id, stock=stock["symbol"])
        
        if not sell_shares or int(sell_shares[0]["shares"]) < shares:
            return apology("You do not have that many shares to sell")
            
        # select cash to enable ability to add sale price
        add_cash = db.execute ("SELECT cash FROM users WHERE id=:id", id=user_id)
        sell_price = float(stock["price"])*float(shares)
        
        # update cash in user table
        db.execute("UPDATE users SET cash = cash + :sale WHERE id=:id", sale = sell_price, id = user_id)
        
        # insert sale into histories table  
        date = time.strftime('%Y-%m-%d %H:%M:%S')
        result = db.execute("INSERT INTO histories (shares, symbol, name, id, price, sellDATE) \
                        VALUES (:shares, :symbol, :name, :id, :price, :sellDATE)", \
                        shares=shares, symbol=stock["symbol"], name=stock["name"], id=user_id, price=sell_price, sellDATE=date)

        if not result:
            return apology("Share info not in history")
        
        # update shares in portfolio

        port = db.execute("UPDATE portfolio SET shares = shares -:shares WHERE id=:id AND symbol=:symbol",\
                        shares=shares, id=user_id, symbol=stock["symbol"])    

        if not port:
            return apology("Information not in portfolio")
        
        return render_template("sold.html", cash=cash, stock = stock)
    else:
        return render_template("sell.html", cash=cash) 
        
# A way to change the password if user has forgetten their password
@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    """Change forgotten password"""
    
    # if user reached route via POST
    if request.method == "POST":
        
        get_email = request.form.get("email")
        
        # make sure user provides all iformation needed
        if get_email is "":
            return apology("Must provide valid email")
        
        elif request.form.get("password") is "":
            return apology("Must provide a password")

        elif request.form.get("password") != request.form.get("password2"):
            return apology("Password and confirmation must match")    

        # query the database for email
        db_email = db.execute("SELECT * FROM users WHERE email = :email", email = get_email)
        
        # ensure email is in database
        if (len(db_email) != 1):
            return apology("email doesn't exist")
        
        # hash the new password and update the database
        new_pw = request.form.get("password")
        hashed = pwd_context.hash(new_pw)
        result = db.execute("UPDATE users SET hash = :hash", hash = hashed)
        if not result:
            return apology("password could not be changed")
        
        # keep the user logded in
        session["user_id"] = db_email[0]["id"]
            
        #return render_template("pwchngd.html", db_email=db_email, get_email=get_email)
        return redirect(url_for("index"))
    
    # else if user reached route via GET    
    else:    
        return render_template("forgot.html")     

        
    