from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify, Markup
from flask_mail import Mail, Message
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, temp_pass, usd, is_number, lookup
import os
from datetime import datetime, timezone, timedelta
import random
from card_generator import *
import html


app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True

app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = os.environ.get("email")
app.config['MAIL_PASSWORD'] = os.environ.get("password")
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)


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
db = SQL("sqlite:///database.db")
start_bank_account_id = 9351002596

if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    rows = db.execute("SELECT firstname, lastname, amount, bank_account FROM users LEFT JOIN bank_accounts ON bank_accounts.user_id=users.id WHERE id=?", session["user_id"])
    return render_template("index.html", firstname=rows[0]['firstname'], lastname=rows[0]['lastname'], amount=usd(rows[0]['amount']), account=rows[0]['bank_account'])

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect("/login")

@app.route("/login", methods=["POST", "GET"])
def login():

    session.clear()

    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        rows = db.execute("SELECT id, hash, is_closed FROM users WHERE email=?", email)

        if len(rows) == 0 or not check_password_hash(rows[0]["hash"], password):
            return render_template("login.html", message="Email/Password Incorrect!", msg_type="danger")

        if rows[0]["is_closed"]:
            return render_template("login.html", message="Account is closed!", msg_type="danger")

        session["user_id"] = rows[0]["id"]

        return redirect("/")

@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "GET":
        rows = db.execute("SELECT id, city FROM cities ORDER BY city ASC;")
        return render_template("register.html", cities=rows)
    elif request.method == "POST":
        firstname = request.form.get("FirstName")
        lastname = request.form.get("LastName")
        idNumber = request.form.get("IdNumber")
        email = request.form.get("email")
        phone = request.form.get("PhoneNumber")
        street = request.form.get("StreetAdress")
        zipCode = request.form.get("ZipCode")
        city = request.form.get("city")

        rows = db.execute("SELECT id FROM users WHERE idNumber=? OR email=?;", idNumber, email)

        if len(rows) != 0:
            return "User already exist"

        rows = db.execute("SELECT id FROM cities WHERE id=?;", city)

        if len(rows) == 0:
            return "Invalid city"

        password = temp_pass()
        hashed = generate_password_hash(password)

        user_id = db.execute("INSERT INTO users(firstname, lastname, idNumber, email, phone, address, zip, city, hash) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?);", firstname, lastname, idNumber, email, phone, street, zipCode, city, hashed)

        rows = db.execute("SELECT bank_account FROM bank_accounts ORDER BY bank_account DESC LIMIT 1")

        account_id = start_bank_account_id

        if len(rows) != 0:
            account_id = int(rows[0]["bank_account"]) + 1

        db.execute("INSERT INTO bank_accounts(bank_account, user_id) VALUES(?, ?)", account_id, user_id)

        msg = Message('Maze bank registration', sender = 'bank-mailserver@gmail.com', recipients = [email])
        msg.body = f"Hello {firstname} {lastname},\nthis is your temporary password {password}"
        mail.send(msg)

        print(password)
        msg = Markup("An email has been sent to you with your password<br><a href='/login'>Click here</a> to login")
        return render_template("register.html", msg_type="success", message=msg)

@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "GET":
        return render_template("change_password.html")
    elif request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        conf = request.form.get("confirmation")
        user_id = session["user_id"]

        rows = db.execute("SELECT * FROM users WHERE id=?", user_id)

        if not old_password:
            return render_template("change_password.html", message="Please enter your old password", msg_type="danger")

        if not new_password:
            return render_template("change_password.html", message="Please enter your new password", msg_type="danger")

        if not conf:
            return render_template("change_password.html", message="Please enter your confirmation password", msg_type="danger")

        if not check_password_hash(rows[0]['hash'], old_password):
            return render_template("change_password.html", message="Wrong Password!", msg_type="danger")

        if new_password != conf:
            return render_template("change_password.html", message="Confirmation password is different from new password!", msg_type="danger")

        db.execute("UPDATE users SET hash=? WHERE id=?", generate_password_hash(new_password), user_id)
        session.clear()
        return render_template("change_password.html", message="Password has been changed successfully!", msg_type="success")


