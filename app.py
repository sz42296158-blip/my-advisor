import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import time

# ==========================================
# 資料儲存與處理設定
# ==========================================
PORTFOLIO_FILE = "portfolio.json"

def load_data():
    default_scan_pool = ["2330.TW", "2317.TW", "2454.TW", "2382.TW", "3231.TW", "2303.TW", "0050.TW"]
    default_data = {"watchlist": ["2330.TW"], "holdings": {}, "scan_pool": default_scan_pool}
    
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return default_data
                if "scan_pool" not in data:
                    data["scan_pool"] = default_scan_pool
                return data
        except:
            return default_data
    return default_data

def save_data(data):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f)

def format_ticker(ticker):
    t = ticker.strip().upper()
    if t and t[0].isdigit() and '.' not in t:
        return f"{t}.TW"
    return t

# ==========================================
# 核心分析與繪圖邏輯
# ==========================================
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        return df
    except Exception as e:
        return pd.DataFrame() 

def analyze_stock(df):
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    
    delta = df['Close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=13, adjust=False).mean()
    ema_down = down.ewm(com=13, adjust=False).mean()
    rs = ema_up / ema_down
    df['RSI'] = 100 - (100 / (1 + rs))
    
    latest = df.iloc[-1]
    current_price = latest['Close']
    ma5 = latest['MA5']
    ma10 = latest['MA10']
    ma20 = latest['MA20']
    ma50 = latest['MA50']
    rsi = latest['RSI']
    
    current_price_rounded = round(current_price, 2)
    recent_high = round(df['High'].tail(20).max(), 2)
    
    if ma20 > ma50:
        if rsi >= 70:
            recommendation = "🟡 觀望 (Hold) - 短線過熱"
            suggested_buy_price = round(ma20, 2)
            suggested_sell_price = recent_high
            status = f"雖然趨勢偏多，但 RSI 指標高達 {rsi:.1f}，顯示目前處於「超買」過熱狀態。建議耐心等待價格回檔至 MA20 ({suggested_buy_price}) 附近再作考慮。"
        else:
            recommendation = "🟢 推薦買入 (Buy)"
            suggested_sell_price = recent_high
            bias_ratio = (current_price - ma20) / ma20
            
            if bias_ratio > 0.08:
                suggested_buy_price = round(ma5, 2)
                status = f"強勢多頭飆升！現價 ({current_price_rounded})，尚未過熱 (RSI: {rsi:.1f})。已切換至 **5 日均線** ({suggested_buy_price}) 作為積極買入參考。"
            elif bias_ratio > 0.04:
                suggested_buy_price = round(ma10, 2)
                status = f"多頭穩步上漲中。現價 ({current_price_rounded})，尚未過熱 (RSI: {rsi:.1f})。已切換至 **10 日均線** ({suggested_buy_price}) 作為短線買入參考。"
            else:
                suggested_buy_price = round(ma20, 2)
                status = f"穩健多頭趨勢且尚未過熱 (RSI: {rsi:.1f})。現價 ({current_price_rounded})，維持以 **20 日均線** ({suggested_buy_price}) 作為回檔買入支撐。"
            
    elif ma20 < ma50:
        recommendation = "🔴 推薦賣出 (Sell)"
        suggested_buy_price = round(ma20, 2) 
        suggested_sell_price = round(ma20, 2)
        status = f"空頭趨勢 (RSI: {rsi:.1f})。當前價格 {current_price_rounded}。建議果斷出脫，或趁反彈至 MA20 壓力位 ({suggested_sell_price}) 時減碼停損。"
    else:
        recommendation = "🟡 觀望 (Hold)"
        suggested_buy_price = round(ma20, 2)
        suggested_sell_price = recent_high
        status = f"趨勢不明確 (RSI: {rsi:.1f})。當前價格 {current_price_rounded}。建議在支撐 ({suggested_buy_price}) 與壓力 ({suggested_sell_price}) 區間內觀察。"
        
    return df, recommendation, status, suggested_buy_price, suggested_sell_price, current_price_rounded

def plot_interactive_chart(df, ticker):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, row_heights=[0.7, 0.3])
    
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K 線'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='pink', width=1, dash='dot'), name='5日均線'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA10'], line=dict(color='yellow', width=1, dash='dot'), name='10日均線'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=2), name='20日均線'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA50'], line=dict(color='blue', width=2), name='50日均線'), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=1.5), name='RSI (14)'), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    fig.update_layout(title=f'{ticker.upper()} 走勢與 RSI 指標', template='plotly_dark', xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0), height=500)
    fig.update_yaxes(title_text="股價", row=1, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=2, col=1) 
    
    return fig

@st.cache_data(ttl=600) 
def scan_market_opportunities(market_pool):
    opportunities = []
    # 如果名單太長，限制最多掃描 40 檔避免雲端當機
    safe_pool = market_pool[:40] 
    
    for ticker in safe_pool:
        df = get_stock_data(ticker)
        if not df.empty:
            _, rec, status, buy_price, sell_price, current_price = analyze_stock(df)
            if "買入" in rec:
                opportunities.append({
                    "ticker": ticker,
                    "status": status,
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                    "current_price": current_price
                })
        time.sleep(1.5) 
            
    return opportunities

