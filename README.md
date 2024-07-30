# Insider Stock Transaction Dashboard 

This is a dashboard to visualize stock price, technical indicators in insider trades. This application is made using python specifically the dash library, plotly and some css. I have always loved trading stocks and crypto currencies and have found insider transaction data extremely useful when trading. The website I used to use to find insider stock data is pretty ugly to me. I found myself going back and forth between this ugly website and trading view drawing vertical lines where insider transactions took place and overall just having a tough time. After finishing the CS50ai course, I wanted to make a big project using python. I did not want to make a common run of the mill thing that everyone else has done, and most importantly I wanted to provide real use. This was ultimately what I decided to do. I had to learn a lot about data science, working with databases, dataframes, huge TSV files and processing large amounts of data with maximum efficiency. After completing the first fully working base release, not only have I learned a TON but I truly believe this is a very useful tool for anyone that trades stocks. Essentially any stock can be inputted into this application and all of insider transactions along with basic stock data will be visualized in a clean and helpful way.  


The insider trading data comes right from the SECs data and is stored in the database. Due to the large size of the database, it must be downloaded from the releases section of the repository. (I dont want to spend money on hosting the database but I will continue to search for free hosting options) For now, I will continue to update the database locally and thus provide a new release. The database must be downloaded to your local machine for this dashboard to work. 


Steps to use: 

1. git clone git@github.com:koleada/Insider-Stock-Transaction-Dashboard.git
2. Download database to your local machine from the 'Releases' section of the repository
3. pip install -r requirements.txt
4. ** DO NOT FORGET TO CHANGE THE FILE PATH TO THE DATABASE in app.py line 158 **
5. Run app.py, open the local file in your browser, input any stock and begin your analysis!


I included a lot of 'extra' code that I used for testing, creating the database and generally experimenting before creating the actual application. There was a lot of behind the scenes code used to process and clean the quite messy SEC data. I created this project as something that provides use to me but also to share on my resume so I wanted to fully show my entire learning/thought process throughout the creation of this project.

The application contains two main pages, Insider and Technical. The insider page contains a main graph showcasing stock price with all insider transactions overlaid. Upon hovering over the insider transactions you can see a bunch of info like number of shares, average cost, and date filed. Each of the transactions are either green or red, showing if that transaction was a buy or sell respectively. This main chart can be either log or linear. Below this main chart there is a chart depicting the monthly insider trading volume for the specific stock. Finally, on the right side there is a table containing all insider transactions. The table is ordered by date it shows the shares, avg price, buy/sell and the percent change in holdings after the transaction. 
