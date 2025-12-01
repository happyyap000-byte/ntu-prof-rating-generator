# 文件名稱：app.py (包含單一查詢和比較功能)
import streamlit as st
import crawlptt       # 爬蟲程式
import analy          # PTT 評論分析程式
import excel_tool     # Excel 成績查詢程式
import time 
import requests 
import pandas as pd
import numpy as np

# 網站標題與設定
st.set_page_config(layout="centered")
st.title("🎓 台大教授評價與成績彙整生成器")

st.markdown("##### 請輸入教授姓名，系統將為您彙整評價與成績數據。")

# 設置兩個輸入框 (主查詢和比較對象)
col_main, col_compare = st.columns(2)
with col_main:
    professor_input = st.text_input("輸入第一個教授名字 (主查詢):", key="prof1")
with col_compare:
    professor_compare_input = st.text_input("輸入第二個教授名字 (比較對象，可選):", key="prof2")


def get_professor_review(professor_name):
    """
    執行爬蟲、分析、和 Excel 查詢，回傳顯示用的 dict 和原始數據 tuple。
    """
    if not professor_name:
        return None, None
    
    ptt_result_tuple = None
    
    # --- 1. 執行 PTT 爬蟲與分析 ---
    try:
        crawlptt.crawl(professor_name) 
        ptt_result_tuple = analy.analy(professor_name)
        
        if ptt_result_tuple is False:
            ptt_data = {"total_count": 0, "sweet_rating": "無資料", "push_ratio_display": "N/A", "summary": "PTT NTUcourse 版查無相關評論數據。"}
        else:
            total_count = ptt_result_tuple[1]
            push_ratio = float(ptt_result_tuple[3])
            sweet_ratio = float(ptt_result_tuple[5])
            
            if sweet_ratio > 0.6:
                sweet_rating = "⭐️⭐️⭐️⭐️⭐️ (極甜)"
            elif sweet_ratio > 0.3:
                sweet_rating = "⭐️⭐️⭐️⭐️ (偏甜)"
            else:
                sweet_rating = "⭐️⭐️ (偏硬)"
                
            summary_text = f"【PTT 評論彙整】：根據 {total_count} 則評論，教授獲得約 {push_ratio*100:.0f}% 的正面評價（推）。在甜度方面，提及「甜」的比例約為 {sweet_ratio*100:.0f}%。"
            
            ptt_data = {
                "total_count": total_count,
                "sweet_rating": sweet_rating,
                "push_ratio_display": f"{push_ratio*100:.2f}%",
                "summary": summary_text
            }

    except Exception as e:
        ptt_data = {"total_count": 0, "sweet_rating": "錯誤", "push_ratio_display": "N/A", "summary": f"PTT 爬蟲或分析失敗。錯誤：{e}"}
        
    # --- 2. 執行 Excel 成績查詢 ---
    excel_data_string = excel_tool.search_grade(professor_name)

    # 3. 彙整結果
    display_dict = {
        "name": professor_name,
        "sweetness": ptt_data['sweet_rating'],
        "push_ratio_display": ptt_data['push_ratio_display'],
        "total_count": ptt_data['total_count'],
        "ptt_summary": ptt_data['summary'],
        "excel_data": excel_data_string, # Excel 查詢的結果字串
    }
    
    return display_dict, ptt_result_tuple


def display_single_review(review_data):
    """顯示單一教授的詳細結果"""
    st.success("✅ 評價與成績生成完畢！")
    
    st.subheader(f"👨‍🏫 {review_data['name']} 教授綜合分析")
    
    # PTT 數據區域
    st.markdown("##### PTT 評論數據分析")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="甜度 (推估分數大方程度)", value=review_data['sweetness']) 
    with col2:
        st.metric(label="正面評價比率 (推/讚)", value=review_data['push_ratio_display']) 
    with col3:
        st.metric(label="總評論數", value=review_data['total_count']) 

    st.info(f"**📝 彙整懶人包:** {review_data['ptt_summary']}")
    
    st.markdown("---")
    
    # Excel 數據區域
    st.markdown("##### 課程 A+ 比例數據 (Excel 查詢)")
    st.code(review_data['excel_data'], language='text')

    st.markdown("---")
    st.caption("🌐 資訊來源：PTT NTUcourse 板爬蟲 & 自行上傳之 Excel 成績單")


def display_comparison(prof1_raw, prof2_raw):
    """顯示兩位教授的比較表格"""
    st.subheader("📊 教授評價數據比較")
    
    labels = [
        "名稱:", "總評價數:", "推   次數:", "推   比率:",
        "甜   次數:", "甜   比率:", "不推 次數:", "不推 比率:",
        "不甜 次數:", "不甜 比率:"
    ]
    
    # 將 tuple 轉換為列表
    prof1_list = list(prof1_raw)
    prof2_list = list(prof2_raw)
    
    # 將比率欄位轉換為百分比顯示
    for i in [3, 5, 7, 9]:
        if isinstance(prof1_list[i], (float, np.float64)):
            prof1_list[i] = f"{prof1_list[i]*100:.2f}%"
        if isinstance(prof2_list[i], (float, np.float64)):
            prof2_list[i] = f"{prof2_list[i]*100:.2f}%"
    
    data = {
        "指標": labels,
        prof1_list[0]: prof1_list,
        prof2_list[0]: prof2_list,
    }
    
    # 建立 DataFrame，並將第一欄作為索引
    df = pd.DataFrame(data).set_index("指標")
    
    st.dataframe(df, use_container_width=True)
    st.caption("數值：次數；比率：在總評論數中的佔比。")
    st.markdown("---")


# --- 網站介面主要執行區 ---

if st.button("🔍 開始查詢或比較"):
    
    prof1_name = professor_input.strip()
    prof2_name = professor_compare_input.strip()

    if not prof1_name:
        st.warning("請至少輸入第一個教授名字才能查詢喔！")
    else:
        # --- 處理單一查詢 ---
        if not prof2_name:
            with st.spinner(f"正在搜尋並分析 {prof1_name} 的評價與成績..."):
                prof1_data, prof1_raw = get_professor_review(prof1_name)
            
            if prof1_data:
                display_single_review(prof1_data)
            else:
                st.error("❌ 查無相關資訊，請確認輸入是否正確，或爬蟲程式執行失敗。")

        # --- 處理比較查詢 ---
        else:
            with st.spinner(f"正在搜尋並分析 {prof1_name} 與 {prof2_name} 的評價數據..."):
                # 取得第一個教授數據
                prof1_data, prof1_raw = get_professor_review(prof1_name)
                
                # 取得第二個教授數據
                prof2_data, prof2_raw = get_professor_review(prof2_name)
            
            st.success("✅ 數據獲取完畢！正在生成比較表。")

            # 檢查數據是否完整
            if prof1_raw is False:
                st.error(f"❌ 無法取得第一個教授 ({prof1_name}) 的 PTT 評論數據進行比較。")
            
            if prof2_raw is False:
                st.error(f"❌ 無法取得第二個教授 ({prof2_name}) 的 PTT 評論數據進行比較。")
            
            # 如果兩邊都有數據，才顯示比較表
            if prof1_raw and prof2_raw:
                display_comparison(prof1_raw, prof2_raw)
            
            # 即使比較失敗，依然顯示第一個教授的詳細資訊
            if prof1_data:
                st.markdown("---")
                st.subheader(f"✨ {prof1_name} 教授詳細數據 (主查詢)")
                display_single_review(prof1_data)