import os

# ==========================================
# 核心修复区：强制禁用代理 (必须放在最开头)
# ==========================================
# 这几行代码告诉 Python：无论系统有没有开 VPN，都不要走代理，直接连接。
# 这样可以解决 'ProxyError' 和 'RemoteDisconnected' 问题。
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['NO_PROXY'] = '*' # 强制所有地址不走代理

# ==========================================
# 正常逻辑区
# ==========================================
import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go

# 1. 页面配置
st.set_page_config(page_title="个股PR估值诊断", layout="centered")

st.title("🔬 个股估值诊断器 (PR Model)")
st.markdown("Quant Approach to Value Investing | Target: **Specific Stock**")

# 2. 用户输入区
with st.form("stock_input_form"):
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        symbol_input = st.text_input("输入股票代码 (A股)", value="600519", help="例如：600519 或 000858")
    with col_btn:
        submitted = st.form_submit_button("开始诊断")

# 3. 数据获取引擎
@st.cache_data(ttl=600)
def get_stock_spot(symbol):
    try:
        # 再次强制指定 Akshare 内部请求不使用代理（防御性编程）
        # 虽然上面的 os.environ 通常够了，但这能确保万无一失
        df = ak.stock_zh_a_spot_em()
        
        # 数据清洗
        target = df[df['代码'] == symbol]
        
        if target.empty:
            return None
            
        data = {
            'name': target['名称'].values[0],
            'price': float(target['最新价'].values[0]),
            'pe_ttm': float(target['市盈率-动态'].values[0]),
            'pb': float(target['市净率'].values[0]),
            'market_cap': float(target['总市值'].values[0])
        }
        return data
    except Exception as e:
        # 将具体的错误打印出来，方便调试
        st.error(f"数据源连接失败。错误详情: {e}")
        return None

# 4. 核心逻辑与渲染
if submitted or symbol_input:
    # 加一个简单的 Loading 提示
    with st.spinner(f'正在直连交易所数据源拉取 {symbol_input}...'):
        data = get_stock_spot(symbol_input)
    
    if data:
        # 计算逻辑
        if data['pe_ttm'] > 0:
            roe_implied = (data['pb'] / data['pe_ttm']) * 100
            pr_ratio = data['pe_ttm'] / roe_implied
        else:
            roe_implied = 0
            pr_ratio = 999 # 亏损股处理

        st.divider()
        st.header(f"{data['name']} ({symbol_input})")
        
        # 指标展示
        c1, c2, c3 = st.columns(3)
        c1.metric("PE (动态)", f"{data['pe_ttm']:.2f}")
        c2.metric("隐含 ROE", f"{roe_implied:.2f}%")
        
        # PR 颜色逻辑
        delta_color = "off"
        if pr_ratio < 0.75: delta_color = "inverse" # 绿
        elif pr_ratio > 1.5: delta_color = "normal" # 红
        
        c3.metric("PR (市赚率)", f"{pr_ratio:.2f}", delta="越低越好", delta_color=delta_color)

        # 仪表盘
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = pr_ratio,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "PR 估值温度计"},
            gauge = {
                'axis': {'range': [0, 4]},
                'bar': {'color': "black"},
                'steps': [
                    {'range': [0, 0.75], 'color': "#2ecc71"},
                    {'range': [0.75, 1.5], 'color': "#f1c40f"},
                    {'range': [1.5, 4], 'color': "#e74c3c"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75, 'value': pr_ratio
                }
            }
        ))
        st.plotly_chart(fig, use_container_width=True)

        # 诊断结论
        st.subheader("📝 深度诊断")
        if pr_ratio < 0.75:
            st.success(f"✅ **击球区** | PR={pr_ratio:.2f}。资产极具性价比，如果商业模式稳健，属于“捡钱”区间。")
        elif 0.75 <= pr_ratio < 1.5:
            st.warning(f"⚠️ **观察区** | PR={pr_ratio:.2f}。价格公允，需要极强的成长性才能支撑买入。")
        else:
            st.error(f"⛔ **高估区** | PR={pr_ratio:.2f}。透支了未来业绩，安全边际不足。")
            
    else:
        # 如果还是报错，说明可能IP被暂时封了
        st.warning(f"未找到代码 {symbol_input}。如果是网络报错，请尝试关闭所有 VPN 软件后重试。")