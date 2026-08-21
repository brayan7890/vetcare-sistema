import sqlite3

db = sqlite3.connect(r"C:\Users\operador_usau03\Documents\mi-proyecto\veterinaria.db")
cur = db.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cur.fetchall()]
print("=== TABLAS ===")
for t in tables:
    print(f"  - {t}")

for tabla in tables:
    cur.execute(f"SELECT * FROM {tabla}")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    print(f"\n=== {tabla.upper()} ({len(rows)} registros) ===")
    print(f"  Columnas: {cols}")
    for row in rows:
        print(f"  {row}")

db.close()
