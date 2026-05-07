from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import gradio as gr
import pandas as pd
import plotly.express as px
from collections import Counter
import re
from deep_translator import GoogleTranslator

app = FastAPI(title="Quotes Management API", version="1.0")
DB_FILE = "quotes.db"

# ==========================================
# 1. FastAPI 백엔드 영역 (CRUD API)
# ==========================================
class QuoteCreate(BaseModel):
    text: str
    author: str
    tags: str

class QuoteUpdate(BaseModel):
    text: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[str] = None

class QuoteResponse(BaseModel):
    id: int
    text: str
    author: str
    tags: str

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@app.post("/quotes/", response_model=dict, status_code=201)
def create_quote(quote: QuoteCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO quotes (text, author, tags) VALUES (?, ?, ?)", 
                   (quote.text, quote.author, quote.tags))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/quotes/", response_model=List[QuoteResponse])
def read_quotes(skip: int = 0, limit: int = 20, author: Optional[str] = None, tag: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM quotes WHERE 1=1"
    params = []
    if author: query += " AND author = ?"; params.append(author)
    if tag: query += " AND tags LIKE ?"; params.append(f"%{tag}%")
    query += " LIMIT ? OFFSET ?"; params.extend([limit, skip])
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.patch("/quotes/{quote_id}")
def update_quote(quote_id: int, quote: QuoteUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    updates = []; params = []
    if quote.text is not None: updates.append("text = ?"); params.append(quote.text)
    if quote.author is not None: updates.append("author = ?"); params.append(quote.author)
    if quote.tags is not None: updates.append("tags = ?"); params.append(quote.tags)
    
    if not updates:
        conn.close()
        raise HTTPException(status_code=400, detail="수정할 내용이 없습니다.")
        
    params.append(quote_id)
    cursor.execute(f"UPDATE quotes SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.delete("/quotes/{quote_id}")
def delete_quote(quote_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}


# ==========================================
# 2. 데이터 분석 및 Gradio 헬퍼 함수
# ==========================================
def get_all_data():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM quotes", conn)
    conn.close()
    return df

def get_unique_list(column_name):
    df = get_all_data()
    if df.empty: return []
    if column_name == 'author':
        return sorted(df['author'].unique().tolist())
    elif column_name == 'tags':
        all_tags = []
        for tags_str in df['tags'].dropna():
            all_tags.extend([t.strip() for t in tags_str.split(',')])
        return sorted(list(set(all_tags)))

def get_word_frequencies(text_series, top_n=10):
    all_text = " ".join(text_series).lower()
    words = re.findall(r'\b[a-z]{3,}\b', all_text)
    stopwords = {'the', 'and', 'that', 'for', 'you', 'with', 'not', 'this', 'but', 'are', 'have', 'what', 'can', 'all', 'your'}
    filtered = [w for w in words if w not in stopwords]
    return Counter(filtered).most_common(top_n)

# --- Gradio용 CRUD 브릿지 함수 ---
def gr_load_for_update(q_id):
    if not q_id: return None, None, None, "⚠️ 검색할 ID를 입력해주세요."
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM quotes WHERE id = ?", (int(q_id),))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None, None, None, f"❌ ID [{q_id}]에 해당하는 데이터를 찾을 수 없습니다."
    
    res = dict(row)
    return res['text'], res['author'], res['tags'], f"✅ ID [{q_id}] 데이터를 불러왔습니다. 내용을 수정한 후 '수정하기'를 누르세요."

def gr_create(text, author, tags):
    if not text or not author: return "⚠️ 격언 내용과 작가를 모두 입력해주세요.", get_all_data()
    try:
        create_quote(QuoteCreate(text=text, author=author, tags=tags))
        return "✅ 성공적으로 새 격언이 추가되었습니다.", get_all_data()
    except Exception as e:
        return f"❌ 오류 발생: {str(e)}", get_all_data()

def gr_update(q_id, text, author, tags):
    if not q_id: return "⚠️ 수정할 데이터의 ID를 입력해주세요.", get_all_data()
    try:
        update_quote(int(q_id), QuoteUpdate(
            text=text if text else None,
            author=author if author else None,
            tags=tags if tags else None
        ))
        return f"✅ ID [{q_id}] 데이터가 성공적으로 수정되었습니다.", get_all_data()
    except Exception as e:
        return f"❌ 오류 발생: {str(e)}", get_all_data()

def gr_delete(q_id):
    if not q_id: return "⚠️ 삭제할 데이터의 ID를 입력해주세요.", get_all_data()
    try:
        delete_quote(int(q_id))
        return f"✅ ID [{q_id}] 데이터가 성공적으로 삭제되었습니다.", get_all_data()
    except Exception as e:
        return f"❌ 오류 발생: {str(e)}", get_all_data()


# ==========================================
# 3. Gradio 프론트엔드 영역
# ==========================================
translator = GoogleTranslator(source='en', target='ko')

css = """
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 25px; padding: 20px 0; }
.quote-card { background: white; border: 1px solid #eaeaea; border-radius: 12px; padding: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.03); transition: transform 0.2s, box-shadow 0.2s; position: relative; }
.quote-card:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.08); }
.quote-icon { font-size: 2.5em; color: #f0f0f0; position: absolute; top: 10px; left: 15px; font-family: serif; line-height: 1; }
.quote-text { font-size: 1.1em; color: #333; line-height: 1.6; font-weight: 500; margin-bottom: 20px; margin-top: 10px; position: relative; z-index: 1; }
.quote-author { color: #2c3e50; font-weight: 800; font-size: 0.95em; text-align: right; margin-bottom: 15px; }
.quote-tags { display: flex; flex-wrap: wrap; gap: 8px; border-top: 1px dashed #eee; padding-top: 15px; }
.tag-badge { padding: 4px 10px; border-radius: 20px; font-size: 0.8em; font-weight: 600; color: #555; display: flex; align-items: center; gap: 4px; border: 1px solid rgba(0,0,0,0.05); }
"""

def get_tag_style(tag_name):
    tag_name = tag_name.lower().strip()
    color_map = {
        'love': '#ffe4e1', 'life': '#e8f5e9', 'inspirational': '#fff9c4',
        'humor': '#f3e5f5', 'friends': '#ffe0b2', 'friendship': '#ffe0b2',
        'heartbreak': '#eceff1', 'books': '#e3f2fd', 'reading': '#e3f2fd', 'truth': '#e0f7fa'
    }
    fallback_colors = ['#fce4ec', '#f1f8e9', '#e8eaf6', '#fff3e0', '#f9fbe7']
    return color_map.get(tag_name, fallback_colors[len(tag_name) % len(fallback_colors)])

def render_gallery(search_author, search_tag, language):
    quotes = read_quotes(skip=0, limit=100, author=search_author if search_author else None, tag=search_tag if search_tag else None)
    if not quotes:
        return "<div style='text-align:center; padding:50px; color:#888; font-size: 1.2em;'>🔍 검색 결과가 없습니다.</div>"
        
    html_content = "<div class='card-grid'>"
    for q in quotes:
        display_text = q['text']
        if language == "한국어 (Korean)":
            display_text = translator.translate(display_text)
            
        tags_html = ""
        for t in q['tags'].split(','):
            if not t.strip(): continue
            t_clean = t.strip()
            bg_color = get_tag_style(t_clean)
            tags_html += f"<span class='tag-badge' style='background-color: {bg_color};'>🏷️ {t_clean}</span>"
        
        card = f"""
        <div class='quote-card'>
            <div class='quote-icon'>❝</div>
            <div class='quote-text'>{display_text}</div>
            <div class='quote-author'>— {q['author']} <span style='font-size:0.7em; color:#bbb; float:left;'>ID: {q['id']}</span></div>
            <div class='quote-tags'>{tags_html}</div>
        </div>
        """
        html_content += card
    html_content += "</div>"
    return html_content

def analyze_author(author_name):
    df = get_all_data()
    if df.empty or not author_name: return None, None
    author_df = df[df['author'] == author_name]
    
    tags_list = [t.strip() for tags in author_df['tags'] for t in tags.split(',')]
    tag_counts = pd.DataFrame(Counter(tags_list).most_common(10), columns=['Tag', 'Count'])
    fig_tags = px.pie(tag_counts, values='Count', names='Tag', title=f"{author_name}의 주력 태그", hole=0.4)
    
    word_freq = get_word_frequencies(author_df['text'])
    word_df = pd.DataFrame(word_freq, columns=['Word', 'Frequency'])
    fig_words = px.bar(word_df, x='Word', y='Frequency', title=f"{author_name}가 자주 쓰는 영단어", text_auto=True)
    return fig_tags, fig_words

def analyze_tag(tag_name):
    df = get_all_data()
    if df.empty or not tag_name: return None, None
    tag_df = df[df['tags'].str.contains(tag_name, na=False, case=False)]
    
    author_counts = tag_df['author'].value_counts().reset_index().head(10)
    author_counts.columns = ['Author', 'Count']
    fig_authors = px.pie(author_counts, values='Count', names='Author', title=f"#{tag_name} 태그 최다 기여 작가", hole=0.4)
    
    word_freq = get_word_frequencies(tag_df['text'])
    word_df = pd.DataFrame(word_freq, columns=['Word', 'Frequency'])
    fig_words = px.bar(word_df, x='Word', y='Frequency', title=f"#{tag_name} 태그 핵심 영단어", text_auto=True)
    return fig_authors, fig_words


# Gradio UI 구성
with gr.Blocks(css=css, theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🎓 격언 관리 및 데이터 분석 시스템")
    
    with gr.Tabs():
        # --- TAB 1: 검색 라운지 ---
        with gr.Tab("📖 탐색 라운지"):
            with gr.Row():
                search_a = gr.Textbox(label="👤 작가 검색 (예: Albert Einstein)", placeholder="작가를 입력하세요")
                search_t = gr.Textbox(label="🏷️ 태그 검색 (예: love, life)", placeholder="태그를 입력하세요")
            with gr.Row():
                lang_toggle = gr.Radio(choices=["English (Default)", "한국어 (Korean)"], value="English (Default)", label="🌐 언어 선택", interactive=True)
                search_btn = gr.Button("🔍 검색 적용", variant="primary")
                
            gallery_html = gr.HTML(value=render_gallery("", "", "English (Default)"))
            
            search_btn.click(fn=render_gallery, inputs=[search_a, search_t, lang_toggle], outputs=gallery_html)
            lang_toggle.change(fn=render_gallery, inputs=[search_a, search_t, lang_toggle], outputs=gallery_html)

        # --- TAB 2: 데이터 관리 (CRUD) ---
        with gr.Tab("📝 데이터 관리 (CRUD)"):
            gr.Markdown("데이터베이스의 격언을 조회하고 수정/삭제할 수 있습니다.")
            
            with gr.Row():
                # 좌측: 데이터 조회 표 (Read)
                with gr.Column(scale=2):
                    gr.Markdown("### 📋 전체 데이터 조회 (Read)")
                    db_table = gr.Dataframe(value=get_all_data(), interactive=False)
                    refresh_btn = gr.Button("🔄 표 새로고침")
                    refresh_btn.click(fn=get_all_data, outputs=db_table)
                
                # 우측: 생성/수정/삭제 컨트롤
                with gr.Column(scale=1):
                    result_msg = gr.Textbox(label="상태 메시지", interactive=False)
                    
                    with gr.Accordion("➕ 새 격언 추가 (Create)", open=False):
                        c_text = gr.Textbox(label="격언 내용", placeholder="새로운 명언을 입력하세요")
                        c_author = gr.Textbox(label="작가 이름", placeholder="작가를 입력하세요")
                        c_tags = gr.Textbox(label="태그", placeholder="쉼표(,)로 구분 (예: life, truth)")
                        btn_create = gr.Button("추가하기", variant="primary")
                        btn_create.click(fn=gr_create, inputs=[c_text, c_author, c_tags], outputs=[result_msg, db_table])
                        
                    with gr.Accordion("✏️ 기존 격언 수정 (Update)", open=True):
                        gr.Markdown("**1단계:** 수정할 ID를 입력하고 '데이터 불러오기'를 누르세요.")
                        u_id = gr.Number(label="수정할 대상 ID", precision=0)
                        btn_load = gr.Button("🔍 데이터 불러오기", variant="secondary")
                        
                        gr.Markdown("**2단계:** 아래 필드에서 내용을 수정한 후 '수정하기'를 누르세요.")
                        u_text = gr.Textbox(label="격언 내용")
                        u_author = gr.Textbox(label="작가 이름")
                        u_tags = gr.Textbox(label="태그")
                        btn_update = gr.Button("수정하기", variant="primary")
                        
                        # 이벤트 연결: 불러오기 -> 텍스트박스에 값 채우기
                        btn_load.click(fn=gr_load_for_update, inputs=u_id, outputs=[u_text, u_author, u_tags, result_msg])
                        # 이벤트 연결: 수정하기 -> DB 반영 및 표 새로고침
                        btn_update.click(fn=gr_update, inputs=[u_id, u_text, u_author, u_tags], outputs=[result_msg, db_table])
                        
                    with gr.Accordion("🗑️ 데이터 삭제 (Delete)", open=False):
                        d_id = gr.Number(label="삭제할 대상 ID", precision=0)
                        btn_delete = gr.Button("삭제하기", variant="stop")
                        btn_delete.click(fn=gr_delete, inputs=[d_id], outputs=[result_msg, db_table])

        # --- TAB 3: 데이터 인사이트 ---
        with gr.Tab("📊 데이터 인사이트 (분석)"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 👤 작가 심층 분석")
                    author_dropdown = gr.Dropdown(choices=get_unique_list('author'), label="분석할 작가 선택")
                    author_plot_1 = gr.Plot()
                    author_plot_2 = gr.Plot()
                    author_dropdown.change(fn=analyze_author, inputs=author_dropdown, outputs=[author_plot_1, author_plot_2])
                
                with gr.Column():
                    gr.Markdown("### 🏷️ 태그 심층 분석")
                    tag_dropdown = gr.Dropdown(choices=get_unique_list('tags'), label="분석할 태그 선택")
                    tag_plot_1 = gr.Plot()
                    tag_plot_2 = gr.Plot()
                    tag_dropdown.change(fn=analyze_tag, inputs=tag_dropdown, outputs=[tag_plot_1, tag_plot_2])

        # --- TAB 4: API 테스트 (교수님 채점용) ---
        with gr.Tab("⚙️ API 명세서 (개발자용)"):
            gr.Markdown("""
            ### 📌 Swagger UI를 통한 REST API 테스트
            본 프로젝트는 FastAPI 기반의 완전한 백엔드 API를 제공합니다. 
            아래 링크를 클릭하여 API 명세서를 확인하고 Endpoint별 테스트를 진행할 수 있습니다.
            
            👉 **[Swagger UI 접속하기 (/docs)](/docs)**
            """)

# FastAPI 애플리케이션에 Gradio 마운트
app = gr.mount_gradio_app(app, demo, path="/")