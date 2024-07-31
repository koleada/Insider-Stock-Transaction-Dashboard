import sqlite3
import os

try:
    import polars as pl
except ImportError:
    exit("polars library missing, please install them with pip.", 1)

"""
This program is responsible for loading all of the data into our sqlite database for querying later on. This program begins with 2 polars dataframes (faster then pandas) one for the 
transaction data the other for submission data. It then processes both of them eliminating malformed or bad data (which there is a ton of... thanks SEC :) ) it also processes all 
duplicate transaction data. The way the SEC inputs this data, there will be 1 line of submission data that could correspond to multiple transactions. So I went through all of the 
transaction data found the duplicates and just added the number of shares together and took the mean of price / share. After processing I joined the 2 dataframes together using 
the accession_number (unqiue ID given by SEC). Then the completed dataframe gets added to our database, quite quickly and efficiently I might add.  
"""


# TODO:
# run once more just have 10 more folders to run through
def main():
    # starting from 71 will go through all of the data add to a polars dataframe and VERY efficiently submit it to the database
    for i in reversed(range(1, 11)):
        trans_name = os.path.join("data", str(i), "NONDERIV_TRANS.tsv")
        sub_name = os.path.join("data", str(i), "SUBMISSION.tsv")

        final_trans = get_trans_frame(trans_name)
        sub_df = get_sub_frame(sub_name)

        combined_df = sub_df.join(final_trans, on="ACCESSION_NUMBER")

        con = sqlite3.connect("real.db")
        cur = sqlite3.Cursor(con)
        # separating the dataframe into chunks like this makes even faster to insert into the database
        chunk_size = 10000
        for i in range(0, len(combined_df), chunk_size):
            chunk = combined_df[i : i + chunk_size]
            insert_chunk(chunk, con, cur)
        con.close()


# handles getting transaction data from .tsv file and processing the data before adding to the database
def get_trans_frame(path) -> pl.DataFrame:
    trans_cols = [
        "ACCESSION_NUMBER",
        "TRANS_SHARES",
        "TRANS_PRICEPERSHARE",
        "TRANS_ACQUIRED_DISP_CD",
        "SHRS_OWND_FOLWNG_TRANS",
    ]
    trans_df: pl.DataFrame = get_frame(path, trans_cols)
    trans_df = trans_df.filter(pl.col("TRANS_PRICEPERSHARE") > 0)
    # process dups and concat them back with the non dups
    final_trans = df_dups(trans_df)
    return final_trans


# handles getting submission data from .tsv and processing the data before submission to the database
def get_sub_frame(path) -> pl.DataFrame:
    sub_cols = ["ACCESSION_NUMBER", "FILING_DATE", "ISSUERTRADINGSYMBOL"]
    sub_df = get_frame(path, sub_cols)
    # remove all non letters in tickers
    sub_df = sub_df.with_columns(
        pl.col("ISSUERTRADINGSYMBOL").str.replace_all("[^a-zA-Z]", "")
    )
    # remove any rows with a ticker name > 5 chars
    sub_df = sub_df.filter(
        [
            pl.col("ISSUERTRADINGSYMBOL").str.len_chars() < 5,
        ]
    )
    # put all tickers in uppercase
    sub_df = sub_df.select(
        [
            pl.col("ACCESSION_NUMBER"),
            pl.col("FILING_DATE"),
            pl.col("ISSUERTRADINGSYMBOL").str.to_uppercase(),
        ]
    )
    # check for bad ticker names
    bad_tickers = ["ALL", "NONE", "IN", "AS", "IF", "ELSE", "ON"]
    sub_df = sub_df.filter(~pl.col("ISSUERTRADINGSYMBOL").str.contains_any(bad_tickers))
    # format the times correctly before entering to db -> this will enables us to easily plot the transactions using the dates later on
    sub_df = sub_df.with_columns(
        pl.col("FILING_DATE").str.strptime(pl.Date, "%d-%b-%Y")
    )
    return sub_df


# helper function that handles optimized insertion into the DB
def insert_chunk(df: pl.DataFrame, con: sqlite3.Connection, cur: sqlite3.Cursor):
    data = df.to_numpy()
    query = f"INSERT INTO insider_data (ACCESSION_NUMBER, FILING_DATE, ISSUERTRADINGSYMBOL, TRANS_SHARES, TRANS_PRICEPERSHARE, TRANS_ACQUIRED_DISP_CD, SHRS_OWND_FOLWNG_TRANS) VALUES (?, ?, ?, ?, ?, ?, ?)"
    cur.executemany(query, data)
    con.commit()


# little helper function to get the data from file
def get_frame(path, cols):
    desired_columns = cols
    lazyframe1 = pl.scan_csv(path, separator="\t")
    df = lazyframe1.select(desired_columns).collect()
    return df


def df_dups(df):
    """This function takes in a dataframe containing the transaction data. It splits the data frame into 2 - dups and non dups. All of the dups get processed by summing the TRANS_SHARES
        and the SHRS_OWND_FOLWNG_TRANS columns and averaging the trans_pricepershare column of the duplicates.
    Args:
        df (_type_): initial transaction data freshly read in from the tsv file
    Returns:
        _type_: A dataframe containing the processed dups and the non dups
    """
    non_duplicates = df.filter(pl.col("ACCESSION_NUMBER").is_duplicated() == False)

    # empty df to add our newly processed rows to
    empty_df = pl.DataFrame(
        schema=pl.Schema(
            [
                ("ACCESSION_NUMBER", pl.Utf8),
                ("TRANS_SHARES", pl.Float64),
                ("TRANS_PRICEPERSHARE", pl.Float64),
                ("TRANS_ACQUIRED_DISP_CD", pl.Utf8),
                ("SHRS_OWND_FOLWNG_TRANS", pl.Float64),
            ]
        )
    )
    # group the rows with duplicates and filter it so it only contains rows that have duplicate ACCESSION Nums -> return a Groupby object which contains a tuple of a group key and a df of the group
    # thus we need to account for the tuple in the loop and just pass in the dataframe. the group df is a completely separate df containing only the group of dups
    group_frame = df.filter(
        pl.col("ACCESSION_NUMBER").is_duplicated() == True
    ).group_by(pl.col("ACCESSION_NUMBER"))
    # dont care about the group_key for our purpose. just throw the group df into the process func
    for group_key, group_df in group_frame:
        # add the dataframe that contains a single processed elem to the 'empty' dataframe
        empty_df = pl.concat([empty_df, process_group(group_df)])
    # concat the processed dups (empty_df) with the non dups to get final frame baby
    final_df = pl.concat([empty_df, non_duplicates])
    return final_df


# helper function to df_dups
def process_group(group):
    first_row = group.head(1)  # Get the first row of each group
    return pl.DataFrame(
        {
            "ACCESSION_NUMBER": first_row["ACCESSION_NUMBER"],
            "TRANS_SHARES": group["TRANS_SHARES"].sum(),  # Keep value from first row
            "TRANS_PRICEPERSHARE": round(
                group["TRANS_PRICEPERSHARE"].mean(), 2
            ),  # round to 2 decimals
            "TRANS_ACQUIRED_DISP_CD": first_row["TRANS_ACQUIRED_DISP_CD"],
            "SHRS_OWND_FOLWNG_TRANS": group["SHRS_OWND_FOLWNG_TRANS"].sum(),
        }
    )


if __name__ == "__main__":
    main()
