import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import time

# ==========================================
# 資料儲存與處理設定 (已升級支援動態雷達)
# ==========================================
PORTFOLIO_FILE = "portfolio.json"

def load_data():
    # 預設的初始雷達名單
    default_scan_pool = [
        "2330.TW", "2317.TW", "2454.TW", "2382.TW", "3231.TW", "2303.TW",
        "2881.TW", "2882.TW", "0050.TW", "0056.TW", "00878.TW"
    ]
    default_data = {"watchlist": ["2330.TW"], "holdings": {}, "scan_pool": default_scan_pool}
    
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return default_data
                # 防呆：如果舊檔案沒有 scan_pool，自動幫補上預設名單
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

# --- 市場機會掃描器 (已升級：傳入動態清單) ---
@st.cache_data(ttl=600) 
def scan_market_opportunities(market_pool):
    opportunities = []
    for ticker in market_pool:
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
        time.sleep(1.5) # 禮貌休息
            
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

# 💡【新增區塊】動態雷達掃描管理工具
st.sidebar.write("---")
st.sidebar.subheader("🔍 管理雷達掃描清單")
s_ticker = st.sidebar.text_input("輸入代碼加入掃描 (例如: 2603)", key="s_ticker_input")
if st.sidebar.button("➕ 加入雷達"):
    if s_ticker:
        fmt_ticker = format_ticker(s_ticker)
        if fmt_ticker not in app_data["scan_pool"]:
            app_data["scan_pool"].append(fmt_ticker)
            save_data(app_data)
            st.cache_data.clear() # 清除舊快取強制重掃
            st.rerun()

st.sidebar.write("---")
st.sidebar.subheader("🗑️ 移除股票清單")

# 顯示雷達刪除按鈕
for ticker in list(app_data["scan_pool"]):
    col1, col2 = st.sidebar.columns([3, 1])
    col1.write(f"📡 雷達: {ticker}")
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

st.header("🌟 今日台股精選推薦") 
st.markdown("系統每 10 分鐘自動掃描您設定的雷達池，挑選出目前**多頭向上且尚未過熱**的所有潛在機會。")

with st.spinner("正在為您全方位掃描市場機會..."):
    try:
        # 💡【關鍵修改】傳入動態設定的 scan_pool
        opportunities = scan_market_opportunities(app_data["scan_pool"])
        if not opportunities:
            st.info("目前雷達清單中暫無符合安全買入條件的個股。您可以從左側邊欄新增更多股票進雷達池喔！")
        else:
            for i in range(0, len(opportunities), 3):
                chunk = opportunities[i:i+3]
                cols = st.columns(len(chunk))
                for idx, opp in enumerate(chunk):
                    with cols[idx]:
                        st.markdown(f"### 🎯 {opp['ticker']}")
                        st.success("🟢 推薦買入")
                        st.markdown(f"**現價**：{opp['current_price']}")
                        st.info(f"💰 建議買入/支撐：**{opp['buy_price']}**\n\n🎯 目標賣出/壓力：**{opp['sell_price']}**")
                        st.caption(opp['status'])
    except Exception as e:
         st.warning("⚠️ Yahoo 伺服器目前較為繁忙，請稍候 1~2 分鐘後點擊右上角重新整理 (Rerun)。")

st.write("---")

st.header("💼 我的持倉表現")
if not app_data["holdings"]:
    st.info("目前沒有持倉紀錄，請從左側邊欄新增。")
