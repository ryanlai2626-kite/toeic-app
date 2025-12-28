import streamlit as st
import pandas as pd
import os
from gtts import gTTS
import base64
from io import BytesIO
import random
import time
import datetime

# --- 1. 頁面設定 ---
st.set_page_config(page_title="TOEIC 3000 Coach", page_icon="👑", layout="wide")

# --- 2. CSS 美化 ---
st.markdown("""
    <style>
    .stApp { background-color: #f4f6f9; }
    [data-testid="stSidebar"] { background-color: #2c3e50; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #f1c40f !important; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, [data-testid="stSidebar"] div { color: #ecf0f1 !important; font-size: 16px; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: transparent; padding-bottom: 10px; }
    .stTabs [data-baseweb="tab"] { height: 55px; background-color: #e0e0e0; border-radius: 8px; border: 1px solid #ccc; color: #333333 !important; font-weight: 700; font-size: 18px; padding: 0 25px; }
    .stTabs [aria-selected="true"] { background-color: #f1c40f !important; color: #ffffff !important; border: none; transform: translateY(-2px); box-shadow: 0 4px 10px rgba(241, 196, 15, 0.4); }

    .flashcard-container { background: white; border-radius: 20px; padding: 40px 30px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.08); margin-bottom: 25px; border-left: 12px solid #f1c40f; min-height: 350px; display: flex; flex-direction: column; justify-content: center; align-items: center; }
    .flashcard-back { background: #fdfefe; border-left: 12px solid #2ecc71; }
    
    .word-title { font-size: 64px; font-weight: 900; color: #2c3e50; margin-bottom: 5px; }
    .phonetic-text { font-family: 'Lucida Sans Unicode', sans-serif; font-size: 24px; color: #95a5a6; margin-bottom: 20px; font-style: italic; }
    .meaning-text { font-size: 40px; color: #c0392b; font-weight: bold; margin: 20px 0; }
    .example-box { background-color: #ecf0f1; padding: 20px; border-radius: 12px; margin-top: 20px; text-align: left; width: 100%; border-left: 5px solid #3498db; }
    .sent-en { font-size: 20px; color: #2c3e50; margin-bottom: 10px; font-weight: 500; line-height: 1.4; }
    .sent-cn { font-size: 18px; color: #16a085; font-weight: bold; }
    .tag-badge { background-color: #e1f5fe; color: #0288d1; padding: 5px 15px; border-radius: 15px; font-size: 14px; font-weight: bold; margin-bottom: 15px; display: inline-block; }
    audio { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心功能 ---

def autoplay_audio(text):
    try:
        clean_text = str(text).strip()
        if not clean_text or clean_text == 'nan': return
        tts = gTTS(text=clean_text, lang='en')
        audio_bytes = BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_base64 = base64.b64encode(audio_bytes.getvalue()).decode()
        rnd_id = int(time.time() * 1000)
        audio_html = f'<audio src="data:audio/mp3;base64,{audio_base64}" autoplay id="audio_{rnd_id}"></audio>'
        st.empty().markdown(audio_html, unsafe_allow_html=True)
    except: pass

DATA_FILE = "toeic_db.xlsx"
PROGRESS_FILE = "user_progress.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            df_vocab = pd.read_excel(DATA_FILE)
            df_vocab.columns = [c.strip().lower() for c in df_vocab.columns]
            
            # 確保欄位存在
            expected_cols = ['word', 'meaning', 'phonetic', 'sentence', 'sentence_cn', 'type', 'week']
            for col in expected_cols:
                if col not in df_vocab.columns:
                    df_vocab[col] = ''
            
            # 轉字串並處理 NaN
            for col in df_vocab.columns:
                df_vocab[col] = df_vocab[col].astype(str).replace('nan', '')
                
            # 去除單字本身的重複
            df_vocab.drop_duplicates(subset=['word'], inplace=True)
            
        except Exception as e:
            st.error(f"讀取資料庫失敗: {e}")
            return pd.DataFrame()
    else:
        st.warning("⚠️ 找不到 toeic_db.xlsx")
        return pd.DataFrame()

    if os.path.exists(PROGRESS_FILE):
        df_prog = pd.read_csv(PROGRESS_FILE)
        
        # 關鍵修復：去除進度表中的重複項
        df_prog.drop_duplicates(subset=['word'], keep='last', inplace=True)
        
        if 'last_review_date' not in df_prog.columns:
            df_prog['last_review_date'] = ''
            
        df_vocab = pd.merge(df_vocab, df_prog, on='word', how='left')
        df_vocab['level'] = df_vocab['level'].fillna(1).astype(int)
        df_vocab['last_review_date'] = df_vocab['last_review_date'].fillna('')
    else:
        df_vocab['level'] = 1
        df_vocab['last_review_date'] = ''
        
    return df_vocab

def save_progress(df):
    if 'last_review_date' not in df.columns: df['last_review_date'] = ''
    prog_data = df[['word', 'level', 'last_review_date']].drop_duplicates(subset=['word'], keep='last')
    prog_data.to_csv(PROGRESS_FILE, index=False)

def update_learning_status(df, word, new_level=None):
    idx_list = df[df['word'] == word].index
    if len(idx_list) > 0:
        idx = idx_list[0]
        if new_level is not None:
            df.loc[idx, 'level'] = new_level
        df.loc[idx, 'last_review_date'] = str(datetime.date.today())
        save_progress(df)
    return df

if 'xp' not in st.session_state: st.session_state.xp = 0
if 'fc_index' not in st.session_state: st.session_state.fc_index = 0
if 'fc_flip' not in st.session_state: st.session_state.fc_flip = False

# 載入資料
df = load_data()

# --- 4. 側邊欄 ---
with st.sidebar:
    st.markdown("# 👑 TOEIC Coach")
    st.markdown("---")
    
    if not df.empty:
        total = len(df)
        mastered = len(df[df['level'] >= 4])
        
        today_str = str(datetime.date.today())
        today_count = len(df[df['last_review_date'] == today_str])
        
        st.markdown(f"### 📅 今日戰績: **{today_count}** 字")
        
        st.markdown("### 📊 金色證書進度")
        st.write(f"**已精通:** {mastered} / {total}")
        st.progress(min(mastered / total if total > 0 else 0, 1.0))
        
        st.markdown(f"**XP:** {st.session_state.xp}")
        st.markdown("---")
        
        cats = ["全部 (All)"] + sorted([x for x in df['type'].unique() if x])
        selected_cat = st.selectbox("📂 選擇分類", cats)
            
        try:
            weeks = sorted([int(float(x)) for x in df['week'].unique() if x])
        except:
            weeks = sorted(df['week'].unique())
            
        selected_week = st.selectbox("📅 選擇週次", weeks, format_func=lambda x: f"Week {x}")

# --- 5. 篩選 ---
if df.empty: st.stop()

df['week'] = pd.to_numeric(df['week'], errors='coerce')
filtered_df = df[df['week'] == selected_week]

if selected_cat != "全部 (All)":
    filtered_df = filtered_df[filtered_df['type'] == selected_cat]

review_df = df[(df['week'] < selected_week) & (df['level'] < 3)]
learning_pool = pd.concat([filtered_df, review_df]).drop_duplicates(subset=['word'])

# --- 6. 主畫面 ---
tab1, tab2, tab3 = st.tabs(["🔥 閃卡特訓", "⚔️ 挑戰擂台", "📊 單字總表"])

# === TAB 1: 閃卡 ===
with tab1:
    if learning_pool.empty:
        st.info("本範圍無單字。")
    else:
        if st.session_state.fc_index >= len(learning_pool):
            st.session_state.fc_index = 0
            
        idx = st.session_state.fc_index
        row = learning_pool.iloc[idx]
        st.caption(f"📚 進度: {idx + 1}/{len(learning_pool)}")

        if not st.session_state.fc_flip:
            st.markdown(f"""
            <div class="flashcard-container">
                <div class="tag-badge">{row.get('type', 'General')}</div>
                <div class="word-title">{row['word']}</div>
                <div class="phonetic-text">{row.get('phonetic', '')}</div>
                <div style="color:#bdc3c7; margin-top:20px;">(點擊翻卡查看詳解)</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            cn_sentence = row.get('sentence_cn', '')
            if not cn_sentence: cn_sentence = "(尚無中文翻譯)"

            st.markdown(f"""
            <div class="flashcard-container flashcard-back">
                <div class="word-title" style="font-size: 40px; color:#7f8c8d;">{row['word']}</div>
                <div class="phonetic-text">{row.get('phonetic', '')}</div>
                <hr style="width: 50%; border:1px solid #eee;">
                <div class="meaning-text">{row['meaning']}</div>
                <div class="example-box">
                    <div class="sent-en">🇬🇧 {row.get('sentence', 'No example.')}</div>
                    <div class="sent-cn">🇹🇼 {cn_sentence}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
        with c1:
            if st.button("🔊 唸單字", use_container_width=True):
                autoplay_audio(row['word'])
        with c2:
            if st.button("🗣️ 唸例句", use_container_width=True):
                sent = row.get('sentence', '')
                if not sent: sent = row['word']
                autoplay_audio(sent)
        with c3:
            def toggle_flip(): st.session_state.fc_flip = not st.session_state.fc_flip
            st.button("🔄 翻轉", use_container_width=True, on_click=toggle_flip)
        with c4:
            def next_card():
                st.session_state.fc_flip = False
                st.session_state.fc_index = (st.session_state.fc_index + 1) % len(learning_pool)
            
            if st.session_state.fc_flip:
                 st.button("➡️ 跳過", use_container_width=True, on_click=next_card)
            else:
                 st.button("➡️ 下一張", use_container_width=True, on_click=next_card)

        if st.session_state.fc_flip:
            st.write("")
            b1, b2 = st.columns(2)
            with b1:
                if st.button("❌ 陌生", use_container_width=True):
                    df = update_learning_status(df, row['word'], new_level=1)
                    st.toast("已標記，今日學習 +1", icon="📝")
                    next_card()
                    st.rerun()
            with b2:
                if st.button("✅ 記得", type="primary", use_container_width=True):
                    current_lvl = df.loc[df['word'] == row['word'], 'level'].values[0]
                    df = update_learning_status(df, row['word'], new_level=min(4, current_lvl + 1))
                    st.session_state.xp += 10
                    st.toast("經驗 +10", icon="🎉")
                    next_card()
                    st.rerun()

# === TAB 2: 測驗 ===
with tab2:
    if len(learning_pool) < 4:
        st.warning("單字量不足。")
    else:
        if 'quiz_q' not in st.session_state or st.session_state.quiz_q is None:
            q_row = learning_pool.sample(1).iloc[0]
            st.session_state.quiz_q = q_row
            correct = q_row['meaning']
            distractors = df[df['meaning'] != correct].sample(3)['meaning'].tolist()
            opts = distractors + [correct]
            random.shuffle(opts)
            st.session_state.quiz_opts = opts

        q = st.session_state.quiz_q
        st.markdown(f"""
        <div class="flashcard-container" style="border-left: 12px solid #3498db; min-height: 200px;">
            <div style="font-size:20px; color:#bdc3c7;">Meaning?</div>
            <div class="word-title" style="color:#2980b9;">{q['word']}</div>
            <div class="phonetic-text">{q.get('phonetic', '')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        cols = st.columns(2)
        for i, opt in enumerate(st.session_state.quiz_opts):
            def check_ans(o=opt):
                current_lvl = df.loc[df['word'] == q['word'], 'level'].values[0]
                if o == q['meaning']:
                    st.toast("✅ 正確！", icon="🎉")
                    st.session_state.xp += 20
                    autoplay_audio("Correct")
                    df_upd = update_learning_status(df, q['word'], new_level=min(4, current_lvl + 1))
                else:
                    st.toast("❌ 錯誤", icon="⚠️")
                    autoplay_audio("Wrong")
                    df_upd = update_learning_status(df, q['word'], new_level=1)
                st.session_state.quiz_q = None
                
            if cols[i % 2].button(opt, key=f"q_{i}", use_container_width=True):
                check_ans()
                st.rerun()

# === TAB 3: 總表 ===
with tab3:
    st.markdown("### 📊 完整單字庫 (已啟用分頁模式)")
    
    search_term = st.text_input("🔍 搜尋單字 (Search)", "")
    
    if search_term:
        display_df = df[df['word'].str.contains(search_term, case=False, na=False)]
    else:
        display_df = df

    PAGE_SIZE = 50
    total_pages = (len(display_df) // PAGE_SIZE) + 1
    
    col_p1, col_p2 = st.columns([1, 3])
    with col_p1:
        page_num = st.number_input("頁碼", min_value=1, max_value=total_pages, value=1)
    
    start_idx = (page_num - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    
    view_cols = ['week', 'type', 'word', 'phonetic', 'meaning', 'level', 'last_review_date']
    
    # --- 修正重點：移除 use_container_width=True ---
    st.dataframe(display_df[view_cols].iloc[start_idx:end_idx])
    
    st.caption(f"顯示第 {start_idx+1} 到 {min(end_idx, len(display_df))} 筆，共 {len(display_df)} 筆")