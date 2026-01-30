import streamlit as st
import sqlite3
import base64
import pandas as pd
from openai import OpenAI
from urllib.parse import quote
from datetime import datetime

# --- 1. CONFIGURAÇÃO DO APP ---
st.set_page_config(page_title="Gestor Granrio", page_icon="🏗️", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stButton>button {width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; background-color: #004aad; color: white;}
    .stTextInput>div>div>input {border-radius: 10px;}
    </style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS (AMPLIADO) ---
def init_db():
    conn = sqlite3.connect("loja_granrio.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS vip (nome TEXT, celular TEXT)')
    # Nova tabela para controle de promoções
    c.execute('''CREATE TABLE IF NOT EXISTS historico 
                 (data TEXT, produto TEXT, preco TEXT, legenda TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- 3. SERVIÇOS DE IA ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except:
    api_key = "SUA_CHAVE_AQUI"

client = OpenAI(api_key=api_key)

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

# --- 4. INTERFACE ---
st.title("🏗️ Gestor Granrio")
tab_post, tab_hist, tab_vip, tab_agenda = st.tabs(["📸 Criar Post", "📊 Controle", "👥 Lista VIP", "📅 Datas"])

# --- ABA 1: GERADOR ---
with tab_post:
    foto = st.camera_input("Foto do Produto")
    preco = st.text_input("Preço R$", placeholder="Ex: 29.90")
    
    if foto and st.button("✨ Gerar e Salvar Promoção"):
        with st.spinner('GPT-4o analisando...'):
            img_b64 = encode_image(foto)
            res = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Marketing para a Granrio em Indiaporã. Seja amigável e direto."},
                    {"role": "user", "content": [{"type": "text", "text": f"Gere um post para este produto por R$ {preco}"},
                                                 {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}]}
                ]
            )
            legenda = res.choices[0].message.content
            st.session_state['legenda'] = legenda
            
            # Salva no histórico automaticamente
            data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
            conn.execute("INSERT INTO historico VALUES (?, ?, ?, ?)", (data_hoje, "Produto Identificado", preco, legenda))
            conn.commit()

    if 'legenda' in st.session_state:
        txt = st.text_area("Legenda:", value=st.session_state['legenda'], height=200)
        num = st.text_input("Zap do Cliente:")
        if st.button("📲 Compartilhar"):
            st.markdown(f"[Abrir WhatsApp](https://wa.me/55{num}?text={quote(txt)})")

# --- ABA 2: CONTROLE DE POSTS (NOVA) ---
with tab_hist:
    st.subheader("📊 Histórico de Promoções")
    dados = pd.read_sql_query("SELECT data, produto, preco FROM historico ORDER BY data DESC", conn)
    if not dados.empty:
        st.dataframe(dados, use_container_width=True)
        if st.button("🗑️ Limpar Histórico"):
            conn.execute("DELETE FROM historico")
            conn.commit()
            st.rerun()
    else:
        st.info("Nenhuma promoção registrada ainda.")

# --- ABA 3: LISTA VIP ---
with tab_vip:
    with st.form("cad"):
        nome = st.text_input("Nome")
        cel = st.text_input("Celular")
        if st.form_submit_button("Salvar"):
            conn.execute("INSERT INTO vip VALUES (?, ?)", (nome, cel))
            conn.commit()
            st.success("Salvo!")
    
    st.write("---")
    clientes = pd.read_sql_query("SELECT * FROM vip", conn)
    st.table(clientes)

# --- ABA 4: DATAS ---
with tab_agenda:
    datas = {"30/06": "Dia do Caminhoneiro", "13/12": "Dia do Pedreiro", "15/10": "Dia do Professor"}
    hoje = datetime.now().strftime("%d/%m")
    st.write(f"Hoje: {hoje}")
    if hoje in datas: st.success(f"🎉 {datas[hoje]}!")
    for d, n in datas.items(): st.write(f"📅 {d} - {n}")