@app.route("/close_account", methods=["GET","POST"])
@login_required
def close_account():
    if request.method == "GET":
        return render_template("close_account.html")
    elif request.method == "POST":
        user_id = session["user_id"]
        closing_date = datetime.now(timezone.utc)
        db.execute("UPDATE users SET is_closed=1, closing_date=? WHERE id=?", closing_date, user_id)
        return redirect("/login")

"""The code below use a function created by by ..:: crazyjunkie ::.. 2014"""
@app.route("/order_card", methods=["GET","POST"])
@login_required
def order_card():
    pny = ["VISA", "MASTERCARD", "AMEX"]
    if request.method == "GET":
        return render_template("order_card.html")

    elif request.method == "POST":
        user_id = session["user_id"]
        user_input = request.form.get("card")

        if user_input not in pny:
            return render_template("order_card.html", msg_type="danger", message="Payment network not valid!")

        rows = db.execute("SELECT bank_account, amount FROM bank_accounts WHERE user_id=?", user_id)
        account_id = rows[0]["bank_account"]
        balance = rows[0]["amount"]

        if balance < 15:
            return render_template("order_card.html", msg_type="danger", message="Not enough money in your bank account!")

        random.seed(datetime.now())
        cc_output = credit_card_number(user_input)[0]
        expiry_date = (datetime.now() + timedelta(days=3*365)).strftime("%m/%y")
        cvv = ''.join([str(random.randint(0,9)) for i in range(0,3)])
        pin = ''.join([str(random.randint(0,9)) for i in range(0,4)])

        db.execute("UPDATE bank_accounts SET amount=amount-15 WHERE bank_account=? AND user_id=?", account_id, user_id)
        db.execute("INSERT INTO credit_cards(card_number, expiry_date, cvv, user_id, account_id, pin, card_type) VALUES(?, ?, ?, ?, ?, ?, ?)", cc_output, expiry_date, int(cvv), user_id, account_id, int(pin), user_input)
        db.execute("INSERT INTO transfer_history(from_id, to_id, amount_trans, comment) VALUES(?, ?, ?, ?)", session["user_id"], 0, 15, "Order card fees")

        return render_template("order_card.html", msg_type="success", message="Card linked to your bank account!")


@app.route("/transfer_money", methods=["POST", "GET"])
@login_required
def transfer_money():
    if request.method == "GET":
        user_input = request.args.get("bank_account")

        if not user_input:
            user_input = ""

        return render_template("transfer_money.html", user_input=user_input)
    elif request.method == "POST":
        bank_account = request.form.get("bank_account")
        amount = request.form.get("amount")

        if not bank_account:
            return render_template("transfer_money.html", msg_type="danger", message="Recipient's Bank account field is empty!")

        if not is_number(bank_account):
            return render_template("transfer_money.html", msg_type="danger", message="Recipient's Bank account should be a number")

        if not amount:
            return render_template("transfer_money.html", msg_type="danger", message="Amount field is empty!")

        if not is_number(amount):
            return render_template("transfer_money.html", msg_type="danger", message="Amount should be a number!")

        rec = db.execute("SELECT bank_account FROM bank_accounts WHERE bank_account=?", bank_account)

        if len(rec) == 0:
            return render_template("transfer_money.html", msg_type="danger", message="Receipient not found!")

        rows = db.execute("SELECT amount FROM bank_accounts WHERE user_id=?", session["user_id"])
        balance = rows[0]["amount"]

        if float(amount) + 1 > balance:
            return render_template("transfer_money.html", msg_type="danger", message="Not enough balance!")

        db.execute("UPDATE bank_accounts SET amount=?+amount WHERE user_id=?", -float(amount)-1, session["user_id"])
        db.execute("UPDATE bank_accounts SET amount=?+amount WHERE bank_account=?", float(amount), bank_account)
        db.execute("INSERT INTO transfer_history(from_id, to_id, amount_trans, comment) VALUES(?, ?, ?, ?)", session["user_id"], bank_account, amount, "Transfer")
        db.execute("INSERT INTO transfer_history(from_id, to_id, amount_trans, comment) VALUES(?, ?, ?, ?)", session["user_id"], 0, 1, "Transfer Fees")

        return render_template("transfer_money.html", msg_type="success", message="Money sent")


