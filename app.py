import sqlite3
from datetime import date

import numpy as np

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from database import DATABASE_PATH, create_database
from ml.predict_category import predict_category


# ==========================================
# 1. CREATE FLASK APPLICATION
# ==========================================

app = Flask(__name__)

app.config["SECRET_KEY"] = "my-finance-secret-key-123"


# ==========================================
# 2. FLASK LOGIN CONFIGURATION
# ==========================================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ==========================================
# 3. DATABASE CONNECTION
# ==========================================

def get_db_connection():

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


# ==========================================
# 4. SHOPPING CATEGORY CORRECTION
# ==========================================

def correct_expense_category(description, transaction_type, category):

    clothing_keywords = [
        "clothes",
        "clothing",
        "shirt",
        "shirts",
        "jeans",
        "dress",
        "dresses",
        "shoes",
        "sneakers",
        "jacket",
        "jackets",
        "trousers",
        "pants",
        "shopping"
    ]

    if transaction_type == "Expense":

        description_lower = description.lower()

        if any(word in description_lower for word in clothing_keywords):
            return "Shopping"

    return category


# ==========================================
# 5. USER CLASS
# ==========================================

class User(UserMixin):

    def __init__(self, user_id, name, email):

        self.id = user_id
        self.name = name
        self.email = email


# ==========================================
# 6. LOAD USER
# ==========================================

@login_manager.user_loader
def load_user(user_id):

    conn = get_db_connection()

    try:

        user = conn.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()

    finally:

        conn.close()

    if user:

        return User(
            user["user_id"],
            user["name"],
            user["email"]
        )

    return None


# ==========================================
# 7. HOME PAGE
# ==========================================

@app.route("/")
def index():

    if current_user.is_authenticated:

        return redirect(url_for("dashboard"))

    return render_template("index.html")


