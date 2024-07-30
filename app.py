from dash import Dash, html, dash_table, dcc, callback, Output, Input, exceptions, State
import dash_bootstrap_components as dbc
import datetime
import plotly.graph_objects as go
import plotly.subplots
import plotly
import pandas as pd
import yfinance as yf
import polars as pl
import sqlalchemy as sql
from datetime import date
import numpy as np
from plotly.subplots import make_subplots

colors = {
    "teal": "#0aabcf",
    "lightgreen": "#4aed90",
    "lightishblue": "#54b1e3",
    "bluepurp": "#5465e3",
    "maingraphcolor": "#5eb2c4",
}

app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
app.title = "SEC Insider Trading Dashboard"
app.layout = html.Div(
    id="bodydiv",
    style={"display": "flex"},
    children=[
        html.Div(
            id="top",
            children=[
                html.H2(
                    children="SEC Insider Stock Transaction Dashboard",
                    id="title",
                ),
                html.Div(
                    id="buttondiv",
                    children=[
                        dbc.RadioItems(
                            id="radios",
                            className="btn-group",
                            inputClassName="btn-check",
                            labelClassName="btn btn-outline-primary",
                            labelCheckedClassName="active",
                            options=[
                                {"label": "Insider", "value": 1},
                                {"label": "Technical", "value": 2},
                            ],
                            value=1,
                        ),
                        html.Div(id="output"),
                    ],
                    className="radio-group",
                ),
                html.Div(
                    id="inputdiv",
                    children=[
                        dbc.Input(
                            id="ticker_input",
                            type="text",
                            placeholder="Enter Stock Ticker",
                        ),
                        dbc.Button(
                            "Submit",
                            id="submit_button",
                        ),
                    ],
                ),
            ],
        ),
        html.Div(id="maindiv", children=[]),
    ],
)