@app.route("/list_favorites", methods=["POST", "GET"])
@login_required
def list_favorites():
    if request.method == "GET":
        rows = db.execute("SELECT firstname, lastname, bank_account, fav_id FROM users LEFT JOIN favorites ON users.id = favorites.fav_id LEFT JOIN bank_accounts ON favorites.fav_id=bank_accounts.user_id WHERE favorites.user_id=? ORDER BY firstname ASC;", session["user_id"])
        return render_template("list.html", rows=rows, length=len(rows))
    elif request.method == "POST":
        user_input = request.form.get("favorite")
        final = db.execute("SELECT firstname, lastname, bank_account FROM users LEFT JOIN favorites ON users.id = favorites.fav_id LEFT JOIN bank_accounts ON favorites.fav_id=bank_accounts.user_id WHERE favorites.user_id=? ORDER BY firstname ASC;", session["user_id"])

        if not user_input:
            return render_template("list.html", msg_type="danger", message="Please input an email address!", rows=final, length=len(final))

        rows = db.execute("SELECT id FROM users WHERE email=?", user_input)

        if len(rows) == 0:
            return render_template("list.html", msg_type="danger", message="User not found!", rows=final, length=len(final))

        temp = rows[0]["id"]

        if session["user_id"] == temp:
            return render_template("list.html", msg_type="danger", message="You can't add yourself!", rows=final, length=len(final))

        rows =  db.execute("SELECT * FROM favorites WHERE user_id=? AND fav_id=?", session["user_id"], temp)

        if len(rows) != 0:
            return render_template("list.html", msg_type="danger", message="This is user is already in your list", rows=final, length=len(final))

        db.execute("INSERT INTO favorites(user_id, fav_id) VALUES(?, ?)", session["user_id"], temp)
        final = db.execute("SELECT firstname, lastname, bank_account, fav_id FROM users LEFT JOIN favorites ON users.id = favorites.fav_id LEFT JOIN bank_accounts ON favorites.fav_id=bank_accounts.user_id WHERE favorites.user_id=? ORDER BY firstname ASC;", session["user_id"])

        return render_template("list.html", msg_type="success", message="User added to favorite!", rows=final, length=len(final))

@app.route("/remove_favorite")
@login_required
def remove_favorite():
    user_id = request.args.get("id")

    if not user_id:
        return redirect("/list_favorites")

    db.execute("DELETE FROM favorites WHERE user_id=? AND fav_id=?", session["user_id"], user_id)
    return redirect("/list_favorites")


@app.route("/operations_history")
@login_required
def operations_history():
    #rows = db.execute("SELECT * FROM transfer_history LEFT JOIN bank_accounts ON to_id=bank_account WHERE from_id=? OR bank_accounts.user_id=?", session["user_id"], session["user_id"])
    rows = db.execute("SELECT t1.date as date, t1.from_id as from_id, t4.firstname as send_first, t4.lastname as send_last, t2.user_id as to_id, t3.firstname as rec_first, t3.lastname as rec_last, t1.amount_trans as amount, t1.comment as comment\
    FROM transfer_history as t1 \
    LEFT JOIN bank_accounts as t2 ON t1.to_id=t2.bank_account \
    LEFT JOIN users as t3 ON t2.user_id=t3.id \
    LEFT JOIN users as t4 ON t1.from_id=t4.id \
    WHERE from_id=? OR t2.user_id=? ORDER by t1.date DESC;", session["user_id"], session["user_id"])
    return render_template("op_history.html", rows=rows, user=session["user_id"], usd=usd)


