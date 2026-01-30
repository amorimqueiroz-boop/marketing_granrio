import streamlit as st
import sqlite3
import base64
import pandas as pd
from openai import OpenAI
from urllib.parse import quote
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import io

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Studio Granrio", page_icon="🏗️", layout="wide") # Layout wide para caber o editor

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stButton>button {width: 100%; border-radius: 8px; font-weight: bold;}
    /* Ajuste para mobile */
    @media (max-width: 640px) {
        .block-container {padding: 1rem;}
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS & API ---
conn = sqlite3.connect("loja_granrio_v5.db", check_same_thread=False)
conn.execute('CREATE TABLE IF NOT EXISTS vip (nome TEXT, celular TEXT)')
conn.execute('CREATE TABLE IF NOT EXISTS historico (data TEXT, tipo TEXT, conteudo TEXT)')
conn.commit()

try:
    api_key = st.secrets["OPENAI_API_KEY"]
except:
    api_key = "SUA_CHAVE_AQUI" # Configure no .streamlit/secrets.toml para produção
client = OpenAI(api_key=api_key)

# --- 3. MOTOR GRÁFICO (O "CANVA" EM PYTHON) ---
def criar_design(imagem_base, texto_princ, texto_sec, tema, cor_fundo, pos_y_texto, opacidade_fundo):
    # Base: Transforma para RGBA para permitir transparências
    base = imagem_base.convert("RGBA")
    largura, altura = base.size
    
    # Camada de Design (Transparente)
    overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Fontes (Tenta carregar Arial, senão usa default)
    try:
        font_G = ImageFont.truetype("arial.ttf", int(altura * 0.08)) # 8% da altura
        font_M = ImageFont.truetype("arial.ttf", int(altura * 0.05))
        font_P = ImageFont.truetype("arial.ttf", int(altura * 0.03))
    except:
        font_G = ImageFont.load_default()
        font_M = ImageFont.load_default()
        font_P = ImageFont.load_default()

    # --- TEMA 1: OFERTA RELÂMPAGO (Faixa Inferior) ---
    if tema == "Oferta Clássica":
        # Retângulo de Fundo do Texto
        h_box = int(altura * 0.3) # 30% da altura
        y_box = int((altura - h_box) * (pos_y_texto / 100)) # Posição controlada pelo Slider
        
        # Cor Hex para RGBA
        c_r, c_g, c_b = tuple(int(cor_fundo.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        draw.rectangle([(0, y_box), (largura, y_box + h_box)], fill=(c_r, c_g, c_b, int(255 * (opacidade_fundo/100))))
        
        # Textos
        draw.text((largura*0.05, y_box + h_box*0.2), texto_princ, font=font_G, fill="white")
        draw.text((largura*0.05, y_box + h_box*0.6), texto_sec, font=font_M, fill="yellow")

    # --- TEMA 2: DICA DO ESPECIALISTA (Caixa Flutuante) ---
    elif tema == "Dica/Aviso":
        # Caixa centralizada
        margin = int(largura * 0.1)
        c_r, c_g, c_b = tuple(int(cor_fundo.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        # Fundo escuro total leve
        draw.rectangle([(0,0), (largura, altura)], fill=(0,0,0, 100))
        
        # Caixa de texto
        y_centro = int(altura * (pos_y_texto / 100))
        draw.rounded_rectangle([(margin, y_centro - 150), (largura-margin, y_centro + 150)], radius=20, fill=(c_r, c_g, c_b, 240))
        
        draw.text((margin+20, y_centro - 80), "GRANRIO INFORMA:", font=font_P, fill="yellow")
        draw.text((margin+20, y_centro - 20), texto_princ, font=font_M, fill="white")
        draw.text((margin+20, y_centro + 80), texto_sec, font=font_P, fill="white")

    # --- TEMA 3: MINIMALISTA (Só Preço) ---
    elif tema == "Preço Gigante":
        # Círculo
        raio = int(largura * 0.25)
        centro_x = int(largura * 0.8)
        centro_y = int(altura * (pos_y_texto / 100))
        
        draw.ellipse([(centro_x - raio, centro_y - raio), (centro_x + raio, centro_y + raio)], fill="#e11d48", outline="white", width=5)
        
        w_text = draw.textlength(texto_princ, font=font_G)
        draw.text((centro_x - w_text/2, centro_y - 20), texto_princ, font=font_G, fill="white")
        draw.text((centro_x - 40, centro_y + 60), "À VISTA", font=font_P, fill="white")

    # Branding Fixo (Sempre aparece)
    draw.text((20, altura - 40), "🏗️ Granrio Indiaporã", font=font_P, fill="white", stroke_width=2, stroke_fill="black")

    # Compõe a imagem final
    img_final = Image.alpha_composite(base, overlay)
    return img_final.convert("RGB")

# --- 4. INTERFACE ---
st.title("🏗️ Studio Granrio")
st.write("Crie designs profissionais para a loja em segundos.")

col_editor, col_preview = st.columns([1, 1.5]) # Coluna esquerda controles, direita imagem

with col_editor:
    st.subheader("1. Imagem & Conteúdo")
    
    # Opção: Câmera ou Upload
    modo_foto = st.radio("Origem da Imagem:", ["📸 Câmera", "📁 Galeria/Upload"], horizontal=True)
    if modo_foto == "📸 Câmera":
        arquivo_img = st.camera_input("Tirar Foto")
    else:
        arquivo_img = st.file_uploader("Escolher foto", type=['jpg', 'png'])
        
    st.write("---")
    st.subheader("2. Personalização")
    
    # Controles do "Canva"
    tema_selecionado = st.selectbox("Estilo do Design:", ["Oferta Clássica", "Dica/Aviso", "Preço Gigante"])
    
    txt_principal = st.text_input("Texto Principal (Título/Preço):", value="OFERTA R$ 49,90")
    txt_secundario = st.text_input("Texto Secundário (Detalhe):", value="Cimento CP-II 50kg")
    
    with st.expander("🎨 Ajustes Finos (Cores e Posição)"):
        cor_tema = st.color_picker("Cor do Elemento:", "#004aad") # Azul Granrio padrão
        posicao_y = st.slider("Posição Vertical:", 0, 100, 80) # 80% é rodapé
        opacidade = st.slider("Transparência do Fundo:", 50, 100, 90)

with col_preview:
    st.subheader("👁️ Visualização em Tempo Real")
    
    if arquivo_img:
        # Carrega imagem
        img_pil = Image.open(arquivo_img)
        # Redimensiona para agilizar processamento e padronizar
        img_pil.thumbnail((800, 800))
        
        # CHAMA O MOTOR GRÁFICO
        # O segredo: Isso roda toda vez que ela mexe num slider
        imagem_pronta = criar_design(img_pil, txt_principal, txt_secundario, tema_selecionado, cor_tema, posicao_y, opacidade)
        
        # Mostra Imagem
        st.image(imagem_pronta, use_column_width=True, caption="Design Gerado Automaticamente")
        
        # Botões de Ação
        buf = io.BytesIO()
        imagem_pronta.save(buf, format="PNG")
        btn = st.download_button(
            label="⬇️ Baixar Imagem HD",
            data=buf.getvalue(),
            file_name="post_granrio.png",
            mime="image/png"
        )
        
        # Botão Inteligente: Gerar Legenda com IA baseada na imagem final
        if st.button("✨ Gerar Legenda para este Design"):
            with st.spinner("GPT-4o está escrevendo..."):
                # Codifica a imagem final (com texto e tudo) para a IA ver
                img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                res = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "Você é o marketing da Granrio. Crie uma legenda curta para Instagram baseada nesta imagem."},
                        {"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}]}
                    ]
                )
                st.info(res.choices[0].message.content)
                st.write("Copie o texto acima 👆")
                
    else:
        # Placeholder bonito enquanto não tem foto
        st.info("👈 Tire uma foto ou faça upload para começar a editar.")
        st.markdown("""
            <div style="background-color:#eee; height:300px; display:flex; align-items:center; justify-content:center; border-radius:10px; color:#aaa;">
                Pré-visualização aparecerá aqui
            </div>
        """, unsafe_allow_html=True)
