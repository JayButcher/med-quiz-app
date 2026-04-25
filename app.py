import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# ==========================================
# CONFIGURAÇÃO INICIAL E SEGURANÇA
# ==========================================
# Link para pegar a chave: https://aistudio.google.com/
# No Streamlit Cloud, coloque em Secrets: api_key = "SUA_CHAVE"

try:
    API_KEY = st.secrets["api_key"]
except:
    st.error("⚠️ API_KEY não encontrada nos Secrets do Streamlit.")
    st.stop()

genai.configure(api_key=API_KEY)

# Usamos o 1.5 Flash para velocidade e longa janela de contexto (para ler imagem + texto longo)
model = genai.GenerativeModel('gemini-pro')

st.set_page_config(page_title="MedCase Tutor - UNIFUNCESI", layout="wide")

# Inicialização do estado da sessão (para armazenar dados entre cliques)
if 'modo' not in st.session_state:
    st.session_state['modo'] = 'Criar'
if 'questao_pronta' not in st.session_state:
    st.session_state['questao_pronta'] = None
if 'resposta_usuario' not in st.session_state:
    st.session_state['resposta_usuario'] = None
if 'historico_respostas' not in st.session_state:
    st.session_state['historico_respostas'] = []

# ==========================================
# BARRA LATERAL - NAVEGAÇÃO E RELATÓRIOS
# ==========================================
with st.sidebar:
    st.title("🔒 Acesso Restrito")
    senha_correta = "itabira2026"
    senha_digitada = st.text_input("Digite a senha da turma:", type="password")

    if senha_digitada != senha_correta:
        st.warning("Aguardando senha...")
        st.stop() # Trava o app aqui se a senha estiver errada

    st.divider() # Uma linha para separar a trava do menu
    st.title("🩺 MedCase Tutor")
    st.subheader("by João Paulo")
    
    st.session_state['modo'] = st.radio("Selecione o Módulo:", ["Criar Questão", "Responder", "Relatório de Desempenho"])
    
    st.markdown("---")
    if st.button("Limpar Tudo e Recomeçar"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# MÓDULO 1: CRIAR QUESTÃO (DOCENTE)
# ==========================================
if st.session_state['modo'] == "Criar Questão":
    st.header("1️⃣ Criar Novo Caso Clínico")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Entradas do Professor")
        uploaded_image = st.file_uploader("Upload da Imagem Médica:", type=["jpg", "png", "jpeg"])
        texto_explicativo = st.text_area("Texto explicativo/Gabarito comentado (opcional):", height=300, placeholder="Cole aqui a explicação detalhada do caso, diretrizes ou o laudo...")
        
        nivel_dificuldade = st.select_slider("Nível da Questão:", options=["Básico", "Intermediário", "Residência/Avançado"])

    with col2:
        st.subheader("Geração Automática por IA")
        if uploaded_image and st.button("✨ Bolar Questão com Gemini"):
            img = Image.open(uploaded_image)
            
            with st.spinner("O Gemini está analisando a imagem e o texto para criar a questão..."):
                # PROMPT ENGENHADO PARA RESULTADO MÉDICO PADRÃO-OURO
                prompt = f"""
                Você é um professor de medicina renomado. Baseado na imagem anexada e no texto explicativo fornecido abaixo, crie uma questão de múltipla escolha de alto nível (nível {nivel_dificuldade}).

                Texto Explicativo/Base:
                ---
                {texto_explicativo}
                ---

                Estruture sua resposta EXATAMENTE no formato JSON abaixo:
                {{
                    "enunciado": "O texto do enunciado da questão...",
                    "alternativas": {{
                        "A": "Texto da alternativa A",
                        "B": "Texto da alternativa B",
                        "C": "Texto da alternativa C",
                        "D": "Texto da alternativa D",
                        "E": "Texto da alternativa E"
                    }},
                    "correta": "LETRA_DA_CORRETA (ex: C)",
                    "feedback_detalhado": "Um feedback completo e acadêmico, explicando por que a correta está certa e por que cada uma das incorretas está errada, baseando-se FORTEMENTE no texto explicativo fornecido.",
                    "ponto_forte_tópico": "Tópico principal acertado (ex: Radiologia Torácica)",
                    "ponto_fraco_tópico": "Tópico principal errado (ex: Diagnóstico Diferencial de Pneumonia)"
                }}
                Use apenas JSON puro na resposta, sem formatação markdown.
                """
                try:
                    response = model.generate_content([prompt, img])
                    # Limpeza de possíveis formatações markdown do JSON
                    json_str = response.text.replace("```json", "").replace("```", "").strip()
                    import json
                    questao_json = json.loads(json_str)
                    
                    # Salva a imagem em bytes para persistir na sessão
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format=img.format)
                    st.session_state['imagem_bytes'] = img_byte_arr.getvalue()
                    
                    st.session_state['questao_pronta'] = questao_json
                    st.success("Questão gerada com sucesso! Vá para o módulo 'Responder'.")
                except Exception as e:
                    st.error(f"Erro ao gerar questão. Verifique a API Key ou o formato da resposta da IA. Erro: {e}")

