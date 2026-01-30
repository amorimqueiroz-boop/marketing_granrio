import streamlit as st
import sqlite3
import base64
from openai import OpenAI
from urllib.parse import quote
from datetime import datetime

# --- CONFIGURAÇÃO DO APP (MODO MOBILE) ---
st.set_page_config(
    page_title="Omnisfera Varejo - Indiaporã",
    page_icon="🏗️",
    layout="centered"
)

# Esconder menus para parecer App nativo
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stButton>button {width: 100%; border-radius: 10px;}
    </style>
""", unsafe_allow_index=True)

# --- INICIALIZAÇÃO ---
client = OpenAI(api_key="SUA_CHAVE_API_AQUI")

def init_db():
    conn = sqlite3.connect("loja_indiapora.db")
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS vip (nome TEXT, celular TEXT)')
    conn.commit()
    return conn

conn = init_db()

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

# --- PERSONA DE MARKETING (PROMPT DO SISTEMA) ---
PERSONA_MARKETING = """
Você é o braço direito de marketing de uma loja de materiais de construção em Indiaporã, interior de SP.
Seu público são pessoas simples, pedreiros, caminhoneiros e donos de casa.
Linguagem: Humilde, prestativa, usa o nome do cliente, evita termos técnicos difíceis.
Foco: Preço justo, confiança de quem é da cidade e qualidade do material.
Sempre inclua hashtags como #Indiapora #Reforma #Construcao #MaterialDeConstrucao.
"""

# --- UI PRINCIPAL ---
st.title("🏗️ Marketing Omnisfera")
tab1, tab2, tab3 = st.tabs(["📸 Novo Post", "👥 Lista VIP", "📅 Calendário"])

# --- TAB 1: GERADOR DE POST COM GPT-4O VISION ---
with tab1:
    st.subheader("Tire uma foto e crie o post")
    foto = st.camera_input("Capturar Produto")
    
    preco_input = st.text_input("Preço de Venda (Opcional):", placeholder="Ex: R$ 29,90")
    estilo = st.selectbox("Tom da mensagem:", ["Oferta Relâmpago", "Homenagem Profissional", "Dica de Reforma"])

    if foto:
        if st.button("✨ Gerar Marketing com GPT-4o"):
            with st.spinner('Analisando produto...'):
                base64_img = encode_image(foto)
                try:
                    res = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": PERSONA_MARKETING},
                            {"role": "user", "content": [
                                {"type": "text", "text": f"Identifique este produto e crie um post para WhatsApp e Instagram. Preço: {preco_input}. Estilo: {estilo}."},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                            ]}
                        ]
                    )
                    st.session_state['legenda'] = res.choices[0].message.content
                except Exception as e:
                    st.error(f"Erro: {e}")

    if 'legenda' in st.session_state:
        txt_final = st.text_area("Texto Gerado:", value=st.session_state['legenda'], height=250)
        
        c1, c2 = st.columns(2)
        with c1:
            num = st.text_input("Enviar para (DDD+Número):")
            if st.button("📲 Enviar WhatsApp"):
                link = f"https://wa.me/55{num}?text={quote(txt_final)}"
                st.markdown(f"**[Clique aqui para Abrir WhatsApp]({link})**")
        with c2:
            st.info("Dica: Copie o texto e use a foto tirada no seu Instagram!")

# --- TAB 2: GESTÃO VIP ---
with tab2:
    st.subheader("Cadastro de Clientes")
    with st.form("cad_cliente"):
        n = st.text_input("Nome do Cliente:")
        c = st.text_input("Celular (só números):")
        if st.form_submit_button("Salvar na Lista VIP"):
            conn.execute("INSERT INTO vip VALUES (?, ?)", (n, c))
            conn.commit()
            st.success("Cliente Salvo!")
    
    st.write("---")
    st.subheader("Sua Lista VIP")
    clientes = conn.execute("SELECT * FROM vip").fetchall()
    for cli in clientes:
        st.write(f"👤 {cli[0]} - {cli[1]}")

# --- TAB 3: DATAS DE INDIAPORÃ ---
with tab3:
    hoje = datetime.now().strftime("%d/%m")
    datas = {
        "19/03": "Dia do Carpinteiro", "30/06": "Dia do Caminhoneiro",
        "25/07": "Dia do Motorista", "13/12": "Dia do Pedreiro",
        "15/10": "Dia do Professor"
    }
    st.info(f"Hoje é: {hoje}")
    if hoje in datas:
        st.warning(f"🔔 DATA ESPECIAL: {datas[hoje]}! Ótimo dia para promoção!")
    else:
        st.write("Próximas datas importantes:")
        for d, n in datas.items():
            st.write(f"📅 {d} - {n}")
