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
st.set_page_config(page_title="TOEIC Game Master", page_icon="🎮", layout="wide")

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
    
    .battle-card { background-color: #ffffff; padding: 30px; border-radius: 15px; border: 2px solid #3498db; border-left: 15px solid #2980b9; box-shadow: 0 5px 15px rgba(0,0,0,0.1); text-align: center; margin-bottom: 20px; color: #2c3e50; }
    .battle-word { font-size: 56px; font-weight: 900; color: #2c3e50; margin: 15px 0; }
    .battle-label { font-size: 18px; color: #7f8c8d; font-weight: bold; text-transform: uppercase; }

    .word-title { font-size: 64px; font-weight: 900; color: #2c3e50; margin-bottom: 5px; }
    .phonetic-text { font-family: 'Lucida Sans Unicode', sans-serif; font-size: 24px; color: #95a5a6; margin-bottom: 20px; font-style: italic; }
    .meaning-text { font-size: 40px; color: #c0392b; font-weight: bold; margin: 20px 0; }
    .example-box { background-color: #ecf0f1; padding: 20px; border-radius: 12px; margin-top: 20px; text-align: left; width: 100%; border-left: 5px solid #3498db; }
    .sent-en { font-size: 20px; color: #2c3e50; margin-bottom: 10px; font-weight: 500; line-height: 1.4; }
    .sent-cn { font-size: 18px; color: #16a085; font-weight: bold; }
    .tag-badge { background-color: #e1f5fe; color: #0288d1; padding: 5px 15px; border-radius: 15px; font-size: 14px; font-weight: bold; margin-bottom: 15px; display: inline-block; }
    
    .rpg-container { background-color: #2c3e50; padding: 20px; border-radius: 15px; color: white; text-align: center; margin-bottom: 20px; border: 3px solid #f1c40f; }
    .monster-img { font-size: 100px; margin-bottom: 10px; animation: bounce 2s infinite; }
    .health-bar-container { width: 100%; background-color: #555; border-radius: 10px; margin: 10px 0; height: 25px; }
    .health-bar-fill { height: 100%; border-radius: 10px; transition: width 0.5s ease-in-out; }
    
    @keyframes bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
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
            
            expected_cols = ['word', 'meaning', 'phonetic', 'sentence', 'sentence_cn', 'type', 'week']
            for col in expected_cols:
                if col not in df_vocab.columns:
                    df_vocab[col] = ''
            
            for col in df_vocab.columns:
                df_vocab[col] = df_vocab[col].astype(str).replace('nan', '')
                
            df_vocab.drop_duplicates(subset=['word'], inplace=True)
            
        except Exception as e:
            st.error(f"讀取資料庫失敗: {e}")
            return pd.DataFrame()
    else:
        st.warning("⚠️ 找不到 toeic_db.xlsx")
        return pd.DataFrame()

    if os.path.exists(PROGRESS_FILE):
        df_prog = pd.read_csv(PROGRESS_FILE)
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

# --- 關鍵修正：全域變數安全初始化 ---
# 確保所有變數在程式一開始都存在，防止 AttributeError
default_values = {
    'xp': 0,
    'fc_index': 0,
    'fc_flip': False,
    'monster_hp': 100,
    'player_hp': 100,
    'game_status': "playing",
    'quiz_q': None,    # 測驗題目
    'quiz_opts': [],   # 測驗選項
    'spell_q': None,   # 拼字題目
    'rpg_q': None,     # RPG 題目
    'rpg_opts': []     # RPG 選項
}

for key, val in default_values.items():
    if key not in st.session_state:
        st.session_state[key] = val

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
        st.progress(min(mastered / total if total > 0 else 0, 1.0))
        st.write(f"已精通: {mastered} / {total}")
        st.markdown(f"**XP:** {st.session_state.xp}")
        st.markdown("---")
        
        cats = ["全部 (All)"] + sorted([x for x in df['type'].unique() if x])
        selected_cat = st.selectbox("📂 選擇分類", cats)
        
        try:
            valid_weeks = []
            for w in df['week'].unique():
                try: valid_weeks.append(int(float(w)))
                except: pass
            weeks = ["全部 (All)"] + sorted(list(set(valid_weeks)))
        except:
            weeks = ["全部 (All)"]
            
        selected_week = st.selectbox("📅 選擇週次", weeks)

# --- 5. 篩選邏輯 ---
if df.empty: st.stop()

df['week'] = pd.to_numeric(df['week'], errors='coerce')
learning_pool = df.copy()

if selected_cat != "全部 (All)":
    learning_pool = learning_pool[learning_pool['type'] == selected_cat]

if selected_week != "全部 (All)":
    learning_pool = learning_pool[learning_pool['week'] == selected_week]

if learning_pool.empty:
    st.warning("⚠️ 此分類與週次的組合下沒有單字，請嘗試調整篩選條件。")
    learning_pool = df.head(1)

# --- 6. 主畫面 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔥 閃卡特訓", "⚔️ 挑戰擂台", "🎧 聽音拼字", "👹 勇者鬥惡龍", "📊 單字總表"])

# === TAB 1: 閃卡 ===
with tab1:
    if st.session_state.fc_index >= len(learning_pool):
        st.session_state.fc_index = 0
        
    idx = st.session_state.fc_index
    row = learning_pool.iloc[idx]
    
    st.caption(f"📚 範圍單字數: {len(learning_pool)} | 進度: {idx + 1}")

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
        cn_sentence = row.get('sentence_cn', '') or "(尚無中文翻譯)"
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
            s = row.get('sentence', '')
            if not s: s = row['word']
            autoplay_audio(s)
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
                next_card()
                st.rerun()
        with b2:
            if st.button("✅ 記得", type="primary", use_container_width=True):
                current_lvl = df.loc[df['word'] == row['word'], 'level'].values[0]
                df = update_learning_status(df, row['word'], new_level=min(4, current_lvl + 1))
                st.session_state.xp += 10
                next_card()
                st.rerun()

# === TAB 2: 測驗 (擂台) ===
with tab2:
    if len(learning_pool) < 4:
        st.warning("單字量不足 (至少需要4個)。")
    else:
        if st.session_state.quiz_q is None:
            q_row = learning_pool.sample(1).iloc[0]
            st.session_state.quiz_q = q_row
            correct = q_row['meaning']
            others = df[df['meaning'] != correct].sample(3)['meaning'].tolist()
            opts = others + [correct]
            random.shuffle(opts)
            st.session_state.quiz_opts = opts

        q = st.session_state.quiz_q
        
        st.markdown(f"""
        <div class="battle-card">
            <div class="battle-label">Question</div>
            <div class="battle-word">{q['word']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        col_audio_q, col_space_q = st.columns([1, 4])
        with col_audio_q:
            if st.button("🔊 聽發音", key="quiz_audio_btn"):
                autoplay_audio(q['word'])
        
        cols = st.columns(2)
        for i, opt in enumerate(st.session_state.quiz_opts):
            def check_ans(o=opt):
                if o == q['meaning']:
                    st.toast("✅ 正確！", icon="🎉")
                    st.session_state.xp += 20
                    autoplay_audio("That is correct! Great job!")
                    df_upd = update_learning_status(df, q['word'], new_level=min(4, df.loc[df['word'] == q['word'], 'level'].values[0] + 1))
                else:
                    st.toast("❌ 錯誤", icon="⚠️")
                    autoplay_audio("Sorry, that is incorrect.")
                    df_upd = update_learning_status(df, q['word'], new_level=1)
                st.session_state.quiz_q = None
                
            if cols[i % 2].button(opt, key=f"q_{i}", use_container_width=True):
                check_ans()
                st.rerun()

# === TAB 3: 聽音拼字 ===
with tab3:
    st.header("🎧 聽音拼字挑戰")
    
    if st.session_state.spell_q is None:
        st.session_state.spell_q = learning_pool.sample(1).iloc[0]

    sq = st.session_state.spell_q
    
    col_s1, col_s2 = st.columns([1, 2])
    
    with col_s1:
        if st.button("🔊 播放發音", use_container_width=True, type="primary"):
            autoplay_audio(sq['word'])
    
    with col_s2:
        st.info(f"提示: {sq['meaning']} ({len(sq['word'])} 個字母)")
    
    user_spell = st.text_input("請輸入單字:", key="spell_input_box")
    
    if st.button("送出檢查"):
        if user_spell.strip().lower() == sq['word'].strip().lower():
            st.success("✅ 拼對了！")
            autoplay_audio("That is correct!")
            st.session_state.xp += 30
            update_learning_status(df, sq['word'], new_level=4)
            time.sleep(1)
            st.session_state.spell_q = None
            st.rerun()
        else:
            st.error(f"❌ 錯誤！正確是: {sq['word']}")
            autoplay_audio("Sorry, incorrect.")
            update_learning_status(df, sq['word'], new_level=1)
            if st.button("再試一題"):
                st.session_state.spell_q = None
                st.rerun()

# === TAB 4: 勇者鬥惡龍 (RPG) ===
with tab4:
    st.header("👹 勇者鬥惡龍")
    
    if st.button("🔄 重置遊戲"):
        st.session_state.monster_hp = 100
        st.session_state.player_hp = 100
        st.session_state.game_status = "playing"
        st.session_state.rpg_q = None
        st.rerun()

    m_hp = st.session_state.monster_hp
    p_hp = st.session_state.player_hp
    
    st.markdown(f"""
    <div class="rpg-container">
        <div class="monster-img">{'👿' if m_hp > 0 else '💀'}</div>
        <h3>多益大魔王 (TOEIC Boss)</h3>
        <div class="health-bar-container">
            <div class="health-bar-fill" style="width: {m_hp}%; background-color: #e74c3c;"></div>
        </div>
        <p>HP: {m_hp}/100</p>
    </div>
    
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
        <div style="width:45%; text-align:center; padding:10px; background: #34495e; border-radius:10px; color:white;">
            <h4>🛡️ 勇者 (You)</h4>
            <div class="health-bar-container">
                <div class="health-bar-fill" style="width: {p_hp}%; background-color: #2ecc71;"></div>
            </div>
            <p>HP: {p_hp}/100</p>
        </div>
        <div style="font-size:30px;">VS</div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.game_status == "win":
        st.balloons()
        st.success("🏆 恭喜！你打倒了魔王！")
        if st.button("再來一局"):
            st.session_state.monster_hp = 100
            st.session_state.player_hp = 100
            st.session_state.game_status = "playing"
            st.rerun()
    elif st.session_state.game_status == "lose":
        st.error("💀 你被打敗了...")
        if st.button("復活"):
            st.session_state.player_hp = 100
            st.session_state.game_status = "playing"
            st.rerun()
    else:
        # 使用安全的屬性檢查，避免 AttributeError
        if st.session_state.rpg_q is None:
            st.session_state.rpg_q = learning_pool.sample(1).iloc[0]
            correct_r = st.session_state.rpg_q['meaning']
            dists_r = df[df['meaning'] != correct_r].sample(3)['meaning'].tolist()
            opts_r = dists_r + [correct_r]
            random.shuffle(opts_r)
            st.session_state.rpg_opts = opts_r

        rq = st.session_state.rpg_q
        
        st.markdown(f"""
        <div class="battle-card" style="border-color: #e74c3c;">
            <div class="battle-label" style="color:#e74c3c;">⚔️ 攻擊指令 (Attack Command)</div>
            <div class="battle-word">{rq['word']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        col_audio, col_space = st.columns([1, 4])
        with col_audio:
            if st.button("🔊 聽發音", key="rpg_audio_btn"):
                autoplay_audio(rq['word'])

        r_cols = st.columns(2)
        for i, opt in enumerate(st.session_state.rpg_opts):
            def rpg_attack(selected=opt):
                if selected == rq['meaning']:
                    dmg = random.randint(15, 25)
                    st.session_state.monster_hp = max(0, st.session_state.monster_hp - dmg)
                    autoplay_audio("That is correct! Attack!") 
                    st.toast(f"⚔️ 攻擊成功！造成 {dmg} 點傷害！", icon="💥")
                    update_learning_status(df, rq['word'], new_level=4)
                else:
                    dmg = random.randint(10, 20)
                    st.session_state.player_hp = max(0, st.session_state.player_hp - dmg)
                    autoplay_audio("Wrong! You take damage.")
                    st.toast(f"🛡️ 答錯了！受到 {dmg} 點傷害！", icon="🩸")
                    update_learning_status(df, rq['word'], new_level=1)
                
                if st.session_state.monster_hp == 0:
                    st.session_state.game_status = "win"
                elif st.session_state.player_hp == 0:
                    st.session_state.game_status = "lose"
                
                st.session_state.rpg_q = None
                
            if r_cols[i % 2].button(opt, key=f"rpg_{i}", use_container_width=True):
                rpg_attack()
                st.rerun()

# === TAB 5: 總表 ===
with tab5:
    st.markdown("### 📊 完整單字庫")
    search_term = st.text_input("🔍 搜尋單字", "")
    
    if search_term:
        display_df = df[df['word'].str.contains(search_term, case=False, na=False)]
    else:
        if selected_cat != "全部 (All)":
            display_df = df[df['type'] == selected_cat]
        else:
            display_df = df

    col_t1, col_t2 = st.columns([1, 1])
    with col_t1: st.write(f"**總筆數:** {len(display_df)}")
    with col_t2: show_all = st.checkbox("顯示全部")

    view_cols = ['week', 'type', 'word', 'phonetic', 'meaning', 'level', 'last_review_date']

    if show_all:
        st.dataframe(display_df[view_cols])
    else:
        PAGE_SIZE = 50
        total_pages = max(1, (len(display_df) // PAGE_SIZE) + 1)
        col_p1, col_p2 = st.columns([1, 3])
        with col_p1: page_num = st.number_input("頁碼", 1, total_pages, 1)
        start_idx = (page_num - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        st.dataframe(display_df[view_cols].iloc[start_idx:end_idx])
