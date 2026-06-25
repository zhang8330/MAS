import sqlite3

conn = sqlite3.connect("dataset.db")
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print("tables", tables)
for t in tables:
    print("\n===", t, "===")
    cur.execute(f"PRAGMA table_info({t})")
    cols = [r[1] for r in cur.fetchall()]
    print("cols", cols)
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print("count", cur.fetchone()[0])
    cur.execute(f"SELECT * FROM {t} LIMIT 1")
    print("sample", cur.fetchone())
conn.close()