@app.callback(
    # this makes it so the update function will only be called when the submit button is pressed. note the submit button is the only input and the text input is a state
    Output("maindiv", "children"),
    [Input("submit_button", "n_clicks"), Input("radios", "value")],
    [State("ticker_input", "value")],
)
# also note the order of which the arguments are passed, input first then the text input value
def get_layout(n_clicks, value, ticker_input):
    if n_clicks is None:
        raise exceptions.PreventUpdate()

    # Input validation
    if len(ticker_input) > 5 or not ticker_input.isalpha() or len(ticker_input) == 0:
        return html.H1("Invalid stock ticker input", style={"text-align": "center"})

    stock_data, db_df = get_stock_data(ticker_input)

    # check which radio button is selected
    if value == 1:
        return html.Div(
            id="horizontaldiv",
            children=[
                html.Div(
                    id="graphdiv",
                    children=[
                        dcc.Graph(
                            figure=get_main_graph(ticker_input, stock_data, db_df),
                            id="main_graph",
                        ),
                        dcc.Graph(
                            figure=histogram_df_manipulation(
                                ticker_input, stock_data, db_df
                            ),
                            id="histogram",
                        ),
                    ],
                ),
                html.Div(
                    id="tablediv",
                    children=[
                        # header for the table:
                        dbc.Row(
                            html.H6(
                                f"Insider Transaction Data for {ticker_input.upper()}",
                                id="tableheader",
                            )
                        ),
                        html.Div(
                            id="innertablediv",
                            children=[
                                dbc.Table.from_dataframe(
                                    get_table_df(db_df),
                                    id="table",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )
    else:
        main_fig, ta_fig, bollinger_fig = get_page_2(ticker_input)
        return html.Div(
            id="page2div",
            children=[
                dcc.Graph(figure=main_fig, id="main_fig_2"),
                dcc.Graph(figure=ta_fig, id="ta_fig_2"),
                dcc.Graph(figure=bollinger_fig, id="bollinger_fig_2"),
            ],
        )


def get_stock_data(ticker_input):
    """
    Once a ticker is supplied this function gets all necessary data for that given stock. Uses the local DB and yfinance
    """
    """TODO: add try / except here"""
    # will have to implement checks to prevent sqli just because itll be fun to do so
    ticker = ticker_input.upper().strip()

    engine = sql.create_engine(
        "sqlite:////home/kole/pythonStuff/dataAnalyticsProj/insiderdashboard/real.db"
    )
    con = engine.connect()
    query = f'SELECT * FROM insider_data WHERE ISSUERTRADINGSYMBOL = "{ticker}"'

    """TODO: add try / except here"""
    # initialize dataframe with results from the query
    db_df = pd.read_sql(query, con)

    if len(db_df) == 0:
        return html.H1(
            f"No insider transactions found for {ticker}",
            style={"text-align": "center"},
        )
    # access oldest avail insider transaction date
    oldest_date = db_df["FILING_DATE"].min()
    # subtract 2 years from oldest inside trade
    oldest_date = (
        datetime.datetime.strptime(oldest_date, "%Y-%m-%d")
        - datetime.timedelta(days=365 * 1)
    ).date()
    todays_date = date.today().strftime("%Y-%m-%d")
    # get stock data on the daily timeframe from the oldest avail insider (actions=True gives us info about stock split)
    stock_data = yf.download(ticker, start=oldest_date, end=todays_date, actions=True)

    # get all rows where stock splits are not = 0
    split = stock_data[stock_data["Stock Splits"] != 0]
    # if there are stock splits -> change the price per share to that stock close price on that given day (thus reflecting the stock split)
    if len(split) > 0:
        for index, row in db_df.iterrows():
            try:
                db_df.at[index, "TRANS_PRICEPERSHARE"] = round(
                    stock_data.loc[row["FILING_DATE"], "Close"], 2
                )
            except KeyError:
                db_df.drop(index)

    return stock_data, db_df


""" 
START FIRST PAGE GRAPHS ------------------------
"""


def get_main_graph(ticker, stock_data, db_df):
    """This function creates the main graph in the application. This graph shows the stock closing price with all insider transactions overlaid. This function handles much of the graph styling too.

    Args:
        ticker (str): _description_
        stock_data (pd.DataFrame): dataframe containing the daily stock closing price and its index is the date
        db_df (pd.DataFrame): dataframe containing all of the insider transaction information for the particular stock

    Returns:
        go.Figure: The main graph to be displayed in the application
    """
    # print(db_df.head())
    fig = go.Figure()
    # stock_data.index is the date, then the y axis is plotting the closing price
    fig.add_trace(
        go.Scatter(x=stock_data.index, y=stock_data["Close"], name="Stock Price")
    )
    fig.update_traces(
        line_color="#5465e3",
    )

    fig = add_insider_trace1(fig, db_df)

    updatemenus = [
        dict(
            font=dict(family="white-rabbit", size=12, color="#5eb2c4", weight="bold"),
            bordercolor="#5eb2c4",
            active=0,
            bgcolor="#060606",
            type="buttons",
            direction="down",
            x=1.25,  # Adjust horizontal position
            y=0.31,
            buttons=list(
                [
                    dict(
                        args=[
                            {
                                "yaxis": {
                                    "type": "linear",
                                    "title": "Price ($)",
                                    "titlefont": {
                                        "family": "white-rabbit",
                                        "size": 18,
                                        "color": "#5eb2c4",
                                        "weight": "bold",
                                    },
                                    "tickfont": {
                                        "color": "#5eb2c4",
                                        "weight": "bold",
                                        "size": 16,
                                        "family": "white-rabbit",
                                    },
                                }
                            }
                        ],
                        label="Linear Scale",
                        method="relayout",
                    ),
                    dict(
                        args=[
                            {
                                "yaxis": {
                                    "type": "log",
                                    "title": "Price ($)",
                                    "titlefont": {
                                        "family": "white-rabbit",
                                        "size": 18,
                                        "color": "#5eb2c4",
                                        "weight": "bold",
                                    },
                                    "tickfont": {
                                        "color": "#5eb2c4",
                                        "weight": "bold",
                                        "size": 16,
                                        "family": "white-rabbit",
                                    },
                                }
                            }
                        ],
                        label="Log Scale",
                        method="relayout",
                    ),
                ]
            ),
        ),
    ]
    fig.update_yaxes(showgrid=False)
    # adds the little buttons to look at specific time ranges
    fig.update_xaxes(
        showgrid=False,
        range=[stock_data.index.min(), stock_data.index.max()],
        uirevision="fixed",
        rangeslider_visible=False,
        rangeselector=dict(
            bgcolor="#5eb2c4",
            buttons=list(
                [
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="todate"),
                    dict(count=5, label="5Y", step="year", stepmode="backward"),
                ]
            ),
        ),
    )
    # adds colors, buttons, legend styles etc
    fig.update_layout(
        title=dict(text=f"{ticker.upper()} Insider Trades vs Stock Price", x=0.45),
        title_font=dict(family="white-rabbit", size=22, color="#5eb2c4", weight="bold"),
        xaxis_title="Date",
        xaxis_title_font=dict(
            family="white-rabbit", size=18, color="#5eb2c4", weight="bold"
        ),
        yaxis_title="Price ($)",
        yaxis_title_font=dict(
            family="white-rabbit", size=18, color="#5eb2c4", weight="bold"
        ),
        yaxis_tickfont=dict(
            family="white-rabbit", color="#5eb2c4", weight="bold", size=16
        ),
        xaxis_tickfont=dict(
            family="white-rabbit", color="#5eb2c4", weight="bold", size=16
        ),
        legend=dict(font=dict(family="white-rabbit", size=12, color="#5eb2c4")),
        paper_bgcolor="#7b8b8f",
        plot_bgcolor="#5eb2c4",
        updatemenus=updatemenus,
    )
    fig.update_xaxes()
    return fig


def add_insider_trace1(fig, db_df):
    # Filter the DataFrame into buy and sell DataFrames
    df_buy = db_df[db_df["TRANS_ACQUIRED_DISP_CD"] == "A"]
    df_sell = db_df[db_df["TRANS_ACQUIRED_DISP_CD"] == "D"]

    # create a scatter plot for the insider trading info:
    insider_buy = go.Scatter(
        x=df_buy["FILING_DATE"],
        y=df_buy[
            "TRANS_PRICEPERSHARE"
        ],  # stock_data.loc[db_df['FILING_DATE'], 'Close'],
        mode="markers",
        marker=dict(color="green", size=8, opacity=0.7),
        name="Insider Buys",
        hovertext=db_df.apply(
            lambda row: f"Insider Transaction Info:<br>Shares:{row['TRANS_SHARES']}<br>Avg Cost: ${row['TRANS_PRICEPERSHARE']}<br>Filed on {row['FILING_DATE']}",
            axis=1,
        ),
        hoverinfo="text",
        visible=True,
    )
    insider_sell = go.Scatter(
        x=df_sell["FILING_DATE"],
        y=df_sell[
            "TRANS_PRICEPERSHARE"
        ],  # stock_data.loc[db_df['FILING_DATE'], 'Close'],
        mode="markers",
        marker=dict(color="red", size=8, opacity=0.7),
        name="Insider Sales",
        hovertext=db_df.apply(
            lambda row: f"Insider Transaction Info:<br>Shares:{row['TRANS_SHARES']}<br>Avg Cost: ${row['TRANS_PRICEPERSHARE']}<br>Filed on {row['FILING_DATE']}",
            axis=1,
        ),
        hoverinfo="text",
        visible=True,
    )

    # Add traces to the figure
    fig.add_trace(insider_buy)
    fig.add_trace(insider_sell)
    return fig


def histogram_df_manipulation(ticker, stock_data, db_df):
    """This function manipulates the insider data DataFrame creates monthly volume etc and creates the a histogram containing the insider trading volume and overlays the stock price (by calling helper method)

    Args:
        ticker (str): _description_
        stock_data (DataFrame): DataFrame containing the stock prices
        db_df (DataFrame): DataFrame containing all of the insider transaction data for the stock ticker specified

    Returns:
        go.Figure: The histogram to be displayed in the application
    """
    # create date column
    stock_data["Date"] = stock_data.index

    # create new dataframe containing all of the dates, convert them to datetime objects and remove the date index
    stock_date = stock_data[["Date"]]
    stock_date["Date"] = pd.to_datetime(stock_date["Date"])
    stock_date.reset_index(drop=True, inplace=True)

    # group by filing date -> get duplicate dates sum the total shares and avg the price per share
    db_df = (
        db_df.groupby("FILING_DATE")
        .agg(
            TRANS_SHARES=("TRANS_SHARES", "sum"),
            TRANSPRICEPERSHARE=("TRANS_PRICEPERSHARE", "mean"),
            TRANS_ACQUIRED_DISP_CD=("TRANS_ACQUIRED_DISP_CD", "first"),
        )
        .reset_index()
    )

    # add new row called VOLUME made by multiplying shares and price per share then remove all other rows besides that and filing date
    db_df["VOLUME"] = db_df["TRANS_SHARES"] * db_df["TRANSPRICEPERSHARE"]
    db_df["Date"] = pd.to_datetime(db_df["FILING_DATE"])
    # select only date, buy/sell and volume columns
    db_df = db_df[["Date", "VOLUME", "TRANS_ACQUIRED_DISP_CD"]]

    # merge dfs
    volume_df = pd.merge(stock_date, db_df, on="Date", how="left")
    # fill NaN with 0
    volume_df.fillna({"VOLUME": 0}, inplace=True)
    # set date back as the index
    volume_df.set_index("Date", inplace=True)
    # Create a 'quarter' column
    volume_df["month"] = volume_df.index.to_period("M")
    # Group by quarter and sum volume
    monthly_data = volume_df.groupby("month")["VOLUME"].sum().reset_index()
    # Convert PeriodIndex to Timestamp
    monthly_data["month"] = monthly_data["month"].dt.to_timestamp()

    stock_data = stock_data[["Close"]]
    stock_data["month"] = stock_data.index.to_period("M")
    monthly_stock = stock_data.groupby("month")["Close"].mean().reset_index()
    monthly_stock["month"] = monthly_stock["month"].dt.to_timestamp()

    return get_histogram(monthly_data, monthly_stock, ticker)


def get_histogram(monthly_data, monthly_stock, ticker):
    """
    creates the histogram figure itself
    """
    fig = plotly.subplots.make_subplots(specs=[[{"secondary_y": True}]])
    # Create the histogram
    fig.add_trace(
        go.Bar(
            x=monthly_data["month"],
            y=monthly_data["VOLUME"],
            name="Insider Trading Volume",
            marker_color="#5eb2c4",
        ),
        secondary_y=False,
    )
    # Add stock price line trace with secondary y-axis
    fig.add_trace(
        go.Scatter(
            x=monthly_data["month"],
            y=monthly_stock["Close"],
            name="Stock Price",
            line=dict(color="#5eb2c4"),
        ),
        secondary_y=True,
    )
    fig.update_yaxes(showgrid=False)
    # adds the little buttons to look at specific time ranges
    fig.update_xaxes(
        showgrid=False,
        range=[monthly_data["month"].min(), monthly_data["month"].max()],
        uirevision="fixed",
        rangeslider_visible=False,
        rangeselector=dict(
            bgcolor="#5465e3",
            buttons=list(
                [
                    dict(count=1, label="1Y", step="year", stepmode="todate"),
                    dict(count=3, label="3Y", step="year", stepmode="backward"),
                    dict(count=5, label="5Y", step="year", stepmode="backward"),
                    dict(count=10, label="10Y", step="year", stepmode="backward"),
                ]
            ),
        ),
    )
    fig.update_layout(
        barmode="overlay",
        title=dict(
            font=dict(family="white-rabbit", size=18, color="#5465e3", weight="bold"),
            text=f"<b>Logarithmic Monthly Volume of Insider Transactions for {ticker.upper()}</b>",
            x=0.1,
        ),
        xaxis_title="Date",
        legend=dict(
            y=1.0,
            font=dict(family="white-rabbit", size=12, color="#5465e3", weight="bold"),
        ),
        paper_bgcolor="#7b8b8f",
        plot_bgcolor="#5465e3",
        xaxis_title_font=dict(
            family="white-rabbit", size=14, color="#5465e3", weight="bold"
        ),
        yaxis_title_font=dict(
            family="white-rabbit", size=14, color="#5465e3", weight="bold"
        ),
        yaxis2_title_font=dict(
            family="white-rabbit", size=14, color="#5465e3", weight="bold"
        ),
        xaxis_tickfont=dict(
            family="white-rabbit",
            weight="bold",
            color="#5465e3",
        ),
        yaxis_tickfont=dict(
            family="white-rabbit",
            color="#5465e3",
            weight="bold",
        ),
        yaxis2_tickfont=dict(
            family="white-rabbit",
            weight="bold",
            color="#5465e3",
        ),
    )
    fig.update_yaxes(
        title_text="Monthly Insider Volume (Logarithmic)",
        secondary_y=False,
        type="log",
    )
    fig.update_yaxes(
        title_text="Stock Price (Logarithmic)",
        secondary_y=True,
        type="log",
    )
    return fig


def get_table_df(db_df: pd.DataFrame) -> pd.DataFrame:
    """Creates the table containing all of the insider transaction data. Also adds a change in holding columns by calculating the % change in insider holdings after the transaction.

    Args:
        db_df (pd.DataFrame): DataFrame containing the insider transaction data

    Returns:
        pd.DataFrame: The updated DataFrame to be used in the creation of the dbc.Table, which will be displayed in the application.
    """

    db_df["change"] = round(
        ((db_df["TRANS_SHARES"] / db_df["SHRS_OWND_FOLWNG_TRANS"]) * 100), 2
    )

    new_columns = ["Date", "Shares", "Price", "Buy/Sell", "Change in Holdings (%)"]
    table_df = pd.DataFrame(columns=new_columns)

    table_df["Date"] = db_df["FILING_DATE"]
    table_df["Shares"] = db_df["TRANS_SHARES"]
    table_df["Price"] = db_df["TRANS_PRICEPERSHARE"]
    table_df["Buy/Sell"] = db_df["TRANS_ACQUIRED_DISP_CD"].map(
        {"A": "Buy", "D": "Sell"}
    )
    table_df["Change in Holdings (%)"] = db_df["change"]

    return table_df


""" 
START SECOND PAGE GRAPHS ------------------------
"""

updatemenus = [
    dict(
        font=dict(family="white-rabbit", size=12, color="#5465e3", weight="bold"),
        bordercolor="#5465e3",
        active=0,
        bgcolor="#7b8b8f",
        type="buttons",
        direction="down",
        x=1.175,  # Adjust horizontal position
        y=0.31,
        buttons=list(
            [
                dict(
                    args=[
                        {
                            "yaxis": {
                                "type": "linear",
                                "title": "Price ($)",
                                "titlefont": {
                                    "family": "white-rabbit",
                                    "size": 18,
                                    "color": "#5465e3",
                                    "weight": "bold",
                                },
                                "tickfont": {
                                    "color": "#5465e3",
                                    "weight": "bold",
                                    "size": 16,
                                    "family": "white-rabbit",
                                },
                            }
                        }
                    ],
                    label="Linear Scale",
                    method="relayout",
                ),
                dict(
                    args=[
                        {
                            "yaxis": {
                                "type": "log",
                                "title": "Price ($)",
                                "titlefont": {
                                    "family": "white-rabbit",
                                    "size": 18,
                                    "color": "#5465e3",
                                    "weight": "bold",
                                },
                                "tickfont": {
                                    "color": "#5465e3",
                                    "weight": "bold",
                                    "size": 16,
                                    "family": "white-rabbit",
                                },
                            }
                        }
                    ],
                    label="Log Scale",
                    method="relayout",
                ),
            ]
        ),
    ),
]


def get_page_2(ticker):
    stock_data, db_df = get_stock_data(ticker)

    stock_data["20_day"] = stock_data["Close"].rolling(window=20).mean()
    stock_data["50_day"] = stock_data["Close"].rolling(window=50).mean()
    stock_data["100_day"] = stock_data["Close"].rolling(window=100).mean()
    stock_data["200_day"] = stock_data["Close"].rolling(window=200).mean()
    # find crosses of the 50 day and 200 day
    stock_data["crossover"] = 0
    stock_data.loc[
        (stock_data["50_day"] > stock_data["200_day"])
        & (stock_data["50_day"].shift(1) <= stock_data["200_day"].shift(1)),
        "crossover",
    ] = 1
    stock_data.loc[
        (stock_data["50_day"] < stock_data["200_day"])
        & (stock_data["50_day"].shift(1) >= stock_data["200_day"].shift(1)),
        "crossover",
    ] = -1

    # Calculate the 20-period Standard Deviation (SD)
    stock_data["SD"] = stock_data["Close"].rolling(window=20).std()

    # Calculate the Upper Bollinger Band (UB) and Lower Bollinger Band (LB)
    stock_data["UB"] = stock_data["20_day"] + 2 * stock_data["SD"]
    stock_data["LB"] = stock_data["20_day"] - 2 * stock_data["SD"]

    # Calculate RSI
    delta = stock_data["Close"].diff()
    gain = delta.copy()
    loss = delta.copy()
    gain[gain < 0] = 0
    loss[loss > 0] = 0
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = abs(loss.rolling(window=14).mean())
    rs = avg_gain / avg_loss
    stock_data["rsi"] = 100 - (100 / (1 + rs))
    # Calculate the percentage change
    stock_data["pct_change"] = (
        (stock_data["Close"] - stock_data["Open"]) / stock_data["Open"] * 100
    )

    # see if price increased or decreased for volume chart
    stock_data["Increase"] = stock_data["Close"] >= stock_data["Open"]

    main_fig = make_main_fig(stock_data, db_df, ticker)
    ta_fig = make_ta_fig(stock_data, ticker)
    bollinger_fig = make_bollinger_fig(stock_data, ticker)

    return main_fig, ta_fig, bollinger_fig


def make_main_fig(df, db_df, ticker):
    """Facilitates the creation of the main graph shown on the second page. Makes a candlestick graph of stock price, overlays insider data and a bunch of SMAs and highlights
       golden/ death crosses

    Args:
        df (pd.DataFrame): df contianinng all of the stock price data along with SMAs, RSI, Volume and crossover columns
        db_df (pd.DataFrame): df containing all of the insider transaction data
        ticker (str): the ticker that was input by the user

    Returns:
        go.Figure: a plotly figure containing all of the data described above
    """
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=f"{ticker} Stock Price",
            increasing_line_color="#4aed90",  # Green hex color
            decreasing_line_color="#e04343",  # Red hex color
        )
    )
    # Calculate total percentage change
    total_pct_change = (
        (df["Close"].iloc[-1] - df["Close"].iloc[0]) / df["Close"].iloc[0]
    ) * 100
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["50_day"],
            mode="lines",
            name="50 Day MA",
            line=dict(color="#b143e0"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["100_day"],
            mode="lines",
            name="100 Day MA",
            line=dict(color="#5eb2c4"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["200_day"],
            mode="lines",
            name="200 Day MA",
            line=dict(color="#436be0"),
        )
    )
    fig = add_crosses(df, fig)
    fig = add_insider_trace2(fig, db_df)

    fig.update_yaxes(showgrid=False)
    # adds the little buttons to look at specific time ranges
    fig.update_xaxes(
        showgrid=False,
        range=[df.index.min(), df.index.max()],
        uirevision="fixed",
        rangeslider_visible=False,
        rangeselector=dict(
            bgcolor="#7b8b8f",
            buttons=list(
                [
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="todate"),
                    dict(count=5, label="5Y", step="year", stepmode="backward"),
                ]
            ),
        ),
    )
    fig.update_layout(
        title=dict(
            text=f"{ticker.upper()} Stock Price, SMAs, Golden/Death Crosses and Insider Trades",
            x=0.45,
        ),
        title_font=dict(family="white-rabbit", size=22, color="#7b8b8f", weight="bold"),
        xaxis_title="Date",
        xaxis_title_font=dict(
            family="white-rabbit", size=18, color="#7b8b8f", weight="bold"
        ),
        yaxis_title="Price ($)",
        yaxis_title_font=dict(
            family="white-rabbit", size=18, color="#7b8b8f", weight="bold"
        ),
        yaxis_tickfont=dict(
            family="white-rabbit", color="#7b8b8f", weight="bold", size=16
        ),
        xaxis_tickfont=dict(
            family="white-rabbit", color="#7b8b8f", weight="bold", size=16
        ),
        legend=dict(font=dict(family="white-rabbit", size=12, color="#7b8b8f")),
        paper_bgcolor="#5465e3",
        plot_bgcolor="#7b8b8f",
        xaxis=dict(rangeslider=dict(visible=False)),
        height=650,
        updatemenus=updatemenus,
    )
    return fig


def add_crosses(df, fig):
    """Adds scatter plots (circles) either red or green in color indicating death cross or golden cross respectively

    Args:
        df (pd.Dataframe): dataframe containing stock data, SMAs, crossovers of 50 day and 200 day etc
        fig (go.Figure): The figure that the cross indicators should be added to

    Returns:
        go.Figure: The updated figure
    """
    golden_crosses = go.Scatter(
        x=df[df["crossover"] == 1].index,
        y=df[df["crossover"] == 1]["50_day"],
        mode="markers",
        marker=dict(size=12, color="#4aed90", line=dict(width=2, color="white")),
        name="Golden Cross",
    )

    death_crosses = go.Scatter(
        x=df[df["crossover"] == -1].index,
        y=df[df["crossover"] == -1]["50_day"],
        mode="markers",
        marker=dict(size=12, color="#e04343", line=dict(width=2, color="white")),
        name="Death Cross",
    )

    # Add the scatter plots to the figure
    fig.add_trace(golden_crosses)
    fig.add_trace(death_crosses)
    return fig


def make_ta_fig(df, ticker):
    """Creates a subplot figure containing RSI and Volume charts

    Args:
        df (pd.DataFrame): DF cotnaining stock data, RSI and volume columns as well
        ticker (str): Ticker inputted by the user. Will be used in titling the graphs

    Returns:
        plotly.subplots: Figure containing 2 plots, RSI and weekly volume
    """
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.5, 0.5])

    # Add RSI plot
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["rsi"],
            name="RSI",
            mode="lines",
            line=dict(color="#5465e3"),
        )
    )
    fig.add_shape(
        type="line",
        x0=df.index[0],
        y0=70,
        x1=df.index[-1],
        y1=70,
        line=dict(color="#e04343", dash="dash"),
    )
    fig.add_shape(
        type="line",
        x0=df.index[0],
        y0=30,
        x1=df.index[-1],
        y1=30,
        line=dict(color="#4aed90", dash="dash"),
    )

    volume_df = add_weekly_volume(df)
    # Create the volume histogram
    fig.add_trace(
        go.Bar(
            x=volume_df["week"],
            y=volume_df["Volume"],
            marker_color=np.where(df["Increase"], "#4aed90", "#e04343"),
            name="Weekly Volume",
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        height=500,
        xaxis_rangeslider_visible=False,
        paper_bgcolor="#7b8b8f",
        legend=dict(font=dict(size=12, color="#5465e3", weight="bold")),
        annotations=[
            dict(
                text="Relative Strength Index",
                x=0.5,
                y=1.1,
                showarrow=False,
                xref="paper",
                yref="paper",
                font=dict(size=16, color="#5465e3", weight="bold"),
            ),
            dict(
                text="Weekly Trading Volume",
                x=0.5,
                y=0.5,
                showarrow=False,
                xref="paper",
                yref="paper",
                font=dict(size=16, color="#5465e3", weight="bold"),
            ),
        ],
    )
    fig.update_xaxes(showticklabels=False, row=1, col=1)
    fig.update_xaxes(showticklabels=False, row=2, col=1)

    fig.update_yaxes(
        tickfont=dict(size=12, color="#5465e3", weight="bold"), row=1, col=1
    )
    fig.update_yaxes(
        tickfont=dict(size=12, color="#5465e3", weight="bold"), row=2, col=1
    )
    return fig


def make_bollinger_fig(df, ticker):
    """Creates a figure displaying the stock price with bollinger bands

    Args:
        df (pd.DataFrame):stock data DataFrame
        ticker (str): ticker inputted by the user

    Returns:
        go.Figure: Figuring displaying the bollinger bands
    """
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Close"],
            mode="lines",
            name="Stock Price",
            line=dict(color="black", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["LB"],
            mode="lines",
            name="Lower Bollinger Band",
            line=dict(color="#e04343"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["UB"],
            mode="lines",
            name="Upper Bollinger Band",
            fill="tonexty",
            line=dict(color="#4aed90"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["20_day"],
            mode="lines",
            name="Middle Band",
            line=dict(color="#b143e0"),
        )
    )
    fig.update_xaxes(
        showgrid=False,
        range=[df.index.min(), df.index.max()],
        uirevision="fixed",
        rangeslider_visible=False,
        rangeselector=dict(
            bgcolor="#7b8b8f",
            buttons=list(
                [
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="todate"),
                    dict(count=5, label="5Y", step="year", stepmode="backward"),
                ]
            ),
        ),
    )
    fig.update_layout(
        title=dict(
            text=f"{ticker.upper()} Stock Price With Bollinger Bands",
            x=0.45,
        ),
        title_font=dict(family="white-rabbit", size=22, color="#7b8b8f", weight="bold"),
        xaxis_title="Date",
        xaxis_title_font=dict(
            family="white-rabbit", size=18, color="#7b8b8f", weight="bold"
        ),
        yaxis_title="Price ($)",
        yaxis_title_font=dict(
            family="white-rabbit", size=18, color="#7b8b8f", weight="bold"
        ),
        yaxis_tickfont=dict(
            family="white-rabbit", color="#7b8b8f", weight="bold", size=16
        ),
        xaxis_tickfont=dict(
            family="white-rabbit", color="#7b8b8f", weight="bold", size=16
        ),
        legend=dict(font=dict(family="white-rabbit", size=12, color="#7b8b8f")),
        paper_bgcolor="#5465e3",
        plot_bgcolor="#7b8b8f",
        xaxis=dict(rangeslider=dict(visible=False)),
        height=650,
        updatemenus=updatemenus,
    )

    return fig


def add_weekly_volume(stock_data):
    # helper func to aggregate volume by weeks

    volume_df = pd.DataFrame(stock_data["Volume"])
    volume_df.set_index(stock_data.index, inplace=True)
    # Create a 'quarter' column
    volume_df["week"] = volume_df.index.to_period("W")
    # Group by quarter and sum volume
    monthly_data = volume_df.groupby("week")["Volume"].sum().reset_index()
    # Convert PeriodIndex to Timestamp
    monthly_data["week"] = monthly_data["week"].dt.to_timestamp()

    return monthly_data


def add_insider_trace2(fig, db_df):
    """
    Adds the insider stock transaction data to the graph. For this graph it will start out invisible and users can turn on as needed.
    """
    # Filter the DataFrame into buy and sell DataFrames
    df_buy = db_df[db_df["TRANS_ACQUIRED_DISP_CD"] == "A"]
    df_sell = db_df[db_df["TRANS_ACQUIRED_DISP_CD"] == "D"]

    # create a scatter plot for the insider trading info:
    insider_buy = go.Scatter(
        x=df_buy["FILING_DATE"],
        y=df_buy[
            "TRANS_PRICEPERSHARE"
        ],  # stock_data.loc[db_df['FILING_DATE'], 'Close'],
        mode="markers",
        marker=dict(color="green", size=8, opacity=0.7),
        name="Insider Buys",
        hovertext=db_df.apply(
            lambda row: f"Insider Transaction Info:<br>Shares:{row['TRANS_SHARES']}<br>Avg Cost: ${row['TRANS_PRICEPERSHARE']}<br>Filed on {row['FILING_DATE']}",
            axis=1,
        ),
        hoverinfo="text",
        showlegend=True,
        visible="legendonly",
    )
    insider_sell = go.Scatter(
        x=df_sell["FILING_DATE"],
        y=df_sell[
            "TRANS_PRICEPERSHARE"
        ],  # stock_data.loc[db_df['FILING_DATE'], 'Close'],
        mode="markers",
        marker=dict(color="red", size=8, opacity=0.7),
        name="Insider Sales",
        hovertext=db_df.apply(
            lambda row: f"Insider Transaction Info:<br>Shares:{row['TRANS_SHARES']}<br>Avg Cost: ${row['TRANS_PRICEPERSHARE']}<br>Filed on {row['FILING_DATE']}",
            axis=1,
        ),
        hoverinfo="text",
        showlegend=True,
        visible="legendonly",
    )
    # Add traces to the figure
    fig.add_trace(insider_buy)
    fig.add_trace(insider_sell)
    return fig


if __name__ == "__main__":
    app.run(debug=True)
