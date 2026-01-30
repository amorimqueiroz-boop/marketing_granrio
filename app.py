import streamlit as st
import sqlite3
import base64
from openai import OpenAI
from urllib.parse import quote
from datetime import datetime

# --- 1. CONFIGURAÇÃO DO APP (INTERFACE PWA) ---
st.set_page_config(
    page_title="Omnisfera Varejo - Indiaporã",
    page_icon="🏗️",
    layout="centered"
)

# Injeção de CSS corrigida (Removido o erro unsafe_allow_index)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stButton>button {
        width: 100%; 
        border-radius: 10px; 
        height: 3em; 
        font-weight: bold;
    }
    .stTextInput>div>div>input {border-radius: 10px;}
    </style>
""", unsafe_allow_html=True)

# --- 2. LÓGICA DE BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect("loja_indiapora.db", check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS vip (nome TEXT, celular TEXT)')
    conn.commit()
    return conn

conn = init_db()

# --- 3. SERVIÇOS DE IA (GPT-4o VISION) ---
# Dica: No Streamlit Cloud, use st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key="SUA_CHAVE_AQUI")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

PERSONA_MARKETING = """
Você é um especialista em marketing para lojas de material de construção no interior de SP.
Seu tom é simples, amigável e focado em confiança. Use gírias leves do interior se fizer sentido.
Sempre identifique o produto da foto e sugira uma legenda para Instagram e WhatsApp.
Inclua hashtags: #Indiapora #MaterialDeConstrucao #Reforma #Obra.
"""

# --- 4. INTERFACE PRINCIPAL (TABS) ---
st.title("🏗️ Gestor Indiaporã")

tab_post, tab_vip, tab_agenda = st.tabs(["📸 Criar Post", "👥 Lista VIP", "📅 Datas"])

# --- ABA 1: GERADOR VISUAL ---
with tab_post:
    st.subheader("Marketing Automático")
    foto = st.camera_input("Tire a foto do produto")
    
    preco = st.text_input("Preço Promocional (Opcional):", placeholder="Ex: R$ 49,90")
    estilo = st.selectbox("Objetivo:", ["Oferta do Dia", "Dica Técnica", "Homenagem"])

    if foto:
        if st.button("✨ Gerar Post com GPT-4o"):
            with st.spinner('Analisando imagem com GPT-4o...'):
                img_base64 = encode_image(foto)
                try:
                    res = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": PERSONA_MARKETING},
                            {"role": "user", "content": [
                                {"type": "text", "text": f"Crie um post para este produto. Preço: {preco}. Estilo: {estilo}."},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                            ]}
                        ]
                    )
                    st.session_state['legenda_atual'] = res.choices[0].message.content
                except Exception as e:
                    st.error(f"Erro na API: {e}")

    if 'legenda_atual' in st.session_state:
        txt_editado = st.text_area("Legenda Gerada (Pode editar):", value=st.session_state['legenda_atual'], height=200)
        
        num_destino = st.text_input("Enviar para (DDD + Número):", placeholder="17999999999")
        if st.button("📲 Enviar via WhatsApp"):
            if num_destino:
                link_whatsapp = f"https://wa.me/55{num_destino}?text={quote(txt_editado)}"
                st.markdown(f"**[CLIQUE AQUI PARA ENVIAR]({link_whatsapp})**")
            else:
                st.warning("Insira o número do cliente.")

# --- ABA 2: LISTA VIP ---
with tab_vip:
    st.subheader("Cadastro de Clientes VIP")
    with st.form("novo_vip", clear_on_submit=True):
        nome_cli = st.text_input("Nome do Cliente:")
        cel_cli = st.text_input("WhatsApp (Só números):")
        if st.form_submit_button("Salvar na Lista"):
            if nome_cli and cel_cli:
                conn.execute("INSERT INTO vip VALUES (?, ?)", (nome_cli, cel_cli))
                conn.commit()
                st.success("Cliente cadastrado!")
    
    st.write("---")
    st.subheader("Clientes Cadastrados")
    clientes = conn.execute("SELECT * FROM vip").fetchall()
    for c in clientes:
        st.write(f"👤 **{c[0]}** - {c[1]}")

# --- ABA 3: CALENDÁRIO LOCAL ---
with tab_agenda:
    hoje = datetime.now().strftime("%d/%m")
    datas_locais = {
        "19/03": "Dia do Carpinteiro",
        "25/05": "Dia do Trabalhador Rural",
        "30/06": "Dia do Caminhoneiro",
        "15/10": "Dia do Professor",
        "13/12": "Dia do Pedreiro"
    }
    
    st.info(f"Hoje: {hoje}")
    if hoje in datas_locais:
        st.balloons()
        st.success(f"🎉 HOJE É {datas_locais[hoje].upper()}! Faça uma promoção!")
    
    st.write("Próximas Datas para Promoções:")
    for d, n in datas_locais.items():
        st.write(f"📅 {d} — {n}")

