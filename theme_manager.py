"""
theme_manager.py - Gerenciador de Temas e Cores DBMILESX
Sistema completo de gerenciamento de temas com suporte a cores personalizadas
"""

import streamlit as st
import json
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass


logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTES E TEMAS PRÉ-DEFINIDOS
# ============================================================================

class ThemeMode(Enum):
    LIGHT = "claro"
    DARK = "escuro"
    SYSTEM = "sistema"


class ThemePreset(Enum):
    DEFAULT = "default"
    DARK_BLUE = "dark_blue"
    LIGHT_BLUE = "light_blue"
    DARK_GREEN = "dark_green"
    DARK_PURPLE = "dark_purple"
    AMBER = "amber"
    HIGH_CONTRAST = "high_contrast"


# Cores pré-definidas para a grade - ORGANIZADAS POR FAMÍLIA
PREDEFINED_COLORS = [
    # Azuis (Família 1)
    {'name': 'Azul DBMILESX', 'primary': '#3d8bfd', 'secondary': '#5c9cff', 'family': 'Azuis'},
    {'name': 'Azul Escuro', 'primary': '#2563eb', 'secondary': '#3b82f6', 'family': 'Azuis'},
    {'name': 'Azul Claro', 'primary': '#60a5fa', 'secondary': '#93c5fd', 'family': 'Azuis'},
    {'name': 'Azul Petróleo', 'primary': '#0f4c5c', 'secondary': '#1e6f8f', 'family': 'Azuis'},
    {'name': 'Azul Cobalto', 'primary': '#1e3a8a', 'secondary': '#1d4ed8', 'family': 'Azuis'},
    
    # Roxos (Família 2)
    {'name': 'Roxo Royal', 'primary': '#8b5cf6', 'secondary': '#a78bfa', 'family': 'Roxos'},
    {'name': 'Roxo Vibrante', 'primary': '#a855f7', 'secondary': '#c084fc', 'family': 'Roxos'},
    {'name': 'Roxo Lavanda', 'primary': '#9b87f5', 'secondary': '#b8a9f8', 'family': 'Roxos'},
    {'name': 'Roxo Escuro', 'primary': '#6b21a8', 'secondary': '#7e22ce', 'family': 'Roxos'},
    
    # Verdes (Família 3)
    {'name': 'Verde Esmeralda', 'primary': '#10b981', 'secondary': '#34d399', 'family': 'Verdes'},
    {'name': 'Verde Limão', 'primary': '#84cc16', 'secondary': '#a3e635', 'family': 'Verdes'},
    {'name': 'Verde Floresta', 'primary': '#2d6a4f', 'secondary': '#40916c', 'family': 'Verdes'},
    {'name': 'Verde Água', 'primary': '#14b8a6', 'secondary': '#2dd4bf', 'family': 'Verdes'},
    
    # Laranjas/Vermelhos (Família 4)
    {'name': 'Laranja Vibrante', 'primary': '#f97316', 'secondary': '#fb923c', 'family': 'Laranjas'},
    {'name': 'Vermelho Rubi', 'primary': '#ef4444', 'secondary': '#f87171', 'family': 'Vermelhos'},
    {'name': 'Vermelho Escuro', 'primary': '#b91c1c', 'secondary': '#dc2626', 'family': 'Vermelhos'},
    {'name': 'Laranja Queimado', 'primary': '#c2410c', 'secondary': '#ea580c', 'family': 'Laranjas'},
    
    # Tons Neutros (Família 5)
    {'name': 'Grafite', 'primary': '#4b5563', 'secondary': '#6b7280', 'family': 'Neutros'},
    {'name': 'Cinza Azulado', 'primary': '#475569', 'secondary': '#64748b', 'family': 'Neutros'},
    {'name': 'Cinza Escuro', 'primary': '#374151', 'secondary': '#4b5563', 'family': 'Neutros'},
    
    # Cores Especiais (Família 6)
    {'name': 'Rosa', 'primary': '#ec4899', 'secondary': '#f472b6', 'family': 'Rosa'},
    {'name': 'Turquesa', 'primary': '#14b8a6', 'secondary': '#2dd4bf', 'family': 'Turquesa'},
    {'name': 'Amarelo', 'primary': '#eab308', 'secondary': '#facc15', 'family': 'Amarelos'},
    {'name': 'Índigo', 'primary': '#6366f1', 'secondary': '#818cf8', 'family': 'Índigo'},
]

COLORS_BY_FAMILY = {}
for color in PREDEFINED_COLORS:
    family = color['family']
    if family not in COLORS_BY_FAMILY:
        COLORS_BY_FAMILY[family] = []
    COLORS_BY_FAMILY[family].append(color)


