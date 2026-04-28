"""
config_manager.py - Gerenciador de Configurações do Sistema DBMILESX
Gerencia temas, cores, persistência e validação segura de configurações
COM HIERARQUIA DE EMPRESAS E PERFIL DE USUÁRIO
"""

import json
import os
import logging
import time
import shutil
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import streamlit as st
import hashlib
import secrets
import re
import base64
from PIL import Image
from io import BytesIO

# Configuração de logging
logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTES DE CONFIGURAÇÃO
# ============================================================================

# Caminho do arquivo de configuração
CONFIG_DIR = Path.home() / '.dbmilesx'
CONFIG_FILE = CONFIG_DIR / 'config.json'
CONFIG_BACKUP_DIR = CONFIG_DIR / 'backups'

# Tema padrão
DEFAULT_THEME = {
    'modo': 'escuro',
    'cor_principal': '#3d8bfd',
    'cor_secundaria': '#5c9cff',
    'cor_sucesso': '#4CAF50',
    'cor_erro': '#f44336',
    'cor_aviso': '#ff9800',
    'cor_info': '#2196F3',
    'cores_personalizadas': {},
    'fonte': 'Padrão'
}

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

# Organizar por família para exibição
COLORS_BY_FAMILY = {}
for color in PREDEFINED_COLORS:
    family = color['family']
    if family not in COLORS_BY_FAMILY:
        COLORS_BY_FAMILY[family] = []
    COLORS_BY_FAMILY[family].append(color)

# Configurações padrão
DEFAULT_CONFIG = {
    'version': '2.0.0',
    'last_updated': None,
    'user_id': None,
    'empresa_id': None,
    'theme': DEFAULT_THEME.copy(),
    'preferences': {
        'moeda': 'BRL',
        'idioma': 'pt-BR',
        'notificacoes': True,
        'auto_save': True,
        'compact_view': False,
        'animacoes': True,
        'seguir_sistema': False,
        'alto_contraste': False
    },
    'security': {
        'last_backup': None,
        'config_hash': None,
        'backup_count': 0,
        'encrypted': False
    },
    'empresa': {
        'nome': None,
        'logo': None,
        'cores_personalizadas': {}
    }
}

# ============================================================================
# CLASSE PRINCIPAL DE GERENCIAMENTO DE CONFIGURAÇÕES
# ============================================================================

