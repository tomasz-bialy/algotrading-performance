import os
import numpy as np
import pandas as pd
from datetime import datetime, date
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from util import Broker, DataLoader

INVESTMENT_AMT = 10000
RISK_FREE_RATE = 5.75/100
START_DATE = '09/01/2024'
BROKER_LOGIN = os.getenv('BROKER_LOGIN')
BROKER_PASSWORD = os.getenv('BROKER_PASSWORD')

con = Broker(BROKER_LOGIN, BROKER_PASSWORD)
history = con.get_History(start=f"{START_DATE} 00:00:00")
con.logout()

loader = DataLoader(
    from_date=datetime.strptime(START_DATE, '%m/%d/%Y').date(),
    to_date=date(2050, 1, 1),
)
df_index = loader.fetch_index()

df = pd.DataFrame(history['returnData'])
df['date'] = pd.to_datetime(df['close_timeString'].str.replace('CEST', '').str.strip(), format='%a %b %d %H:%M:%S %Y')
df['date'] = df['date'].dt.date
df['log_return'] = np.log(df['close_price'] / df['open_price'])


df_grouped = df.groupby(['symbol', 'date']).apply(
    lambda x: pd.Series({
        'weighted_log_return': (x['log_return'] * x['volume']).sum() / x['volume'].sum(),
        'transaction_profit': x['profit'].sum()
    })
)
df_grouped = df_grouped.sort_values(by='date').reset_index()
df_grouped.loc[0, 'transaction_profit'] = 0
df_grouped.loc[0, 'weighted_log_return'] = np.nan

num_transactions = df_grouped.shape[0]
profitable_transactions = df_grouped[df_grouped['transaction_profit'] > 0].shape[0]
percentage_profitable = (profitable_transactions / num_transactions) * 100
average_win = df_grouped[df_grouped['weighted_log_return'] > 0]['weighted_log_return'].mean()
average_win = np.exp(average_win) - 1
average_win = average_win * 100
average_loss = df_grouped[df_grouped['weighted_log_return'] <= 0]['weighted_log_return'].mean()
average_loss = np.exp(average_loss) - 1
average_loss = average_loss * 100
average_profit_per_transaction = df_grouped['weighted_log_return'].mean()
average_profit_per_transaction = np.exp(average_profit_per_transaction) - 1
average_profit_per_transaction = average_profit_per_transaction * 100

df_grouped2 = df_grouped.groupby('date').agg({'transaction_profit': 'sum'})
df_grouped2 = df_grouped2.rename(columns={'transaction_profit': 'daily_profit'})
df_grouped2 = df_grouped2.sort_values(by='date').reset_index()
df_grouped2['cum_profit'] = df_grouped2['daily_profit'].cumsum()
df_grouped2['cum_profit_pct'] = df_grouped2['cum_profit'] / INVESTMENT_AMT
df_grouped2['daily_log_return'] = np.log((df_grouped2['daily_profit'] + INVESTMENT_AMT) / INVESTMENT_AMT )
df_grouped2['cum_max'] = df_grouped2['cum_profit'].cummax()  
df_grouped2['drawdown'] = df_grouped2['cum_profit'] - df_grouped2['cum_max']
df_grouped2['drawdown_pct'] = df_grouped2['drawdown'] / INVESTMENT_AMT
mean_daily_log_returns = df_grouped2['daily_log_return'].mean()
std_daily_log_returns = df_grouped2['daily_log_return'].std()
daily_risk_free_rate = np.log(1 + RISK_FREE_RATE / 251)
sharpe_ratio = ((mean_daily_log_returns-daily_risk_free_rate)/std_daily_log_returns)*np.sqrt(251)
mean_annual_return = np.exp(mean_daily_log_returns*251) - 1

df_grouped2 = pd.merge(df_grouped2, df_index, on='date', how='left')
df_grouped2['index_daily_log_return'] = np.log(df_grouped2['index_close'] / df_grouped2['index_close'].shift(1))
mean_daily_log_returns_index = df_grouped2['index_daily_log_return'].mean()
std_daily_log_returns_index = df_grouped2['index_daily_log_return'].std()
sharpe_ratio_index = ((mean_daily_log_returns_index-daily_risk_free_rate)/std_daily_log_returns_index)*np.sqrt(251)
df_grouped2['index_close_pct'] = (df_grouped2['index_close'] - df_grouped2['index_close'][0]) / df_grouped2['index_close'][0]
mean_annual_return_index = np.exp(mean_daily_log_returns_index*251) - 1
average_profit_per_transaction_index = 1 - (df_grouped2['index_close'].head(1).values[0] / df_grouped2['index_close'].tail(1).values[0])

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.15,
                    row_heights=[0.8, 0.2],
                    subplot_titles=("Cumulative Profit Over Time", "Strategy Drawdown Over Time"))
