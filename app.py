import streamlit as st
import sqlite3
import base64
from openai import OpenAI
from urllib.parse import quote
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from rembg import remove
import io

# --- 1. CONFIGURAÇÃO E CORREÇÃO DO ERRO ---
st.set_page_config(page_title="Gestor Granrio", page_icon="🏗️", layout="centered")

# CORREÇÃO AQUI: unsafe_allow_html=True
st.markdown("""
    <style>
    .stApp {background-color: #f8f9fa;}
    .stButton>button {
        width: 100%; border-radius: 8px; height: 3em; 
        font-weight: bold; background-color: #004aad; color: white; border: none;
    }
    div[data-testid="stButton"] > button[kind="secondary"] {
        background-color: #dc2626 !important; color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect("granrio_final.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS vip (nome TEXT, celular TEXT)')
    conn.commit()
    return conn

conn = init_db()

# --- 3. CONFIGURAÇÃO API (OPENAI É MAIS ESTÁVEL PARA TEXTO) ---
try:
    # Tenta pegar dos segredos ou usa uma chave temporária se estiver testando local
    api_key = st.secrets.get("OPENAI_API_KEY", "SUA_CHAVE_AQUI")
except:
    api_key = "SUA_CHAVE_AQUI"
client = OpenAI(api_key=api_key)

# --- 4. MOTOR DE DESIGN GRÁFICO (O "CANVA" AUTOMÁTICO) ---
def criar_card_oferta(foto_upload, preco, nome_prod, usar_recorte, cor_fundo):
    # 1. Prepara a imagem base
    img = Image.open(foto_upload).convert("RGBA")
    
    # 2. Recorte Inteligente (Opcional)
    if usar_recorte:
        with st.spinner("✂️ Recortando fundo..."):
            img = remove(img)
    
    # 3. Cria o Fundo do Card (Quadrado Instagram 1080x1080)
    card = Image.new("RGBA", (1080, 1080), color=cor_fundo)
    
    # 4. Posiciona o Produto
    # Ajusta tamanho para caber no centro
    img.thumbnail((900, 800)) 
    largura_img, altura_img = img.size
    pos_x = (1080 - largura_img) // 2
    pos_y = (1080 - altura_img) // 2
    
    # Se for fundo transparente (recorte), adiciona uma sombra fake simples para dar "peso"
    if usar_recorte:
        sombra = Image.new("RGBA", (largura_img, int(altura_img*0.1)), (0,0,0, 50))
        # card.paste(sombra, (pos_x, pos_y + altura_img - 20), sombra) # Sombra simples
    
    card.paste(img, (pos_x, pos_y), img)
    
    # 5. Elementos Gráficos (Faixas e Textos)
    draw = ImageDraw.Draw(card)
    
    try:
        font_preco = ImageFont.truetype("arial.ttf", 140)
        font_titulo = ImageFont.truetype("arial.ttf", 70)
        font_footer = ImageFont.truetype("arial.ttf", 40)
    except:
        font_preco = ImageFont.load_default()
        font_titulo = ImageFont.load_default()
        font_footer = ImageFont.load_default()
    
    # Faixa Superior (Nome do Produto)
    draw.rectangle([(0, 0), (1080, 180)], fill="#004aad") # Azul Granrio
    w_tit = draw.textlength(nome_prod, font=font_titulo)
    draw.text(((1080-w_tit)/2, 60), nome_prod, font=font_titulo, fill="white")
    
    # Preço (Bola ou Faixa)
    # Vamos fazer uma "Etiqueta" no canto inferior direito
    draw.rounded_rectangle([(650, 850), (1030, 1030)], radius=20, fill="#dc2626", outline="white", width=5)
    
    draw.text((690, 880), "R$", font=font_footer, fill="white")
    draw.text((750, 890), preco, font=font_preco, fill="white")
    draw.text((780, 1000), "à vista", font=font_footer, fill="yellow")

    # Rodapé
    draw.rectangle([(0, 1030), (1080, 1080)], fill="white")
    draw.text((350, 1040), "🏗️ Granrio Indiaporã • (17) 99999-9999", font=font_footer, fill="#004aad")

    return card

# --- 5. INTERFACE DO APP ---
st.title("🏗️ Criador de Encartes Granrio")
st.write("Crie posts profissionais sem montagens falsas.")

tab_criador, tab_vip = st.tabs(["🎨 Criar Arte", "👥 Clientes"])

with tab_criador:
    # Upload ou Câmera
    opcao_foto = st.radio("Foto do Produto:", ["📸 Câmera", "📁 Upload"], horizontal=True)
    if opcao_foto == "📸 Câmera":
        arquivo = st.camera_input("Tirar Foto")
    else:
        arquivo = st.file_uploader("Escolher Imagem", type=["jpg", "png"])
    
    st.write("---")
    
    col1, col2 = st.columns(2)
    with col1:
        nome_prod = st.text_input("Nome do Produto:", value="Cimento CP-II")
        preco_prod = st.text_input("Preço (Só números):", value="32,90")
    
    with col2:
        # Opções de Design Sólido
        cor_nome = st.selectbox("Cor de Fundo do Card:", 
                                ["Branco Limpo", "Azul Granrio Suave", "Cinza Concreto", "Laranja Oferta"])
        recortar = st.checkbox("Recortar Fundo (Remover cenário da loja)?", value=True)

    # Mapa de cores
    cores = {
        "Branco Limpo": "#ffffff",
        "Azul Granrio Suave": "#bfdbfe",
        "Cinza Concreto": "#e5e7eb",
        "Laranja Oferta": "#ffedd5"
    }

    if arquivo and st.button("✨ GERAR ENCARTE INSTAGRAM"):
        img_final = criar_card_oferta(arquivo, preco_prod, nome_prod, recortar, cores[cor_nome])
        
        # Exibe resultado
        st.image(img_final, caption="Pronto para Postar!", use_column_width=True)
        
        # Botão Download
        buf = io.BytesIO()
        img_final.save(buf, format="PNG")
        st.download_button("⬇️ Baixar Imagem HD", data=buf.getvalue(), file_name="encarte_granrio.png", mime="image/png")
        
        # Gera Legenda com IA
        with st.spinner("✍️ Criando legenda..."):
            prompt = f"Crie uma legenda de venda para Instagram. Produto: {nome_prod}. Preço: {preco_prod}. Loja: Granrio Material de Construção (Indiaporã). Use emojis de obra."
            res = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
            st.text_area("Copie a legenda:", value=res.choices[0].message.content)

with tab_vip:
    st.write("Gestão de Clientes (Código anterior mantido aqui...)")
    # (Pode colar o código do banco de dados das respostas anteriores aqui se quiser manter)

