import sqlite3

"""
Tiny script just to initialize the database and create an index on the database
table is called 'insider_data' the columns are created exactly as they are presented in the DataFrame 
"""

con = sqlite3.connect("real.db")

cur = (
    con.cursor()
)  # note that the table name is escaped using double quotes so we can use keywords as table names

cur.execute(
    """CREATE TABLE IF NOT EXISTS "insider_data" (ACCESSION_NUMBER VARCHAR(200), FILING_DATE VARCHAR(200), ISSUERTRADINGSYMBOL VARCHAR(200), TRANS_SHARES REAL, TRANS_PRICEPERSHARE REAL, TRANS_ACQUIRED_DISP_CD VARCHAR(100), SHRS_OWND_FOLWNG_TRANS REAL)"""
)

con.commit()

# add index to the table on the ISSUERTRADINGSYMBOL column ( this is the main column we will use to query the DB )
cur.execute(
    """CREATE INDEX idx_ISSUERTRADINGSYMBOL ON insider_data(ISSUERTRADINGSYMBOL)"""
)
con.commit()
con.close()
