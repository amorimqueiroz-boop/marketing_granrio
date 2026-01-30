import streamlit as st
import base64
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from rembg import remove
import io
import requests

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Studio Granrio Pro", page_icon="🏗️", layout="centered")

st.markdown("""
    <style>
    .stApp {background-color: #0e1117;}
    h1 {color: #fff;}
    .stButton>button {
        width: 100%; border-radius: 12px; height: 50px; 
        font-weight: bold; font-size: 18px;
        background: linear-gradient(90deg, #004aad 0%, #0078d4 100%);
        border: none; color: white;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. API SETUP ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except:
    api_key = "SUA_CHAVE_AQUI"
client = OpenAI(api_key=api_key)

# --- 3. FUNÇÕES DE ELITE (O MOTOR) ---

def remover_fundo(input_image):
    # Usa IA para recortar o produto
    return remove(input_image)

def gerar_fundo_ia(descricao_cenario):
    # DALL-E 3 gera APENAS o fundo (sem produto)
    prompt = f"Background image only, no products, no text. {descricao_cenario}. Bokeh effect, professional photography lighting, blurred background, high resolution."
    
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    image_url = response.data[0].url
    # Baixa a imagem gerada
    img_data = requests.get(image_url).content
    return Image.open(io.BytesIO(img_data))

def montar_imagem_final(fundo, produto_sem_fundo, texto_preco):
    # Redimensiona fundo para garantir 1024x1024
    fundo = fundo.resize((1024, 1024))
    
    # Ajusta o tamanho do produto para caber bem no cenário
    # Mantém a proporção
    largura_prod, altura_prod = produto_sem_fundo.size
    aspect_ratio = largura_prod / altura_prod
    
    nova_altura = 700 # Ocupa boa parte da imagem verticalmente
    nova_largura = int(nova_altura * aspect_ratio)
    
    produto_resized = produto_sem_fundo.resize((nova_largura, nova_altura))
    
    # Centraliza o produto no fundo
    pos_x = (1024 - nova_largura) // 2
    pos_y = (1024 - nova_altura) // 2 + 50 # Um pouco para baixo
    
    # Cola o produto sobre o fundo (usando a máscara de transparência)
    fundo.paste(produto_resized, (pos_x, pos_y), produto_resized)
    
    # Adiciona o Preço (Design Premium)
    draw = ImageDraw.Draw(fundo)
    
    # Carrega fonte (ou default)
    try:
        font_preco = ImageFont.truetype("arial.ttf", 120)
        font_moeda = ImageFont.truetype("arial.ttf", 60)
    except:
        font_preco = ImageFont.load_default()
        font_moeda = ImageFont.load_default()
    
    # Bolha de Preço
    x_tag = 750
    y_tag = 850
    raio = 130
    draw.ellipse([(x_tag-raio, y_tag-raio), (x_tag+raio, y_tag+raio)], fill="#e11d48", outline="white", width=8)
    
    draw.text((x_tag-60, y_tag-80), "R$", font=font_moeda, fill="white")
    draw.text((x_tag-90, y_tag-20), texto_preco, font=font_preco, fill="white")
    
    return fundo

# --- 4. INTERFACE ---
st.title("🏗️ Studio Granrio Pro")
st.write("Transforme fotos simples em anúncios de revista.")

# Passo 1: Captura
img_file = st.camera_input("1. Tire a foto do produto (Fundo não importa)")

if img_file:
    # Mostra progresso visual
    col1, col2, col3 = st.columns(3)
    
    with st.spinner("🚀 Processando imagem..."):
        # Carrega imagem original
        input_img = Image.open(img_file)
        
        # ETAPA A: REMOVER FUNDO
        with col1:
            st.image(input_img, caption="Original", use_column_width=True)
            
        with st.spinner("✂️ Recortando fundo com IA..."):
            produto_png = remover_fundo(input_img)
            with col2:
                st.image(produto_png, caption="Recortado", use_column_width=True)

    # Passo 2: Configuração do Cenário
    st.write("---")
    st.subheader("2. Escolha o Cenário")
    
    cenario_opcao = st.selectbox(
        "Onde esse produto deve aparecer?",
        [
            "Banheiro de Luxo (Mármore Claro)",
            "Obra em Construção (Clean)",
            "Jardim Externo com Sol",
            "Fundo Azul Profissional (Estúdio)",
            "Cozinha Moderna Planejada"
        ]
    )
    
    preco = st.text_input("Preço (Só o número):", value="99")
    
    if st.button("✨ GERAR IMAGEM FINAL"):
        with st.spinner("🎨 O DALL-E está pintando o cenário e montando a foto..."):
            
            # Define o prompt do cenário baseado na escolha
            if "Banheiro" in cenario_opcao: prompt_cenario = "Luxury bright bathroom with white marble counter, blurred background"
            elif "Obra" in cenario_opcao: prompt_cenario = "Clean construction site, soft daylight, blurred concrete background"
            elif "Jardim" in cenario_opcao: prompt_cenario = "Beautiful garden with green grass and sunlight, blurred background"
            elif "Cozinha" in cenario_opcao: prompt_cenario = "Modern kitchen counter, granite surface, blurred background"
            else: prompt_cenario = "Professional abstract dark blue studio background with spotlight"
            
            # ETAPA B: GERAR FUNDO
            fundo_ia = gerar_fundo_ia(prompt_cenario)
            
            # ETAPA C: MONTAR
            imagem_final = montar_imagem_final(fundo_ia, produto_png, preco)
            
            st.success("Pronto!")
            st.image(imagem_final, caption="Anúncio Final", use_column_width=True)
            
            # Botão de Download
            buf = io.BytesIO()
            imagem_final.save(buf, format="PNG")
            st.download_button(
                label="⬇️ Baixar Imagem para o Instagram",
                data=buf.getvalue(),
                file_name="granrio_post_pro.png",
                mime="image/png"
            )
            
            # Sugestão de Legenda (Extra)
            st.info("Dica: Copie a imagem acima e poste nos Stories!")

else:
    st.info("👆 Tire uma foto para começar a mágica.")
