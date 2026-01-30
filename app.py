import streamlit as st
import sqlite3
import base64
import pandas as pd
from openai import OpenAI
from urllib.parse import quote
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from rembg import remove
import io
import requests

# --- 1. CONFIGURAÇÃO GERAL ---
st.set_page_config(page_title="Gestor Granrio", page_icon="🏗️", layout="centered")

# CSS para ficar bonito no celular
st.markdown("""
    <style>
    .stApp {background-color: #f8f9fa;}
    .stButton>button {
        width: 100%; border-radius: 10px; height: 3.5em; 
        font-weight: bold; background-color: #004aad; color: white; border: none;
    }
    div[data-testid="stButton"] > button[kind="secondary"] {
        background-color: #e11d48 !important; color: white !important;
    }
    .stTextInput>div>div>input {border-radius: 10px;}
    h1, h2, h3 {color: #0f172a;}
    </style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS (Unificado) ---
def init_db():
    conn = sqlite3.connect("loja_granrio_full.db", check_same_thread=False)
    c = conn.cursor()
    # Tabela de Clientes VIP
    c.execute('CREATE TABLE IF NOT EXISTS vip (nome TEXT, celular TEXT)')
    # Tabela de Histórico (Posts e Imagens)
    c.execute('CREATE TABLE IF NOT EXISTS historico (data TEXT, tipo TEXT, conteudo TEXT)')
    conn.commit()
    return conn

conn = init_db()

# --- 3. INTEGRAÇÃO OPENAI ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except:
    api_key = "SUA_CHAVE_AQUI"
client = OpenAI(api_key=api_key)

# --- 4. FUNÇÕES DO STUDIO MAGIC (O "Photoroom" Local) ---

def remover_fundo_ia(input_image):
    # Usa a biblioteca rembg para recortar o produto
    return remove(input_image)

def gerar_cenario_dalle(descricao_cenario):
    # Pede ao DALL-E apenas o fundo
    prompt = f"Background image only, no products in center. {descricao_cenario}. Bokeh effect, professional architectural photography lighting, blurred background, high resolution, 8k."
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    img_data = requests.get(response.data[0].url).content
    return Image.open(io.BytesIO(img_data))

def compor_imagem_final(fundo, produto_recortado, texto_preco):
    fundo = fundo.resize((1024, 1024))
    
    # Ajusta proporção do produto
    largura_orig, altura_orig = produto_recortado.size
    ratio = largura_orig / altura_orig
    
    # Define tamanho do produto na cena (70% da altura)
    nova_altura = 750
    nova_largura = int(nova_altura * ratio)
    
    # Redimensiona o produto recortado
    produto_final = produto_recortado.resize((nova_largura, nova_altura))
    
    # Centraliza
    pos_x = (1024 - nova_largura) // 2
    pos_y = (1024 - nova_altura) // 2 + 50 
    
    # Cola o produto no fundo
    fundo.paste(produto_final, (pos_x, pos_y), produto_final)
    
    # Adiciona a etiqueta de preço
    draw = ImageDraw.Draw(fundo)
    try:
        font_p = ImageFont.truetype("arial.ttf", 100)
    except:
        font_p = ImageFont.load_default()
        
    # Desenha bolha vermelha
    x_bolha, y_bolha = 850, 900
    r = 120
    draw.ellipse([(x_bolha-r, y_bolha-r), (x_bolha+r, y_bolha+r)], fill="#dc2626", outline="white", width=5)
    
    # Texto do preço
    w = draw.textlength(texto_preco, font=font_p)
    draw.text((x_bolha - w/2, y_bolha - 50), texto_preco, font=font_p, fill="white")
    
    return fundo

# --- 5. INTERFACE PRINCIPAL ---
st.title("🏗️ Gestor Granrio")

# Variáveis de Estado (Memória do App)
if 'img_final' not in st.session_state: st.session_state['img_final'] = None
if 'legenda_final' not in st.session_state: st.session_state['legenda_final'] = None

# Abas com todas as funções
tab_studio, tab_agenda, tab_vip, tab_hist = st.tabs(["📸 Studio Magic", "📅 Agenda", "👥 Lista VIP", "📊 Controle"])

# --- ABA 1: STUDIO MAGIC (Foto -> Recorte -> Fundo -> Post) ---
with tab_studio:
    st.subheader("Transformar Foto Real em Premium")
    
    foto_input = st.camera_input("Tire a foto (Não importa o fundo)")
    
    col1, col2 = st.columns(2)
    with col1:
        preco = st.text_input("Preço:", value="R$ 99,90")
    with col2:
        cenario = st.selectbox("Escolha o Cenário:", [
            "Banheiro de Luxo (Mármore)",
            "Obra Limpa e Iluminada",
            "Jardim com Sol",
            "Cozinha Planejada Moderna",
            "Estúdio Fundo Infinito Azul"
        ])
    
    if foto_input and st.button("✨ Criar Mágica (Recortar + Gerar Fundo)"):
        img_pil = Image.open(foto_input)
        
        # Passo 1: Recorte
        with st.spinner("✂️ Recortando fundo feio..."):
            prod_sem_fundo = remover_fundo_ia(img_pil)
            
        # Passo 2: Gerar Fundo (DALL-E)
        with st.spinner(f"🎨 Pintando cenário: {cenario}..."):
            # Traduz cenário para prompt em inglês pro DALL-E entender melhor
            prompts = {
                "Banheiro de Luxo (Mármore)": "Luxury bathroom white marble counter",
                "Obra Limpa e Iluminada": "Clean construction site concrete daylight",
                "Jardim com Sol": "Beautiful sunny garden green grass",
                "Cozinha Planejada Moderna": "Modern kitchen granite counter",
                "Estúdio Fundo Infinito Azul": "Abstract professional dark blue studio background"
            }
            fundo_ia = gerar_cenario_dalle(prompts[cenario])
            
        # Passo 3: Montagem
        with st.spinner("🔨 Montando imagem final..."):
            img_composta = compor_imagem_final(fundo_ia, prod_sem_fundo, preco)
            st.session_state['img_final'] = img_composta
            
        # Passo 4: Legenda (GPT-4o)
        with st.spinner("✍️ Escrevendo legenda..."):
            # Converte a imagem final para mandar pro GPT ver
            buf = io.BytesIO(); img_composta.save(buf, format="PNG")
            b64_img = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            res = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Marketing Granrio Indiaporã. Texto curto e vendedor."},
                    {"role": "user", "content": [{"type": "text", "text": f"Crie legenda para este produto. Preço {preco}."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}]}
                ]
            )
            st.session_state['legenda_final'] = res.choices[0].message.content
            
            # Salva no histórico
            conn.execute("INSERT INTO historico VALUES (?, ?, ?)", 
                         (datetime.now().strftime("%d/%m %H:%M"), "Studio Magic", st.session_state['legenda_final']))
            conn.commit()
            st.rerun()

    # Exibição do Resultado
    if st.session_state['img_final']:
        st.write("---")
        st.image(st.session_state['img_final'], caption="Resultado Final", use_column_width=True)
        
        # Botão Download
        buf_down = io.BytesIO()
        st.session_state['img_final'].save(buf_down, format="PNG")
        st.download_button("⬇️ Baixar Imagem", data=buf_down.getvalue(), file_name="granrio_magic.png", mime="image/png")
        
        txt = st.text_area("Legenda:", value=st.session_state['legenda_final'])
        
        # Enviar Zap
        zap = st.text_input("Zap do Cliente:", key="zap_studio")
        if st.button("📲 Enviar no WhatsApp"):
            url = f"https://wa.me/55{zap}?text={quote(txt)}"
            st.markdown(f"[CLIQUE PARA ENVIAR]({url})")

# --- ABA 2: AGENDA INTELIGENTE ---
with tab_agenda:
    st.header("📅 Sugestão do Dia")
    datas = {"30/01": "Dia da Saudade", "19/03": "Dia do Carpinteiro", "13/12": "Dia do Pedreiro"}
    hoje = datetime.now().strftime("%d/%m")
    
    if hoje in datas:
        st.success(f"Hoje é {datas[hoje]}! Aproveite.")
    else:
        st.info("Dia comum. Que tal uma dica de obra?")
        
    if st.button("💡 Gerar Ideia de Hoje"):
        prompt = f"Crie um post para hoje ({hoje}) para loja de construção. Se tiver data especial, use. Senão, dê uma dica útil."
        res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        st.text_area("Ideia:", value=res.choices[0].message.content, height=150)

# --- ABA 3: LISTA VIP ---
with tab_vip:
    st.header("👥 Clientes VIP")
    with st.form("vip_add"):
        n = st.text_input("Nome")
        c = st.text_input("Celular")
        if st.form_submit_button("Salvar"):
            conn.execute("INSERT INTO vip VALUES (?, ?)", (n, c)); conn.commit(); st.rerun()
            
    df = pd.read_sql_query("SELECT * FROM vip", conn)
    st.dataframe(df, use_container_width=True)

# --- ABA 4: CONTROLE ---
with tab_hist:
    st.header("📊 Histórico de Posts")
    if st.button("Atualizar"): st.rerun()
    df_h = pd.read_sql_query("SELECT * FROM historico ORDER BY data DESC", conn)
    st.dataframe(df_h, use_container_width=True)