else:
    total_cost_all = 0.0
    total_value_all = 0.0
    with st.spinner("正在計算整體持倉損益..."):
        for ticker, info in app_data["holdings"].items():
            data = get_stock_data(ticker)
            if not data.empty:
                latest = data.iloc[-1]
                current_price = latest['Close']
                total_cost_all += info["price"] * info["quantity"]
                total_value_all += current_price * info["quantity"]
        
        total_pnl = total_value_all - total_cost_all
        total_pnl_percent = (total_pnl / total_cost_all * 100) if total_cost_all > 0 else 0
        
        if total_pnl > 0:
            overall_advice = "🟢 整體投資組合目前處於獲利狀態。若部分個股出現 RSI 過熱訊號，可考慮分批部分停利入袋。"
        elif total_pnl < 0:
            overall_advice = "🔴 整體投資組合目前呈現虧損。建議檢視持倉中是否有跌破關鍵均線支撐的弱勢股，必要時執行停損。"
        else:
            overall_advice = "🟡 整體投資組合目前處於損益兩平附近。建議持續觀察大盤走向。"

    st.markdown("#### 📊 整體表現摘要")
    sum_col1, sum_col2, sum_col3 = st.columns(3)
    with sum_col1:
        st.metric(label="投資總成本", value=f"{total_cost_all:,.2f}")
    with sum_col2:
        st.metric(label="目前總市值", value=f"{total_value_all:,.2f}")
    with sum_col3:
        st.metric(label="未實現總損益", value=f"{total_pnl:,.2f}", delta=f"{total_pnl_percent:.2f}%")
    
    st.info(f"**總體操作建議**：\n{overall_advice}")
    st.write("---")
    
    st.markdown("#### 📋 個股詳細狀況")
    for ticker, info in app_data["holdings"].items():
        with st.container():
            st.markdown(f"### 📌 【持倉】 {ticker}")
            data = get_stock_data(ticker)
            if not data.empty:
                analyzed_data, rec, status, buy_price, sell_price, current_price = analyze_stock(data)
                cost_price = info["price"]
                qty = info["quantity"]
                total_cost = cost_price * qty
                current_value = current_price * qty
                pnl = current_value - total_cost
                pnl_percent = (pnl / total_cost * 100) if total_cost > 0 else 0
                pnl_color = "red" if pnl >= 0 else "green" 
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown(f"**買入均價**：{cost_price} | **持有股數**：{qty}")
                    st.markdown(f"**目前現價**：{current_price:.2f}")
                    st.markdown(f"**未實現損益**：:<span style='color:{pnl_color}; font-size:20px; font-weight:bold;'>{pnl:.2f} ({pnl_percent:.2f}%)</span>", unsafe_allow_html=True)
                    st.write("---")
                    
                    if "觀望" in rec:
                        st.warning(f"系統建議：{rec}")
                    elif "賣出" in rec:
                        st.error(f"系統建議：{rec}")
                    else:
                        st.success(f"系統建議：{rec}")
                        
                    st.info(f"💰 建議買入/支撐：**{buy_price}**\n\n🎯 建議賣出/壓力：**{sell_price}**")
                    st.markdown(status)
                with col2:
                    st.plotly_chart(plot_interactive_chart(analyzed_data, ticker), use_container_width=True)
            else:
                st.warning(f"⚠️ 暫時無法取得 {ticker} 的資料，可能受到網路或流量限制，請稍候再試。")
        st.write("---")

st.header("👀 關注清單分析")
if not app_data["watchlist"]:
    st.info("目前沒有關注股票，請從左側邊欄新增。")
else:
    for ticker in app_data["watchlist"]:
        with st.container():
            st.markdown(f"### 📌 【關注】 {ticker}")
            data = get_stock_data(ticker)
            if not data.empty:
                analyzed_data, rec, status, buy_price, sell_price, current_price = analyze_stock(data)
                col1, col2 = st.columns([1, 2])
                with col1:
                    if "觀望" in rec:
                        st.warning(f"系統建議：{rec}")
                    elif "賣出" in rec:
                        st.error(f"系統建議：{rec}")
                    else:
                        st.success(f"系統建議：{rec}")
                        
                    st.info(f"💰 建議買入/支撐：**{buy_price}**\n\n🎯 建議賣出/壓力：**{sell_price}**")
                    st.markdown(status)
                with col2:
                    st.plotly_chart(plot_interactive_chart(analyzed_data, ticker), use_container_width=True)
            else:
                 st.warning(f"⚠️ 暫時無法取得 {ticker} 的資料，請稍候再試。")
        st.write("---")
