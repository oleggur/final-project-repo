from flask import Flask, render_template, flash, request, redirect, session, send_file
from flask_session import Session
from cs50 import SQL
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required
from datetime import datetime, date
import csv
import os
from shutil import rmtree



#initialize web app
app = Flask(__name__)
app.secret_key = "bananaapple"

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)



# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///database.db")



@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        # get form data
        username = request.form.get("username")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")

        # get usernames already in database to check later
        existing_user = db.execute("SELECT username, user_id FROM Users WHERE username = ?;", username)

        if not username or not password1:
            flash("Username or password were not provided", "error")
            return redirect("/register")
        elif not username.isalnum():
            flash("Username must only contain letters and numbers", "error")
            return redirect("/register")
        elif password1 != password2:
            flash("Passwords do not match", "error")
            return redirect("/register")
        elif len(username) > 8 or len(username) < 1 or len(password1) > 8 or len(password1) < 1:
            flash("Invalid username or password provided", "error")
            return redirect("/register")
        # if username already exists:
        elif len(existing_user) != 0:
            flash("Username already exists", "error")
            return redirect("/register")

        #if everything ok
        else:
            db.execute("INSERT INTO Users(username, hash) VALUES(?, ?);", username, generate_password_hash(password1))
            # log him in
            session.clear()
            session["sort_count"] = 0
            session["user_id"] = db.execute("SELECT user_id FROM Users WHERE username = ?;", username)[0]["user_id"]
            flash("Registered! You can now use the app", "success")
            return redirect("/about")