# Temas pré-definidos completos
PRESET_THEMES = {
    ThemePreset.DEFAULT: {
        "id": "default",
        "nome": "DBMILESX Padrão",
        "descricao": "Tema original do DBMILESX",
        "icone": "✈️",
        "modo": "escuro",
        "cores": {
            "primaria": "#3d8bfd",
            "secundaria": "#5c9cff",
            "destaque": "#3d8bfd",
            "fundo": "#0e0e0e",
            "card": "#1e1e1e",
            "texto": "#ffffff",
            "borda": "#333333",
            "sucesso": "#4CAF50",
            "erro": "#f44336",
            "aviso": "#ff9800",
            "info": "#2196F3"
        }
    },
    ThemePreset.DARK_BLUE: {
        "id": "dark_blue",
        "nome": "Azul Profundo",
        "descricao": "Tema escuro com tons de azul",
        "icone": "🔵",
        "modo": "escuro",
        "cores": {
            "primaria": "#1E88E5",
            "secundaria": "#42A5F5",
            "destaque": "#1E88E5",
            "fundo": "#0a0e27",
            "card": "#1a1f3a",
            "texto": "#ffffff",
            "borda": "#2a2f4a",
            "sucesso": "#4CAF50",
            "erro": "#f44336",
            "aviso": "#ff9800",
            "info": "#2196F3"
        }
    },
    ThemePreset.LIGHT_BLUE: {
        "id": "light_blue",
        "nome": "Azul Claro",
        "descricao": "Tema claro com tons de azul",
        "icone": "☀️",
        "modo": "claro",
        "cores": {
            "primaria": "#1976D2",
            "secundaria": "#42A5F5",
            "destaque": "#1976D2",
            "fundo": "#f5f5f5",
            "card": "#ffffff",
            "texto": "#333333",
            "borda": "#e0e0e0",
            "sucesso": "#4CAF50",
            "erro": "#f44336",
            "aviso": "#ff9800",
            "info": "#2196F3"
        }
    },
    ThemePreset.DARK_GREEN: {
        "id": "dark_green",
        "nome": "Verde Floresta",
        "descricao": "Tema escuro com tons verdes",
        "icone": "🌲",
        "modo": "escuro",
        "cores": {
            "primaria": "#2E7D32",
            "secundaria": "#43A047",
            "destaque": "#2E7D32",
            "fundo": "#0a1a0a",
            "card": "#1a2a1a",
            "texto": "#ffffff",
            "borda": "#2a3a2a",
            "sucesso": "#4CAF50",
            "erro": "#f44336",
            "aviso": "#ff9800",
            "info": "#2196F3"
        }
    },
    ThemePreset.DARK_PURPLE: {
        "id": "dark_purple",
        "nome": "Roxo Royal",
        "descricao": "Tema escuro com tons roxos",
        "icone": "🟣",
        "modo": "escuro",
        "cores": {
            "primaria": "#7B1FA2",
            "secundaria": "#9C27B0",
            "destaque": "#7B1FA2",
            "fundo": "#0a0a1a",
            "card": "#1a1a2a",
            "texto": "#ffffff",
            "borda": "#2a2a3a",
            "sucesso": "#4CAF50",
            "erro": "#f44336",
            "aviso": "#ff9800",
            "info": "#2196F3"
        }
    },
    ThemePreset.AMBER: {
        "id": "amber",
        "nome": "Âmbar",
        "descricao": "Tema escuro com tons âmbar",
        "icone": "🟠",
        "modo": "escuro",
        "cores": {
            "primaria": "#FF8F00",
            "secundaria": "#FFA726",
            "destaque": "#FF8F00",
            "fundo": "#1a0a00",
            "card": "#2a1a0a",
            "texto": "#ffffff",
            "borda": "#3a2a1a",
            "sucesso": "#4CAF50",
            "erro": "#f44336",
            "aviso": "#ff9800",
            "info": "#2196F3"
        }
    },
    ThemePreset.HIGH_CONTRAST: {
        "id": "high_contrast",
        "nome": "Alto Contraste",
        "descricao": "Tema de alto contraste para acessibilidade",
        "icone": "♿",
        "modo": "escuro",
        "cores": {
            "primaria": "#FFFF00",
            "secundaria": "#00FF00",
            "destaque": "#FFFF00",
            "fundo": "#000000",
            "card": "#000000",
            "texto": "#FFFFFF",
            "borda": "#FFFFFF",
            "sucesso": "#00FF00",
            "erro": "#FF0000",
            "aviso": "#FFFF00",
            "info": "#00FFFF"
        }
    }
}


# ============================================================================
# CLASSE THEME
# ============================================================================