class ConfigManager:
    """
    Gerenciador de configurações com validação, persistência e segurança
    Suporte para múltiplos usuários e empresas
    """
    
    def __init__(self):
        """Inicializa o gerenciador de configurações"""
        self.config_dir = CONFIG_DIR
        self.config_file = CONFIG_FILE
        self.backup_dir = CONFIG_BACKUP_DIR
        
        # Criar diretórios se não existirem
        self._ensure_directories()
        
        # Carregar configurações
        self.config = self._load_config()
    
    # ==================== GERENCIAMENTO DE ARQUIVOS ====================
    
    def _ensure_directories(self):
        """Garante que os diretórios necessários existam"""
        try:
            self.config_dir.mkdir(exist_ok=True, mode=0o700)
            self.backup_dir.mkdir(exist_ok=True, mode=0o700)
            logger.info(f"✅ Diretórios de configuração criados: {self.config_dir}")
        except Exception as e:
            logger.error(f"❌ Erro ao criar diretórios: {e}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configurações do arquivo com validação"""
        config = DEFAULT_CONFIG.copy()
        
        if not self.config_file.exists():
            logger.info("Arquivo de configuração não encontrado. Usando padrões.")
            return config
        
        try:
            # Verificar permissões do arquivo
            self._check_file_permissions()
            
            # Ler arquivo
            with open(self.config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
            
            # Validar e mesclar configurações
            if self._validate_config(file_config):
                config = self._merge_configs(config, file_config)
                logger.info("✅ Configurações carregadas com sucesso")
            else:
                logger.warning("⚠️ Arquivo de configuração inválido. Restaurando backup...")
                config = self._restore_from_backup()
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erro ao decodificar JSON: {e}")
            config = self._restore_from_backup()
        except Exception as e:
            logger.error(f"❌ Erro ao carregar configurações: {e}")
            config = self._restore_from_backup()
        
        return config
    
    def _check_file_permissions(self):
        """Verifica se as permissões do arquivo são seguras"""
        if os.name == 'posix':  # Linux/Mac
            mode = oct(self.config_file.stat().st_mode)[-3:]
            if mode not in ['600', '700']:
                logger.warning(f"⚠️ Permissões inseguras no arquivo de configuração: {mode}")
                self.config_file.chmod(0o600)
    
    def _validate_config(self, config: Dict) -> bool:
        """Valida a estrutura e conteúdo do arquivo de configuração"""
        try:
            # Verificar campos obrigatórios
            required_fields = ['version', 'theme', 'preferences']
            for field in required_fields:
                if field not in config:
                    logger.warning(f"Campo obrigatório ausente: {field}")
                    return False
            
            # Validar versão
            if not isinstance(config.get('version'), str):
                return False
            
            # Validar tema
            theme = config.get('theme', {})
            if not isinstance(theme, dict):
                return False
            
            # Validar modo do tema
            if 'modo' in theme and theme['modo'] not in ['claro', 'escuro', 'sistema']:
                theme['modo'] = 'escuro'
            
            # Validar cor principal (formato hex)
            if 'cor_principal' in theme:
                cor = theme['cor_principal']
                if not self._validate_hex_color(cor):
                    theme['cor_principal'] = '#3d8bfd'
            
            # Validar preferências
            prefs = config.get('preferences', {})
            if 'moeda' in prefs and prefs['moeda'] not in ['BRL', 'USD', 'EUR', 'GBP']:
                prefs['moeda'] = 'BRL'
            
            return True
            
        except Exception as e:
            logger.error(f"Erro na validação: {e}")
            return False
    
    def _validate_hex_color(self, color: str) -> bool:
        """Valida formato de cor hexadecimal"""
        if not color or not isinstance(color, str):
            return False
        color = color.lstrip('#')
        return len(color) in [3, 6] and all(c in '0123456789abcdefABCDEF' for c in color)
    
    def _merge_configs(self, default: Dict, user: Dict) -> Dict:
        """Mescla configurações do usuário com as padrões de forma segura"""
        merged = default.copy()
        
        # Mesclar tema
        if 'theme' in user and isinstance(user['theme'], dict):
            merged['theme'].update(user['theme'])
        
        # Mesclar preferências
        if 'preferences' in user and isinstance(user['preferences'], dict):
            merged['preferences'].update(user['preferences'])
        
        # Mesclar campos de segurança
        if 'security' in user and isinstance(user['security'], dict):
            merged['security'].update(user['security'])
        
        # Mesclar dados da empresa
        if 'empresa' in user and isinstance(user['empresa'], dict):
            merged['empresa'].update(user['empresa'])
        
        # Atualizar timestamp
        merged['last_updated'] = datetime.now().isoformat()
        
        return merged
    
    # ==================== BACKUP E RECUPERAÇÃO ====================
    
    def _create_backup(self) -> Optional[Path]:
        """Cria backup do arquivo de configuração"""
        try:
            if not self.config_file.exists():
                return None
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"config_backup_{timestamp}.json"
            
            # Copiar arquivo
            shutil.copy2(self.config_file, backup_file)
            
            # Manter apenas os 10 backups mais recentes
            self._cleanup_old_backups(keep=10)
            
            logger.info(f"✅ Backup criado: {backup_file}")
            return backup_file
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar backup: {e}")
            return None
    
    def _cleanup_old_backups(self, keep: int = 10):
        """Mantém apenas os N backups mais recentes"""
        try:
            backups = sorted(self.backup_dir.glob("config_backup_*.json"))
            for backup in backups[:-keep]:
                backup.unlink()
                logger.info(f"🗑️ Backup antigo removido: {backup}")
        except Exception as e:
            logger.error(f"Erro ao limpar backups antigos: {e}")
    
    def _restore_from_backup(self) -> Dict[str, Any]:
        """Restaura configurações do backup mais recente"""
        try:
            backups = sorted(self.backup_dir.glob("config_backup_*.json"), reverse=True)
            
            if not backups:
                logger.warning("Nenhum backup encontrado. Usando configurações padrão.")
                return DEFAULT_CONFIG.copy()
            
            for backup_file in backups:
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        backup_config = json.load(f)
                    
                    if self._validate_config(backup_config):
                        logger.info(f"✅ Configurações restauradas de: {backup_file}")
                        return backup_config
                        
                except Exception as e:
                    logger.error(f"Erro ao carregar backup {backup_file}: {e}")
                    continue
            
            return DEFAULT_CONFIG.copy()
            
        except Exception as e:
            logger.error(f"❌ Erro na restauração: {e}")
            return DEFAULT_CONFIG.copy()
    
    # ==================== SALVAR CONFIGURAÇÕES ====================
    
    def salvar_configuracoes(self, user_id: Optional[int] = None, empresa_id: Optional[int] = None) -> bool:
        """Salva as configurações atuais no arquivo com validação e backup"""
        try:
            # Atualizar metadados
            self.config['last_updated'] = datetime.now().isoformat()
            if user_id:
                self.config['user_id'] = user_id
            if empresa_id:
                self.config['empresa_id'] = empresa_id
            
            # Criar hash de integridade
            config_str = json.dumps(self.config, sort_keys=True)
            self.config['security']['config_hash'] = hashlib.sha256(
                config_str.encode()
            ).hexdigest()
            
            # Criar backup antes de salvar
            self._create_backup()
            
            # Salvar arquivo com permissões seguras
            temp_file = self.config_file.with_suffix('.tmp')
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            # Garantir que o arquivo temporário foi escrito
            if os.name == 'posix':
                temp_file.chmod(0o600)
            
            # Substituir arquivo original
            temp_file.replace(self.config_file)
            
            # Atualizar contador de backups
            self.config['security']['backup_count'] = len(
                list(self.backup_dir.glob("config_backup_*.json"))
            )
            
            logger.info(f"✅ Configurações salvas com sucesso para usuário {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar configurações: {e}")
            return False
    
    def carregar_configuracoes(self, user_id: Optional[int] = None, empresa_id: Optional[int] = None) -> Dict[str, Any]:
        """Carrega configurações do arquivo"""
        if not self.config_file.exists():
            return DEFAULT_CONFIG.copy()
        
        try:
            # Verificar integridade
            stored_hash = self.config.get('security', {}).get('config_hash')
            if stored_hash:
                config_copy = self.config.copy()
                config_copy['security'] = config_copy.get('security', {}).copy()
                config_copy['security'].pop('config_hash', None)
                
                calculated_hash = hashlib.sha256(
                    json.dumps(config_copy, sort_keys=True).encode()
                ).hexdigest()
                
                if stored_hash != calculated_hash:
                    logger.warning("⚠️ Arquivo de configuração modificado!")
                    self.config = self._restore_from_backup()
            
            # Filtrar por usuário se necessário
            if user_id and self.config.get('user_id') != user_id:
                # Carregar configurações específicas do usuário
                pass
            
            # Filtrar por empresa se necessário
            if empresa_id and self.config.get('empresa_id') != empresa_id:
                # Carregar configurações específicas da empresa
                pass
            
            return self.config
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar configurações: {e}")
            return DEFAULT_CONFIG.copy()
    
    # ==================== GERENCIAMENTO DE TEMA ====================
    
    def set_tema(self, modo: str, cor_principal: str, cores_personalizadas: Optional[Dict] = None):
        """Define as configurações de tema"""
        if modo not in ['claro', 'escuro', 'sistema']:
            raise ValueError(f"Modo inválido: {modo}")
        
        if not self._validate_hex_color(cor_principal):
            raise ValueError(f"Cor inválida: {cor_principal}")
        
        self.config['theme']['modo'] = modo
        self.config['theme']['cor_principal'] = cor_principal
        
        if cores_personalizadas:
            self.config['theme']['cores_personalizadas'] = cores_personalizadas
        
        logger.info(f"✅ Tema atualizado: {modo} - {cor_principal}")
    
    def get_tema(self) -> Dict[str, Any]:
        """Retorna as configurações atuais de tema"""
        return self.config.get('theme', DEFAULT_THEME.copy())
    
    def get_cor_principal(self) -> str:
        """Retorna a cor principal atual"""
        return self.config['theme'].get('cor_principal', '#3d8bfd')
    
    def get_modo_tema(self) -> str:
        """Retorna o modo atual do tema"""
        return self.config['theme'].get('modo', 'escuro')
    
    # ==================== GERENCIAMENTO DE PREFERÊNCIAS ====================
    
    def set_preferencia(self, chave: str, valor: Any):
        """Define uma preferência específica"""
        preferencias_validas = ['moeda', 'idioma', 'notificacoes', 'auto_save', 
                                'compact_view', 'animacoes', 'seguir_sistema', 'alto_contraste']
        
        if chave not in preferencias_validas:
            raise ValueError(f"Preferência inválida: {chave}")
        
        # Validações específicas
        if chave == 'moeda' and valor not in ['BRL', 'USD', 'EUR', 'GBP']:
            raise ValueError(f"Moeda inválida: {valor}")
        
        if chave == 'idioma' and valor not in ['pt-BR', 'en-US', 'es-ES']:
            raise ValueError(f"Idioma inválido: {valor}")
        
        self.config['preferences'][chave] = valor
        logger.info(f"✅ Preferência {chave} = {valor}")
        
        # Salvar automaticamente se auto_save estiver ativo
        if self.config['preferences'].get('auto_save', True):
            self.salvar_configuracoes()
    
    def get_preferencia(self, chave: str, default=None):
        """Retorna uma preferência específica"""
        return self.config.get('preferences', {}).get(chave, default)
    
    def get_all_preferences(self) -> Dict[str, Any]:
        """Retorna todas as preferências"""
        return self.config.get('preferences', {})
    
    # ==================== GERENCIAMENTO DE EMPRESA ====================
    
    def set_empresa_config(self, nome: str, logo: Optional[str] = None, cores: Optional[Dict] = None):
        """Define configurações da empresa"""
        if nome:
            self.config['empresa']['nome'] = nome
        if logo:
            self.config['empresa']['logo'] = logo
        if cores:
            self.config['empresa']['cores_personalizadas'] = cores
        
        logger.info(f"✅ Configurações da empresa atualizadas: {nome}")
    
    def get_empresa_config(self) -> Dict[str, Any]:
        """Retorna configurações da empresa"""
        return self.config.get('empresa', {})
    
    # ==================== UTILITÁRIOS ====================
    
    def reset_to_defaults(self):
        """Reseta configurações para os valores padrão"""
        self.config = DEFAULT_CONFIG.copy()
        self.config['last_updated'] = datetime.now().isoformat()
        logger.info("🔄 Configurações resetadas para padrão")
    
    def export_config(self) -> str:
        """Exporta configurações como string JSON"""
        export_data = self.config.copy()
        # Remover dados sensíveis
        export_data.pop('security', None)
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    def import_config(self, config_str: str) -> bool:
        """Importa configurações de uma string JSON"""
        try:
            imported = json.loads(config_str)
            # Validar antes de importar
            if self._validate_config(imported):
                # Preservar dados de segurança
                imported['security'] = self.config.get('security', {})
                self.config = imported
                logger.info("✅ Configurações importadas com sucesso")
                return True
            else:
                logger.error("❌ Configurações importadas inválidas")
                return False
        except Exception as e:
            logger.error(f"❌ Erro ao importar configurações: {e}")
            return False
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Retorna um resumo das configurações atuais"""
        return {
            'versao': self.config.get('version'),
            'ultima_atualizacao': self.config.get('last_updated'),
            'tema': self.config['theme'].get('modo'),
            'cor_principal': self.config['theme'].get('cor_principal'),
            'moeda': self.config['preferences'].get('moeda'),
            'usuario_id': self.config.get('user_id'),
            'empresa_id': self.config.get('empresa_id'),
            'backups': self.config['security'].get('backup_count', 0)
        }


# ============================================================================
# FUNÇÕES DE INTERFACE STREAMLIT
# ============================================================================

def pagina_configuracoes_melhorada():
    """
    Página de configurações melhorada com seleção de tema, cores e persistência
    Agora com abas de PERFIL e EMPRESA!
    """
    from theme_manager import get_theme_manager, aplicar_tema_atual
    
    # Inicializar gerenciador de configurações
    if 'config_manager' not in st.session_state:
        st.session_state.config_manager = ConfigManager()
    
    config_manager = st.session_state.config_manager
    
    # Carregar configurações do usuário
    usuario_id = st.session_state.get('usuario_id')
    empresa_id = st.session_state.get('empresa_id')
    
    if usuario_id or empresa_id:
        config_manager.carregar_configuracoes(usuario_id, empresa_id)
    
    # Título com estilo
    st.markdown("""
    <style>
    .chrome-header {
        background: linear-gradient(135deg, #3d8bfd, #5c9cff);
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 25px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .chrome-tabs {
        border-bottom: 2px solid #e0e0e0;
        margin-bottom: 25px;
    }
    .profile-avatar {
        width: 150px;
        height: 150px;
        border-radius: 50%;
        background: linear-gradient(135deg, #3d8bfd, #5c9cff);
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 20px auto;
        border: 3px solid white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .profile-initials {
        font-size: 48px;
        font-weight: bold;
        color: white;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="chrome-header"><h1>⚙️ Configurações do Sistema</h1><p>Personalize sua experiência no DBMILESX</p></div>', unsafe_allow_html=True)
    
    # Botão voltar
    col_voltar, _ = st.columns([1, 5])
    with col_voltar:
        if st.button("← Voltar ao Início", key="btn_voltar_config", use_container_width=True):
            st.session_state.pagina = 'inicio'
            st.rerun()
    
    # Abas principais
    tab_perfil, tab_empresa, tab_aparencia, tab_preferencias, tab_sistema = st.tabs([
        "👤 Meu Perfil", "🏢 Minha Empresa", "🎨 Aparência", "⚙️ Preferências", "💻 Sistema"
    ])
    
    # Renderizar cada aba
    with tab_perfil:
        _render_aba_perfil(config_manager)
    
    with tab_empresa:
        _render_aba_empresa(config_manager)
    
    with tab_aparencia:
        _render_aba_aparencia(config_manager)
    
    with tab_preferencias:
        _render_aba_preferencias(config_manager)
    
    with tab_sistema:
        _render_aba_sistema(config_manager)


def _render_aba_perfil(config_manager: ConfigManager):
    """Renderiza a aba de perfil do usuário"""
    from database import atualizar_perfil_usuario
    import time
    
    st.markdown("### 👤 Meu Perfil")
    st.caption("Gerencie suas informações pessoais")
    
    # Inicializar estado para foto
    if 'foto_perfil' not in st.session_state:
        st.session_state.foto_perfil = st.session_state.get('foto_perfil', None)
    
    col_foto, col_dados = st.columns([1, 2])
    
    with col_foto:
        st.markdown("#### 📸 Foto de Perfil")
        
        if st.session_state.foto_perfil:
            st.image(st.session_state.foto_perfil, width=150, caption="Sua foto")
        else:
            nome = st.session_state.usuario_nome
            iniciais = ''.join([p[0].upper() for p in nome.split()[:2]]) if nome else "??"
            
            st.markdown(f"""
            <div class="profile-avatar">
                <span class="profile-initials">{iniciais}</span>
            </div>
            <p style="text-align: center; color: #666;">Sem foto</p>
            """, unsafe_allow_html=True)
        
        foto_upload = st.file_uploader(
            "📤 Alterar foto",
            type=['png', 'jpg', 'jpeg', 'gif'],
            key="upload_foto_perfil",
            help="Formatos aceitos: PNG, JPG, JPEG, GIF"
        )
        
        if foto_upload:
            bytes_data = foto_upload.getvalue()
            base64_data = base64.b64encode(bytes_data).decode()
            st.session_state.foto_perfil = f"data:image/{foto_upload.type.split('/')[-1]};base64,{base64_data}"
            st.success("✅ Foto atualizada!")
            st.rerun()
        
        if st.button("🗑️ Remover foto", use_container_width=True, type="secondary"):
            st.session_state.foto_perfil = None
            st.rerun()
    
    with col_dados:
        st.markdown("#### 📋 Informações Pessoais")
        
        with st.form("form_editar_perfil"):
            nome = st.text_input(
                "**Nome completo** *",
                value=st.session_state.usuario_nome,
                placeholder="Seu nome completo"
            )
            
            email = st.text_input(
                "**Email**",
                value=st.session_state.usuario_email,
                disabled=True,
                help="Email não pode ser alterado por segurança"
            )
            
            col_telefone, col_cargo = st.columns(2)
            
            with col_telefone:
                telefone = st.text_input(
                    "**Telefone (opcional)**",
                    value=st.session_state.get('telefone', ''),
                    placeholder="(11) 99999-9999"
                )
            
            with col_cargo:
                cargo = st.text_input(
                    "**Cargo/Função (opcional)**",
                    value=st.session_state.get('cargo', ''),
                    placeholder="Ex: Gerente de Vendas"
                )
            
            st.markdown("---")
            
            col_salvar, col_cancelar = st.columns(2)
            
            with col_salvar:
                salvar = st.form_submit_button("💾 Salvar alterações", type="primary", use_container_width=True)
            
            with col_cancelar:
                if st.form_submit_button("🔄 Cancelar", use_container_width=True):
                    st.rerun()
            
            if salvar:
                if not nome:
                    st.error("❌ Nome é obrigatório!")
                else:
                    dados_perfil = {
                        'nome': nome,
                        'telefone': telefone if telefone else None,
                        'cargo': cargo if cargo else None,
                        'foto_perfil': st.session_state.foto_perfil
                    }
                    
                    st.session_state.usuario_nome = nome
                    st.session_state.telefone = telefone
                    st.session_state.cargo = cargo
                    
                    from database import atualizar_perfil_usuario
                    sucesso, msg = atualizar_perfil_usuario(
                        st.session_state.usuario_id,
                        dados_perfil
                    )
                    
                    if sucesso:
                        st.success("✅ Perfil atualizado com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
    
    st.markdown("---")
    
    # Estatísticas do usuário
    st.markdown("#### 📊 Estatísticas da Conta")
    
    from database import obter_estatisticas_usuario
    stats = obter_estatisticas_usuario(st.session_state.usuario_id)
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    
    with col_stat1:
        st.metric("Cotações criadas", stats.get('total_cotacoes', 0))
    
    with col_stat2:
        st.metric("Cálculos realizados", stats.get('total_calculos', 0))
    
    with col_stat3:
        nivel = st.session_state.get('nivel_acesso', 'membro').capitalize()
        st.metric("Nível de acesso", nivel)


def _render_aba_empresa(config_manager: ConfigManager):
    """Renderiza a aba de configurações da empresa"""
    from database import get_empresa, atualizar_empresa
    
    st.markdown("### 🏢 Minha Empresa")
    st.caption("Gerencie as informações da sua empresa")
    
    empresa_id = st.session_state.get('empresa_id')
    
    if not empresa_id:
        st.info("ℹ️ Você não está associado a nenhuma empresa ainda.")
        
        # Opção para criar empresa
        with st.expander("➕ Criar nova empresa", expanded=True):
            with st.form("form_criar_empresa"):
                nome_empresa = st.text_input("**Nome da Empresa** *", placeholder="Digite o nome da sua empresa")
                cnpj = st.text_input("**CNPJ (opcional)**", placeholder="00.000.000/0001-00")
                telefone_empresa = st.text_input("**Telefone (opcional)**", placeholder="(11) 99999-9999")
                email_empresa = st.text_input("**Email (opcional)**", placeholder="contato@empresa.com")
                
                if st.form_submit_button("🚀 Criar Empresa", type="primary", use_container_width=True):
                    if not nome_empresa:
                        st.error("❌ Nome da empresa é obrigatório!")
                    else:
                        from database import criar_empresa
                        sucesso, resultado = criar_empresa(
                            nome=nome_empresa,
                            cnpj=cnpj if cnpj else None,
                            telefone=telefone_empresa if telefone_empresa else None,
                            email=email_empresa if email_empresa else None,
                            criado_por=st.session_state.usuario_id
                        )
                        
                        if sucesso:
                            st.success(f"✅ Empresa '{nome_empresa}' criada com sucesso!")
                            st.info(f"📋 Código de acesso: **{resultado['codigo']}**")
                            st.info(f"🔑 Senha: **{resultado['senha']}**")
                            st.warning("⚠️ Guarde estas informações! Você será redirecionado.")
                            time.sleep(3)
                            st.rerun()
                        else:
                            st.error(f"❌ {resultado}")
        return
    
    # Carregar dados da empresa
    empresa = get_empresa(empresa_id)
    
    if not empresa:
        st.error("Erro ao carregar dados da empresa")
        return
    
    col_logo, col_info = st.columns([1, 2])
    
    with col_logo:
        st.markdown("#### 📸 Logo da Empresa")
        
        if empresa.get('logo'):
            st.image(empresa['logo'], width=150, caption="Logo atual")
        else:
            st.markdown("""
            <div style="width: 150px; height: 150px; background: #f0f0f0; border-radius: 12px; display: flex; align-items: center; justify-content: center;">
                <span style="font-size: 48px;">🏢</span>
            </div>
            """, unsafe_allow_html=True)
        
        logo_upload = st.file_uploader(
            "Alterar logo",
            type=['png', 'jpg', 'jpeg'],
            key="upload_logo_empresa"
        )
        
        if logo_upload:
            bytes_data = logo_upload.getvalue()
            base64_data = base64.b64encode(bytes_data).decode()
            logo_base64 = f"data:image/{logo_upload.type.split('/')[-1]};base64,{base64_data}"
            
            if atualizar_empresa(empresa_id, logo=logo_base64):
                st.success("✅ Logo atualizada!")
                st.rerun()
    
    with col_info:
        st.markdown("#### 📋 Dados da Empresa")
        
        with st.form("form_editar_empresa"):
            nome = st.text_input("**Nome da Empresa** *", value=empresa.get('nome', ''))
            cnpj = st.text_input("**CNPJ**", value=empresa.get('cnpj', '') or '')
            telefone = st.text_input("**Telefone**", value=empresa.get('telefone', '') or '')
            email = st.text_input("**Email**", value=empresa.get('email', '') or '')
            site = st.text_input("**Site**", value=empresa.get('site', '') or '')
            endereco = st.text_area("**Endereço**", value=empresa.get('endereco', '') or '', height=80)
            
            if st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                if not nome:
                    st.error("❌ Nome da empresa é obrigatório!")
                else:
                    if atualizar_empresa(empresa_id, nome=nome, cnpj=cnpj or None, 
                                        telefone=telefone or None, email=email or None,
                                        site=site or None, endereco=endereco or None):
                        st.success("✅ Dados da empresa atualizados!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Erro ao atualizar dados")
    
    st.markdown("---")
    
    # Membros da empresa
    st.markdown("### 👥 Membros da Empresa")
    
    from database import get_usuarios_empresa
    membros = get_usuarios_empresa(empresa_id)
    
    if membros:
        for membro in membros:
            col_membro1, col_membro2, col_membro3 = st.columns([3, 2, 2])
            with col_membro1:
                st.markdown(f"**{membro['nome']}**")
                st.caption(membro['email'])
            with col_membro2:
                st.markdown(f"**Nível:** {membro['nivel_acesso'].capitalize()}")
            with col_membro3:
                if st.session_state.get('nivel_acesso') == 'admin' and membro['id'] != st.session_state.usuario_id:
                    novo_nivel = st.selectbox(
                        "Alterar nível",
                        ['membro', 'gerente', 'admin'],
                        index=['membro', 'gerente', 'admin'].index(membro['nivel_acesso']),
                        key=f"nivel_{membro['id']}",
                        label_visibility="collapsed"
                    )
                    if novo_nivel != membro['nivel_acesso']:
                        from database import atualizar_nivel_acesso
                        sucesso, msg = atualizar_nivel_acesso(membro['id'], novo_nivel, st.session_state.usuario_id)
                        if sucesso:
                            st.success(f"Nível alterado para {novo_nivel}")
                            st.rerun()
            st.divider()
    else:
        st.info("Nenhum membro encontrado")
    
    # Convidar membros
    with st.expander("📨 Convidar Novo Membro"):
        with st.form("form_convidar_membro"):
            email_convite = st.text_input("**Email do convidado**", placeholder="email@exemplo.com")
            nome_convite = st.text_input("**Nome do convidado**", placeholder="Nome completo")
            nivel_convite = st.selectbox("**Nível de acesso**", ['membro', 'gerente'], index=0)
            
            if st.form_submit_button("📧 Enviar Convite", type="primary", use_container_width=True):
                if not email_convite or not nome_convite:
                    st.error("❌ Preencha todos os campos")
                else:
                    from database import convidar_membro
                    token = convidar_membro(
                        empresa_id=empresa_id,
                        email=email_convite,
                        nome=nome_convite,
                        nivel_acesso=nivel_convite,
                        convidado_por=st.session_state.usuario_id
                    )
                    
                    if token:
                        st.success(f"✅ Convite enviado para {email_convite}")
                        st.info(f"🔗 Link de convite: `/?convite={token}`")
                    else:
                        st.error("❌ Erro ao enviar convite. Verifique se o email já está cadastrado.")

def _render_aba_aparencia(config_manager: ConfigManager):
    """Renderiza a aba de aparência com grade de cores"""
    from theme_manager import get_theme_manager, aplicar_tema_atual, aplicar_css_completo, botao_recarregar_pagina
    
    st.markdown("### 🎨 Personalização da Interface")
    st.caption("Escolha o modo e a cor principal do sistema")
    
    tema_atual = config_manager.get_tema()
    theme_manager = get_theme_manager()
    
    # Botão recarregar
    botao_recarregar_pagina()
    
    st.markdown("---")
    
    # Seleção de modo
    st.markdown("#### 🌓 Modo de Visualização")
    
    col_modo1, col_modo2, col_modo3 = st.columns(3)
    
    with col_modo1:
        if st.button("🌙 Escuro", use_container_width=True, 
                    type="primary" if tema_atual['modo'] == 'escuro' else "secondary"):
            tema_atual['modo'] = 'escuro'
            st.session_state.tema = 'escuro'
            config_manager.set_tema(modo='escuro', cor_principal=tema_atual.get('cor_principal', '#3d8bfd'))
            theme_manager.aplicar_tema_customizado('escuro', tema_atual.get('cor_principal', '#3d8bfd'))
            aplicar_css_completo()
            st.rerun()
    
    with col_modo2:
        if st.button("☀️ Claro", use_container_width=True,
                    type="primary" if tema_atual['modo'] == 'claro' else "secondary"):
            tema_atual['modo'] = 'claro'
            st.session_state.tema = 'claro'
            config_manager.set_tema(modo='claro', cor_principal=tema_atual.get('cor_principal', '#3d8bfd'))
            theme_manager.aplicar_tema_customizado('claro', tema_atual.get('cor_principal', '#3d8bfd'))
            aplicar_css_completo()
            st.rerun()
    
    with col_modo3:
        if st.button("💻 Seguir Sistema", use_container_width=True,
                    type="primary" if tema_atual['modo'] == 'sistema' else "secondary"):
            tema_atual['modo'] = 'sistema'
            st.session_state.tema = 'sistema'
            config_manager.set_tema(modo='sistema', cor_principal=tema_atual.get('cor_principal', '#3d8bfd'))
            theme_manager.aplicar_tema_customizado('sistema', tema_atual.get('cor_principal', '#3d8bfd'))
            aplicar_css_completo()
            st.rerun()
    
    st.markdown("---")
    
    # Grade de cores
    st.markdown("#### 🎨 Cor Principal")
    
    families = list(COLORS_BY_FAMILY.keys())
    color_tabs = st.tabs(families)
    
    cor_selecionada = tema_atual.get('cor_principal', '#3d8bfd')
    
    for tab_idx, (family, colors) in enumerate(COLORS_BY_FAMILY.items()):
        with color_tabs[tab_idx]:
            cols = st.columns(4)
            for idx, cor_info in enumerate(colors):
                col_idx = idx % 4
                with cols[col_idx]:
                    is_selected = cor_info['primary'].lower() == cor_selecionada.lower()
                    
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, {cor_info['primary']}, {cor_info['secondary']});
                        border-radius: 12px;
                        padding: 20px 10px;
                        margin: 8px 0;
                        text-align: center;
                        border: 3px solid {'white' if is_selected else 'transparent'};
                        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                    ">
                        <div style="color: white; font-weight: bold;">{cor_info['name']}</div>
                        <div style="color: rgba(255,255,255,0.8); font-size: 0.8rem;">{cor_info['primary']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Selecionar", key=f"cor_{family}_{idx}", use_container_width=True):
                        tema_atual['cor_principal'] = cor_info['primary']
                        config_manager.set_tema(
                            modo=tema_atual['modo'],
                            cor_principal=cor_info['primary']
                        )
                        theme_manager.aplicar_tema_customizado(
                            tema_atual['modo'],
                            cor_info['primary']
                        )
                        aplicar_css_completo()
                        st.rerun()
    
    # Cor personalizada
    with st.expander("🎨 Cor Personalizada", expanded=False):
        col_hex1, col_hex2 = st.columns([3, 1])
        with col_hex1:
            cor_personalizada = st.text_input(
                "Digite uma cor (formato HEX)",
                value=tema_atual.get('cor_principal', '#3d8bfd'),
                placeholder="#RRGGBB"
            )
        with col_hex2:
            if st.button("✅ Aplicar", use_container_width=True):
                if re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', cor_personalizada):
                    tema_atual['cor_principal'] = cor_personalizada
                    config_manager.set_tema(
                        modo=tema_atual['modo'],
                        cor_principal=cor_personalizada
                    )
                    aplicar_css_completo()
                    st.rerun()
                else:
                    st.error("Formato inválido!")
    
    # Botões de ação
    col_salvar, col_reset = st.columns(2)
    with col_salvar:
        if st.button("💾 Salvar Tema", type="primary", use_container_width=True):
            config_manager.salvar_configuracoes(st.session_state.get('usuario_id'))
            aplicar_css_completo()
            st.success("✅ Tema salvo!")
            time.sleep(1)
            st.rerun()
    
    with col_reset:
        if st.button("🔄 Resetar Padrão", use_container_width=True):
            tema_atual['modo'] = 'escuro'
            tema_atual['cor_principal'] = '#3d8bfd'
            st.session_state.tema = 'escuro'
            config_manager.set_tema('escuro', '#3d8bfd')
            aplicar_css_completo()
            st.rerun()

def _render_aba_preferencias(config_manager: ConfigManager):
    """Renderiza a aba de preferências gerais"""
    st.markdown("### ⚙️ Preferências Gerais")
    st.caption("Configure suas preferências de uso do sistema")
    
    preferencias = config_manager.get_all_preferences()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 💰 Moeda")
        moeda_atual = preferencias.get('moeda', 'BRL')
        moedas = {
            "BRL": "🇧🇷 Real Brasileiro (R$)",
            "USD": "🇺🇸 Dólar Americano ($)",
            "EUR": "🇪🇺 Euro (€)",
            "GBP": "🇬🇧 Libra Esterlina (£)"
        }
        
        nova_moeda = st.selectbox(
            "Selecione a moeda principal",
            options=list(moedas.keys()),
            format_func=lambda x: moedas[x],
            index=list(moedas.keys()).index(moeda_atual) if moeda_atual in moedas else 0,
            label_visibility="collapsed"
        )
        
        if nova_moeda != moeda_atual:
            config_manager.set_preferencia('moeda', nova_moeda)
            st.session_state.moeda = nova_moeda
            st.success(f"Moeda alterada para {moedas[nova_moeda]}")
    
    with col2:
        st.markdown("#### 🌐 Idioma")
        st.selectbox(
            "Selecione o idioma",
            options=["pt-BR", "en-US", "es-ES"],
            format_func=lambda x: {"pt-BR": "🇧🇷 Português", "en-US": "🇺🇸 English", "es-ES": "🇪🇸 Español"}[x],
            index=0,
            label_visibility="collapsed",
            disabled=True
        )
        st.caption("🔜 Mais idiomas em breve")
    
    st.markdown("---")
    st.markdown("#### 🤖 Comportamento")
    
    col_comp1, col_comp2 = st.columns(2)
    
    with col_comp1:
        auto_save = st.toggle(
            "💾 Salvar automaticamente",
            value=preferencias.get('auto_save', True),
            help="Salvar configurações automaticamente ao alterar"
        )
        config_manager.set_preferencia('auto_save', auto_save)
        
        notificacoes = st.toggle(
            "🔔 Notificações do sistema",
            value=preferencias.get('notificacoes', True),
            help="Mostrar notificações de eventos do sistema"
        )
        config_manager.set_preferencia('notificacoes', notificacoes)
    
    with col_comp2:
        compact_view = st.toggle(
            "📦 Visualização compacta",
            value=preferencias.get('compact_view', False),
            help="Usar visualização mais compacta nas listagens"
        )
        config_manager.set_preferencia('compact_view', compact_view)
        
        animacoes = st.toggle(
            "✨ Animações",
            value=preferencias.get('animacoes', True),
            help="Ativar animações na interface"
        )
        config_manager.set_preferencia('animacoes', animacoes)


def _render_aba_sistema(config_manager: ConfigManager):
    """Renderiza a aba de informações do sistema"""
    st.markdown("### 💻 Informações do Sistema")
    
    summary = config_manager.get_config_summary()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📁 Configuração Atual")
        st.json(summary)
    
    with col2:
        st.markdown("#### 💾 Backups")
        backups = list(config_manager.backup_dir.glob("config_backup_*.json"))
        st.info(f"📦 {len(backups)} backup(s) disponíveis")
        
        if backups:
            with st.expander("Ver backups recentes"):
                for backup in sorted(backups, reverse=True)[:5]:
                    data = backup.stem.replace('config_backup_', '').replace('_', ' às ')
                    st.caption(f"📄 {data}")
    
    st.markdown("---")
    
    # Exportar/Importar
    st.markdown("#### 📤 Exportar/Importar")
    
    tab_export, tab_import = st.tabs(["Exportar", "Importar"])
    
    with tab_export:
        config_json = config_manager.export_config()
        st.code(config_json, language="json", line_numbers=True)
        
        st.download_button(
            "📥 Baixar Configurações",
            data=config_json,
            file_name=f"dbmilesx_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with tab_import:
        st.warning("⚠️ Importar configurações substituirá as configurações atuais!")
        
        uploaded_file = st.file_uploader("Selecione um arquivo JSON", type=['json'])
        
        if uploaded_file:
            try:
                config_str = uploaded_file.read().decode('utf-8')
                if st.button("🔄 Importar Configurações", type="primary", use_container_width=True):
                    if config_manager.import_config(config_str):
                        config_manager.salvar_configuracoes(st.session_state.get('usuario_id'))
                        st.success("✅ Configurações importadas!")
                        time.sleep(2)
                        st.rerun()
            except Exception as e:
                st.error(f"❌ Erro: {e}")
    
    st.markdown("---")
    
    # Zona de perigo
    st.markdown("#### ⚠️ Zona de Perigo")
    
    with st.expander("⚠️ Ações Destrutivas", expanded=False):
        st.error("As ações abaixo são irreversíveis!")
        
        col_reset1, col_reset2 = st.columns(2)
        
        with col_reset1:
            if st.button("🔄 Resetar Configurações", use_container_width=True):
                config_manager.reset_to_defaults()
                config_manager.salvar_configuracoes()
                st.warning("Configurações resetadas!")
                st.rerun()
        
        with col_reset2:
            confirmar = st.checkbox("Entendo os riscos")
            if confirmar:
                if st.button("🗑️ Limpar Todos os Dados", type="secondary", use_container_width=True):
                    if config_manager.config_file.exists():
                        config_manager.config_file.unlink()
                    for backup in config_manager.backup_dir.glob("*.json"):
                        backup.unlink()
                    st.success("Dados limpos!")
                    st.rerun()


# ============================================================================
# FUNÇÕES DE COMPATIBILIDADE
# ============================================================================

def get_config_manager() -> ConfigManager:
    """Retorna instância global do gerenciador de configurações"""
    if 'config_manager' not in st.session_state:
        st.session_state.config_manager = ConfigManager()
    return st.session_state.config_manager


def salvar_configuracoes_global(user_id: Optional[int] = None, empresa_id: Optional[int] = None) -> bool:
    """Função global para salvar configurações"""
    manager = get_config_manager()
    return manager.salvar_configuracoes(user_id, empresa_id)


def carregar_configuracoes_global(user_id: Optional[int] = None, empresa_id: Optional[int] = None) -> Dict[str, Any]:
    """Função global para carregar configurações"""
    manager = get_config_manager()
    return manager.carregar_configuracoes(user_id, empresa_id)


# ============================================================================
# TESTE DO MÓDULO
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 TESTANDO MÓDULO CONFIG_MANAGER")
    print("=" * 60)
    
    cm = ConfigManager()
    print(f"✅ Diretório: {cm.config_dir}")
    print(f"✅ Arquivo: {cm.config_file}")
    print(f"✅ Tema atual: {cm.get_modo_tema()}")
    print(f"✅ Cor principal: {cm.get_cor_principal()}")
    
    print("\n✅ MÓDULO CONFIG_MANAGER OK!")
    print("=" * 60)