@app.route('/login', methods=["GET", "POST"])
def login():
    try:
        if session["user_id"]:
            flash("You were logged out!")
            session.clear()
    except KeyError:
        pass
    if request.method == "GET":
        return render_template("login.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        users = db.execute("SELECT username, hash FROM Users WHERE username = ?;", username)
        if not username or not password:
            flash("Username or password not provided", "error")
            return redirect('/login')
        elif len(users) != 1:
            flash("Wrong username or password", "error")
            return redirect('/login')
        elif not check_password_hash(users[0]["hash"], password):
            flash("Wrong username or password", "error")
            return redirect('/login')
        else:
            # log him in if everything ok
            session.clear()
            session["sort_count"] = 0
            session["user_id"] = db.execute("SELECT user_id FROM Users WHERE username = ?;", username)[0]["user_id"]
        return redirect("/")


@app.route("/logout")
def logout():

    # Forget any user_id
    session.clear()
    flash("Logged out!", "success")

    # Redirect user to login form
    return redirect("/login")



@app.route('/', methods=["GET", "POST"])
@login_required
def index():
    rows = db.execute("SELECT * FROM Transactions WHERE user_id = ? ORDER BY date DESC;", session["user_id"])
    if request.method == "GET":
        return render_template("index.html", rows=rows)
    else:
        exist_trans = request.form.get("exist_trans")
        if exist_trans:
            db.execute("DELETE FROM Transactions WHERE user_id = ? AND trans_id = ?;", session["user_id"], exist_trans)
            return redirect("/")
        return redirect("/new")

@app.route('/profile', methods=["GET", "POST"])
@login_required
def profile():
    rows = db.execute("SELECT username, date FROM Users WHERE user_id = ?;", session["user_id"])
    if request.args.get("action") == "delete_account":
        username = rows[0]["username"]
        if os.path.exists(f"export/{username}"):
            rmtree(f"export/{username}")
        db.execute("DELETE FROM Users WHERE user_id = ?;", session["user_id"])
        session.clear()
        flash("Account deleted!", "success")
        return redirect("/login")
    elif request.args.get("action") == "change_pass":
        return redirect("/change")
    return render_template("profile.html", username=rows[0]["username"], date=rows[0]["date"][0:10])


@app.route('/change', methods=["GET", "POST"])
@login_required
def change():
    if request.method == "GET":
        return render_template("change.html")
    else:
        old_pas1 = request.form.get("old_pas1")
        old_pas2 = request.form.get("old_pas2")
        new_pas = request.form.get("new_pas")

        if not old_pas1 or not old_pas2:
            flash("Please enter old password and confirmation", "error")
            return redirect("/change")
        elif old_pas1 != old_pas2:
            flash("Passwords do not match", "error")
            return redirect("/change")
        elif not new_pas:
            flash("New password not provided", "error")
            return redirect("/change")
        elif len(new_pas) > 8 or len(new_pas) < 1:
            flash("Please provide a valid password. Max 8 characters", "error")
            return redirect("/change")
        # check old password
        else:
            hash = db.execute("SELECT hash FROM Users WHERE user_id = ?;", session["user_id"])[0]["hash"]
            if not check_password_hash(hash, old_pas1):
                flash("Old password is incorrect, try again", "error")
                return redirect("/change")
            else:
                if old_pas1 == new_pas:
                    flash("Password was not changed as the new password matches the old one", "success")
                else:
                    db.execute("UPDATE Users SET hash = ? WHERE user_id = ?;", generate_password_hash(new_pas), session["user_id"])
                    flash("Password changed", "success")
                return redirect("/profile")


@app.route('/new', methods=["GET", "POST"])
@login_required
def new():
    if request.method == "GET":
        cur_date = date.today()
        rows = db.execute("SELECT name FROM Categories WHERE user_id = ?;", session["user_id"])
        return render_template("new.html", rows=rows, cur_date=cur_date)
    else:
        type = request.form.get("type")
        trans_date = request.form.get("date")
        category = request.form.get("category")
        if not category:
            flash("Please choose category", "error")
            return redirect("/new")
        amount = request.form.get("amount")
        currency = request.form.get("currency")
        note = request.form.get("note")
        db.execute("INSERT INTO Transactions(date, user_id, type, category, amount, currency, note) VALUES(?, ?, ?, ?, ?, ?, ?);", trans_date, session["user_id"], type, category, amount, currency, note)
        flash('Transaction added! <a href="/" class="alert-link">Back to home page<a>', 'success')
        return redirect("/new")


@app.route('/categories', methods=["GET", "POST"])
@login_required
def categories():
    rows = db.execute("SELECT name FROM Categories WHERE user_id = ?;", session["user_id"])
    if request.method == "GET":
        return render_template("categories.html", rows=rows)
    else:
        name = request.form.get("name")
        if name:
            names = [row["name"] for row in rows]
            if name in names:
                flash("This category already exists!", "error")
                return redirect("/categories")
            else:
                db.execute("INSERT INTO Categories(user_id, name) VALUES(?, ?);", session["user_id"], name)
                return redirect("/categories")
        else:
            to_delete = request.form.get("exist_name")
            db.execute("DELETE FROM Categories WHERE user_id = ? AND name = ?;", session["user_id"], to_delete)
            return redirect("/categories")

@app.route("/about")
@login_required
def about():
    return render_template("about.html")


@app.route("/stats")
@login_required
def stats():
    rows = []

    total_exp = db.execute("SELECT SUM(amount) AS sum, currency FROM Transactions WHERE user_id = ? AND type = 'Expense' AND currency = 'USD' GROUP BY currency;", session["user_id"])
    total_inc = db.execute("SELECT SUM(amount) AS sum, currency FROM Transactions WHERE user_id = ? AND type = 'Income' AND currency = 'USD' GROUP BY currency;", session["user_id"])
    if total_exp:
        total_exp = total_exp[0]["sum"]
    else:
        total_exp = 0
    if total_inc:
        total_inc = total_inc[0]["sum"]
    else:
        total_inc = 0


    type = request.args.get("type", "expense")
    cat = request.args.get("cat")
    sort = request.args.get("sort", "amount")
    session["sort_count"] += 1


    # if user clicked a specific category
    if cat:
        if sort in ["date", "type", "category", "amount", "note"]:
            if session.get("sort_count") % 2 == 0:
                rows = db.execute(f"SELECT date, type, category, amount, note FROM Transactions WHERE user_id = ? AND currency = 'USD' AND category = ? ORDER BY {sort} DESC;", session["user_id"], cat)
            else:
                rows = db.execute(f"SELECT date, type, category, amount, note FROM Transactions WHERE user_id = ? AND currency = 'USD' AND category = ? ORDER BY {sort};", session["user_id"], cat)
        else:
            flash("Wrong sorting argument provided. Try again")
            return redirect("/stats")
        return render_template("stats.html", type=type, cat=cat, total_exp=total_exp, total_inc=total_inc, rows=rows)


    # if user did not click a category yet
    else:
        if sort in ["category", "amount"]:
            if session.get("sort_count") % 2 == 0:
                exp_by_type = db.execute(f"SELECT SUM(amount) AS amount, category FROM Transactions WHERE user_id = ? AND type = 'Expense' AND currency = 'USD' GROUP BY category ORDER BY {sort} DESC;", session["user_id"])
                inc_by_type = db.execute(f"SELECT SUM(amount) AS amount, category FROM Transactions WHERE user_id = ? AND type = 'Income' AND currency = 'USD' GROUP BY category ORDER BY {sort} DESC;", session["user_id"])
            else:
                exp_by_type = db.execute(f"SELECT SUM(amount) AS amount, category FROM Transactions WHERE user_id = ? AND type = 'Expense' AND currency = 'USD' GROUP BY category ORDER BY {sort};", session["user_id"])
                inc_by_type = db.execute(f"SELECT SUM(amount) AS amount, category FROM Transactions WHERE user_id = ? AND type = 'Income' AND currency = 'USD' GROUP BY category ORDER BY {sort};", session["user_id"])
        else:
            flash("Wrong sorting argument provided. Try again")
            return redirect("/stats")
        return render_template("stats.html", type=type, total_exp=total_exp, total_inc=total_inc, exp_by_type=exp_by_type, inc_by_type=inc_by_type)

@app.route("/export")
@login_required
def export():
    can_export = False
    to_write = db.execute("SELECT date, type, category, amount, currency, note FROM Transactions WHERE user_id = ?;", session["user_id"])
    if to_write:
        can_export = True
    if not request.args.get("download"):
        return render_template("export.html", can_export=can_export)

    # if user clicks download button
    else:
        username = db.execute("SELECT username FROM Users WHERE user_id = ?;", session["user_id"])[0]["username"]
        filename = f"{username}_{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.csv"
        path = f"export/{username}/{filename}"
        if not os.path.exists(f"export/{username}"):
            os.mkdir(f"export/{username}")

        header = to_write[0].keys()
        with open(path, "w", encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=header)
            writer.writeheader()
            for item in to_write:
                writer.writerow(item)
        return send_file(path)

