import streamlit as st
import pandas as pd
import os
from datetime import datetime

# ================= 配置区 =================
# 依然建议使用绝对路径，防止找不到文件
DATA_FILE = "literature_db.csv"
PAGE_TITLE = "QuantResearch · 文献库"

st.set_page_config(page_title=PAGE_TITLE, page_icon="📚", layout="wide")

# ================= 核心逻辑：数据读写 =================

def load_data():
    """读取数据，自动处理编码与新增列"""
    # 1. 定义标准列名 (增加了 'abstract' 摘要列)
    std_columns = ["date", "category", "source", "title", "tags", "abstract", "link", "read_status"]
    
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=std_columns)
        df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
        return df
    
    try:
        df = pd.read_csv(DATA_FILE)
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(DATA_FILE, encoding="gbk")
        except:
            df = pd.read_csv(DATA_FILE, encoding="gbk", errors="ignore")
    
    # *** 自动修补旧数据 ***
    # 如果旧文件里没有 'abstract' 列，自动补上，防止报错
    if 'abstract' not in df.columns:
        df['abstract'] = ""
    
    return df

def save_data(df):
    try:
        df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
    except Exception as e:
        st.error(f"保存失败: {e}")

# ================= UI 样式 (保持卡片美观) =================
st.markdown("""
<style>
    /* 顶部统计卡片样式 */
    .card-container {
        padding: 20px;
        border-radius: 6px;
        color: white;
        margin-bottom: 20px;
        height: 120px;
        display: flex;
        flex-direction: column;
        justify_content: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .bg-blue { background-color: #5B7CA6; }
    .bg-orange { background-color: #D68640; }
    .card-title { font-size: 20px; font-weight: bold; }
    .card-sub { font-size: 13px; opacity: 0.85; margin-top: 5px; }
    
    /* 调整 Expander 的样式，使其更紧凑 */
    .streamlit-expanderHeader {
        font-size: 16px;
        font-weight: 500;
        color: #333;
    }
    
    /* 标签的小徽章样式 */
    .tag-badge {
        background-color: #e8f0fe;
        color: #1a73e8;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        margin-right: 5px;
        border: 1px solid #d2e3fc;
    }
</style>
""", unsafe_allow_html=True)

# ================= 主程序 =================

def main():
    df = load_data()

    # --- 侧边栏：录入 ---
    with st.sidebar:
        st.title("⚙️ 管理")
        mode = st.radio("模式", ["浏览库", "录入新文", "数据表编辑"])
        
        if mode == "录入新文":
            st.info("新增文献记录")
            with st.form("add_form", clear_on_submit=True):
                i_date = st.date_input("日期", datetime.now())
                i_source = st.selectbox("来源", ["JFE", "RFS", "管理世界", "经济研究", "研报", "其他"])
                i_cat = st.selectbox("归类", ["精选文章", "文章系列", "期刊目录", "研究领域"])
                i_title = st.text_input("标题", placeholder="输入标题...")
                
                # *** 新增：摘要输入框 ***
                i_abstract = st.text_area("摘要/备注", placeholder="这里输入核心观点、笔记或摘要...", height=100)
                
                i_tags = st.text_input("标签", placeholder="例如: 动量, 波动率")
                i_link = st.text_input("链接")
                
                if st.form_submit_button("💾 提交"):
                    new_row = {
                        "date": i_date.strftime("%Y-%m-%d"),
                        "category": i_cat,
                        "source": i_source,
                        "title": i_title,
                        "abstract": i_abstract, # 保存摘要
                        "tags": i_tags.replace("，", ","),
                        "link": i_link,
                        "read_status": "未读"
                    }
                    df = pd.concat([pd.DataFrame([new_row]), df], ignore_index=True)
                    save_data(df)
                    st.success("已保存！")
                    st.rerun()

    # --- 主界面 ---
    if mode == "数据表编辑":
        st.subheader("🛠️ 全局数据编辑")
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, height=600)
        if not df.equals(edited_df):
            if st.button("💾 保存表格修改"):
                save_data(edited_df)
                st.success("更新成功")
                st.rerun()

    elif mode == "浏览库":
        # 1. 顶部卡片 (统计)
        c1, c2, c3, c4 = st.columns(4)
        def card(col, color, title, sub):
            col.markdown(f"""
            <div class="card-container {color}">
                <div class="card-title">{title}</div>
                <div class="card-sub">{sub}</div>
            </div>""", unsafe_allow_html=True)

        card(c1, "bg-blue", "文章系列", f"Total: {len(df)}")
        card(c2, "bg-blue", "研究领域", "Quant / Strategy")
        card(c3, "bg-blue", "期刊目录", f"Sources: {df['source'].nunique()}")
        card(c4, "bg-orange", "精选文章", f"Hot: {len(df[df['category']=='精选文章'])}")

        # 2. 列表展示 (Expander模式)
        st.markdown("### 📨 文献列表")
        
        # 搜索与筛选
        col_search, col_filter = st.columns([3, 1])
        search_txt = col_search.text_input("🔍 搜索标题或标签")
        filter_src = col_filter.multiselect("来源筛选", df['source'].unique() if not df.empty else [])
        
        view_df = df.copy()
        if search_txt:
            view_df = view_df[view_df['title'].str.contains(search_txt, case=False, na=False) | 
                              view_df['tags'].str.contains(search_txt, case=False, na=False)]
        if filter_src:
            view_df = view_df[view_df['source'].isin(filter_src)]

        if view_df.empty:
            st.info("没有找到相关文献。")
        else:
            # 遍历显示
            for idx, row in view_df.iterrows():
                # --- 标题栏逻辑 (日期 + 标题) ---
                try:
                    d_str = row['date'].replace("-", "") # 20251209
                except: d_str = "00000000"
                
                # 这一行决定了不点开时看什么：【20251209】 标题
                expander_label = f"【{d_str}】 {row['title']}"
                
                # --- 展开后的内容 (二级菜单) ---
                with st.expander(expander_label):
                    # 1. 标签行 (处理成小气泡)
                    if pd.notna(row['tags']) and row['tags']:
                        tags_html = "".join([f'<span class="tag-badge">{t.strip()}</span>' for t in row['tags'].split(",") if t.strip()])
                        st.markdown(f"**🏷️ 标签：** {tags_html}", unsafe_allow_html=True)
                    
                    # 2. 来源与分类
                    st.caption(f"📌 来源: {row['source']} | 分类: {row['category']}")
                    
                    # 3. 摘要 (重点显示区域)
                    if pd.notna(row.get('abstract')) and row['abstract']:
                        st.markdown(f"**📝 摘要/笔记：**")
                        st.info(row['abstract']) # 用蓝色框框展示摘要，很醒目
                    else:
                        st.caption("（暂无摘要）")
                    
                    # 4. 链接按钮
                    if pd.notna(row['link']) and row['link']:
                        st.link_button("🔗 阅读原文 / 打开文件", row['link'])

if __name__ == "__main__":
    main()