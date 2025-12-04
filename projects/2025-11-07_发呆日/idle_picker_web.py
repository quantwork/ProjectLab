import streamlit as st
import csv, os, re, random, time
import pandas as pd
from datetime import datetime, timedelta
import webbrowser

# ------- 配置与核心逻辑 (复用原逻辑) -------
DEFAULT_POOL = r"D:\Quant\ProjectLab\projects\2025-11-07_发呆日\idle_pool.md"
DEFAULT_LOG  = r"D:\Quant\ProjectLab\projects\2025-11-07_发呆日\logs\idle_pick_log.csv"

def normalize(s:str)->str:
    return re.sub(r"\s+"," ", s.strip())

def ensure_dir(p:str):
    d=os.path.dirname(os.path.abspath(p))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def read_pool(path:str):
    if not os.path.exists(path):
        return []
    ext=os.path.splitext(path)[1].lower()
    items=[]
    try:
        if ext==".csv":
            # 简化 CSV 读取，使用 pandas 更稳健
            df = pd.read_csv(path)
            # 假设有一列叫 title
            col = next((c for c in df.columns if c.lower() == 'title'), None)
            if col:
                items = df[col].dropna().astype(str).tolist()
        else:
            with open(path,"r",encoding="utf-8-sig") as f:
                for line in f:
                    line=normalize(line)
                    if not line or line.startswith("#") or line.startswith(">"):
                        continue
                    line=re.sub(r"^[-*\d\.)]+\s*","",line)
                    items.append(line)
    except Exception as e:
        st.error(f"读取清单失败: {e}")
    return items

def read_recent_titles(log_path:str, dedup_days:int)->set:
    if not os.path.exists(log_path): return set()
    try:
        df = pd.read_csv(log_path)
        df['date'] = pd.to_datetime(df['date'])
        cutoff = datetime.now() - timedelta(days=dedup_days)
        recent = df[df['date'] >= cutoff]
        return set(recent['title'].unique())
    except Exception:
        return set()

def split_title_url(s:str):
    if "|" in s:
        left, right = s.split("|", 1)
        return normalize(left), normalize(right)
    return s, None

def append_log(log_path:str, title:str):
    ensure_dir(log_path)
    exists = os.path.exists(log_path)
    with open(log_path, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "time", "title"])
        if not exists: w.writeheader()
        now = datetime.now()
        w.writerow({
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "title": title
        })

# ------- Streamlit 页面布局 -------

st.set_page_config(page_title="灵感抽取器", page_icon="🎲", layout="centered")

# CSS 美化：大卡片显示
st.markdown("""
<style>
    .big-font {
        font-size: 30px !important;
        font-weight: bold;
        color: #FF4B4B;
        text-align: center;
        padding: 20px;
        border: 2px dashed #cccccc;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .stButton>button {
        width: 100%;
        height: 3em;
        font-size: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- 侧边栏：设置 ---
with st.sidebar:
    st.title("🎲 灵感配置")
    
    # 1. 常用参数 (直接显示，最简洁)
    excl_input = st.text_input("排除关键词", value="", placeholder="例如：交易 策略", help="输入不想看到的词，用空格分隔")
    dedup_days = st.slider("最近去重 (天)", 0, 90, 30, help="最近多少天抽过的不再显示")
    
    st.divider()

    # 2. 路径设置 (默认折叠，需要修改时再点开)
    with st.expander("📂 文件路径设置"):
        pool_path = st.text_input("清单文件", value=DEFAULT_POOL)
        log_path = st.text_input("日志文件", value=DEFAULT_LOG)
        
        if st.button("🔄 刷新数据读取"):
            st.cache_data.clear()
            st.success("已刷新")
            
    # 底部版权或提示
    st.caption("ZeroPhase · Idle Picker")

# --- 主界面 ---
st.title("💡 灵感抽取器 Web版")
st.caption("不知道做什么？让随机性来决定。")

# 1. 准备数据
items = read_pool(pool_path)
excl_words = [w.strip() for w in excl_input.split() if w.strip()]
seen_titles = read_recent_titles(log_path, dedup_days)

# 过滤逻辑
candidates = [t for t in items if not any(w in t for w in excl_words) and t not in seen_titles]
if not candidates:
    # 如果过滤后为空，回退到仅关键词过滤
    candidates = [t for t in items if not any(w in t for w in excl_words)]

st.info(f"当前池中共有 **{len(items)}** 条灵感，过滤后剩余 **{len(candidates)}** 条可用。")

# 2. 抽取区域
if 'current_pick' not in st.session_state:
    st.session_state.current_pick = None
if 'current_url' not in st.session_state:
    st.session_state.current_url = None

col1, col2 = st.columns([3, 1])

with col1:
    # 这是显示结果的占位符
    result_placeholder = st.empty()

    if st.button("🎲 开始抽取", type="primary"):
        if not candidates:
            st.error("没有可抽取的项目！请检查清单或放宽过滤条件。")
        else:
            # 动画效果：快速滚动显示
            n_jumps = 15
            for i in range(n_jumps):
                temp_pick = random.choice(candidates)
                # 模拟滚动速度变慢
                sleep_time = 0.05 + (i / n_jumps) * 0.1
                result_placeholder.markdown(f'<div class="big-font" style="color:#aaa">{temp_pick}</div>', unsafe_allow_html=True)
                time.sleep(sleep_time)
            
            # 最终结果
            final_pick = random.choice(candidates)
            disp_title, disp_url = split_title_url(final_pick)
            
            st.session_state.current_pick = disp_title
            st.session_state.current_url = disp_url
            
            # 写入日志
            append_log(log_path, disp_title)
            
            # 撒花庆祝
            st.balloons()

# 保持显示最终结果（防止刷新消失）
if st.session_state.current_pick:
    result_placeholder.markdown(f'<div class="big-font">{st.session_state.current_pick}</div>', unsafe_allow_html=True)
    
    if st.session_state.current_url:
        st.link_button("🔗 点击打开相关链接", st.session_state.current_url)
    else:
        st.caption("此条目无链接")

# 3. 历史记录 (日志展示)
st.divider()
st.subheader("📝 最近抽取记录")

if os.path.exists(log_path):
    try:
        df_log = pd.read_csv(log_path)
        # 按时间倒序
        df_log = df_log.sort_index(ascending=False).head(10)
        st.dataframe(df_log, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error("日志文件格式可能有误")
else:
    st.write("尚无记录")

# 页脚
st.markdown("---")
st.markdown("<div style='text-align: center; color: grey;'>ZeroPhase · Idle Picker v1.0 Web</div>", unsafe_allow_html=True)