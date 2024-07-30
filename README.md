# Insider Stock Transaction Dashboard

This is a dashboard to visualize stock prices and technical indicators in insider trades. This application is made using Python specifically the dash library, plotly, and some css. I have always loved trading stocks and cryptocurrencies and have found insider transaction data extremely useful when trading. The website I used to use to find insider stock data is pretty ugly to me. I found myself going back and forth between this ugly website and trading view drawing vertical lines where insider transactions took place and overall just having a tough time. After finishing the CS50ai course, I wanted to make a big project using Python. I did not want to make a common run-of-the-mill thing that everyone else has done, and most importantly I wanted to provide real use. This was ultimately what I decided to do. I had to learn a lot about data science, working with databases, dataframes, huge TSV files, and processing large amounts of data with maximum efficiency. After completing the first fully working base release, not only have I learned a TON but I truly believe this is a very useful tool for anyone that trades stocks. Essentially any stock can be inputted into this application and all insider transactions along with basic stock data will be visualized cleanly and helpfully.

## Steps to use:

1. git clone git@github.com:koleada/Insider-Stock-Transaction-Dashboard.git
2. Download the database to your local machine from the 'Releases' section of the repository
3. pip install -r requirements.txt
4. **DO NOT FORGET TO CHANGE THE FILE PATH TO THE DATABASE in app.py line 158**
5. Run app.py, open the local file in your browser, input any stock, and begin your analysis!

## Pictures and Explanations:

The application contains two main pages, Insider and Technical.

**Insider Page:**
The insider page contains a main graph showcasing stock prices with all insider transactions overlaid. Upon hovering over the insider transactions you can see a bunch of info like the number of shares, average cost, and date filed. Each of the transactions is either green or red, showing if that transaction was a buy or sell respectively. This main chart can be either log or linear. Below this main chart, there is a chart depicting the monthly insider trading volume for the specific stock along with the overlaid stock price. Finally, on the right side, there is a table containing all insider transactions. The table is ordered by date it shows the shares, average price, buy/sell, and the percent change in holdings after the transaction.

<img src='images/main.jpg' height=250)/>

<img src='images/histogram1.jpg' height=250)/>

**Technical Page:**
The technical page focuses less on insider trades and more on some of the most common and useful technical indicators. The main graph on this page is a candlestick chart of the stock's daily closing price. It then contains 3 commons SMAs 50-day, 100-day, and 200-day. I also highlighted golden and death crosses which, for those unfamiliar, are very effective indicators. A golden cross occurs when the 50-day SMA rises above the 200-day SMA and the reverse indicates a death cross. These indicators are very good at identifying long-term momentum shifts. I did include the insider data on this graph as well but it is not visible at first, it can easily be made visible by clicking on the legend.
<img src='images/page2main.PNG.jpg' height=250)/>

This page also contains a graph showing the relative strength index over the same time frame as the main graph. If unfamiliar with RSI, the two dashed lines show two important levels of strength, the red is 70 and the green is 30. RSI above 70 usually means we are approaching oversold territory. RSI below 30 often aligns closely with local bottoms. Also shown on this graph is the total weekly trading volume again along the same time frame as the main graph.
<img src='images/tagraph.jpg' height=250)/>

Lastly, this page contains a line graph showing the stock price with Bollinger bands overlaid. The middle band is simply the 20-day SMA and the upper and lower bands are created using a simple calculation using the 20-day SMA along with the 20-day standard deviation. Bollinger bands can be very useful in identifying changes in the momentum of a stock's price.
<img src='images/bollinger.jpg' height=250)/>

### Notes:

The insider trading data comes right from the SEC and is stored in the database. Due to the large size of the database, it must be downloaded from the releases section of the repository. (I do not want to spend money on hosting the database but I will continue to search for free hosting options) For now, I will continue to update the database locally and thus provide a new release. The database must be downloaded to your local machine for this dashboard to work.

I included a lot of 'extra' code that I used for testing, creating the database, and generally experimenting before creating the actual application. There was a lot of behind-the-scenes code used to process and clean the quite messy SEC data. I created this project as something that provides use to me but also to share on my resume so I wanted to fully show my entire learning/thought process throughout the creation of this project.
