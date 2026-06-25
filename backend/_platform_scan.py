import sqlite3

conn = sqlite3.connect('dataset.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print('tables:', tables)

preferred = ['functions', 'function_samples', 'samples', 'cases', 'func_pairs', 'repos']
table = None
for t in preferred:
    if t in tables:
        table = t
        break
print('using_table:', table)

if not table:
    raise SystemExit(0)

cur.execute(f"PRAGMA table_info({table})")
cols = [r[1] for r in cur.fetchall()]
print('columns:', cols)

for c in ['migration_type', 'source_platform', 'target_platform']:
    if c in cols:
        cur.execute(f"SELECT {c} v, COUNT(*) c FROM {table} GROUP BY {c} ORDER BY c DESC")
        rows = cur.fetchall()
        print(f"\n{c} values:")
        for r in rows[:50]:
            print(f"  {r['v']!r}: {r['c']}")
    else:
        print(f"\n{c} not found")

conn.close()
