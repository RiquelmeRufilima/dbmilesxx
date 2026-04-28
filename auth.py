"""
auth.py - Módulo de Autenticação DBMILESX
"""

import streamlit as st
import time
import secrets
import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from functools import wraps

from database import (
    criar_conexao,
    get_db_cursor,
    verificar_login_simplificado,
    registrar_usuario as db_registrar_usuario,
    gerar_token_recuperacao,
    validar_token_recuperacao,
    marcar_token_como_usado,
    redefinir_senha_com_token,
    registrar_evento_seguranca,
    convidar_membro as db_convidar_membro
)

from securitymax import (
    security,
    get_client_ip,
    validate_password_strength,
    sanitize_input,
    check_rate_limit
)

logger = logging.getLogger(__name__)


def registrar_usuario(email: str, senha: str, nome: str, 
                      telefone: Optional[str] = None,
                      convite_token: Optional[str] = None) -> Tuple[bool, str, Optional[Dict]]:
    """Registra novo usuário"""
    try:
        client_ip = get_client_ip()
        rate_key = f"registro:{client_ip}:{email}"
        
        if not check_rate_limit(rate_key, max_requests=3, window=3600):
            return False, "Muitas tentativas. Aguarde 1 hora.", None
        
        email = sanitize_input(email.strip().lower())
        nome = sanitize_input(nome.strip())
        
        if not security.validate_email(email):
            return False, "Email inválido", None
        
        if len(nome) < 3:
            return False, "Nome deve ter pelo menos 3 caracteres", None
        
        validacao = validate_password_strength(senha)
        if not validacao['valid']:
            return False, f"Senha fraca: {', '.join(validacao['feedback'][:2])}", None
        
        empresa_id = None
        nivel_acesso = 'membro'
        
        if convite_token:
            from database import validar_convite
            valido, dados_convite = validar_convite(convite_token)
            if valido and dados_convite and dados_convite.get('email') == email:
                empresa_id = dados_convite.get('empresa_id')
                nivel_acesso = dados_convite.get('nivel_acesso', 'membro')
        
        with get_db_cursor() as cursor:
            cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
            if cursor.fetchone():
                return False, "Email já cadastrado", None
            
            senha_hash = security.hash_password(senha)
            csrf_token = secrets.token_urlsafe(32)
            sessao_token = secrets.token_urlsafe(64)
            
            cursor.execute('''
            INSERT INTO usuarios (email, senha_hash, nome, telefone, empresa_id, nivel_acesso, csrf_token, sessao_token)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (email, senha_hash, nome, telefone, empresa_id, nivel_acesso, csrf_token, sessao_token))
            
            usuario_id = cursor.lastrowid
            
            if convite_token:
                cursor.execute('UPDATE convites SET usado = 1 WHERE token = ?', (convite_token,))
        
        registrar_evento_seguranca(usuario_id, "REGISTRO_SUCESSO", f"Novo usuário: {email}", "INFO")
        
        return True, "Conta criada com sucesso!", {
            'usuario_id': usuario_id,
            'usuario_nome': nome,
            'usuario_email': email,
            'empresa_id': empresa_id,
            'nivel_acesso': nivel_acesso
        }
        
    except Exception as e:
        logger.error(f"Erro ao registrar: {e}")
        return False, f"Erro: {str(e)}", None


def verificar_login(email: str, senha: str, db_path: str = None) -> Tuple[bool, Any]:
    """Verifica login do usuário"""
    try:
        return verificar_login_simplificado(email, senha)
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        return False, f"Erro: {str(e)}"


def redefinir_senha(email: str, nova_senha: str) -> Tuple[bool, str]:
    """Redefine senha do usuário"""
    try:
        token = gerar_token_recuperacao(email)
        if not token:
            return False, "Erro ao gerar token"
        
        return redefinir_senha_com_token(token, nova_senha)
    except Exception as e:
        logger.error(f"Erro ao redefinir senha: {e}")
        return False, f"Erro: {str(e)}"


def solicitar_recuperacao_senha(email: str) -> Tuple[bool, str]:
    """Solicita recuperação de senha"""
    try:
        client_ip = get_client_ip()
        rate_key = f"recuperacao:{client_ip}:{email}"
        
        if not check_rate_limit(rate_key, max_requests=3, window=3600):
            return False, "Muitas tentativas. Aguarde 1 hora."
        
        token = gerar_token_recuperacao(email)
        
        if token:
            base_url = "http://localhost:8501"
            link = f"{base_url}/?token={token}"
            logger.info(f"Link de recuperação: {link}")
            return True, f"Link gerado: {link}"
        
        return True, "Se o email estiver cadastrado, você receberá as instruções."
        
    except Exception as e:
        logger.error(f"Erro na recuperação: {e}")
        return False, f"Erro: {str(e)}"


def aceitar_convite(token: str, senha: str, nome: Optional[str] = None) -> Tuple[bool, str]:
    """Aceita convite para empresa"""
    try:
        from database import validar_convite, aceitar_convite as db_aceitar
        
        valido, dados = validar_convite(token)
        if not valido:
            return False, "Convite inválido ou expirado"
        
        validacao = validate_password_strength(senha)
        if not validacao['valid']:
            return False, "Senha muito fraca"
        
        return db_aceitar(token, senha)
        
    except Exception as e:
        logger.error(f"Erro ao aceitar convite: {e}")
        return False, f"Erro: {str(e)}"


def fazer_logout(usuario_id: Optional[int] = None) -> bool:
    """Realiza logout seguro"""
    try:
        if usuario_id:
            registrar_evento_seguranca(usuario_id, "LOGOUT", "Logout realizado", "INFO")
        
        for key in list(st.session_state.keys()):
            if key not in ['csrf_token', 'rate_limiter']:
                del st.session_state[key]
        
        st.session_state.logado = False
        st.session_state.pagina = 'login'
        
        return True
    except Exception as e:
        logger.error(f"Erro no logout: {e}")
        return False


def verificar_sessao() -> bool:
    """Verifica se a sessão é válida"""
    if not st.session_state.get('logado', False):
        return False
    
    last_activity = st.session_state.get('last_activity', 0)
    if time.time() - last_activity > 1800:
        fazer_logout(st.session_state.get('usuario_id'))
        st.warning("Sessão expirada")
        return False
    
    st.session_state.last_activity = time.time()
    return True


def gerar_convite_com_email(empresa_id: int, 
                            email: str, 
                            nome: str, 
                            nivel_acesso: str = 'membro', 
                            convidado_por: int = None,
                            config_email: Dict = None) -> Optional[str]:
    """Gera convite com email"""
    try:
        token = db_convidar_membro(
            empresa_id=empresa_id,
            email=email,
            nome=nome,
            nivel_acesso=nivel_acesso,
            convidado_por=convidado_por,
            config_email=config_email
        )
        return token
    except Exception as e:
        logger.error(f"Erro ao gerar convite: {e}")
        return None


def obter_usuario_atual() -> Optional[Dict]:
    """Retorna dados do usuário logado"""
    if not verificar_sessao():
        return None
    
    return {
        'id': st.session_state.get('usuario_id'),
        'nome': st.session_state.get('usuario_nome'),
        'email': st.session_state.get('usuario_email'),
        'empresa_id': st.session_state.get('empresa_id'),
        'nivel_acesso': st.session_state.get('nivel_acesso', 'membro')
    }


def requer_autenticacao(func):
    """Decorator para exigir autenticação"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not verificar_sessao():
            st.error("❌ Você precisa estar logado.")
            st.session_state.pagina = 'login'
            st.rerun()
            return None
        return func(*args, **kwargs)
    return wrapper


def requer_permissao(permissao: str):
    """Decorator para exigir permissão"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not verificar_sessao():
                st.error("❌ Você precisa estar logado.")
                st.rerun()
                return None
            
            nivel = st.session_state.get('nivel_acesso', 'membro')
            permissoes = {
                'admin': ['admin', 'gerente', 'membro', 'visualizador'],
                'gerente': ['gerente', 'membro', 'visualizador'],
                'membro': ['membro', 'visualizador'],
                'visualizador': ['visualizador']
            }
            
            if permissao not in permissoes.get(nivel, []):
                st.error(f"❌ Acesso negado. Permissão '{permissao}' necessária.")
                return None
            
            return func(*args, **kwargs)
        return wrapper
    return decorator