# ==========================================
# 8. USER REGISTRATION
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:

        return redirect(url_for("dashboard"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password or not confirm_password:

            flash("Please fill in all fields.")

        elif "@" not in email or "." not in email:

            flash("Please enter a valid email address.")

        elif len(password) < 8:

            flash("Password must contain at least 8 characters.")

        elif password != confirm_password:

            flash("Passwords do not match.")

        else:

            password_hash = generate_password_hash(password)

            conn = get_db_connection()

            try:

                conn.execute(
                    """
                    INSERT INTO users (name, email, password_hash)
                    VALUES (?, ?, ?)
                    """,
                    (name, email, password_hash)
                )

                conn.commit()

                flash("Registration successful! Please log in.")

                return redirect(url_for("login"))

            except sqlite3.IntegrityError:

                flash("This email is already registered.")

            finally:

                conn.close()

    return render_template("register.html")


# ==========================================
# 9. USER LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:

        return redirect(url_for("dashboard"))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db_connection()

        try:

            user = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            ).fetchone()

        finally:

            conn.close()

        if user and check_password_hash(user["password_hash"], password):

            user_object = User(
                user["user_id"],
                user["name"],
                user["email"]
            )

            login_user(user_object)

            flash("Login successful!")

            return redirect(url_for("dashboard"))

        else:

            flash("Invalid email or password. Please try again.")

    return render_template("login.html")


# ==========================================
# 10. DASHBOARD
# ==========================================

@app.route("/dashboard")
@login_required
def dashboard():

    conn = get_db_connection()

    try:

        totals = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE
                    WHEN type = 'Income' THEN amount
                    ELSE 0
                END), 0) AS total_income,

                COALESCE(SUM(CASE
                    WHEN type = 'Expense' THEN amount
                    ELSE 0
                END), 0) AS total_expenses

            FROM transactions
            WHERE user_id = ?
            """,
            (current_user.id,)
        ).fetchone()

        total_income = totals["total_income"]
        total_expenses = totals["total_expenses"]

        balance = total_income - total_expenses

        recent_transactions = conn.execute(
            """
            SELECT date, description, amount, type, category
            FROM transactions
            WHERE user_id = ?
            ORDER BY date DESC, rowid DESC
            LIMIT 5
            """,
            (current_user.id,)
        ).fetchall()

        category_data = conn.execute(
            """
            SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE user_id = ? AND type = 'Expense'
            GROUP BY category
            """,
            (current_user.id,)
        ).fetchall()

        category_labels = [
            row["category"] for row in category_data
        ]

        category_amounts = [
            row["total"] for row in category_data
        ]

    finally:

        conn.close()

    return render_template(
        "dashboard.html",
        total_income=total_income,
        total_expenses=total_expenses,
        balance=balance,
        recent_transactions=recent_transactions,
        category_labels=category_labels,
        category_amounts=category_amounts
    )


# ==========================================
# 11. ADD INCOME AND EXPENSES
# ==========================================

@app.route("/add-transaction", methods=["GET", "POST"])
@login_required
def add_transaction():

    if request.method == "POST":

        transaction_date = request.form.get("date", "")
        description = request.form.get("description", "").strip()
        amount_text = request.form.get("amount", "").strip()
        transaction_type = request.form.get("type", "").strip()
        category = request.form.get("category", "").strip()

        if not transaction_date or not description or not amount_text or not category:

            flash("Please fill in all fields.")

            return render_template(
                "add_transaction.html",
                today=date.today().isoformat()
            )

        if transaction_type not in ["Income", "Expense"]:

            flash("Please select a valid transaction type.")

            return render_template(
                "add_transaction.html",
                today=date.today().isoformat()
            )

        try:

            amount = float(amount_text)

            if amount <= 0:

                flash("Amount must be greater than zero.")

                return render_template(
                    "add_transaction.html",
                    today=date.today().isoformat()
                )

        except ValueError:

            flash("Please enter a valid amount.")

            return render_template(
                "add_transaction.html",
                today=date.today().isoformat()
            )

        # AI EXPENSE CATEGORY PREDICTION

        if transaction_type == "Expense" and category == "Auto Detect":

            try:

                category = predict_category(description)

                flash("AI predicted category: " + category)

            except Exception as error:

                flash("AI category prediction failed: " + str(error))

                return render_template(
                    "add_transaction.html",
                    today=date.today().isoformat()
                )

        elif category == "Auto Detect":

            flash("Auto Detect is available for expenses only.")

            return render_template(
                "add_transaction.html",
                today=date.today().isoformat()
            )

        # CORRECT CLOTHING CATEGORY

        category = correct_expense_category(
            description,
            transaction_type,
            category
        )

        # SAVE TRANSACTION

        conn = get_db_connection()

        try:

            conn.execute(
                """
                INSERT INTO transactions
                (user_id, date, description, amount, type, category)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    current_user.id,
                    transaction_date,
                    description,
                    amount,
                    transaction_type,
                    category
                )
            )

            conn.commit()

            flash("Transaction added successfully!")

        except sqlite3.Error as error:

            conn.rollback()

            flash("Database error: " + str(error))

        finally:

            conn.close()

        return redirect(url_for("view_transactions"))

    return render_template(
        "add_transaction.html",
        today=date.today().isoformat()
    )


# ==========================================
# 12. LOGOUT
# ==========================================

@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():

    logout_user()

    flash("You have successfully logged out.")

    return redirect(url_for("login"))


# ==========================================
# 13. VIEW TRANSACTIONS
# ==========================================

@app.route("/transactions")
@login_required
def view_transactions():

    conn = get_db_connection()

    try:

        transactions = conn.execute(
            """
            SELECT rowid AS record_id,
                   date,
                   description,
                   amount,
                   type,
                   category
            FROM transactions
            WHERE user_id = ?
            ORDER BY date DESC, rowid DESC
            """,
            (current_user.id,)
        ).fetchall()

    finally:

        conn.close()

    return render_template(
        "transactions.html",
        transactions=transactions
    )


# ==========================================
# 14. DELETE TRANSACTION
# ==========================================

@app.route("/delete-transaction/<int:record_id>", methods=["POST"])
@login_required
def delete_transaction(record_id):

    conn = get_db_connection()

    try:

        cursor = conn.execute(
            """
            DELETE FROM transactions
            WHERE rowid = ? AND user_id = ?
            """,
            (record_id, current_user.id)
        )

        conn.commit()

        if cursor.rowcount > 0:

            flash("Transaction deleted successfully!")

        else:

            flash("Transaction not found.")

    except sqlite3.Error as error:

        conn.rollback()

        flash("Database error: " + str(error))

    finally:

        conn.close()

    return redirect(url_for("view_transactions"))
