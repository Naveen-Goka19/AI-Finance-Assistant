import sqlite3

connection = sqlite3.connect("finance.db")

cursor = connection.cursor()

cursor.execute("""
    SELECT user_id, name, email, password_hash
    FROM users
""")

users = cursor.fetchall()

for user in users:
    print(user)

connection.close()