# ==========================================
# 網頁介面設計開始
# ==========================================
st.set_page_config(page_title="專屬投資顧問", layout="wide")
app_data = load_data()

# ------------------------------------------
# 側邊欄：投資組合管理 與 雷達管理
# ------------------------------------------
st.sidebar.title("💼 投資組合管理")

st.sidebar.subheader("💰 新增 / 更新持倉")
h_ticker = st.sidebar.text_input("輸入代碼 (例如: 0056)", key="h_ticker_input")
col_p, col_q = st.sidebar.columns(2)
h_price = col_p.number_input("買入均價", min_value=0.0, step=1.0, format="%.2f")
h_qty = col_q.number_input("持有股數", min_value=0, step=1)

if st.sidebar.button("➕ 加入持倉"):
    if h_ticker and h_qty > 0:
        fmt_ticker = format_ticker(h_ticker)
        app_data["holdings"][fmt_ticker] = {"price": h_price, "quantity": h_qty}
        if fmt_ticker in app_data["watchlist"]:
            app_data["watchlist"].remove(fmt_ticker)
        save_data(app_data)
        st.cache_data.clear() 
        st.rerun()

st.sidebar.write("---")

st.sidebar.subheader("👀 新增關注股票")
w_ticker = st.sidebar.text_input("輸入代碼 (例如: 006208)", key="w_ticker_input")
if st.sidebar.button("➕ 加入關注"):
    if w_ticker:
        fmt_ticker = format_ticker(w_ticker)
        if fmt_ticker not in app_data["watchlist"] and fmt_ticker not in app_data["holdings"]:
            app_data["watchlist"].append(fmt_ticker)
            save_data(app_data)
            st.cache_data.clear() 
            st.rerun()

# 💡【全新精銳部隊功能區塊】
st.sidebar.write("---")
st.sidebar.subheader("🔍 管理雷達掃描清單")

if st.sidebar.button("👑 一鍵載入台灣 Top 40 精銳", type="primary"):
    # 寫入台灣最具代表性的 40 檔高流動性權值股
    top_40_list = [
        "2330.TW", "2317.TW", "2454.TW", "2382.TW", "2308.TW", "2881.TW", "2882.TW", "2412.TW", "2891.TW", "3231.TW",
        "2303.TW", "2886.TW", "1301.TW", "1303.TW", "2002.TW", "1216.TW", "2884.TW", "2892.TW", "2603.TW", "2885.TW",
        "3711.TW", "5871.TW", "2357.TW", "2880.TW", "2379.TW", "2395.TW", "3045.TW", "2912.TW", "1101.TW", "2207.TW",
        "2883.TW", "1326.TW", "2887.TW", "6669.TW", "3034.TW", "2890.TW", "3008.TW", "2324.TW", "2353.TW", "2609.TW"
    ]
    app_data["scan_pool"] = top_40_list
    save_data(app_data)
    st.cache_data.clear()
    st.rerun()

s_ticker = st.sidebar.text_input("輸入代碼加入掃描 (例如: 0050)", key="s_ticker_input")
if st.sidebar.button("➕ 手動加入雷達"):
    if s_ticker:
        fmt_ticker = format_ticker(s_ticker)
        if fmt_ticker not in app_data["scan_pool"]:
            app_data["scan_pool"].append(fmt_ticker)
            save_data(app_data)
            st.cache_data.clear()
            st.rerun()

st.sidebar.write("---")
st.sidebar.subheader("🗑️ 移除股票清單")

with st.sidebar.expander("展開查看並編輯目前雷達名單"):
    for ticker in list(app_data["scan_pool"]):
        col1, col2 = st.columns([3, 1])
        col1.write(f"📡 {ticker}")
        if col2.button("❌", key=f"del_s_{ticker}"):
            app_data["scan_pool"].remove(ticker)
            save_data(app_data)
            st.cache_data.clear()
            st.rerun()

st.sidebar.write("---")

for ticker in list(app_data["holdings"].keys()):
    col1, col2 = st.sidebar.columns([3, 1])
    col1.write(f"💼 持倉: {ticker}")
    if col2.button("❌", key=f"del_h_{ticker}"):
        del app_data["holdings"][ticker]
        save_data(app_data)
        st.rerun()

for ticker in app_data["watchlist"]:
    col1, col2 = st.sidebar.columns([3, 1])
    col1.write(f"👀 關注: {ticker}")
    if col2.button("❌", key=f"del_w_{ticker}"):
        app_data["watchlist"].remove(ticker)
        save_data(app_data)
        st.rerun()

# ------------------------------------------
# 主畫面：分析與損益報告
# ------------------------------------------
st.title("📈 專屬投資組合與大盤分析")

st.header("🌟 今日精銳部隊推薦") 
st.markdown("系統每 10
