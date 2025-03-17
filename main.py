import yfiance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import requests
import streamlit as st # For Streamlit Dashboard
import plotly.graph_objects as go # For Streamlit Dashboard

# Data Collection Layer
def fetch_stock_data(ticker, period="3mo", interval="1d"):
  """Fetch historical stock data from Yahoo finance"""
  stock = yf.Ticker(ticker)
  df = stock.history(period=period, interval=interval)
  return df

#Signal Collection

#Moving Average Crossover

def ma_crossover_signal(df, short_windwo=20, long_window=50):
  """Generate signals based on the moving average crossover"""
  signals = pd.DataFrame(index=df.index)
  signals['price'] = df['Close']
  signals['short_mavg'] = df['Close'].rolling(window=short_window).mean()
  signals['long_mavg'] = df['Close'].rolling(window=long_window).mean()
  signals['signal'] = 0.0

#Generate signals
signals['signal'][short_window:] = np.where(
  signals['short_mavg'][short_window:] > signals['long_mavg'][short_window:], 1.0, 0.0)

#Generating Trading orders
signals['position'] = signals['signal'].diff()

return signals

#RSI Overbought/Oversold
def rsi_signal(df, period=14, upper=70, lower=30):
    """Generate signals based on RSI indicator"""
    signals = pd.DataFrame(index=df.index)
    signals['price'] = df['Close']
    
    # Calculate RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    signals['rsi'] = 100 - (100 / (1 + rs))
    
    # Generate signals
    signals['signal'] = 0.0
    signals['signal'] = np.where(signals['rsi'] < lower, 1.0, 0.0)  # Oversold - buy signal
    signals['signal'] = np.where(signals['rsi'] > upper, -1.0, signals['signal'])  # Overbought - sell signal
    
    return signals

#Volume Spike Detection
def volume_spike_signal(df, window=20, threshold=2.0):
    """Generate signals based on unusual volume spikes"""
    signals = pd.DataFrame(index=df.index)
    signals['price'] = df['Close']
    signals['volume'] = df['Volume']
    
    # Calculate average volume
    signals['avg_volume'] = df['Volume'].rolling(window=window).mean()
    signals['volume_ratio'] = signals['volume'] / signals['avg_volume']
    
    # Generate signals on volume spikes with price increase
    signals['signal'] = 0.0
    price_change = df['Close'].pct_change()
    signals['signal'] = np.where((signals['volume_ratio'] > threshold) & 
                                 (price_change > 0), 1.0, 0.0)
    
    return signals

#Backtesting Module

def backtest_strategy(signals, initial_capital=100000.0):
    """Backtest a trading strategy based on generated signals"""
    # Create a position column
    positions = pd.DataFrame(index=signals.index).fillna(0.0)
    positions['position'] = signals['signal']
    
    # Initialize portfolio
    portfolio = pd.DataFrame(index=signals.index)
    portfolio['positions'] = positions['position'] * signals['price']
    portfolio['cash'] = initial_capital - (positions['position'].diff().fillna(0) * signals['price']).cumsum()
    portfolio['total'] = portfolio['positions'] + portfolio['cash']
    portfolio['returns'] = portfolio['total'].pct_change()
    
    # Performance metrics
    sharpe_ratio = np.sqrt(252) * (portfolio['returns'].mean() / portfolio['returns'].std())
    cumulative_return = (portfolio['total'][-1] / portfolio['total'][0]) - 1
    
    return portfolio, sharpe_ratio, cumulative_return

#Alert System

def send_email_alert(subject, message, to_email, from_email, password):
    """Send an email alert"""
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(from_email, password)
    server.send_message(msg)
    server.quit()

def send_telegram_alert(message, bot_token, chat_id):
    """Send a Telegram alert"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message
    }
    response = requests.post(url, data=data)
    return response.json()

#Dashboard with Streamlit (comment out if you don't want to use streamlit)
def run_dashboard():
    st.title("SignalSprint Trading Dashboard")
    
    # Sidebar for user inputs
    st.sidebar.header("Settings")
    ticker = st.sidebar.text_input("Stock Ticker", "AAPL")
    
    # Fetch data
    data = fetch_stock_data(ticker)
    
    # Generate signals
    ma_signals = ma_crossover_signal(data)
    rsi_signals = rsi_signal(data)
    volume_signals = volume_spike_signal(data)
    
    # Plot the data
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines', name='Price'))
    fig.add_trace(go.Scatter(x=ma_signals.index, y=ma_signals['short_mavg'], mode='lines', name='20-day MA'))
    fig.add_trace(go.Scatter(x=ma_signals.index, y=ma_signals['long_mavg'], mode='lines', name='50-day MA'))
    
    # Add buy signals
    buy_signals = ma_signals[ma_signals['positions'] == 1.0]
    fig.add_trace(go.Scatter(
        x=buy_signals.index, 
        y=buy_signals['price'],
        mode='markers',
        marker=dict(size=10, color='green', symbol='triangle-up'),
        name='Buy Signal'
    ))
    
    st.plotly_chart(fig)
    
    # Display recent signals
    st.header("Recent Signals")
    combined_signals = pd.DataFrame(index=data.index)
    combined_signals['MA Crossover'] = ma_signals['positions']
    combined_signals['RSI'] = rsi_signals['signal']
    combined_signals['Volume Spike'] = volume_signals['signal']
    
    st.dataframe(combined_signals.tail(10))

