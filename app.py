import streamlit as st
import sqlite3
import base64
import pandas as pd
from openai import OpenAI
from urllib.parse import quote
from datetime import datetime
import requests
from io import BytesIO

# --- 1. CONFIGURAÇÃO GERAL ---
st.set_page_config(page_title="Gestor Granrio IA", page_icon="🏗️", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stButton>button {width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; background-color: #004aad; color: white;}
    .stTextInput>div>div>input {border-radius: 10px;}
    /* Estilo para o botão de fechar câmera ser vermelho */
    div[data-testid="stButton"] > button[kind="secondary"] {background-color: #e11d48 !important; color: white !important;}
    </style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect("loja_granrio_v3.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS vip (nome TEXT, celular TEXT)')
    # Atualizei a tabela histórico para salvar se a imagem foi gerada por IA
    c.execute('CREATE TABLE IF NOT EXISTS historico (data TEXT, tipo TEXT, conteudo TEXT, imagem_ia BOOLEAN)')
    conn.commit()
    return conn

conn = init_db()

# --- 3. SERVIÇOS DE IA (GPT-4o + DALL-E 3) ---
try:
    # Certifique-se de que sua chave tenha acesso ao GPT-4o E ao DALL-E 3
    api_key = st.secrets["OPENAI_API_KEY"]
except:
    api_key = "SUA_CHAVE_AQUI_TESTE_LOCAL"

client = OpenAI(api_key=api_key)

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

# --- FUNÇÃO MÁGICA: TRANSFORMAR FOTO ---
def transformar_imagem_premium(img_b64):
    # Passo 1: GPT-4o Vê e Descreve o objeto
    desc_res = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Você é um assistente visual. Descreva apenas o objeto principal da imagem com detalhes técnicos (material, cor, tipo)."},
            {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}]}
        ]
    )
    descricao_objeto = desc_res.choices[0].message.content
    
    # Passo 2: DALL-E 3 Gera a nova imagem "Premium"
    # Prompt para o "Artista"
    prompt_dalle = f"A professional, high-end product photograph of {descricao_objeto}. The product is placed in a beautiful, finished construction context (e.g., a luxury renovated bathroom, a modern construction site at golden hour, a polished concrete floor). Studio lighting, high resolution, cinematic look."

    dalle_res = client.images.generate(
        model="dall-e-3",
        prompt=prompt_dalle,
        size="1024x1024",
        quality="standard", # Use "hd" para mais qualidade (custa mais)
        n=1,
    )
    # Retorna a URL da imagem gerada e a descrição para usar no texto depois
    return dalle_res.data[0].url, descricao_objeto

# --- 4. DADOS E PROMPTS ---
PERSONA = "Você é o gerente de marketing da Granrio em Indiaporã. Tom amigável, simples e direto. Use emojis."
CALENDARIO_VAREJO = {"19/03": "Dia do Carpinteiro", "01/05": "Dia do Trabalho", "30/06": "Dia do Caminhoneiro", "15/10": "Dia do Professor", "13/12": "Dia do Pedreiro"}

# --- 5. INTERFACE PRINCIPAL ---
st.title("🏗️ Gestor Granrio IA")

# Inicializa estado da câmera
if 'camera_ativa' not in st.session_state: st.session_state['camera_ativa'] = False
if 'imagem_premium_url' not in st.session_state: st.session_state['imagem_premium_url'] = None

tab_post, tab_agenda, tab_vip, tab_hist = st.tabs(["📸 Estúdio IA", "📅 Agenda", "👥 VIP", "📊 Controle"])

