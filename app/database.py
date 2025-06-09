import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('trading_app.db')
    cursor = conn.cursor()

    # Create settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exchange_name TEXT UNIQUE NOT NULL,
            api_key_encrypted TEXT NOT NULL
        )
    ''')

    # Create trade_history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE NOT NULL,
            timestamp DATETIME NOT NULL,
            symbol TEXT NOT NULL,
            type TEXT NOT NULL,
            price REAL NOT NULL,
            quantity REAL NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database trading_app.db initialized with settings and trade_history tables.")