# ==========================================
# MÓDULO 2: RESPONDER (DISCENTE)
# ==========================================
elif st.session_state['modo'] == "Responder":
    st.header("2️⃣ Resolva o Caso Clínico")
    
    if st.session_state['questao_pronta'] is None:
        st.warning("Nenhuma questão foi criada ainda. Vá para 'Criar Questão'.")
    else:
        q = st.session_state['questao_pronta']
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if 'imagem_bytes' in st.session_state:
                st.image(st.session_state['imagem_bytes'], caption="Imagem de Referência", use_container_width=True)
            
        with col2:
            st.subheader(q['enunciado'])
            
            # Opções de múltipla escolha
            opcoes = [f"{letra}) {texto}" for letra, texto in q['alternativas'].items()]
            
            resposta = st.radio("Selecione sua resposta:", opcoes, index=None)
            
            if st.button("Confirmar Resposta") and resposta:
                letra_resposta = resposta[0] # Pega apenas a letra (A, B, C...)
                st.session_state['resposta_usuario'] = letra_resposta
                
                eh_correta = letra_resposta == q['correta']
                
                # Salva no histórico para o relatório
                st.session_state['historico_respostas'].append({
                    "enunciado": q['enunciado'][:50] + "...",
                    "acertou": eh_correta,
                    "ponto_forte": q['ponto_forte_tópico'],
                    "ponto_fraco": q['ponto_fraco_tópico']
                })
                
                st.rerun() # Recarrega para mostrar o feedback

        # Exibição do Feedback (Canvas)
        if st.session_state['resposta_usuario']:
            q = st.session_state['questao_pronta']
            letra_user = st.session_state['resposta_usuario']
            eh_correta = letra_user == q['correta']
            
            st.markdown("---")
            st.subheader("📋 Feedback Detalhado (Estilo Canvas)")
            
            if eh_correta:
                st.success(f"✅ CORRETO! Você selecionou a alternativa {letra_user}.")
            else:
                st.error(f"❌ INCORRETO. Você selecionou a {letra_user}, mas a correta era a {q['correta']}.")
            
            # Usando expander para o feedback longo
            with st.expander("Ver Análise Completa do Caso", expanded=True):
                st.markdown(q['feedback_detalhado'])
                st.info(f"**Tópico Dominado:** {q['ponto_forte_tópico']}")

# ==========================================
# MÓDULO 3: RELATÓRIO (ANÁLISE FINA)
# ==========================================
elif st.session_state['modo'] == "Relatório de Desempenho":
    st.header("3️⃣ Sua Análise de Pontos Fortes e Fracos")
    
    if not st.session_state['historico_respostas']:
        st.warning("Responda algumas questões primeiro para gerar o relatório.")
    else:
        historico = st.session_state['historico_respostas']
        total = len(historico)
        acertos = sum(1 for r in historico if r['acertou'])
        erros = total - acertos
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Questões", total)
        col2.metric("Acertos", acertos, f"{ (acertos/total)*100:.1f}%" if total > 0 else "0%")
        col3.metric("Erros", erros)
        
        # Análise Cognitiva por IA (A "IA como você" gerando o relatório final)
        st.subheader("🕵️‍♂️ Análise Cognitiva do Tutor IA")
        with st.spinner("Analisando seu padrão de respostas..."):
            
            # Prepara os dados para enviar para a IA
            dados_relatorio = "\n".join([f"Questão: {r['enunciado']} | Acertou: {r['acertou']} | Forte: {r['ponto_forte']} | Fraco: {r['ponto_fraco']}" for r in historico])
            
            prompt_relatorio = f"""
            Com base no histórico de respostas de um estudante de medicina abaixo, gere um relatório final curto e encorajador.
            Identifique os 2 principais Pontos Fortes (onde ele acertou) e as 2 principais Áreas de Melhoria (onde ele errou).
            Sugira brevemente como ele pode estudar os pontos fracos.

            Histórico:
            ---
            {dados_relatorio}
            ---
            Gere a resposta formatada em Markdown, com emojis médicos.
            """
            
            try:
                response_relatorio = model.generate_content(prompt_relatorio)
                st.markdown(response_relatorio.text)
            except:
                st.error("Erro ao gerar relatório cognitivo.")