""" The code below part of it used from the finance project """
@app.route("/quote", methods=["POST", "GET"])
@login_required
def quote():
    if request.method == "GET":
        return render_template("quote.html")
    elif request.method == "POST":
        user_input = request.form.get("symbol")

        if not user_input:
            return render_template("quote.html", message="Please type in a symbol!", msg_type="danger")

        result = lookup(user_input)

        if not result:
            return render_template("quote.html", message="Symbol not valid!", msg_type="danger")

        price = usd(result['price'])
        message = f"{result['name']} is worth {price}"
        return render_template("quote.html", message=message, msg_type="success")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        number = request.form.get("shares")
        result = lookup(symbol)
        if not symbol:
            return render_template("buy.html", message="Please type in a symbol!", msg_type="danger")

        if not number:
            return render_template("buy.html", message="Please type in the number of shares", msg_type="danger")

        if not is_number(number):
            return render_template("buy.html", message="Only numbers!", msg_type="danger")

        if float(number) % 1 != 0 or float(number) <= 0:
            return render_template("buy.html", message="Invalid number!", msg_type="danger")

        number = float(number)

        if result == None:
            return render_template("buy.html", message="Invalid Symbol!", msg_type="danger")

        rows = db.execute("SELECT amount FROM bank_accounts WHERE user_id=?", session["user_id"])
        price = result['price']
        symbol_name = result['name']
        balance = rows[0]['amount']
        total = number*price

        if total > float(balance):
            return render_template("buy.html", message="You don't have enough money!", msg_type="danger")


        db.execute("UPDATE bank_accounts SET amount=?+amount WHERE user_id=?", -total, session["user_id"])
        db.execute("INSERT INTO transactions (user_id, action, symbol, symbol_name, quantity, unit_price) VALUES (?, 'buy', ?, ?, ?, ?)",
                    session["user_id"], symbol.upper(), symbol_name, number, price)


        message = f"{symbol_name} bought for {usd(price)} each.<br>Quantity: {number}<br>Total: {total}"

        return render_template("buy.html", message=Markup(message), msg_type="success")

    else:
        return render_template("buy.html")


@app.route("/sell", methods=["POST", "GET"])
@login_required
def sell():
    symbols = db.execute("SELECT user_id, symbol, symbol_name, SUM(quantity) as sum FROM transactions WHERE user_id=? GROUP BY symbol HAVING SUM > 0", session["user_id"])
    if request.method == "GET":
        return render_template("sell.html", rows=symbols)

    elif request.method == "POST":
        symbol = request.form.get("symbol")
        number = request.form.get("share")

        if not symbol:
            return render_template("sell.html", rows=symbols, message="Invalid symbol!", msg_type="danger")

        rows = db.execute("SELECT user_id, symbol, symbol_name, SUM(quantity) as sum FROM transactions WHERE user_id=? AND symbol=? GROUP BY symbol HAVING SUM > 0", session["user_id"], symbol)

        if len(rows) == 0:
            return render_template("sell.html", rows=symbols, message=f"You don't have any shares from {symbol}!", msg_type="danger")

        if not number:
            return render_template("sell.html", rows=symbols, message="Please type in the number of shares", msg_type="danger")

        if not is_number(number):
            return render_template("sell.html", rows=symbols, message="Only numbers!", msg_type="danger")

        if float(number) % 1 != 0 or float(number) <= 0:
            return render_template("sell.html", rows=symbols, message="Invalid number!", msg_type="danger")

        number = float(number)

        if number > rows[0]['SUM']:
            return render_template("sell.html", rows=symbols, message="Too much shares!", msg_type="danger")

        price = lookup(symbol)['price']
        db.execute("INSERT INTO transactions (user_id, action, symbol, symbol_name, quantity, unit_price) VALUES (?, 'sell', ?, ?, ?, ?)",
                   session['user_id'], rows[0]["symbol"], rows[0]["symbol_name"], -number, price)
        db.execute("UPDATE bank_accounts SET amount=?+amount WHERE user_id=?", number * price, session["user_id"])

        symbols = db.execute("SELECT user_id, symbol, symbol_name, SUM(quantity) as sum FROM transactions WHERE user_id=? GROUP BY symbol HAVING SUM > 0", session["user_id"])
        return render_template("sell.html", rows=symbols, msg_type="success", message=f"{number} shares of {symbol} sold!")


@app.route("/history")
@login_required
def history():
    rows = db.execute("SELECT transaction_id, symbol, symbol_name, quantity, action, unit_price, date FROM transactions WHERE user_id=? ORDER BY date DESC;", session['user_id'])
    return render_template("history.html", rows=rows, usd=usd)


@app.route("/portfolio")
@login_required
def portfolio():
    rows = db.execute("SELECT user_id, symbol, symbol_name, SUM(quantity) as sum FROM transactions WHERE user_id=? GROUP BY symbol HAVING SUM > 0", session["user_id"])
    amount = db.execute("SELECT amount FROM bank_accounts WHERE user_id=?", session["user_id"])[0]['amount']
    total = amount
    for row in rows:
        total += row['SUM'] * lookup(row['symbol'])['price']

    return render_template("portfolio.html", rows=rows, lookup=lookup, usd=usd, amount=usd(amount), total=usd(total))
