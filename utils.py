# utils.py - ARQUIVO CORRIGIDO
import streamlit as st
from datetime import datetime
import os
import base64
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

def carregar_imagem_companhia(nome_companhia):
    """Carrega imagem da companhia aérea"""
    # Primeiro tenta carregar imagem real
    caminhos_companhias = {
        "latam": ["latam.png", "assets/latam.png", "companhias/latam.png"],
        "gol": ["gol.png", "assets/gol.png", "companhias/gol.png"],
        "azul": ["azul.png", "assets/azul.png", "companhias/azul.png"],
        "american": ["american.png", "assets/american.png", "companhias/american.png"]
    }
    
    companhia_lower = nome_companhia.lower()
    for key in caminhos_companhias:
        if key in companhia_lower:
            for caminho in caminhos_companhias[key]:
                if os.path.exists(caminho):
                    try:
                        with open(caminho, "rb") as f:
                            return base64.b64encode(f.read()).decode()
                    except Exception as e:
                        logger.warning(f"Erro ao carregar logo {caminho}: {e}")
    
    # Se não encontrar, gera imagem com cor
    cores_companhias = {
        "latam": ("#1E88E5", "LATAM"),
        "gol": ("#FF6B00", "GOL"),
        "azul": ("#00B0FF", "AZUL"),
        "american": ("#002D72", "AMERICAN")
    }
    
    for key, (cor, texto) in cores_companhias.items():
        if key in companhia_lower:
            break
    else:
        cor, texto = ("#3d8bfd", nome_companhia.upper())
    
    img = Image.new('RGB', (250, 120), color=cor)
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except:
        font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), texto, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (250 - text_width) / 2
    y = (120 - text_height) / 2
    
    draw.text((x, y), texto, fill="white", font=font)
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def get_currency_symbol(moeda):
    """Retorna símbolo da moeda"""
    simbolos = {
        'BRL': 'R$',
        'USD': 'US$',
        'EUR': '€',
        'GBP': '£'
    }
    return simbolos.get(moeda, 'R$')

def get_colors():
    """Retorna cores baseadas no tema"""
    tema = st.session_state.get("tema", "escuro")
    
    if tema == "escuro":
        return {
            'fundo': "#000000",
            'sidebar': '#1a1a1a',
            'card': '#1e1e1e',
            'texto': '#f0f0f0',
            'destaque': '#3d8bfd',
            'destaque_hover': '#2a5cbd',
            'borda': '#333',
            'gradiente_login': 'linear-gradient(135deg, #1a1a1a, #0d0d0d)',
            'hover': '#2a2a2a',
            'fundo_card': '#1a1a1a',
            'texto_claro': '#ffffff',
            'texto_escuro': '#000000',
            'success': '#4CAF50',
            'warning': '#FF9800',
            'error': '#F44336',
            'info': '#2196F3',
            'botao_fundo': '#1a1a1a',
            'botao_texto': '#ffffff',
            'botao_hover': '#2a2a2a',
            'botao_primary_gradient': 'linear-gradient(135deg, #3d8bfd, #2a5cbd)',
            'botao_primary_hover': 'linear-gradient(135deg, #2a5cbd, #3d8bfd)'
        }
    else:  # Modo claro
        return {
            'fundo': '#ffffff',
            'sidebar': '#f8f9fa',
            'card': '#ffffff',
            'texto': '#212529',
            'destaque': '#3d8bfd',
            'destaque_hover': "#347aca",
            'borda': '#dee2e6',
            'gradiente_login': 'linear-gradient(135deg, #ffffff, #f8f9fa)',
            'hover': '#e9ecef',
            'fundo_card': '#f8f9fa',
            'texto_claro': "#8f8f8f",
            'texto_escuro': "#000000",
            'success': '#28a745',
            'warning': '#ffc107',
            'error': '#dc3545',
            'info': '#17a2b8',
            'botao_fundo': '#ffffff',
            'botao_texto': "#424242",
            'botao_hover': '#e9ecef',
            'botao_primary_gradient': 'linear-gradient(135deg, #3d8bfd, #2a5cbd)',
            'botao_primary_hover': 'linear-gradient(135deg, #2a5cbd, #3d8bfd)'
        }