@dataclass
class Theme:
    """Classe que representa um tema completo"""
    id: str
    nome: str
    descricao: str
    icone: str
    modo: str
    cores: Dict[str, str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'icone': self.icone,
            'modo': self.modo,
            'cores': self.cores,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Theme':
        return cls(
            id=data.get('id', 'custom'),
            nome=data.get('nome', 'Tema Personalizado'),
            descricao=data.get('descricao', 'Tema personalizado pelo usuário'),
            icone=data.get('icone', '🎨'),
            modo=data.get('modo', 'escuro'),
            cores=data.get('cores', {}),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )


# ============================================================================
# CLASS THEME_MANAGER
# ============================================================================

class ThemeManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._current_theme: Optional[Theme] = None
        self._custom_themes: List[Theme] = []
        logger.info("🎨 ThemeManager inicializado")
    
    def get_todos_temas(self) -> List[Theme]:
        temas = []
        for preset, data in PRESET_THEMES.items():
            temas.append(Theme(
                id=data['id'],
                nome=data['nome'],
                descricao=data['descricao'],
                icone=data['icone'],
                modo=data['modo'],
                cores=data['cores']
            ))
        temas.extend(self._custom_themes)
        return temas
    
    def get_tema(self, theme_id: str) -> Optional[Theme]:
        for preset, data in PRESET_THEMES.items():
            if data['id'] == theme_id:
                return Theme(
                    id=data['id'],
                    nome=data['nome'],
                    descricao=data['descricao'],
                    icone=data['icone'],
                    modo=data['modo'],
                    cores=data['cores']
                )
        for theme in self._custom_themes:
            if theme.id == theme_id:
                return theme
        return None
    
    def aplicar_tema(self, theme: Theme):
        self._current_theme = theme
        st.session_state.tema = theme.modo
        st.session_state.tema_id = theme.id
        st.session_state.tema_nome = theme.nome
        st.session_state.cor_primaria = theme.cores.get('primaria', '#3d8bfd')
        
        for key, value in theme.cores.items():
            st.session_state[f'cor_{key}'] = value
        
        aplicar_css_completo()
        logger.info(f"✅ Tema '{theme.nome}' aplicado")
    
    def aplicar_tema_customizado(self, modo: str, cor_primaria: str, cores_extra: Optional[Dict] = None):
        st.session_state.tema = modo
        st.session_state.cor_primaria = cor_primaria
        
        cores = self._gerar_cores_tema(modo, cor_primaria, cores_extra)
        for key, value in cores.items():
            st.session_state[f'cor_{key}'] = value
        
        aplicar_css_completo()
    
    def _gerar_cores_tema(self, modo: str, cor_primaria: str, cores_extra: Optional[Dict] = None) -> Dict[str, str]:
        if modo == "claro":
            base = {
                'fundo': '#f5f7fa',
                'fundo_sidebar': '#ffffff',
                'card': '#ffffff',
                'card_hover': '#f8f9fa',
                'texto': '#1a1a2e',
                'texto_secundario': '#4a5568',
                'borda': '#e2e8f0',
                'borda_foco': cor_primaria,
                'input_bg': '#ffffff',
                'input_border': '#cbd5e1',
                'placeholder': '#94a3b8',
                'botao_secondary_bg': '#f1f5f9',
                'botao_secondary_hover': '#e2e8f0',
                'menu_hover': '#eef2ff'
            }
        else:
            base = {
                'fundo': '#0a0a0f',
                'fundo_sidebar': '#111118',
                'card': '#1a1a2e',
                'card_hover': '#16213e',
                'texto': '#f0f0f0',
                'texto_secundario': '#a0a0b0',
                'borda': '#2a2a3e',
                'borda_foco': cor_primaria,
                'input_bg': '#0f0f1a',
                'input_border': '#2a2a3e',
                'placeholder': '#6a6a7a',
                'botao_secondary_bg': '#2a2a3e',
                'botao_secondary_hover': '#3a3a4e',
                'menu_hover': '#2a2a4e'
            }
        
        base['destaque'] = cor_primaria
        base['destaque_hover'] = self._darken_color(cor_primaria, 15)
        base['botao_primary_gradient'] = f'linear-gradient(135deg, {cor_primaria}, {self._darken_color(cor_primaria, 15)})'
        base['botao_primary_hover'] = f'linear-gradient(135deg, {self._darken_color(cor_primaria, 15)}, {self._darken_color(cor_primaria, 25)})'
        
        base['success'] = '#4CAF50' if modo == 'escuro' else '#28a745'
        base['error'] = '#f44336' if modo == 'escuro' else '#dc3545'
        base['warning'] = '#ff9800' if modo == 'escuro' else '#ffc107'
        base['info'] = '#2196F3' if modo == 'escuro' else '#17a2b8'
        
        return base
    
    def _darken_color(self, color: str, percent: int) -> str:
        try:
            color = color.lstrip('#')
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            r = max(0, r - (r * percent // 100))
            g = max(0, g - (g * percent // 100))
            b = max(0, b - (b * percent // 100))
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return color
    
    def criar_tema_personalizado(self, nome: str, modo: str, cores: Dict[str, str]) -> Optional[Theme]:
        theme = Theme(
            id=f"custom_{datetime.now().timestamp()}",
            nome=nome,
            descricao="Tema personalizado",
            icone="🎨",
            modo=modo,
            cores=cores,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        self._custom_themes.append(theme)
        return theme


# ============================================================================
# FUNÇÕES DE UTILIDADE
# ============================================================================

def get_theme_manager() -> ThemeManager:
    if 'theme_manager' not in st.session_state:
        st.session_state.theme_manager = ThemeManager()
    return st.session_state.theme_manager


def get_cores():
    """Retorna as cores do tema atual - COMPLETO para toda interface"""
    tema = st.session_state.get("tema", "escuro")
    cor_primaria = st.session_state.get("cor_primaria", "#3d8bfd")
    
    if tema == "claro":
        return {
            'fundo': '#f5f7fa',
            'sidebar': '#ffffff',
            'card': '#ffffff',
            'card_hover': '#f8f9fa',
            'texto': '#1a1a2e',
            'texto_secundario': '#4a5568',
            'destaque': cor_primaria,
            'destaque_hover': '#2a5cbd',
            'borda': '#e2e8f0',
            'borda_foco': cor_primaria,
            'hover': '#f1f5f9',
            'fundo_card': '#ffffff',
            'texto_claro': '#ffffff',
            'texto_escuro': '#1a1a2e',
            'success': '#28a745',
            'warning': '#ffc107',
            'error': '#dc3545',
            'info': '#17a2b8',
            'input_bg': '#ffffff',
            'input_border': '#cbd5e1',
            'placeholder': '#94a3b8',
            'botao_fundo': '#f1f5f9',
            'botao_texto': '#1a1a2e',
            'botao_hover': '#e2e8f0',
            'botao_secondary_bg': '#f1f5f9',
            'botao_secondary_hover': '#e2e8f0',
            'botao_primary_gradient': f'linear-gradient(135deg, {cor_primaria}, #2a5cbd)',
            'botao_primary_hover': 'linear-gradient(135deg, #2a5cbd, #1e4a9e)',
            'gradiente_login': 'linear-gradient(135deg, #f5f7fa, #ffffff)'
        }
    else:
        return {
            'fundo': '#0a0a0f',
            'sidebar': '#111118',
            'card': '#1a1a2e',
            'card_hover': '#16213e',
            'texto': '#f0f0f0',
            'texto_secundario': '#a0a0b0',
            'destaque': cor_primaria,
            'destaque_hover': '#5c9cff',
            'borda': '#2a2a3e',
            'borda_foco': cor_primaria,
            'hover': '#1e1e3a',
            'fundo_card': '#1a1a2e',
            'texto_claro': '#ffffff',
            'texto_escuro': '#0a0a0f',
            'success': '#4CAF50',
            'warning': '#ff9800',
            'error': '#f44336',
            'info': '#2196F3',
            'input_bg': '#0f0f1a',
            'input_border': '#2a2a3e',
            'placeholder': '#6a6a7a',
            'botao_fundo': '#2a2a3e',
            'botao_texto': '#f0f0f0',
            'botao_hover': '#3a3a4e',
            'botao_secondary_bg': '#2a2a3e',
            'botao_secondary_hover': '#3a3a4e',
            'botao_primary_gradient': f'linear-gradient(135deg, {cor_primaria}, #2a5cbd)',
            'botao_primary_hover': 'linear-gradient(135deg, #2a5cbd, #1e4a9e)',
            'gradiente_login': 'linear-gradient(135deg, #0a0a0f, #111118)'
        }


def get_cores_completas():
    """Alias para get_cores - mantido para compatibilidade"""
    return get_cores()


def aplicar_css_completo():
    """Aplica CSS completo com as cores do tema em TODOS os elementos"""
    cores = get_cores()
    cor_primaria = cores['destaque']
    
    css = f"""
    <style>
    /* ===== FUNDO PRINCIPAL ===== */
    .stApp, .stApp > div, div[data-testid="stAppViewContainer"],
    div[data-testid="stAppViewBlockContainer"], .main .block-container,
    section.main, .st-emotion-cache-1v0mbdj, .st-emotion-cache-6qob1r {{
        background-color: {cores['fundo']} !important;
        background: {cores['fundo']} !important;
    }}
    
    /* ===== SIDEBAR ===== */
    .stSidebar, .stSidebar > div, .st-emotion-cache-1y4p8pa,
    section[data-testid="stSidebar"] {{
        background-color: {cores['sidebar']} !important;
        background: {cores['sidebar']} !important;
        border-right: 1px solid {cores['borda']} !important;
    }}
    
    /* ===== TEXTOS GLOBAIS ===== */
    body, p, h1, h2, h3, h4, h5, h6, label, span, div, 
    .stMarkdown, .stTextInput, .stNumberInput, .stDateInput,
    .stTextArea, .stCheckbox, .stSelectbox,
    .st-emotion-cache-10trblm, .st-emotion-cache-1v0mbdj {{
        color: {cores['texto']} !important;
    }}
    
    /* Textos secundários */
    .st-caption, .st-emotion-cache-16idsys p, small,
    .st-emotion-cache-1y4p8pa p {{
        color: {cores['texto_secundario']} !important;
    }}
    
    /* ===== CARD CONTAINERS ===== */
    div[data-testid="stVerticalBlock"] > div,
    .element-container, .stMarkdown, .stAlert {{
        background-color: transparent !important;
    }}
    
    /* ===== INPUTS ===== */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select,
    input, textarea, select {{
        background-color: {cores['input_bg']} !important;
        color: {cores['texto']} !important;
        border: 1px solid {cores['input_border']} !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
    }}
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stDateInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: {cores['borda_foco']} !important;
        box-shadow: 0 0 0 3px {cor_primaria}20 !important;
        outline: none !important;
    }}
    
    input::placeholder, textarea::placeholder {{
        color: {cores['placeholder']} !important;
    }}
    
    /* ===== BOTÕES ===== */
    .stButton > button {{
        background: {cores['botao_secondary_bg']} !important;
        color: {cores['botao_texto']} !important;
        border: 1px solid {cores['borda']} !important;
        border-radius: 10px !important;
        padding: 8px 16px !important;
        transition: all 0.2s ease !important;
    }}
    
    .stButton > button:hover {{
        background: {cores['botao_secondary_hover']} !important;
        transform: translateY(-1px);
    }}
    
    .stButton > button[kind="primary"] {{
        background: {cores['botao_primary_gradient']} !important;
        color: white !important;
        border: none !important;
    }}
    
    .stButton > button[kind="primary"]:hover {{
        background: {cores['botao_primary_hover']} !important;
        transform: translateY(-1px);
    }}
    
    /* ===== CHECKBOXES ===== */
    div[data-testid="stCheckbox"] {{
        background-color: {cores['card']} !important;
        border: 1px solid {cores['borda']} !important;
        border-radius: 10px !important;
        padding: 12px 16px !important;
        margin: 8px 0 !important;
    }}
    
    div[data-testid="stCheckbox"]:hover {{
        background-color: {cores['card_hover']} !important;
        border-color: {cor_primaria} !important;
    }}
    
    div[data-testid="stCheckbox"] label {{
        color: {cores['texto']} !important;
    }}
    
    /* ===== RADIO BUTTONS ===== */
    .stRadio > div {{
        gap: 16px !important;
    }}
    
    .stRadio label {{
        background-color: {cores['card']} !important;
        border: 1px solid {cores['borda']} !important;
        border-radius: 10px !important;
        padding: 10px 20px !important;
        cursor: pointer !important;
    }}
    
    .stRadio label:hover {{
        background-color: {cores['card_hover']} !important;
    }}
    
    /* ===== SELECTBOX ===== */
    .stSelectbox > div > div {{
        background-color: {cores['input_bg']} !important;
        border: 1px solid {cores['input_border']} !important;
        border-radius: 10px !important;
    }}
    
    /* ===== EXPANDER ===== */
    .streamlit-expanderHeader {{
        background-color: {cores['card']} !important;
        color: {cores['texto']} !important;
        border: 1px solid {cores['borda']} !important;
        border-radius: 10px !important;
    }}
    
    .streamlit-expanderContent {{
        background-color: {cores['card']} !important;
        border: 1px solid {cores['borda']} !important;
        border-top: none !important;
        border-radius: 0 0 10px 10px !important;
    }}
    
    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px !important;
        background-color: {cores['fundo']} !important;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        background-color: {cores['card']} !important;
        color: {cores['texto']} !important;
        border-radius: 10px !important;
        padding: 8px 20px !important;
        border: 1px solid {cores['borda']} !important;
    }}
    
    .stTabs [aria-selected="true"] {{
        background-color: {cor_primaria} !important;
        color: white !important;
        border-color: {cor_primaria} !important;
    }}
    
    /* ===== METRIC CARDS ===== */
    div[data-testid="stMetric"] {{
        background-color: {cores['card']} !important;
        border: 1px solid {cores['borda']} !important;
        border-radius: 12px !important;
        padding: 16px !important;
    }}
    
    div[data-testid="stMetric"] label {{
        color: {cores['texto_secundario']} !important;
    }}
    
    /* ===== ALERTAS ===== */
    .stAlert {{
        background-color: {cores['card']} !important;
        border: 1px solid {cores['borda']} !important;
        border-radius: 10px !important;
    }}
    
    /* ===== DROPDOWN MENU ===== */
    div[data-baseweb="popover"] {{
        background-color: {cores['card']} !important;
        border: 1px solid {cores['borda']} !important;
        border-radius: 10px !important;
    }}
    
    /* ===== CARDS - classes customizadas ===== */
    .card, .config-card, .item-historico, .card-detalhe {{
        background-color: {cores['card']} !important;
        border: 1px solid {cores['borda']} !important;
        border-radius: 12px !important;
        padding: 20px !important;
        margin-bottom: 16px !important;
    }}
    
    /* ===== CALENDÁRIO - DATAS PASSADAS ===== */
    /* Datas que já passaram - FICAM CLARAS/ACINZENTADAS */
    div[data-baseweb="calendar"] [aria-disabled="true"],
    div[data-baseweb="calendar"] [role="gridcell"][aria-disabled="true"],
    div[data-baseweb="calendar"] button:disabled,
    div[data-baseweb="calendar"] [data-baseweb="day"][aria-disabled="true"] {{
        background-color: #e0e0e0 !important;
        color: #999999 !important;
        cursor: not-allowed !important;
        opacity: 0.6 !important;
        pointer-events: none !important;
    }}
    
    /* Dias do calendário que NÃO estão desabilitados (futuros) - FICAM NORMAIS/ESCUROS */
    div[data-baseweb="calendar"] button:not(:disabled),
    div[data-baseweb="calendar"] [data-baseweb="day"]:not([aria-disabled="true"]) {{
        background-color: {cores['card']} !important;
        color: {cores['texto']} !important;
        cursor: pointer !important;
        font-weight: normal !important;
    }}
    
    /* Hover dos dias futuros */
    div[data-baseweb="calendar"] button:not(:disabled):hover,
    div[data-baseweb="calendar"] [data-baseweb="day"]:not([aria-disabled="true"]):hover {{
        background-color: {cor_primaria} !important;
        color: white !important;
        transform: scale(1.05);
        transition: all 0.2s ease;
    }}
    
    /* Dia selecionado */
    div[data-baseweb="calendar"] [aria-selected="true"],
    div[data-baseweb="calendar"] [data-baseweb="day"][aria-selected="true"] {{
        background-color: {cor_primaria} !important;
        color: white !important;
        font-weight: bold !important;
        border-radius: 50% !important;
    }}
    
    /* Cabeçalho do calendário */
    div[data-baseweb="calendar"] div[role="heading"] {{
        font-weight: bold !important;
        color: {cores['texto']} !important;
    }}
    
    /* Botões de navegação do calendário */
    div[data-baseweb="calendar"] button[data-baseweb="icon"] {{
        color: {cor_primaria} !important;
        background-color: transparent !important;
    }}
    
    /* ===== TÍTULOS ===== */
    h1, h2, h3, h4 {{
        color: {cor_primaria} !important;
    }}
    
    .public-header h1 {{
        color: {cor_primaria} !important;
    }}
    
    /* ===== LINKS ===== */
    a {{
        color: {cor_primaria} !important;
        text-decoration: none !important;
    }}
    
    a:hover {{
        color: {cores['destaque_hover']} !important;
        text-decoration: underline !important;
    }}
    
    /* ===== HORIZONTAL LINE ===== */
    hr {{
        border-color: {cores['borda']} !important;
        margin: 20px 0 !important;
    }}
    
    /* ===== CÓDIGO ===== */
    code {{
        background-color: {cores['input_bg']} !important;
        color: {cor_primaria} !important;
        border-radius: 6px !important;
        padding: 2px 6px !important;
    }}
    
    /* ===== DATA TABLE ===== */
    .dataframe, table {{
        background-color: {cores['card']} !important;
        color: {cores['texto']} !important;
        border-color: {cores['borda']} !important;
    }}
    
    /* ===== PROGRESS BAR ===== */
    .stProgress > div > div > div > div {{
        background-color: {cor_primaria} !important;
    }}
    
    /* ===== SLIDER ===== */
    .stSlider > div > div > div > div {{
        background-color: {cor_primaria} !important;
    }}
    
    /* ===== INFO/WARNING/ERROR BOXES ===== */
    .stAlert[data-baseweb="notification"] {{
        background-color: {cores['card']} !important;
    }}
    
    /* ===== DIVIDERS ===== */
    .stDivider {{
        border-color: {cores['borda']} !important;
    }}
    
    @media (max-width: 768px) {{
        .card, .config-card {{
            padding: 12px !important;
        }}
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def botao_recarregar_pagina():
    """Botão para recarregar a página com indicador visual"""
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("🔄 Recarregar Página", type="primary", use_container_width=True):
            st.rerun()
    with col2:
        tema = st.session_state.get("tema", "escuro")
        if tema == "claro":
            st.markdown("""
            <div style="background: linear-gradient(135deg, #f5f7fa, #e2e8f0); 
                        padding: 8px 16px; border-radius: 10px; text-align: center;">
                <small>☀️ Modo Claro</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #1a1a2e, #0a0a0f); 
                        padding: 8px 16px; border-radius: 10px; text-align: center;">
                <small>🌙 Modo Escuro</small>
            </div>
            """, unsafe_allow_html=True)


def aplicar_tema_atual():
    """Aplica o tema atual do sistema"""
    manager = get_theme_manager()
    
    # Verificar se deve seguir tema do sistema
    if st.session_state.get('seguir_sistema', False):
        hora = datetime.now().hour
        modo = 'escuro' if hora < 6 or hora > 18 else 'claro'
        st.session_state.tema = modo
    
    # Obter tema salvo
    theme_id = st.session_state.get('tema_id', 'default')
    theme = manager.get_tema(theme_id)
    
    if theme:
        manager.aplicar_tema(theme)
    else:
        cor_primaria = st.session_state.get('cor_primaria', '#3d8bfd')
        modo = st.session_state.get('tema', 'escuro')
        manager.aplicar_tema_customizado(modo, cor_primaria)
    
    aplicar_css_completo()

def salvar_tema_usuario(usuario_id: int, tema_id: str, modo: str, cor_primaria: str):
    """Salva o tema do usuário no banco de dados"""
    try:
        from database import salvar_preferencias_tema
        
        cores_json = json.dumps({
            'cor_primaria': cor_primaria,
            'tema_id': tema_id
        })
        
        return salvar_preferencias_tema(usuario_id, tema_id, modo, cores_json)
    except Exception as e:
        logger.error(f"Erro ao salvar tema: {e}")
        return False
# ============================================================================
# PÁGINA DE CONFIGURAÇÃO DO TEMA
# ============================================================================
def pagina_configurar_tema():
    """Página para configuração de tema e cores - CORRIGIDA"""
    
    st.markdown("### 🎨 Personalização da Interface")
    st.caption("Escolha o modo e a cor principal do sistema - As alterações são salvas automaticamente")
    
    # Carregar configurações salvas do usuário
    if st.session_state.get('logado') and st.session_state.get('usuario_id'):
        from database import carregar_preferencias_tema
        preferencias = carregar_preferencias_tema(st.session_state.usuario_id)
        if preferencias:
            st.session_state.tema = preferencias.get('modo', 'escuro')
            cores = preferencias.get('cores', {})
            st.session_state.cor_primaria = cores.get('cor_primaria', '#3d8bfd')
    
    # Estado atual
    tema_atual = st.session_state.get('tema', 'escuro')
    cor_atual = st.session_state.get('cor_primaria', '#3d8bfd')
    
    # Botão recarregar e status do tema
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔄 Recarregar Página", type="secondary", use_container_width=True, key="btn_recarregar_tema"):
            st.rerun()
    with col2:
        if tema_atual == "claro":
            st.markdown("""
            <div style="background: linear-gradient(135deg, #e8f0fe, #d4e2fc); 
                        padding: 8px 16px; border-radius: 10px; text-align: center;">
                <small>☀️ Modo Claro Ativo</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #2a2a3e, #1a1a2e); 
                        padding: 8px 16px; border-radius: 10px; text-align: center;">
                <small>🌙 Modo Escuro Ativo</small>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Seleção de modo
    st.markdown("#### 🌓 Modo de Visualização")
    
    col_modo1, col_modo2, col_modo3 = st.columns(3)
    
    with col_modo1:
        if st.button("🌙 Escuro", use_container_width=True, 
                    type="primary" if tema_atual == 'escuro' else "secondary",
                    key="btn_modo_escuro"):
            st.session_state.tema = 'escuro'
            # Salvar no banco
            if st.session_state.get('logado'):
                from theme_manager import salvar_tema_usuario
                salvar_tema_usuario(st.session_state.usuario_id, 'custom', 'escuro', cor_atual)
            # Aplicar tema
            manager = get_theme_manager()
            manager.aplicar_tema_customizado('escuro', cor_atual)
            st.rerun()
    
    with col_modo2:
        if st.button("☀️ Claro", use_container_width=True,
                    type="primary" if tema_atual == 'claro' else "secondary",
                    key="btn_modo_claro"):
            st.session_state.tema = 'claro'
            if st.session_state.get('logado'):
                from theme_manager import salvar_tema_usuario
                salvar_tema_usuario(st.session_state.usuario_id, 'custom', 'claro', cor_atual)
            manager = get_theme_manager()
            manager.aplicar_tema_customizado('claro', cor_atual)
            st.rerun()
    
    with col_modo3:
        if st.button("💻 Seguir Sistema", use_container_width=True,
                    type="primary" if tema_atual == 'sistema' else "secondary",
                    key="btn_seguir_sistema"):
            st.session_state.tema = 'sistema'
            st.session_state.seguir_sistema = True
            # Detectar hora atual
            hora = datetime.now().hour
            modo = 'escuro' if hora < 6 or hora > 18 else 'claro'
            if st.session_state.get('logado'):
                from theme_manager import salvar_tema_usuario
                salvar_tema_usuario(st.session_state.usuario_id, 'custom', modo, cor_atual)
            manager = get_theme_manager()
            manager.aplicar_tema_customizado(modo, cor_atual)
            st.rerun()
    
    st.markdown("---")
    
    # Grade de cores - ORGANIZADA EM ABAS
    st.markdown("#### 🎨 Cor Principal")
    
    # Criar abas para cada família de cores
    families = list(COLORS_BY_FAMILY.keys())
    color_tabs = st.tabs(families)
    
    for tab_idx, family in enumerate(families):
        with color_tabs[tab_idx]:
            colors = COLORS_BY_FAMILY[family]
            # Criar linhas de 4 cores
            for i in range(0, len(colors), 4):
                cols = st.columns(4)
                for j in range(4):
                    idx = i + j
                    if idx < len(colors):
                        cor_info = colors[idx]
                        is_selected = cor_info['primary'].lower() == cor_atual.lower()
                        
                        with cols[j]:
                            # Card da cor
                            st.markdown(f"""
                            <div style="
                                background: linear-gradient(135deg, {cor_info['primary']}, {cor_info['secondary']});
                                border-radius: 12px;
                                padding: 25px 10px;
                                margin: 8px 0;
                                text-align: center;
                                border: 3px solid {'white' if is_selected else 'transparent'};
                                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                                cursor: pointer;
                            ">
                                <div style="color: white; font-weight: bold; font-size: 1rem;">{cor_info['name']}</div>
                                <div style="color: rgba(255,255,255,0.8); font-size: 0.7rem; margin-top: 5px;">{cor_info['primary']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Botão Selecionar
                            if st.button(f"Selecionar", key=f"cor_{family}_{idx}_{cor_info['primary']}", use_container_width=True):
                                st.session_state.cor_primaria = cor_info['primary']
                                # Salvar no banco
                                if st.session_state.get('logado'):
                                    from theme_manager import salvar_tema_usuario
                                    salvar_tema_usuario(
                                        st.session_state.usuario_id, 
                                        'custom', 
                                        st.session_state.tema, 
                                        cor_info['primary']
                                    )
                                # Aplicar tema
                                manager = get_theme_manager()
                                manager.aplicar_tema_customizado(st.session_state.tema, cor_info['primary'])
                                st.rerun()
            
            st.markdown("---")
    
    # Cor personalizada
    with st.expander("🎨 Cor Personalizada", expanded=False):
        col_hex1, col_hex2 = st.columns([3, 1])
        with col_hex1:
            cor_personalizada = st.text_input(
                "Digite uma cor (formato HEX)",
                value=cor_atual,
                placeholder="#RRGGBB",
                key="cor_personalizada_input"
            )
        with col_hex2:
            if st.button("✅ Aplicar", use_container_width=True, key="btn_aplicar_cor"):
                import re
                if re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', cor_personalizada):
                    st.session_state.cor_primaria = cor_personalizada
                    if st.session_state.get('logado'):
                        from theme_manager import salvar_tema_usuario
                        salvar_tema_usuario(
                            st.session_state.usuario_id, 
                            'custom', 
                            st.session_state.tema, 
                            cor_personalizada
                        )
                    manager = get_theme_manager()
                    manager.aplicar_tema_customizado(st.session_state.tema, cor_personalizada)
                    st.rerun()
                else:
                    st.error("Formato inválido! Use #RRGGBB")
    
    st.markdown("---")
    
    # Botões de ação
    col_salvar, col_reset = st.columns(2)
    
    with col_salvar:
        if st.button("💾 Salvar Tema", type="primary", use_container_width=True, key="btn_salvar_tema"):
            if st.session_state.get('logado'):
                from theme_manager import salvar_tema_usuario
                salvar_tema_usuario(
                    st.session_state.usuario_id, 
                    'custom', 
                    st.session_state.tema, 
                    st.session_state.cor_primaria
                )
                st.success("✅ Tema salvo com sucesso!")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("⚠️ Faça login para salvar o tema permanentemente")
    
    with col_reset:
        if st.button("🔄 Resetar Padrão", use_container_width=True, key="btn_resetar_tema"):
            st.session_state.tema = 'escuro'
            st.session_state.cor_primaria = '#3d8bfd'
            if st.session_state.get('logado'):
                from theme_manager import salvar_tema_usuario
                salvar_tema_usuario(st.session_state.usuario_id, 'default', 'escuro', '#3d8bfd')
            manager = get_theme_manager()
            manager.aplicar_tema_customizado('escuro', '#3d8bfd')
            st.rerun()
    
    # Status do salvamento
    st.markdown("---")
    if st.session_state.get('logado'):
        st.success(f"💾 Tema salvo para o usuário: {st.session_state.usuario_nome}")
        st.caption("As configurações de tema são salvas automaticamente e mantidas entre sessões")
    else:
        st.info("🔓 Faça login para salvar suas preferências de tema permanentemente")


# ============================================================================
# TESTE DO MÓDULO
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 TESTANDO MÓDULO THEME_MANAGER")
    print("=" * 60)
    
    cores = get_cores()
    print(f"✅ Cores carregadas: {len(cores)} propriedades")
    print(f"✅ Cor destaque: {cores['destaque']}")
    print(f"✅ Cor texto: {cores['texto']}")
    print(f"✅ Cor fundo: {cores['fundo']}")
    
    print("\n✅ MÓDULO THEME_MANAGER OK!")
    print("=" * 60)