fig.add_trace(go.Scatter(x=df_grouped2['date'], y=df_grouped2['cum_profit_pct'], 
                         mode='lines', name='Strategy',
                         line=dict(color='limegreen')), row=1, col=1)
fig.add_trace(go.Scatter(x=df_grouped2['date'], y=df_grouped2['index_close_pct'], 
                         mode='lines', name='Index', 
                         line=dict(color='steelblue')), row=1, col=1)
fig.add_trace(go.Scatter(x=df_grouped2['date'], y=df_grouped2['drawdown_pct'], 
                         mode='lines', name='Drawdown', fill='tozeroy',
                         line=dict(color='red'), showlegend=False), row=2, col=1)
fig.update_layout(
    height=600, 
    width=1000, 
    margin=dict(l=20, r=20, t=20, b=20),
    yaxis=dict(tickformat=".1%", title="Cumulative Profit"),
    yaxis2=dict(tickformat=".1%", title="Drawdown"),
    xaxis=dict(
        showgrid=True, 
        tickformat='%Y/%m/%d',
        showticklabels=True
    ),
    xaxis2=dict(
        showgrid=True, 
        tickformat='%Y/%m/%d',
        showticklabels=True
    ),
    legend=dict(
        x=0+0.01,  
        y=1-0.013,  
        xanchor='left',  
        yanchor='top',  
        orientation='v',  
    )       
)

plot_div = fig.to_html(full_html=False, include_plotlyjs='cdn')

html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Trading Algorithm Performance</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #ffffff;
        }}
        .section {{
            margin-bottom: 30px;
            margin-left: 30px;
        }}
        .section h2 {{
            border-bottom: none;
            color: #0077b5;
            font-size: 1.5em;
            margin-bottom: 10px;
        }}
        .algorithm-info {{
            width: 930px; 
        }}
        table {{
            width: 700px;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        table, td, th {{
            border: 1px solid #dddddd;
            text-align: left;
            padding: 8px;
        }}
        table th {{
            color: black;
            background-color: #e5ecf6;
        }}
        table td:nth-child(2), table td:nth-child(3) {{
            width: 20%;
        }}
        .plotly-figure {{
            margin-top: 20px;
            margin-left: 0;  /* No margin for the plot */
        }}
        .italic-text {{
            font-style: italic;
            margin-top: 10px;
        }}
    </style>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>

    <div class="content">
        <div class="section algorithm-info">
            <h2>Trading Algorithm</h2>
            <p>
            The performance metrics displayed here reflect the live results of my trading algorithm, which is actively managing my real capital. These 
            results are updated daily based on actual trades made by the algorithm through a direct connection to a brokerage account.
            </p>
            <p>
            For comparison, the algorithm's performance is measured against a benchmark, which is a major stock index in the same market. 
            The benchmark follows a passive 'buy-and-hold' strategy, where the index's stocks are simply held without trading.
            </p>
            <p>Author: Tomasz Bialy (<a href="https://www.linkedin.com/in/tomasz-bialy/" target="_blank">LinkedIn profile</a>)</p>
        </div>

        <div class="section performance-metrics">
            <h2>Performance Overview</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Algorithm</th>
                    <th>Index</th>
                </tr>
                <tr>
                    <td>Number of transactions</td>
                    <td>{num_transactions}</td>
                    <td>1</td>
                </tr>
                <tr>
                    <td>Average profit per transaction</td>
                    <td>{average_profit_per_transaction:.2f}%</td>
                    <td>{100*average_profit_per_transaction_index:.2f}%</td>
                </tr>
                <tr>
                    <td>Percentage of profitable transactions</td>
                    <td>{percentage_profitable:.0f}%</td>
                    <td>-</td> 
                </tr>
                <tr>
                    <td>Average profit per won transaction</td>
                    <td>{average_win:.2f}%</td>
                    <td>-</td> 
                </tr>
                <tr>
                    <td>Average profit per lost transaction</td>
                    <td>{average_loss:.2f}%</td>
                    <td>-</td> 
                </tr>
                <tr>
                    <td>Mean annual return</td>
                    <td>{100*mean_annual_return:.1f}%</td>
                    <td>{100*mean_annual_return_index:.1f}%</td> 
                </tr>
                <tr>
                    <td>Sharpe ratio <a href="https://www.investopedia.com/terms/s/sharperatio.asp" target="_blank">[1]</a></td>
                    <td>{sharpe_ratio:.2f}</td>
                    <td>{sharpe_ratio_index:.2f}</td> 
                </tr>
            </table>
            <p class="italic-text">(Last updated: {datetime.now().strftime("%Y-%m-%d")})</p>
        </div>
        <div class="plotly-figure">
            {plot_div}
        </div>
    </div>
</body>
</html>
"""

with open("index.html", "w") as f:
    f.write(html_template)