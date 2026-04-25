import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import json

# ==========================================
# CONFIGURAÇÃO INICIAL E SEGURANÇA
# ==========================================
st.set_page_config(page_title="MedCase Tutor - UNIFUNCESI", layout="wide")

try:
    API_KEY = st.secrets["api_key"]
    # Configuração direta para evitar erro 404/v1beta
    genai.configure(api_key=API_KEY)
except Exception:
    st.error("⚠️ API_KEY não encontrada nos Secrets do Streamlit.")
    st.stop()

# Definindo o modelo estável de 2026
model = genai.GenerativeModel('gemini-1.5-flash')

# Inicialização do estado da sessão
if 'modo' not in st.session_state:
    st.session_state['modo'] = 'Criar Questão'
if 'questao_pronta' not in st.session_state:
    st.session_state['questao_pronta'] = None
if 'resposta_usuario' not in st.session_state:
    st.session_state['resposta_usuario'] = None
if 'historico_respostas' not in st.session_state:
    st.session_state['historico_respostas'] = []

# ==========================================
# BARRA LATERAL - SEGURANÇA E NAVEGAÇÃO
# ==========================================
with st.sidebar:
    st.title("🔒 Acesso Restrito")
    senha_correta = "itabira2026"
    senha_digitada = st.text_input("Digite a senha da turma:", type="password")

    if senha_digitada != senha_correta:
        st.warning("Aguardando senha...")
        st.stop()

    st.divider()
    st.title("🩺 MedCase Tutor")
    st.subheader("by João Paulo")
    
    st.session_state['modo'] = st.radio(
        "Selecione o Módulo:", 
        ["Criar Questão", "Responder", "Relatório de Desempenho"]
    )
    
    st.markdown("---")
    if st.button("Limpar Tudo e Recomeçar"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# MÓDULO 1: CRIAR QUESTÃO
# ==========================================
if st.session_state['modo'] == "Criar Questão":
    st.header("1️⃣ Criar Novo Caso Clínico")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Entradas do Professor")
        uploaded_image = st.file_uploader("Upload da Imagem Médica:", type=["jpg", "png", "jpeg"])
        texto_explicativo = st.text_area("Texto explicativo/Gabarito comentado (opcional):", height=300)
        nivel_dificuldade = st.select_slider("Nível da Questão:", options=["Básico", "Intermediário", "Residência/Avançado"])

    with col2:
        st.subheader("Geração Automática por IA")
        if uploaded_image and st.button("✨ Bolar Questão com Gemini"):
            img = Image.open(uploaded_image)
            
            with st.spinner("Analisando imagem e gerando caso clínico..."):
                prompt = f"""
                Você é um professor de medicina. Com base na imagem e no texto: {texto_explicativo}, 
                crie uma questão de nível {nivel_dificuldade} em JSON puro:
                {{
                    "enunciado": "...",
                    "alternativas": {{"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."}},
                    "correta": "LETRA",
                    "feedback_detalhado": "...",
                    "ponto_forte_tópico": "...",
                    "ponto_fraco_tópico": "..."
                }}
                """
                try:
                    response = model.generate_content([prompt, img])
                    json_str = response.text.replace("```json", "").replace("```", "").strip()
                    questao_json = json.loads(json_str)
                    
                    # Persistir imagem
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format="PNG")
                    st.session_state['imagem_bytes'] = img_byte_arr.getvalue()
                    
                    st.session_state['questao_pronta'] = questao_json
                    st.session_state['resposta_usuario'] = None # Reseta resposta anterior
                    st.success("Questão pronta! Vá para o módulo 'Responder'.")
                except Exception as e:
                    st.error(f"Erro na geração. Verifique sua cota da API. Detalhes: {e}")

# ==========================================
# MÓDULO 2: RESPONDER
# ==========================================
elif st.session_state['modo'] == "Responder":
    st.header("2️⃣ Resolva o Caso Clínico")
    
    if st.session_state['questao_pronta'] is None:
        st.warning("Crie uma questão primeiro!")
    else:
        q = st.session_state['questao_pronta']
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if 'imagem_bytes' in st.session_state:
                st.image(st.session_state['imagem_bytes'], use_container_width=True)
            
        with col2:
            st.subheader(q['enunciado'])
            opcoes = [f"{l}) {t}" for l, t in q['alternativas'].items()]
            res = st.radio("Sua resposta:", opcoes, index=None)
            
            if st.button("Confirmar") and res:
                letra = res[0]
                st.session_state['resposta_usuario'] = letra
                acertou = letra == q['correta']
                st.session_state['historico_respostas'].append({
                    "enunciado": q['enunciado'][:50],
                    "acertou": acertou,
                    "ponto_forte": q['ponto_forte_tópico'],
                    "ponto_fraco": q['ponto_fraco_tópico']
                })
                st.rerun()

        if st.session_state['resposta_usuario']:
            st.divider()
            if st.session_state['resposta_usuario'] == q['correta']:
                st.success(f"✅ Correto! Alternativa {q['correta']}")
            else:
                st.error(f"❌ Errado. A correta era {q['correta']}")
            st.info(q['feedback_detalhado'])

# ==========================================
# MÓDULO 3: RELATÓRIO
# ==========================================
else:
    st.header("3️⃣ Análise de Desempenho")
    if not st.session_state['historico_respostas']:
        st.info("Sem dados ainda.")
    else:
        for r in st.session_state['historico_respostas']:
            status = "✅" if r['acertou'] else "❌"
            st.write(f"{status} {r['enunciado']}")
        
        if st.button("Gerar Análise Cognitiva"):
            with st.spinner("IA analisando..."):
                try:
                    res_rel = model.generate_content("Analise este histórico médico e dê dicas: " + str(st.session_state['historico_respostas']))
                    st.markdown(res_rel.text)
                except Exception as e:
                    st.error(f"Erro no relatório: {e}")
