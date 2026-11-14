import sqlite3
from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent
DATABASE_PATH=BASE_DIR/"finance.db"
def create_database():
    connection=sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys=ON")
    cursor=connection.cursor()
    cursor.executescript("""
          -- TABLE 1: USERS
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- TABLE 2: TRANSACTIONS
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL CHECK(amount > 0),
        type TEXT NOT NULL CHECK(type IN ('Income', 'Expense')),
        category TEXT NOT NULL,

        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
    );

    -- TABLE 3: BUDGETS
    CREATE TABLE IF NOT EXISTS budgets (
        budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        month TEXT NOT NULL,
        category TEXT NOT NULL,
        limit_amount REAL NOT NULL CHECK(limit_amount > 0),

        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,

        UNIQUE(user_id, month, category)
    );

    -- TABLE 4: PREDICTIONS
    CREATE TABLE IF NOT EXISTS predictions (
        prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER NOT NULL,
        predicted_category TEXT NOT NULL,
        confidence REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (transaction_id)
        REFERENCES transactions(transaction_id)
        ON DELETE CASCADE,

        CHECK(confidence IS NULL OR
              (confidence >= 0 AND confidence <= 1))
    );

    -- TABLE 5: INSIGHTS
    CREATE TABLE IF NOT EXISTS insights (
        insight_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        insight_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
    );

    """)
    connection.commit()
    connection.close()
    print("Database Created Successfully!")
    print("ALL 5 tables Created successfully!")
if __name__=="__main__":
    create_database()