# ==========================================
# 15. BUDGET MANAGEMENT
# ==========================================

@app.route("/budgets", methods=["GET", "POST"])
@login_required
def budgets():

    conn = get_db_connection()

    try:

        if request.method == "POST":

            month = request.form.get("month", "").strip()
            category = request.form.get("category", "").strip()
            limit_text = request.form.get("limit_amount", "").strip()

            if not month or not category or not limit_text:

                flash("Please fill in all fields.")

            else:

                try:

                    limit_amount = float(limit_text)

                    if limit_amount <= 0:

                        flash("Budget must be greater than zero.")

                    else:

                        conn.execute(
                            """
                            INSERT INTO budgets
                            (user_id, month, category, limit_amount)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(user_id, month, category)
                            DO UPDATE SET limit_amount = excluded.limit_amount
                            """,
                            (
                                current_user.id,
                                month,
                                category,
                                limit_amount
                            )
                        )

                        conn.commit()

                        flash("Budget saved successfully!")

                except ValueError:

                    flash("Please enter a valid budget amount.")

        budget_list = conn.execute(
            """
            SELECT
                b.budget_id,
                b.month,
                b.category,
                b.limit_amount,
                COALESCE(SUM(t.amount), 0) AS spent
            FROM budgets b
            LEFT JOIN transactions t
                ON t.user_id = b.user_id
                AND t.category = b.category
                AND substr(t.date, 1, 7) = b.month
                AND t.type = 'Expense'
            WHERE b.user_id = ?
            GROUP BY
                b.budget_id,
                b.month,
                b.category,
                b.limit_amount
            ORDER BY b.month DESC, b.category
            """,
            (current_user.id,)
        ).fetchall()

    except sqlite3.Error as error:

        conn.rollback()

        flash("Database error: " + str(error))

        budget_list = []

    finally:

        conn.close()

    return render_template(
        "budgets.html",
        budget_list=budget_list,
        current_month=date.today().strftime("%Y-%m")
    )


# ==========================================
# 16. EDIT TRANSACTION
# ==========================================

@app.route("/edit-transaction/<int:record_id>", methods=["GET", "POST"])
@login_required
def edit_transaction(record_id):

    conn = get_db_connection()

    try:

        transaction = conn.execute(
            """
            SELECT rowid AS record_id, *
            FROM transactions
            WHERE rowid = ? AND user_id = ?
            """,
            (record_id, current_user.id)
        ).fetchone()

        if transaction is None:

            flash("Transaction not found.")

            return redirect(url_for("view_transactions"))

        if request.method == "POST":

            transaction_date = request.form.get("date", "")
            description = request.form.get("description", "").strip()
            amount_text = request.form.get("amount", "").strip()
            transaction_type = request.form.get("type", "")
            category = request.form.get("category", "")

            # CORRECT CLOTHING CATEGORY

            category = correct_expense_category(
                description,
                transaction_type,
                category
            )

            if not transaction_date or not description or not amount_text or not category:

                flash("Please fill in all fields.")

            elif transaction_type not in ["Income", "Expense"]:

                flash("Please select a valid transaction type.")

            else:

                try:

                    amount = float(amount_text)

                    if amount <= 0:

                        flash("Amount must be greater than zero.")

                    else:

                        conn.execute(
                            """
                            UPDATE transactions
                            SET date = ?,
                                description = ?,
                                amount = ?,
                                type = ?,
                                category = ?
                            WHERE rowid = ? AND user_id = ?
                            """,
                            (
                                transaction_date,
                                description,
                                amount,
                                transaction_type,
                                category,
                                record_id,
                                current_user.id
                            )
                        )

                        conn.commit()

                        flash("Transaction updated successfully!")

                        return redirect(url_for("view_transactions"))

                except ValueError:

                    flash("Please enter a valid amount.")

        return render_template(
            "edit_transaction.html",
            transaction=transaction
        )

    except sqlite3.Error as error:

        conn.rollback()

        flash("Database error: " + str(error))

        return redirect(url_for("view_transactions"))

    finally:

        conn.close()


