import sqlite3

""" 
This was used in testing to the sqlite database just to ensure the information was formatted correctly and everything was working as intended. 
"""

con = sqlite3.connect("real.db")
cur = sqlite3.Cursor(con)

cur.execute('SELECT * FROM insider_data WHERE ISSUERTRADINGSYMBOL = "LENZ"')
rows = cur.fetchall()
# con.commit()
con.close()
print(rows)
