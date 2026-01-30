import streamlit as st
import requests
import sqlite3
import pandas as pd
from openai import OpenAI
from datetime import datetime
from PIL import Image
import io
from urllib.parse import quote

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Gestor Granrio Pro", page_icon="🏗️", layout="centered")

# Correção do erro visual (usando unsafe_allow_html)
st.markdown("""
    <style>
    .stApp {background-color: #f8f9fa;}
    .stButton>button {
        width: 100%; border-radius: 12px; height: 3.5em; 
        font-weight: bold; background-color: #004aad; color: white; border: none;
    }
    .stTextInput>div>div>input {border-radius: 10px;}
    img {border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}
    </style>
""", unsafe_allow_html=True)

# --- 2. CARREGAMENTO DAS CHAVES ---
try:
    PHOTOROOM_API_KEY = st.secrets["PHOTOROOM_API_KEY"]
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
except Exception as e:
    st.error("⚠️ Erro: Chaves não encontradas no secrets.toml")
    st.stop()

client = OpenAI(api_key=OPENAI_KEY)

# --- 3. BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect("granrio_final_v2.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS vip (nome TEXT, celular TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS historico (data TEXT, tipo TEXT, conteudo TEXT)')
    conn.commit()
    return conn

conn = init_db()

# --- 4. MOTOR VISUAL: PHOTOROOM (CORRIGIDO) ---
def gerar_estudio_photoroom(image_bytes, prompt_cenario):
    url = "https://image-api.photoroom.com/v2/edit"
    
    # --- A CORREÇÃO ESTÁ AQUI EMBAIXO ---
    # Mudamos de "image_file" para "imageFile" (Obrigatório pela API)
    files = {
        "imageFile": ("produto.jpg", image_bytes, "image/jpeg")
    }
    
    data = {
        "background.prompt": prompt_cenario,
        "shadow.mode": "ai.soft",  # Sombra realista
        "light.mode": "ai.auto",   # Luz automática
        "padding": "0.1",
        "outputFormat": "png"
    }
    
    headers = {"x-api-key": PHOTOROOM_API_KEY}
    
    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content))
        else:
            st.error(f"Erro Photoroom: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

# --- 5. INTERFACE ---
st.title("🏗️ Gestor Granrio Pro")
st.caption("Status: Conectado (Photoroom Live)")

# Memória
if 'img_final' not in st.session_state: st.session_state['img_final'] = None
if 'legenda' not in st.session_state: st.session_state['legenda'] = ""

tab_studio, tab_agenda, tab_vip, tab_hist = st.tabs(["📸 Studio Pro", "📅 Agenda", "👥 VIP", "📊 Controle"])

# --- ABA 1: STUDIO ---
with tab_studio:
    st.subheader("Estúdio Fotográfico IA")
    
    foto_input = st.camera_input("Tire a foto do produto")
    
    cenarios = {
        "Banheiro de Luxo": "product on a white marble counter in a luxury bright bathroom, bokeh background, high resolution",
        "Obra Limpa": "product placed on a polished concrete floor in a modern construction site, sunlight, soft shadows",
        "Madeira Rústica": "product on a rustic wooden table, warm lighting, blurred background",
        "Cozinha Moderna": "product on a granite kitchen island, modern appliances in background blurred",
        "Fundo Infinito Azul": "product on a professional dark blue studio background, spotlight"
    }
    
    col1, col2 = st.columns(2)
    with col1:
        cenario_escolhido = st.selectbox("Cenário:", list(cenarios.keys()))
    with col2:
        preco = st.text_input("Preço (R$):", value="99,90")

    if foto_input and st.button("✨ Gerar Foto de Estúdio"):
        
        with st.spinner("Enviando para a Photoroom..."):
            img_bytes = foto_input.getvalue()
            # Chama a função corrigida
            imagem_gerada = gerar_estudio_photoroom(img_bytes, cenarios[cenario_escolhido])
            
            if imagem_gerada:
                st.session_state['img_final'] = imagem_gerada
                
                # Gera Legenda
                with st.spinner("Escrevendo legenda..."):
                    prompt_mkt = f"Crie um post vendedor para Instagram. Produto custa R$ {preco}. Cenário: {cenario_escolhido}. Use emojis e hashtags #Indiaporã #Granrio."
                    try:
                        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt_mkt}])
                        st.session_state['legenda'] = res.choices[0].message.content
                    except:
                        st.session_state['legenda'] = f"Oferta Granrio! Só R$ {preco}."
                    
                    # Salva
                    data_hoje = datetime.now().strftime("%d/%m %H:%M")
                    conn.execute("INSERT INTO historico VALUES (?, ?, ?)", (data_hoje, "Studio Pro", st.session_state['legenda']))
                    conn.commit()

    # Resultado
    if st.session_state['img_final']:
        st.write("---")
        st.image(st.session_state['img_final'], caption="Resultado Profissional", use_column_width=True)
        
        buf = io.BytesIO()
        st.session_state['img_final'].save(buf, format="PNG")
        st.download_button("⬇️ Baixar Imagem", data=buf.getvalue(), file_name="granrio_pro.png", mime="image/png")
        
        txt_editavel = st.text_area("Legenda:", value=st.session_state['legenda'], height=150)
        
        zap = st.text_input("Enviar para (DDD+Número):", key="zap_final")
        if st.button("📲 Enviar no WhatsApp"):
            if zap:
                link = f"https://wa.me/55{zap}?text={quote(txt_editavel)}"
                st.markdown(f"[>> ABRIR WHATSAPP <<]({link})")

# --- ABA 2: AGENDA ---
with tab_agenda:
    st.header("📅 Dica do Dia")
    if st.button("💡 Gerar Ideia"):
        try:
            res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": "Dê uma dica rápida de obra para postar hoje."}])
            st.info(res.choices[0].message.content)
        except:
            st.error("Verifique a chave OpenAI")

# --- ABA 3: VIP ---
with tab_vip:
    st.header("👥 Clientes")
    with st.form("vip"):
        n = st.text_input("Nome"); c = st.text_input("Celular")
        if st.form_submit_button("Salvar"):
            conn.execute("INSERT INTO vip VALUES (?, ?)", (n, c)); conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT * FROM vip", conn), use_container_width=True)

# --- ABA 4: CONTROLE ---
with tab_hist:
    st.header("📊 Histórico")
    if st.button("Atualizar"): st.rerun()
    st.dataframe(pd.read_sql_query("SELECT * FROM historico ORDER BY data DESC", conn), use_container_width=True)