# ==========================================
# 17. DATABASE TEST
# ==========================================

@app.route("/db-test")
@login_required
def db_test():

    conn = get_db_connection()

    try:

        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()

    finally:

        conn.close()

    return str([table["name"] for table in tables])


# ==========================================
# 18. FINANCIAL INSIGHTS
# ==========================================

@app.route("/insights")
@login_required
def insights():

    conn = get_db_connection()

    insight_list = []

    income = 0
    expenses = 0

    try:

        current_month = date.today().strftime("%Y-%m")

        totals = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE
                    WHEN type = 'Income' THEN amount
                    ELSE 0
                END), 0) AS income,

                COALESCE(SUM(CASE
                    WHEN type = 'Expense' THEN amount
                    ELSE 0
                END), 0) AS expenses

            FROM transactions
            WHERE user_id = ? AND substr(date, 1, 7) = ?
            """,
            (current_user.id, current_month)
        ).fetchone()

        income = float(totals["income"] or 0)

        expenses = float(totals["expenses"] or 0)

        category_rows = conn.execute(
            """
            SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE user_id = ?
              AND type = 'Expense'
              AND substr(date, 1, 7) = ?
            GROUP BY category
            ORDER BY total DESC
            """,
            (current_user.id, current_month)
        ).fetchall()

        if income == 0 and expenses == 0:

            insight_list.append({
                "insight_text":
                "No transactions found for this month. Add your income and expenses to receive financial insights."
            })

        else:

            if expenses > income:

                insight_list.append({
                    "insight_text":
                    "Your expenses are higher than your income this month. Review your spending and consider reducing non-essential expenses."
                })

            elif income > 0:

                savings = income - expenses

                savings_percent = (savings / income) * 100

                insight_list.append({
                    "insight_text":
                    f"You have saved ₹{savings:,.2f} this month, which is {savings_percent:.1f}% of your income."
                })

            if category_rows:

                highest = category_rows[0]

                insight_list.append({
                    "insight_text":
                    f"Your highest expense category this month is {highest['category']} at ₹{float(highest['total']):,.2f}."
                })

            else:

                insight_list.append({
                    "insight_text":
                    "You have not recorded any expenses this month."
                })

        # SAVE INSIGHTS TO DATABASE

        conn.execute(
            "DELETE FROM insights WHERE user_id = ?",
            (current_user.id,)
        )

        for item in insight_list:

            conn.execute(
                """
                INSERT INTO insights (user_id, insight_text)
                VALUES (?, ?)
                """,
                (current_user.id, item["insight_text"])
            )

        conn.commit()

    except sqlite3.Error as error:

        conn.rollback()

        flash("Could not generate insights: " + str(error))

    finally:

        conn.close()

    return render_template(
        "insights.html",
        insight_list=insight_list,
        income=income,
        expenses=expenses
    )


# ==========================================
# 19. SPENDING FORECAST
# ==========================================

@app.route("/forecast")
@login_required
def forecast():

    conn = get_db_connection()

    monthly_expenses = []

    month_labels = []

    predicted_expense = None

    try:

        rows = conn.execute(
            """
            SELECT
                substr(date, 1, 7) AS month,
                SUM(amount) AS total
            FROM transactions
            WHERE user_id = ? AND type = 'Expense'
            GROUP BY substr(date, 1, 7)
            ORDER BY month ASC
            """,
            (current_user.id,)
        ).fetchall()

        month_labels = [
            row["month"] for row in rows
        ]

        monthly_expenses = [
            float(row["total"] or 0) for row in rows
        ]

        if len(monthly_expenses) >= 2:

            x_values = np.arange(1, len(monthly_expenses) + 1)

            slope, intercept = np.polyfit(
                x_values,
                monthly_expenses,
                1
            )

            predicted_expense = max(
                0,
                float(
                    slope * (len(monthly_expenses) + 1) + intercept
                )
            )

            predicted_expense = round(predicted_expense, 2)

        else:

            flash(
                "Add expenses in at least two different months to generate a forecast."
            )

    except sqlite3.Error as error:

        flash("Could not calculate forecast: " + str(error))

    finally:

        conn.close()

    return render_template(
        "forecast.html",
        month_labels=month_labels,
        monthly_expenses=monthly_expenses,
        predicted_expense=predicted_expense
    )
# ==========================================
# 20. AI FINANCE CHATBOT
# ==========================================

@app.route("/chatbot", methods=["GET", "POST"])
@login_required
def chatbot():

    answer = None

    question = ""

    if request.method == "POST":

        question = request.form.get("message", "").strip()

        lower_question = question.lower()

        if not question:

            answer = "Please type a question so I can help you."

        elif any(word in lower_question for word in ["hello", "hi", "hey"]):

            answer = (
                f"Hello {current_user.name}! I am your FinanceAI assistant. "
                "Ask me about your balance, expenses, budgets or spending forecast."
            )

        elif "balance" in lower_question:

            conn = get_db_connection()

            try:

                row = conn.execute(
                    """
                    SELECT
                        COALESCE(SUM(CASE
                            WHEN type = 'Income' THEN amount
                            ELSE 0
                        END), 0) AS income,

                        COALESCE(SUM(CASE
                            WHEN type = 'Expense' THEN amount
                            ELSE 0
                        END), 0) AS expenses

                    FROM transactions
                    WHERE user_id = ?
                    """,
                    (current_user.id,)
                ).fetchone()

                balance_value = (
                    float(row["income"] or 0)
                    - float(row["expenses"] or 0)
                )

                answer = (
                    f"Your current recorded balance is ₹{balance_value:,.2f}."
                )

            finally:

                conn.close()

        elif "expense" in lower_question or "spend" in lower_question:

            conn = get_db_connection()

            try:

                row = conn.execute(
                    """
                    SELECT COALESCE(SUM(amount), 0) AS total
                    FROM transactions
                    WHERE user_id = ? AND type = 'Expense'
                    """,
                    (current_user.id,)
                ).fetchone()

                answer = (
                    f"Your total recorded expenses are "
                    f"₹{float(row['total'] or 0):,.2f}. "
                    "You can view the category breakdown on your dashboard."
                )

            finally:

                conn.close()

        elif "income" in lower_question:

            conn = get_db_connection()

            try:

                row = conn.execute(
                    """
                    SELECT COALESCE(SUM(amount), 0) AS total
                    FROM transactions
                    WHERE user_id = ? AND type = 'Income'
                    """,
                    (current_user.id,)
                ).fetchone()

                answer = (
                    f"Your total recorded income is "
                    f"₹{float(row['total'] or 0):,.2f}."
                )

            finally:

                conn.close()

        elif "budget" in lower_question:

            answer = (
                "Open the Budgets page to set a monthly spending limit "
                "for each category and compare it with your recorded expenses."
            )

        elif "forecast" in lower_question:

            answer = (
                "Open Spending Forecast to see an estimate based on your "
                "recorded monthly expenses. At least two months of expense "
                "data are needed."
            )

        elif "insight" in lower_question:

            answer = (
                "Open Financial Insights to review your savings percentage "
                "and highest spending category for this month."
            )

        elif "transaction" in lower_question:

            answer = (
                "Use Add Transaction to record income or expenses, "
                "or open Transactions to review, edit and delete your records."
            )

        elif "category" in lower_question or "auto detect" in lower_question:

            answer = (
                "When adding an expense, choose Auto Detect to let the "
                "trained expense-category model predict a category "
                "from its description."
            )

        elif "thank" in lower_question:

            answer = (
                "You're welcome! Keep recording your transactions "
                "to make your financial overview more useful."
            )

        else:

            answer = (
                "I can help with your balance, income, expenses, budgets, "
                "transactions, category prediction and spending forecast. "
                "Try asking about one of these topics."
            )

    return render_template(
        "chatbot.html",
        answer=answer,
        question=question
    )


# ==========================================
# 21. RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    create_database()

    app.run(debug=True)