def aplicar_css():
    """Aplica CSS dinâmico baseado no tema"""
    cores = get_colors()
    
    # CSS responsivo global
    st.markdown("""
    <style>
    /* Estilos responsivos para os cards de detalhes */
    .responsive-details-card {
        background: var(--card-bg, #1e1e1e);
        padding: 1.5rem;
        border-radius: 16px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        color: var(--text-color, #f0f0f0);
        border: 1px solid var(--border-color, #333);
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        transition: all 0.3s ease;
        margin-bottom: 1rem;
    }

    /* Grid responsivo que se adapta automaticamente */
    .responsive-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    /* Cards internos com hover effect */
    .info-card {
        background: var(--card-inner, #2a2a2a);
        padding: 1.2rem;
        border-radius: 12px;
        border: 1px solid var(--border-color, #444);
        transition: transform 0.2s, box-shadow 0.2s;
    }

    .info-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.1);
    }

    /* Grid para valores das milhas - responsivo */
    .milhas-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }

    /* Cards de valor */
    .value-card {
        background: var(--card-inner, #2a2a2a);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        border: 1px solid var(--border-color, #444);
    }

    .value-label {
        font-size: 0.85rem;
        opacity: 0.7;
        margin-bottom: 0.3rem;
    }

    .value-number {
        font-size: 1.3rem;
        font-weight: 600;
        color: var(--highlight, #3d8bfd);
    }

    /* Card de total - destaque especial */
    .total-card {
        background: linear-gradient(135deg, var(--success, #4CAF50)20 0%, transparent 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 6px solid var(--success, #4CAF50);
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        margin-top: 1rem;
    }

    .total-value {
        font-size: clamp(1.5rem, 5vw, 2.5rem);
        font-weight: 700;
        color: var(--success, #4CAF50);
        line-height: 1.2;
    }

    /* Metadados - com scroll se necessário */
    .metadata-container {
        background: var(--info, #2196F3)10;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid var(--info, #2196F3)30;
        margin-top: 1rem;
        overflow-x: auto;
    }

    .metadata-pre {
        margin: 0;
        font-size: 0.85rem;
        color: var(--text-color, #f0f0f0)80;
        white-space: pre-wrap;
        word-wrap: break-word;
        font-family: 'Courier New', monospace;
    }

    /* Títulos com ícones */
    .section-title {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin: 0 0 1rem 0;
        color: var(--highlight, #3d8bfd);
        font-size: 1.2rem;
    }

    /* Responsivo para telas pequenas */
    @media (max-width: 768px) {
        .responsive-details-card {
            padding: 1rem;
        }
        
        .info-card {
            padding: 1rem;
        }
        
        .total-card {
            flex-direction: column;
            text-align: center;
        }
        
        .total-value {
            font-size: 2rem;
        }
    }

    /* Suporte para tema claro */
    @media (prefers-color-scheme: light) {
        .responsive-details-card {
            --card-bg: #ffffff;
            --card-inner: #f5f5f5;
            --border-color: #e0e0e0;
            --text-color: #333333;
        }
    }

    /* Animações suaves */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .fade-in-details {
        animation: fadeIn 0.3s ease-out;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # CSS do tema principal
    is_modo_claro = st.session_state.get("tema", "escuro") == "claro"
    
    if is_modo_claro:
        texto_previa = "#212529"
        fundo_previa = "#ffffff"
        borda_previa = "#dee2e6"
    else:
        texto_previa = "#f0f0f0"
        fundo_previa = "#1e1e1e"
        borda_previa = "#333"
    
    st.markdown(f"""
    <style>
    /* Reset e base */
    * {{
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }}
    
    .stApp {{
        background-color: {cores['fundo']};
        color: {cores['texto']};
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }}
    
    /* Garantir que TODO o texto tenha contraste adequado */
    *:not(button):not(.stButton > button):not([kind="primary"]):not([kind="secondary"]) {{
        color: {cores['texto']} !important;
    }}
    
    /* Headers - força cor do tema */
    h1, h2, h3, h4, h5, h6 {{
        font-weight: 600;
        margin-bottom: 1rem;
        color: {cores['texto']} !important;
    }}
    
    h1 {{ font-size: 2.5rem; }}
    h2 {{ font-size: 2rem; }}
    h3 {{ font-size: 1.75rem; }}
    h4 {{ font-size: 1.5rem; }}
    
    /* Parágrafos, spans, labels - força cor do tema */
    p, span, label, div, small, caption {{
        color: {cores['texto']} !important;
    }}
    
    /* Texto dentro de containers especiais */
    .config-card, .card, .item-historico, .card-detalhe {{
        color: {cores['texto']} !important;
    }}
    
    .config-card p, .config-card h4, .config-card div, 
    .card p, .card h4, .card div,
    .item-historico p, .item-historico h4, .item-historico div,
    .card-detalhe p, .card-detalhe h4, .card-detalhe div {{
        color: {cores['texto']} !important;
    }}
    
    /* Área de pré-visualização com cores fixas para bom contraste */
    .preview-area {{
        background-color: {fundo_previa} !important;
        color: {texto_previa} !important;
        border: 1px solid {borda_previa} !important;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }}
    
    .preview-area p, .preview-area div, .preview-area span {{
        color: {texto_previa} !important;
    }}
    
    /* Informações sobre moeda */
    .currency-note {{
        background-color: {cores['info']}15 !important;
        border-left: 4px solid {cores['info']} !important;
        color: {cores['texto']} !important;
    }}
    
    .currency-note p, .currency-note strong {{
        color: {cores['texto']} !important;
    }}
    
    /* Sidebar */
    .stSidebar {{
        background-color: {cores['sidebar']};
        border-right: 1px solid {cores['borda']};
    }}
    
    /* Texto na sidebar */
    .stSidebar h1, .stSidebar h2, .stSidebar h3,
    .stSidebar p, .stSidebar span, .stSidebar div,
    .stSidebar label {{
        color: {cores['texto']} !important;
    }}
    
    /* Botões */
    .stButton > button {{
        border-radius: 8px;
        font-weight: 600;
        border: 1px solid {cores['borda']};
        background-color: {cores['botao_fundo']} !important;
        color: {cores['botao_texto']} !important;
        transition: all 0.3s ease;
        padding: 0.5rem 1rem;
    }}
    
    .stButton > button:hover {{
        background-color: {cores['botao_hover']} !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }}
    
    .stButton > button[kind="primary"] {{
        background: {cores['botao_primary_gradient']} !important;
        color: white !important;
        border: none !important;
    }}
    
    .stButton > button[kind="primary"]:hover {{
        background: {cores['botao_primary_hover']} !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(61, 139, 253, 0.3);
    }}
    
    .stButton > button[kind="secondary"] {{
        background-color: transparent !important;
        border: 2px solid {cores['destaque']} !important;
        color: {cores['destaque']} !important;
    }}
    
    .stButton > button[kind="secondary"]:hover {{
        background-color: {cores['destaque']}20 !important;
    }}
    
    /* Cards */
    .card {{
        background-color: {cores['card']};
        color: {cores['texto']} !important;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid {cores['borda']};
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }}
    
    .card:hover {{
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
        transform: translateY(-2px);
    }}
    
    .login-container {{
        max-width: 420px;
        margin: 2rem auto;
        padding: 2.5rem;
        border-radius: 20px;
        background: {cores['gradiente_login']};
        border: 1px solid {cores['borda']};
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    }}
    
    .item-historico {{
        background-color: {cores['card']};
        padding: 1.25rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border: 1px solid {cores['borda']};
        transition: all 0.3s ease;
    }}
    
    .item-historico:hover {{
        border-color: {cores['destaque']};
        box-shadow: 0 4px 12px rgba(61, 139, 253, 0.1);
    }}
    
    .config-card {{
        background-color: {cores['card']};
        color: {cores['texto']} !important;
        padding: 1.75rem;
        border-radius: 12px;
        border: 2px solid {cores['borda']};
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }}
    
    .valor-destaque {{
        background: {cores['botao_primary_gradient']};
        color: white;
        padding: 2.5rem;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 8px 25px rgba(61, 139, 253, 0.3);
        margin: 2rem 0;
    }}
    
    .card-detalhe {{
        background: {cores['fundo_card']};
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid {cores['borda']};
        height: 100%;
    }}
    
    .badge {{
        background-color: {cores['destaque']};
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }}
    
    /* Inputs - garantir texto visível */
    div[data-testid="stTextInput"] > div > div > input {{
        background-color: {cores['card']} !important;
        color: {cores['texto']} !important;
        border: 2px solid {cores['borda']} !important;
        border-radius: 8px !important;
        padding: 12px 14px !important;
        font-size: 1rem;
    }}
    
    div[data-testid="stTextInput"] > div > div > input:focus {{
        border-color: {cores['destaque']} !important;
        box-shadow: 0 0 0 3px {cores['destaque']}20 !important;
    }}
    
    div[data-testid="stSelectbox"] > div > div,
    div[data-testid="stSelectbox"] > div > div > div {{
        background-color: {cores['card']} !important;
        color: {cores['texto']} !important;
        border: 2px solid {cores['borda']} !important;
        border-radius: 8px !important;
    }}
    
    div[data-testid="stNumberInput"] > div > div > input {{
        background-color: {cores['card']} !important;
        color: {cores['texto']} !important;
        border: 2px solid {cores['borda']} !important;
        border-radius: 8px !important;
    }}
    
    /* Labels dos inputs */
    label, .stTextInput > label, .stNumberInput > label, 
    .stSelectbox > label, .stRadio > label, .stCheckbox > label {{
        color: {cores['texto']} !important;
    }}
    
    input::placeholder {{
        color: {cores['texto']}60 !important;
    }}
    
    /* Radio buttons e checkboxes */
    .stRadio > div, .stCheckbox > div {{
        color: {cores['texto']} !important;
    }}
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        border-bottom: 1px solid {cores['borda']};
    }}
    
    .stTabs [data-baseweb="tab"] {{
        color: {cores['texto']} !important;
    }}
    
    .stTabs [aria-selected="true"] {{
        color: {cores['destaque']} !important;
        border-bottom: 2px solid {cores['destaque']};
    }}
    
    /* Indicador de segurança */
    .security-indicator {{
        position: fixed;
        bottom: 15px;
        right: 15px;
        background: {cores['success']};
        color: white;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 600;
        z-index: 9999;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    
    /* Mensagens de segurança */
    .security-alert {{
        background: linear-gradient(135deg, #ff980020, #f4433620);
        border-left: 4px solid {cores['error']};
        padding: 1.25rem;
        margin: 1.25rem 0;
        border-radius: 0 8px 8px 0;
    }}
    
    .security-success {{
        background: linear-gradient(135deg, #4CAF5020, #2E7D3220);
        border-left: 4px solid {cores['success']};
        padding: 1.25rem;
        margin: 1.25rem 0;
        border-radius: 0 8px 8px 0;
    }}
    
    .security-info {{
        background: linear-gradient(135deg, #2196F320, #1976D220);
        border-left: 4px solid {cores['info']};
        padding: 1.25rem;
        margin: 1.25rem 0;
        border-radius: 0 8px 8px 0;
    }}
    
    /* Progress bar */
    .stProgress > div > div > div {{
        background: {cores['botao_primary_gradient']};
    }}
    
    /* Expander */
    .streamlit-expanderHeader {{
        background-color: {cores['card']} !important;
        color: {cores['texto']} !important;
        border: 1px solid {cores['borda']} !important;
        border-radius: 8px !important;
    }}
    
    .streamlit-expanderContent {{
        background-color: {cores['card']} !important;
        color: {cores['texto']} !important;
    }}
    
    /* Tooltips */
    [data-testid="stTooltip"] {{
        background-color: {cores['card']} !important;
        color: {cores['texto']} !important;
        border: 1px solid {cores['borda']} !important;
    }}
    
    /* Responsividade */
    @media (max-width: 768px) {{
        .login-container {{
            margin: 1rem;
            padding: 1.5rem;
        }}
        
        h1 {{ font-size: 2rem; }}
        h2 {{ font-size: 1.75rem; }}
        h3 {{ font-size: 1.5rem; }}
    }}
    
    /* Animações sutis */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    
    .fade-in {{
        animation: fadeIn 0.5s ease-out;
    }}
    
    /* Classes específicas para pré-visualização */
    .theme-preview-dark {{
        background-color: #1e1e1e !important;
        color: #f0f0f0 !important;
        border: 1px solid #333 !important;
    }}
    
    .theme-preview-light {{
        background-color: #ffffff !important;
        color: #212529 !important;
        border: 1px solid #dee2e6 !important;
    }}
    
    /* Garantir que texto dentro de expanders seja visível */
    .streamlit-expanderContent p,
    .streamlit-expanderContent span,
    .streamlit-expanderContent div,
    .streamlit-expanderContent li {{
        color: {cores['texto']} !important;
    }}
    
    </style>
    """, unsafe_allow_html=True)
    
    # Indicador de segurança
    if st.session_state.get('security_level'):
        st.markdown(f"""
        <div class="security-indicator fade-in">
            🔒 {st.session_state.get('security_level', 'Seguro')}
            <span style="font-size: 0.75rem; opacity: 0.9;">{datetime.now().strftime('%H:%M')}</span>
        </div>
        """, unsafe_allow_html=True)

# ============= TESTE DO MÓDULO =============
if __name__ == "__main__":
    """Teste do módulo utils"""
    print("=== Teste do módulo utils ===")
    st.set_page_config(layout="wide")
    
    # Testar get_colors
    st.session_state.tema = "escuro"
    cores_escuro = get_colors()
    print(f"✅ Cores modo escuro: {len(cores_escuro)} cores definidas")
    
    st.session_state.tema = "claro"
    cores_claro = get_colors()
    print(f"✅ Cores modo claro: {len(cores_claro)} cores definidas")
    
    # Testar aplicar_css
    aplicar_css()
    print("✅ CSS aplicado com sucesso")
    
    print("✅ Módulo utils testado com sucesso!")