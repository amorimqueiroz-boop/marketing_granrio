import streamlit as st
import sqlite3
import base64
import pandas as pd
from openai import OpenAI
from urllib.parse import quote
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap

# --- 1. CONFIGURAÇÃO GERAL ---
st.set_page_config(page_title="Gestor Granrio", page_icon="🏗️", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stButton>button {width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; background-color: #004aad; color: white;}
    .stTextInput>div>div>input {border-radius: 10px;}
    </style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect("loja_granrio_v4.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS vip (nome TEXT, celular TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS historico (data TEXT, tipo TEXT, conteudo TEXT)')
    conn.commit()
    return conn

conn = init_db()

# --- 3. SERVIÇOS DE IA ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except:
    api_key = "SUA_CHAVE_AQUI"

client = OpenAI(api_key=api_key)

# --- 4. FUNÇÕES DE DESIGN (O "MOTOR" DO CARROSSEL) ---
def criar_imagem_com_texto(texto, subtitulo, cor_fundo, imagem_produto=None, slide_tipo="padrao"):
    # Cria uma base quadrada (Instagram)
    img = Image.new('RGB', (1080, 1080), color=cor_fundo)
    draw = ImageDraw.Draw(img)
    
    # Tenta carregar fonte padrão, senão usa default
    try:
        font_titulo = ImageFont.truetype("arial.ttf", 90)
        font_sub = ImageFont.truetype("arial.ttf", 50)
    except:
        font_titulo = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Se tiver imagem do produto e for Slide 1 ou 3, cola ela no centro
    if imagem_produto and slide_tipo in ["capa", "produto"]:
        # Redimensiona mantendo proporção
        img_prod = imagem_produto.copy()
        img_prod.thumbnail((800, 600)) 
        # Centraliza
        pos_x = (1080 - img_prod.width) // 2
        pos_y = (1080 - img_prod.height) // 2
        img.paste(img_prod, (pos_x, pos_y))
    
    # Desenha Faixa de Texto (Bloco Branco Translucido para leitura)
    if slide_tipo == "capa":
        draw.rectangle([(50, 800), (1030, 1030)], fill="#004aad") # Faixa Azul Granrio
        cor_texto = "white"
        y_text = 820
    else:
        # Slides de texto puro ou misto
        y_text = 100
        cor_texto = "white"

    # Quebra de linha para o texto caber
    linhas = textwrap.wrap(texto, width=20) # Ajuste conforme o tamanho da fonte
    
    for linha in linhas:
        # Centraliza o texto horizontalmente
        # bbox retorna (left, top, right, bottom)
        bbox = draw.textbbox((0, 0), linha, font=font_titulo)
        w_linha = bbox[2] - bbox[0]
        x_text = (1080 - w_linha) // 2
        
        # Desenha texto com borda preta para contraste (outline)
        draw.text((x_text, y_text), linha, font=font_titulo, fill=cor_texto, stroke_width=2, stroke_fill="black")
        y_text += 100

    # Subtitulo (Preço ou Detalhe)
    if subtitulo:
        bbox_sub = draw.textbbox((0, 0), subtitulo, font=font_sub)
        w_sub = bbox_sub[2] - bbox_sub[0]
        x_sub = (1080 - w_sub) // 2
        draw.text((x_sub, y_text + 20), subtitulo, font=font_sub, fill="yellow", stroke_width=1, stroke_fill="black")

    # Marca D'água Granrio (Rodapé)
    draw.text((800, 1020), "@granrio.indiapora", font=font_sub, fill="white")
    
    return img

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

# --- 5. PROMPT DO CARROSSEL ---
PERSONA_CARROSSEL = """
Você é um designer e copywriter.
Analise a imagem do produto e crie textos curtos para 4 slides de Instagram.
Responda APENAS no formato:
SLIDE1: [Título curto e impactante]
SLIDE2: [Uma pergunta de dor/problema que o produto resolve]
SLIDE3: [Principais benefícios resumidos]
SLIDE4: [Chamada para ação com urgência]
"""

# --- 6. INTERFACE ---
st.title("🏗️ Gestor Granrio")
tab_post, tab_carrossel, tab_vip, tab_agenda = st.tabs(["📸 Post Rápido", "🎞️ Carrossel (Novo)", "👥 VIP", "📅 Agenda"])

# --- ABA 1 (Mantida Simples) ---
with tab_post:
    st.write("Post Simples (Código anterior...)") 

# --- ABA 2: CARROSSEL AUTOMÁTICO (NOVIDADE) ---
with tab_carrossel:
    st.header("Gerador de Carrossel (4 Slides)")
    st.info("Cria uma sequência completa para o Instagram automaticamente.")
    
    foto_c = st.camera_input("Foto para o Carrossel", key="cam_carrossel")
    preco_c = st.text_input("Preço:", placeholder="R$ 0,00", key="preco_c")
    
    if foto_c and st.button("🎨 Criar Carrossel"):
        # 1. Analisar com GPT-4o para pegar os textos
        with st.spinner('A IA está escrevendo o roteiro dos slides...'):
            img_bytes = foto_c.getvalue()
            img_pil = Image.open(io.BytesIO(img_bytes))
            img_b64 = base64.b64encode(img_bytes).decode('utf-8')
            
            res = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": PERSONA_CARROSSEL},
                    {"role": "user", "content": [
                        {"type": "text", "text": f"Produto custa {preco_c}. Crie os textos."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]}
                ]
            )
            roteiro = res.choices[0].message.content
            
            # 2. Processar o texto da IA (Parse simples)
            linhas_ia = roteiro.split('\n')
            textos = {"SLIDE1": "", "SLIDE2": "", "SLIDE3": "", "SLIDE4": ""}
            for l in linhas_ia:
                if "SLIDE1:" in l: textos["SLIDE1"] = l.replace("SLIDE1:", "").strip()
                if "SLIDE2:" in l: textos["SLIDE2"] = l.replace("SLIDE2:", "").strip()
                if "SLIDE3:" in l: textos["SLIDE3"] = l.replace("SLIDE3:", "").strip()
                if "SLIDE4:" in l: textos["SLIDE4"] = l.replace("SLIDE4:", "").strip()

        # 3. Gerar as Imagens com Python (Pillow)
        with st.spinner('Gerando as imagens...'):
            # Slide 1: Capa (Azul Escuro)
            img1 = criar_imagem_com_texto(textos["SLIDE1"], "Confira a Oferta!", "#0f172a", img_pil, "capa")
            # Slide 2: Problema (Laranja Atenção)
            img2 = criar_imagem_com_texto(textos["SLIDE2"], "Você passa por isso?", "#ea580c", None, "texto")
            # Slide 3: Solução (Azul Claro)
            img3 = criar_imagem_com_texto(textos["SLIDE3"], f"Só: {preco_c}", "#0284c7", img_pil, "produto")
            # Slide 4: CTA (Verde Zap)
            img4 = criar_imagem_com_texto("Peça Agora no WhatsApp!", textos["SLIDE4"], "#16a34a", None, "texto")
            
            # Salvar em sessão para exibir
            st.session_state['carrossel_imgs'] = [img1, img2, img3, img4]
            st.success("Carrossel Pronto!")

    # Exibição
    if 'carrossel_imgs' in st.session_state:
        cols = st.columns(2)
        for i, img in enumerate(st.session_state['carrossel_imgs']):
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            with cols[i % 2]:
                st.image(img, caption=f"Slide {i+1}", use_column_width=True)
                st.download_button(label=f"⬇️ Baixar Slide {i+1}", data=buf.getvalue(), file_name=f"slide_{i+1}.png", mime="image/png")

# --- RESTO DAS ABAS (MANTIDAS) ---
with tab_agenda: st.write("Agenda Inteligente...")
with tab_vip: st.write("Lista VIP...")
