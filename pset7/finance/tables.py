import sqlite3
# connect to the database and place cursor
conn = sqlite3.connect("finance.db")
cursor = conn.cursor()
print("Sucessfully connected to database")

# while creating tables, drop the the table until correct
cursor.execute("DROP TABLE IF EXISTS portfolio")
cursor.execute("DROP TABLE IF EXISTS histories")


# create histories table
cursor.execute("""CREATE TABLE histories (
                    id          INTEGER,
                    symbol      TEXT,
                    name        TEXT,
                    price       REAL DEFAULT 0.00,
                    shares      INTEGER,
                    buyDATE     INTEGER,
                    sellDATE    INTEGER,
                    historyID INTEGER PRIMARY KEY AUTOINCREMENT,
                    FOREIGN KEY(id) REFERENCES users(id));
                    """)

# create portfolio table
cursor.execute("""CREATE TABLE portfolio (
                    id              INTEGER,
                    symbol          TEXT,
                    name            TEXT,
                    shares          INTEGER,
                    current_price   REAL DEFAULT 0.00,
                    stock_value     REAL DEFAULT 0.00,
                    portfolioID INTEGER PRIMARY KEY AUTOINCREMENT,
                    FOREIGN KEY(id) REFERENCES users(id)
                    FOREIGN KEY(symbol) REFERENCES histories(symbol));
                    """)
                    


print("Table created sucssesfully")
