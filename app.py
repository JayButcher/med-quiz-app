import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import json

# 1. CONFIGURAÇÃO E SEGURANÇA
st.set_page_config(page_title="MedCase Tutor - UNIFUNCESI", layout="wide")

try:
    API_KEY = st.secrets["api_key"]
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ API_KEY não encontrada nos Secrets do Streamlit.")
    st.stop()

# Modelo estável para evitar erros de cota (Quota 429)
model = genai.GenerativeModel('gemini-1.5-flash')

# Estado da sessão
if 'modo' not in st.session_state: st.session_state['modo'] = 'Criar Questão'
if 'questao_pronta' not in st.session_state: st.session_state['questao_pronta'] = None
if 'historico' not in st.session_state: st.session_state['historico'] = []

# 2. BARRA LATERAL
with st.sidebar:
    st.title("🔒 Acesso")
    senha = st.text_input("Senha da turma:", type="password")
    if senha != "itabira2026":
        st.warning("Aguardando senha...")
        st.stop()
    
    st.divider()
    st.title("🩺 MedCase Tutor")
    st.session_state['modo'] = st.radio("Menu:", ["Criar Questão", "Responder", "Relatório"])
    if st.button("Reiniciar App"):
        st.session_state.clear()
        st.rerun()

# 3. MÓDULO CRIAR
if st.session_state['modo'] == "Criar Questão":
    st.header("1️⃣ Gerar Caso Clínico")
    img_file = st.file_uploader("Upload da Imagem:", type=["jpg", "png", "jpeg"])
    texto = st.text_area("Contexto/Laudo (opcional):")
    
    if img_file and st.button("✨ Gerar Questão"):
        img = Image.open(img_file)
        with st.spinner("IA a analisar..."):
            prompt = f"Age como professor de medicina. Cria uma questão de múltipla escolha em JSON: {{'enunciado': '...', 'alternativas': {{'A': '...', 'B': '...', 'C': '...', 'D': '...'}}, 'correta': 'LETRA', 'feedback': '...'}}. Contexto: {texto}"
            try:
                response = model.generate_content([prompt, img])
                res_text = response.text.replace("```json", "").replace("```", "").strip()
                st.session_state['questao_pronta'] = json.loads(res_text)
                
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                st.session_state['img_data'] = buf.getvalue()
                st.success("Pronto! Vá ao menu 'Responder'.")
            except Exception as e:
                st.error(f"Erro: {e}")

# 4. MÓDULO RESPONDER
elif st.session_state['modo'] == "Responder":
    if not st.session_state['questao_pronta']:
        st.info("Crie uma questão primeiro.")
    else:
        q = st.session_state['questao_pronta']
        if 'img_data' in st.session_state:
            st.image(st.session_state['img_data'], width=400)
        st.subheader(q['enunciado'])
        opcoes = [f"{l}) {t}" for l, t in q['alternativas'].items()]
        escolha = st.radio("Sua resposta:", opcoes, index=None)
        if st.button("Validar"):
            if escolha[0] == q['correta']:
                st.success("✅ Correto!")
            else:
                st.error(f"❌ Errado. A correta era {q['correta']}")
            st.info(q['feedback'])