# --- ABA 1: ESTÚDIO IA (O NOVO CORAÇÃO DO APP) ---
with tab_post:
    st.header("Transformar Foto em Post Premium")
    
    # --- CONTROLE DA CÂMERA (SEU PEDIDO 1) ---
    if not st.session_state['camera_ativa']:
        if st.button("📸 Abrir Câmera"):
            st.session_state['camera_ativa'] = True
            st.rerun()
    else:
        foto_raw = st.camera_input("Tire a foto do produto 'crua'")
        if st.button("❌ Fechar Câmera", type="secondary"):
             st.session_state['camera_ativa'] = False
             st.rerun()

        # --- PROCESSAMENTO MÁGICO (SEU PEDIDO 2) ---
        if foto_raw:
            preco = st.text_input("Preço R$ (Opcional):", placeholder="Ex: 99,90")
            
            if st.button("✨ Transformar em Foto Premium & Gerar Texto"):
                img_b64 = encode_image(foto_raw)
                st.session_state['camera_ativa'] = False # Fecha câmera após tirar

                # 1. Gerar Imagem Premium (DALL-E 3)
                with st.spinner('O Artista IA está criando a imagem premium... (aguarde ~15s)'):
                    try:
                        nova_img_url, desc_obj = transformar_imagem_premium(img_b64)
                        st.session_state['imagem_premium_url'] = nova_img_url
                        st.session_state['desc_objeto_atual'] = desc_obj
                        st.success("Imagem Premium Criada!")
                    except Exception as e:
                        st.error(f"Erro ao gerar imagem: {e}")
                        st.stop()

                # 2. Gerar Texto de Venda (GPT-4o)
                with st.spinner('Escrevendo a legenda de vendas...'):
                    prompt_texto = f"Crie um post de venda para Instagram/WhatsApp sobre: {st.session_state['desc_objeto_atual']}. Preço: {preco}. A foto é premium e luxuosa. Use hashtags locais de Indiaporã."
                    res_txt = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "system", "content": PERSONA}, {"role": "user", "content": prompt_texto}]
                    )
                    st.session_state['legenda_premium'] = res_txt.choices[0].message.content
                    
                    # Salvar no histórico
                    conn.execute("INSERT INTO historico VALUES (?, ?, ?, ?)", 
                                 (datetime.now().strftime("%d/%m %H:%M"), "Post Premium IA", st.session_state['legenda_premium'], True))
                    conn.commit()
                st.rerun()

    # --- EXIBIÇÃO DO RESULTADO FINAL ---
    if st.session_state['imagem_premium_url']:
        st.write("---")
        st.subheader("Resultado Final:")
        # Mostra a imagem gerada pelo DALL-E
        st.image(st.session_state['imagem_premium_url'], caption="Imagem Gerada por IA", use_column_width=True)
        st.info("Toque e segure na imagem acima para salvar no celular.")
        
        txt_final = st.text_area("Legenda:", value=st.session_state['legenda_premium'], height=200)
        
        col_a, col_b = st.columns(2)
        with col_a:
             if st.button("Nova Foto"):
                 st.session_state['imagem_premium_url'] = None
                 st.session_state['legenda_premium'] = None
                 st.rerun()
        with col_b:
            num_zap = st.text_input("Enviar Zap:", placeholder="DDD+Num", label_visibility="collapsed")
            if num_zap:
                 st.markdown(f"[>>> ENVIAR ZAP <<<](https://wa.me/55{num_zap}?text={quote(txt_final)})")

# --- ABA 2: AGENDA (MANANTIDA DA VERSÃO ANTERIOR) ---
with tab_agenda:
    # (Código da agenda inteligente igual ao anterior, omitido para brevidade mas deve estar aqui)
    st.write("Agenda Inteligente ativa...")

# --- ABA 3: LISTA VIP ---
with tab_vip:
     with st.form("vip"):
        n = st.text_input("Nome"); c = st.text_input("Celular")
        if st.form_submit_button("Salvar"):
            conn.execute("INSERT INTO vip VALUES (?, ?)", (n, c)); conn.commit(); st.rerun()
     st.dataframe(pd.read_sql_query("SELECT * FROM vip", conn), use_container_width=True)

# --- ABA 4: CONTROLE ---
with tab_hist:
    if st.button("Atualizar"): st.rerun()
    st.dataframe(pd.read_sql_query("SELECT * FROM historico ORDER BY data DESC", conn), use_container_width=True)
