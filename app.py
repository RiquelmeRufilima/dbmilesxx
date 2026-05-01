# ============= IMPORTS CORRETOS =============
import streamlit as st
import time
import os
import traceback
import base64
import bcrypt  
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import sqlite3
from datetime import datetime, timedelta
import hashlib
import secrets
import logging
import json
from typing import Optional, Tuple, Dict, Any, List
# ============= IMPORTAÇÕES DO DATABASE.PY =============
# ============= IMPORTAÇÕES DO DATABASE.PY (SIMPLIFICADA) =============
# ============= IMPORTAÇÕES DO DATABASE.PY (VERSÃO MÍNIMA) =============
# No início do app.py, depois dos imports, faça assim:

try:
    from database import (
        criar_conexao,
        inicializar_banco,
        carregar_preferencias_usuario,
        registrar_evento_seguranca,
        listar_historico,
        excluir_calculo,
        criar_cotacao,
        salvar_calculo,
        get_currency_symbol,
        verificar_login_simplificado,
        registrar_usuario,
        gerar_token_recuperacao,
        validar_token_recuperacao,
        marcar_token_como_usado,
        redefinir_senha_com_token,
        PasswordHasher,
        login_manager
    )
    # Importar funções adicionais separadamente
    from database import (
        criar_tabela_preferencias_tema,
        adicionar_coluna_foto_perfil,
        atualizar_perfil_usuario,
        obter_dados_usuario,
        salvar_preferencias_tema,
        carregar_preferencias_tema
    )
    # Criar tabela de preferências de tema
    criar_tabela_preferencias_tema()
    # Adicionar coluna foto_perfil se não existir
    adicionar_coluna_foto_perfil()
    
except ImportError as e:
    st.error(f"Erro ao importar database: {e}")
    # ... fallback ...
    # ... resto do fallback

    st.error(f"Erro ao importar database: {e}")
    # Fallback - criar funções vazias para não quebrar
    def criar_conexao(): return None
    def inicializar_banco(): pass
    def carregar_preferencias_usuario(*args, **kwargs): pass
    def registrar_evento_seguranca(*args, **kwargs): pass
    def listar_historico(*args, **kwargs): return []
    def excluir_calculo(*args, **kwargs): return False, "Erro"
    def criar_cotacao(*args, **kwargs): return False, "Erro"
    def salvar_calculo(*args, **kwargs): return False, "Erro"
    def get_currency_symbol(moeda): return "R$"
    def verificar_login_simplificado(*args, **kwargs): return False, "Erro"
    def registrar_usuario(*args, **kwargs): return False, "Erro"
    def gerar_token_recuperacao(*args, **kwargs): return None
    def validar_token_recuperacao(*args, **kwargs): return False, "Erro"
    def marcar_token_como_usado(*args, **kwargs): pass
    def redefinir_senha_com_token(*args, **kwargs): return False, "Erro"
    class PasswordHasher: pass
    login_manager = None

from securitymax import (  # <--- TUDO do securitymax
    security, login_manager, data_crypto, two_factor_auth,
    SecurityManager, LoginAttemptManager, DataEncryption, TwoFactorAuth, RateLimiter,
    get_colors, aplicar_css, pagina_configurar_2fa, verificar_2fa_login,
    hash_password, verify_password, validate_password_strength,
    sanitize_input, generate_csrf_token, validate_csrf_token,
    check_rate_limit, get_client_ip, encrypt_data, decrypt_data
)

from auth import registrar_usuario as auth_registrar, redefinir_senha as auth_redefinir, verificar_login as auth_verificar

# Após aplicar_tema_atual()
from theme_manager import aplicar_css_completo, aplicar_tema_atual
aplicar_css_completo()

from config_manager import pagina_configuracoes_melhorada

from utils import carregar_imagem_companhia, get_currency_symbol as utils_currency, get_colors as utils_colors, aplicar_css as utils_css

from exportacao import (
    gerar_relatorio_pdf_selecionados,
    verificar_dependencias_exportacao,
    get_currency_symbol
)

from relatorios import (
    gerar_relatorio_custo_pdf,
    gerar_relatorio_venda_pdf,
)

from solicitacao import (
    mostrar_solicitacoes,
    inicializar_tabelas_solicitacoes,
    exibir_notificacoes_sidebar,
    contar_notificacoes_nao_lidas
)

from admin_painel import pagina_admin_empresa

from empresa import render_pagina_empresa

def encontrar_imagem_site():
    """Encontra a imagem principal do site"""
    possiveis_caminhos = [
        "marca.png",
        "assets/marca.png",
        "dbmilesx.png",
        "assets/dbmilesx.png",
        "logo.png",
        "assets/logo.png",
        "favicon.png",
        "assets/favicon.png"
    ]
    
    for caminho in possiveis_caminhos:
        if os.path.exists(caminho):
            return caminho
    
    return None

# TESTE DE VARIÁVEIS - APAGAR DEPOIS
import os
print("🔍 VARIÁVEIS DE AMBIENTE CARREGADAS:")
print(f"RENDER: {os.getenv('RENDER')}")
print(f"EMAIL_USER: {os.getenv('EMAIL_USER')}")
print(f"EMAIL_APP_URL: {os.getenv('EMAIL_APP_URL')}")
# Configuração da página
imagem_site = encontrar_imagem_site()
st.set_page_config(
    page_icon=imagem_site if imagem_site else "✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "DBMILESX - Sistema de cotação aérea seguro"
    }
)

# Headers de segurança
st.markdown("""
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;">
<meta http-equiv="X-Content-Type-Options" content="nosniff">
<meta http-equiv="X-Frame-Options" content="DENY">
<meta http-equiv="X-XSS-Protection" content="1; mode=block">
<meta name="referrer" content="strict-origin-when-cross-origin">
""", unsafe_allow_html=True)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuração para diferentes ambientes
import tempfile
import os

# Detectar ambiente Render
IS_RENDER = os.getenv('RENDER', False) or os.getenv('RENDER_EXTERNAL_URL', False)

if IS_RENDER or os.getenv('STREAMLIT_CLOUD') or os.getenv('CLOUDFLARE'):
    DB_PATH = os.path.join(tempfile.gettempdir(), 'sistema_aereo_secure.db')
    logger.info(f"🚀 Modo Cloud ativado - Banco em: {DB_PATH}")
else:
    DB_PATH = 'sistema_aereo_secure.db'

class LoginAttemptManager:
    """Gerenciador de tentativas de login"""
    
    def __init__(self):
        self.attempts = {}
        self.lockouts = {}
    
    def record_attempt(self, email: str, success: bool, user_agent: str = None):
        """Registra tentativa de login"""
        pass
    
    def get_client_ip(self) -> str:
        return '127.0.0.1'
    
    def is_locked_out(self, email: str):
        return False, None
    
    def get_client_ip(self) -> str:
        """Obtém IP do cliente de forma segura"""
        try:
            headers = st.secrets.get("headers", {}) if hasattr(st, "secrets") else {}
            
            ip_headers = [
                'X-Forwarded-For',
                'X-Real-IP',
                'CF-Connecting-IP',
                'True-Client-IP'
            ]
            
            for header in ip_headers:
                ip = headers.get(header, "").split(',')[0].strip()
                if ip and self.validate_ip(ip):
                    return ip
            
            return hashlib.sha256(str(st.session_state.get('session_id', 'default')).encode()).hexdigest()[:16]
        except:
            return "unknown"
    
    @staticmethod
    def validate_ip(ip: str) -> bool:
        """Valida formato de IP"""
        try:
            import ipaddress
            ipaddress.ip_address(ip)
            return True
        except:
            return False
    
    def record_attempt(self, email: str, success: bool, user_agent: str = None) -> None:
        """Registra tentativa de login com IP tracking"""
        try:
            now = time.time()
            client_ip = self.get_client_ip()
            
            if success:
                if email in st.session_state.login_attempts:
                    del st.session_state.login_attempts[email]
                if email in st.session_state.lockouts:
                    del st.session_state.lockouts[email]
                if email in st.session_state.failed_logins:
                    del st.session_state.failed_logins[email]
                if client_ip in st.session_state.ip_attempts:
                    del st.session_state.ip_attempts[client_ip]
            else:
                if email not in st.session_state.login_attempts:
                    st.session_state.login_attempts[email] = {
                        'count': 1,
                        'first_attempt': now,
                        'last_attempt': now,
                        'user_agents': [user_agent] if user_agent else [],
                        'ips': [client_ip]
                    }
                else:
                    st.session_state.login_attempts[email]['count'] += 1
                    st.session_state.login_attempts[email]['last_attempt'] = now
                    if user_agent and user_agent not in st.session_state.login_attempts[email]['user_agents']:
                        st.session_state.login_attempts[email]['user_agents'].append(user_agent)
                    if client_ip not in st.session_state.login_attempts[email]['ips']:
                        st.session_state.login_attempts[email]['ips'].append(client_ip)
                
                if client_ip not in st.session_state.ip_attempts:
                    st.session_state.ip_attempts[client_ip] = {
                        'count': 1,
                        'first_attempt': now,
                        'last_attempt': now,
                        'emails': [email]
                    }
                else:
                    st.session_state.ip_attempts[client_ip]['count'] += 1
                    st.session_state.ip_attempts[client_ip]['last_attempt'] = now
                    if email not in st.session_state.ip_attempts[client_ip]['emails']:
                        st.session_state.ip_attempts[client_ip]['emails'].append(email)
                
                if email not in st.session_state.failed_logins:
                    st.session_state.failed_logins[email] = []
                st.session_state.failed_logins[email].append({
                    'timestamp': now,
                    'user_agent': user_agent,
                    'ip': client_ip
                })
                
                if len(st.session_state.failed_logins[email]) > 10:
                    st.session_state.failed_logins[email] = st.session_state.failed_logins[email][-10:]
                
                logger.warning(f"Login falhou para {email} (IP: {client_ip})")
                
        except Exception as e:
            logger.error(f"Erro ao registrar tentativa: {e}")
    
    def is_locked_out(self, email: str) -> Tuple[bool, Optional[str]]:
        """Verifica se está bloqueado"""
        try:
            client_ip = self.get_client_ip()
            
            if client_ip in st.session_state.ip_attempts:
                ip_attempts = st.session_state.ip_attempts[client_ip]
                if ip_attempts['count'] >= 10:
                    time_since_first = time.time() - ip_attempts['first_attempt']
                    if time_since_first < 3600:
                        return True, "🔒 Bloqueio por múltiplas tentativas (IP)"
            
            if email in st.session_state.lockouts:
                lockout_until = st.session_state.lockouts[email]
                if time.time() < lockout_until:
                    remaining = int(lockout_until - time.time())
                    minutes = remaining // 60
                    seconds = remaining % 60
                    return True, f"🔒 Muitas tentativas. Aguarde {minutes}:{seconds:02d}"
                else:
                    del st.session_state.lockouts[email]
            
            if email in st.session_state.login_attempts:
                attempts = st.session_state.login_attempts[email]
                if attempts['count'] >= 5:
                    lockout_duration = 900
                    st.session_state.lockouts[email] = time.time() + lockout_duration
                    return True, f"🔒 Bloqueado por {lockout_duration//60} minutos"
                elif attempts['count'] >= 3:
                    delay = min(2 ** (attempts['count'] - 3), 30)
                    time.sleep(delay)
                    return False, f"⚠️ Atraso de {delay}s aplicado"
            
            return False, None
            
        except Exception as e:
            logger.error(f"Erro ao verificar bloqueio: {e}")
            return False, None

security = SecurityManager()
login_manager = LoginAttemptManager()

def carregar_logo():
    """Carrega logo do sistema baseado no tema"""
    tema = st.session_state.get("tema", "escuro")
    
    if tema == "claro":
        caminhos_logo = [
            "dbmilesx_claro.png",
            "logo_claro.png",
            "marca_claro.png",
            "assets/dbmilesx_claro.png",
            "dbmilesx.png"
        ]
    else:
        caminhos_logo = [
            "dbmilesx.png",
            "marca.png",
            "dbmilesx_escuro.png",
            "logo_escuro.png",
            "assets/dbmilesx.png"
        ]
    
    for caminho in caminhos_logo:
        if os.path.exists(caminho):
            try:
                with open(caminho, "rb") as f:
                    return base64.b64encode(f.read()).decode()
            except Exception as e:
                logger.warning(f"Erro ao carregar logo {caminho}: {e}")
    
    img = Image.new('RGB', (300, 80), color='#3d8bfd')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except:
        font = ImageFont.load_default()
    
    draw.text((40, 20), "DBMILESX", fill="white", font=font)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def carregar_imagem_companhia(nome_companhia):
    """Carrega imagem da companhia aérea"""
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

def limpar_dados_corrompidos():
    """Limpa dados corrompidos do banco de dados"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE usuarios 
        SET bloqueado_ate = NULL 
        WHERE bloqueado_ate IS NOT NULL 
        AND bloqueado_ate NOT LIKE '____-__-__T__:__:__%'
        ''')
        
        rows_affected = cursor.rowcount
        if rows_affected > 0:
            logger.info(f"Limpos {rows_affected} registros com datas de bloqueio inválidas")
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Erro ao limpar dados corrompidos: {e}")

# No início do arquivo, DEPOIS da classe LoginAttemptManager, mantenha APENAS UMA versão:

def reparar_tabela_usuarios():
    """Repara/atualiza a tabela usuarios adicionando colunas faltantes - VERSÃO ÚNICA"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
        if not cursor.fetchone():
            # Criar tabela do zero com colunas MÍNIMAS
            cursor.execute('''
            CREATE TABLE usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                nome TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tema_preferido TEXT DEFAULT 'escuro',
                moeda_preferida TEXT DEFAULT 'BRL',
                csrf_token TEXT
            )
            ''')
            logger.info("✅ Tabela usuarios criada")
        else:
            # Verificar colunas existentes
            cursor.execute("PRAGMA table_info(usuarios)")
            colunas = cursor.fetchall()
            colunas_nomes = [col[1] for col in colunas]
            
            # Colunas essenciais
            colunas_essenciais = [
                ('csrf_token', 'TEXT'),
                ('sessao_token', 'TEXT'),
                ('sessao_criada', 'TIMESTAMP'),
                ('tentativas_login', 'INTEGER DEFAULT 0'),
                ('bloqueado_ate', 'TIMESTAMP')
            ]
            
            for coluna, tipo in colunas_essenciais:
                if coluna not in colunas_nomes:
                    try:
                        cursor.execute(f'ALTER TABLE usuarios ADD COLUMN {coluna} {tipo}')
                        logger.info(f"✅ Coluna {coluna} adicionada")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao adicionar {coluna}: {e}")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao reparar tabela: {e}")
        return False

    
def gerar_token_recuperacao(email: str) -> str:
    """Gera token seguro para recuperação de senha"""
    timestamp = str(int(time.time()))
    random_part = secrets.token_urlsafe(16)
    
    token_string = f"{email}:{timestamp}:{random_part}"
    token_hash = hashlib.sha256(token_string.encode()).hexdigest()
    
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM tokens_recuperacao WHERE email = ?', (email,))
        if cursor.fetchone():
            cursor.execute('DELETE FROM tokens_recuperacao WHERE email = ?', (email,))
        
        expiracao = datetime.now() + timedelta(hours=1)
        cursor.execute('''
            INSERT INTO tokens_recuperacao (email, token, expiracao)
            VALUES (?, ?, ?)
        ''', (email, token_hash, expiracao))
        
        conn.commit()
        conn.close()
        
        return token_hash
        
    except Exception as e:
        logger.error(f"Erro ao gerar token: {e}")
        return None

def validar_token_recuperacao(token: str) -> Tuple[bool, Optional[str]]:
    """Valida token de recuperação"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT email, expiracao 
            FROM tokens_recuperacao 
            WHERE token = ? 
            AND usado = 0
        ''', (token,))
        
        resultado = cursor.fetchone()
        
        if not resultado:
            conn.close()
            return False, "Token inválido ou já utilizado"
        
        email, expiracao = resultado
        
        if datetime.now() > datetime.fromisoformat(expiracao):
            cursor.execute('UPDATE tokens_recuperacao SET usado = 1 WHERE token = ?', (token,))
            conn.commit()
            conn.close()
            return False, "Token expirado"
        
        conn.close()
        return True, email
        
    except Exception as e:
        logger.error(f"Erro ao validar token: {e}")
        return False, "Erro ao validar token"

def marcar_token_como_usado(token: str):
    """Marca token como utilizado"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        cursor.execute('UPDATE tokens_recuperacao SET usado = 1 WHERE token = ?', (token,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao marcar token como usado: {e}")

def enviar_email_recuperacao_real(email: str, token: str) -> Tuple[bool, str]:
    """Envia email REAL com link de recuperação"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Em app.py, na função enviar_email_recuperacao_real()
        smtp_config = {
            "host": os.getenv('EMAIL_SMTP_HOST', 'smtp.gmail.com'),
            "port": int(os.getenv('EMAIL_SMTP_PORT', '587')),
            "user": os.getenv('EMAIL_USER', ''),
            "password": os.getenv('EMAIL_PASSWORD', ''),
            "from": os.getenv('EMAIL_FROM', 'noreply@dbmilesx.com')
        }
        
        if not smtp_config["user"] or not smtp_config["password"]:
            logger.error("Credenciais de email não configuradas no secrets.toml")
            return False, "Configuração de email incompleta. Configure o arquivo secrets.toml"
        
        app_url = st.secrets.get("email", {}).get("APP_URL", "dbmilesx.streamlit.app")
        base_url = f"https://{app_url}"
        link_recuperacao = f"{base_url}/?token={token}"
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "🔐 Redefinição de Senha - DBMILESX"
        msg['From'] = smtp_config["from"]
        msg['To'] = email
        msg['Reply-To'] = smtp_config["from"]
        
        text = f"""Redefinição de Senha - DBMILESX

Olá,

Recebemos uma solicitação para redefinir sua senha no DBMILESX.

Clique no link abaixo para criar uma nova senha:
{link_recuperacao}

Este link expirará em 1 hora.

Se você não solicitou esta redefinição, ignore este email.

Atenciosamente,
Equipe DBMILESX"""
        
        html = f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #3d8bfd, #2a5cbd); padding: 20px; border-radius: 10px 10px 0 0;">
        <h2 style="color: white; margin: 0; text-align: center;">🔐 DBMILESX</h2>
    </div>
    <div style="padding: 30px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 10px 10px;">
        <h3 style="color: #3d8bfd; margin-top: 0;">Redefinição de Senha</h3>
        <p>Olá,</p>
        <p>Recebemos uma solicitação para redefinir sua senha no <strong>DBMILESX</strong>.</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{link_recuperacao}" 
               style="background-color: #3d8bfd; 
                      color: white; 
                      padding: 15px 30px; 
                      text-decoration: none; 
                      border-radius: 8px; 
                      font-weight: bold;
                      display: inline-block;
                      font-size: 16px;
                      box-shadow: 0 4px 12px rgba(61, 139, 253, 0.3);">
                🔑 Redefinir Minha Senha
            </a>
        </div>
        
        <p>Ou copie e cole este link em seu navegador:</p>
        <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #3d8bfd;">
            <code style="word-break: break-all; color: #333;">{link_recuperacao}</code>
        </div>
        
        <div style="background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107; margin: 20px 0;">
            <p style="margin: 0; color: #856404;">
                <strong>⚠️ Atenção:</strong> Este link expirará em <strong>1 hora</strong>.
            </p>
        </div>
        
        <p>Se você não solicitou esta redefinição, ignore este email.</p>
        
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        
        <div style="font-size: 12px; color: #777; text-align: center;">
            <p style="margin: 5px 0;">Equipe DBMILESX</p>
            <p style="margin: 5px 0;">Sistema de Cotação Aérea</p>
            <p style="margin: 5px 0;">Este é um email automático, por favor não responda.</p>
        </div>
    </div>
</body>
</html>"""
        
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        logger.info(f"Tentando enviar email para {email} via {smtp_config['host']}:{smtp_config['port']}")
        
        try:
            server = smtplib.SMTP(smtp_config["host"], smtp_config["port"], timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_config["user"], smtp_config["password"])
            server.sendmail(smtp_config["from"], email, msg.as_string())
            server.quit()
            
            logger.info(f"✅ Email enviado com sucesso para {email}")
            return True, "✅ Email enviado com sucesso! Verifique sua caixa de entrada (e spam)."
            
        except smtplib.SMTPAuthenticationError:
            logger.error("Falha na autenticação SMTP. Verifique usuário/senha.")
            return False, "❌ Falha na autenticação. Verifique as credenciais SMTP."
        except smtplib.SMTPException as smtp_error:
            logger.error(f"Erro SMTP: {smtp_error}")
            return False, f"❌ Erro ao enviar email: {str(smtp_error)}"
        except Exception as conn_error:
            logger.error(f"Erro de conexão: {conn_error}")
            return False, f"❌ Erro de conexão: {str(conn_error)}"
        
    except Exception as e:
        logger.error(f"Erro geral ao enviar email: {e}")
        return False, f"❌ Erro ao enviar email: {str(e)[:100]}"

def enviar_email_recuperacao(email: str, token: str, modo_simulado: Optional[bool] = None) -> Tuple[bool, str]:
    """Envia email com link de recuperação"""
    try:
        try:
            has_creds = all([
                st.secrets.get("email", {}).get("USER", ""),
                st.secrets.get("email", {}).get("PASSWORD", "")
            ])
        except:
            has_creds = False
        
        if modo_simulado is None:
            modo_simulado = not has_creds
        
        if modo_simulado:
            if os.getenv('STREAMLIT_CLOUD'):
                base_url = f"https://{st.secrets.get('email', {}).get('APP_URL', 'dbmilesx.streamlit.app')}"
            else:
                base_url = "http://localhost:8501"
            
            link_recuperacao = f"{base_url}/?token={token}"
            
            logger.info(f"📧 EMAIL SIMULADO para {email}: {link_recuperacao}")
            
            st.info(f"""
            **📧 Email Simulado (Desenvolvimento)**
            
            **Para:** {email}
            **Link de recuperação:** {link_recuperacao}
            
            *Copie e cole este link no navegador para redefinir sua senha.*
            *Em produção com SMTP configurado, um email real seria enviado.*
            """)
            
            return True, "✅ Email simulado enviado. Configure SMTP no secrets.toml para emails reais."
        else:
            return enviar_email_recuperacao_real(email, token)
            
    except Exception as e:
        logger.error(f"❌ Erro ao enviar email: {e}")
        return False, f"❌ Erro ao enviar email: {str(e)[:100]}"

def inicializar_tabela_tokens():
    """Inicializa tabela de tokens de recuperação"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tokens_recuperacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expiracao TIMESTAMP NOT NULL,
                usado INTEGER DEFAULT 0,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tokens_token ON tokens_recuperacao(token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tokens_email ON tokens_recuperacao(email)')
        
        conn.commit()
        conn.close()
        logger.info("Tabela de tokens de recuperação inicializada")
        
    except Exception as e:
        logger.error(f"Erro ao inicializar tabela de tokens: {e}")

def reparar_tabela_historico():
    """Repara/recria a tabela historico_cotacoes se necessário"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='historico_cotacoes'")
        tabela_existe = cursor.fetchone()
        
        if tabela_existe:
            cursor.execute("PRAGMA table_info(historico_cotacoes)")
            colunas = cursor.fetchall()
            colunas_nomes = [col[1] for col in colunas]
            
            colunas_seguranca = [
                ('passageiros', 'INTEGER DEFAULT 1'),
                ('bebes', 'INTEGER DEFAULT 0'),
                ('num_bagagens', 'INTEGER DEFAULT 0'),
                ('metadata', 'TEXT')
            ]
            
            for coluna, tipo in colunas_seguranca:
                if coluna not in colunas_nomes:
                    try:
                        cursor.execute(f'ALTER TABLE historico_cotacoes ADD COLUMN {coluna} {tipo}')
                        logger.info(f"Coluna {coluna} adicionada")
                    except Exception as e:
                        logger.warning(f"Erro ao adicionar coluna {coluna}: {e}")
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao reparar tabela: {e}")

def registrar_evento_seguranca(usuario_id: Optional[int], tipo: str, descricao: str, 
                               nivel_severidade: str = "INFO", metadata: Optional[Dict] = None):
    """Registra evento de segurança com metadados"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute('''
        INSERT INTO logs_seguranca (usuario_id, tipo_evento, nivel_severidade, descricao, metadata)
        VALUES (?, ?, ?, ?, ?)
        ''', (usuario_id, tipo, nivel_severidade, descricao, metadata_json))
        
        conn.commit()
        conn.close()
        
        log_msg = f"[{nivel_severidade}] {tipo}: {descricao}"
        if nivel_severidade in ['ERROR', 'CRITICAL']:
            logger.error(log_msg)
        elif nivel_severidade == 'WARNING':
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
            
    except Exception as e:
        logger.error(f"Erro ao registrar evento: {e}")

    
def pagina_redefinir_senha_com_token(token: str):
    """Página para redefinir senha usando token da URL"""
    cores = get_colors()
    logo_base64 = carregar_logo()
    
    st.markdown(f"""
    <div class="login-container fade-in">
        <div style="text-align: center; margin-bottom: 2rem;">
            <img src="data:image/png;base64,{logo_base64}" style="max-width: 200px; border-radius: 15px; margin-bottom: 1.5rem;">
            <h1 style='color: {cores['destaque']}; margin-top: 0.5rem;'>🔐 Redefinir Senha</h1>
            <p style='color: {cores['texto']}80; font-size: 1.1rem; margin-bottom: 0.5rem;'>DBMILESX - Sistema de Cotação Aérea</p>
        </div>
    """, unsafe_allow_html=True)
    
    with st.spinner("🔍 Validando token..."):
        token_valido, resultado = validar_token_recuperacao(token)
    
    if not token_valido:
        st.error(f"❌ {resultado}")
        st.markdown("""
        <div style='text-align: center; margin-top: 2rem;'>
            <p>O token é inválido, expirou ou já foi utilizado.</p>
            <p>Solicite um novo link de recuperação na página de login.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("← Voltar para Login", type="primary", use_container_width=True):
            try:
                if hasattr(st, 'query_params'):
                    for key in list(st.query_params.keys()):
                        del st.query_params[key]
            except:
                pass
            st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    email = resultado
    
    st.info(f"🔐 Redefinindo senha para: **{email}**")
    
    with st.form("form_redefinir_senha_token"):
        nova_senha = st.text_input(
            "**Nova Senha**",
            type="password",
            placeholder="Mínimo 8 caracteres",
            key="nova_senha_token"
        )
        
        confirmar_senha = st.text_input(
            "**Confirmar Nova Senha**",
            type="password",
            placeholder="Digite novamente",
            key="confirmar_senha_token"
        )
        
        if nova_senha:
            validacao = security.validate_password_strength(nova_senha)
            progresso = min(validacao['score'] * (100/validacao['max_score']), 100)
            
            col_score1, col_score2 = st.columns([3, 1])
            with col_score1:
                st.progress(progresso / 100)
            with col_score2:
                st.markdown(f"<p style='color:{validacao['color']};font-weight:bold;text-align:center;'>{validacao['classification']}</p>", unsafe_allow_html=True)
        
        redefinir = st.form_submit_button("🔐 Redefinir Senha", type="primary", use_container_width=True)
        
        if redefinir:
            if not nova_senha or not confirmar_senha:
                st.error("❌ Preencha todos os campos!")
            elif nova_senha != confirmar_senha:
                st.error("❌ As senhas não coincidem!")
            elif validacao and not validacao['valid']:
                st.error("❌ A senha não atende aos requisitos mínimos de segurança!")
            else:
                with st.spinner("🔐 Redefinindo senha..."):
                    sucesso, mensagem = redefinir_senha(email, nova_senha)
                    
                    if sucesso:
                        marcar_token_como_usado(token)
                        
                        conn = criar_conexao()
                        cursor = conn.cursor()
                        cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
                        usuario = cursor.fetchone()
                        conn.close()
                        
                        if usuario:
                            registrar_evento_seguranca(
                                usuario[0],
                                "SENHA_REDEFINIDA_TOKEN",
                                f"Senha redefinida via token de recuperação",
                                "INFO"
                            )
                        
                        st.success("✅ Senha redefinida com sucesso!")
                        st.info("⚡ Você já pode fazer login com sua nova senha.")
                        
                        time.sleep(3)
                        
                        try:
                            if hasattr(st, 'query_params'):
                                st.query_params.clear()
                        except:
                            pass
                        st.rerun()
                    else:
                        st.error(f"❌ {mensagem}")
    
    st.markdown("</div>", unsafe_allow_html=True)

def get_query_params():
    """Função wrapper para compatibilidade com diferentes versões do Streamlit"""
    try:
        if hasattr(st, 'query_params'):
            return st.query_params.to_dict()
        else:
            return st.experimental_get_query_params()
    except AttributeError:
        return {}

def get_query_param(key, default=None):
    """Obtém um parâmetro da URL"""
    params = get_query_params()
    
    if not params:
        return default
    
    if key in params:
        value = params[key]
        if isinstance(value, list):
            return value[0] if value else default
        return value
    return default

def pagina_login_melhorada():
    """Página de login melhorada com abas, cadastro, recuperação de senha e segurança reforçada"""
    
    # Verificar se há token de recuperação na URL
    token = get_query_param('token')
    if token:
        pagina_redefinir_senha_com_token(token)
        return
    
    cores = get_colors()
    logo_base64 = carregar_logo()
    
    # CSS personalizado para a página de login
    st.markdown(f"""
    <style>
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css');
    
    .login-wrapper {{
        max-width: 450px;
        margin: 2rem auto;
        padding: 2rem;
        background: {cores['card']};
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        border: 1px solid {cores['borda']};
        animation: fadeIn 0.5s ease-out;
    }}
    
    .logo-container {{
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
    }}
    
    .logo-container img {{
        max-width: 250px;
        height: auto;
        border-radius: 15px;
        transition: transform 0.3s ease;
    }}
    
    .logo-container img:hover {{
        transform: scale(1.02);
    }}
    
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: {cores['fundo']};
        padding: 0.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }}
    
    .stTabs [aria-selected="true"] {{
        background-color: {cores['destaque']} !important;
        color: white !important;
    }}
    
    .password-strength-meter {{
        margin-top: 0.5rem;
        padding: 0.75rem;
        border-radius: 8px;
        background: {cores['fundo']};
        font-size: 0.9rem;
    }}
    
    .security-badge {{
        background: {cores['success']}15;
        border-left: 4px solid {cores['success']};
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        font-size: 0.9rem;
    }}
    
    .security-badge i {{
        color: {cores['success']};
        margin-right: 0.5rem;
    }}
    
    .info-box {{
        background: {cores['info']}15;
        border: 1px solid {cores['info']}30;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        font-size: 0.9rem;
    }}
    
    .success-box {{
        background: {cores['success']}15;
        border: 1px solid {cores['success']}30;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        color: {cores['success']};
    }}
    
    .warning-box {{
        background: {cores['warning']}15;
        border: 1px solid {cores['warning']}30;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        color: {cores['warning']};
    }}
    
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(20px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    
    .footer-links {{
        text-align: center;
        margin-top: 2rem;
        padding-top: 1rem;
        border-top: 1px solid {cores['borda']};
        font-size: 0.85rem;
        color: {cores['texto']}70;
    }}
    
    .social-proof {{
        display: flex;
        justify-content: center;
        gap: 1.5rem;
        margin-top: 1.5rem;
        color: {cores['texto']}50;
        font-size: 0.85rem;
    }}
    
    .social-proof i {{
        margin-right: 0.5rem;
        color: {cores['destaque']};
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # Wrapper principal
    st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
    
    # Logo e título
    st.markdown(f"""
    <div class="logo-container fade-in">
        <img src="data:image/png;base64,{logo_base64}" alt="DBMILESX Logo">
        <h1 style='color: {cores['destaque']}; margin: 1rem 0 0.5rem 0;'>DBMILESX</h1>
        <p style='color: {cores['texto']}80; font-size: 1.1rem; margin-bottom: 0.5rem;'>Sistema de Cotação Aérea</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Abas de navegação
    tab1, tab2, tab3 = st.tabs(["🔐 LOGIN", "📝 CADASTRO", "🔑 RECUPERAR SENHA"])
    
    # ============= ABA DE LOGIN =============
    with tab1: 
        st.markdown(f"""
        <div class='security-badge fade-in'>
            <i class="fas fa-shield-alt"></i> <strong>Conexão Segura</strong> • Proteção contra força bruta • Criptografia bcrypt • Tokens CSRF
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input(
                "📧 **Email**",
                placeholder="seu@email.com",
                help="Digite seu email cadastrado",
                key="login_email"
            )
            
            senha = st.text_input(
                "🔒 **Senha**",
                type="password",
                placeholder="••••••••",
                help="Digite sua senha",
                key="login_senha"
            )
            
            col1, col2 = st.columns([1, 1])
            with col1:
                submit_login = st.form_submit_button("🚀 **ENTRAR**", type="primary", use_container_width=True)
            with col2:
                st.markdown("""
                <div style='text-align: center; margin-top: 8px;'>
                    <a href="#" style='color: #3d8bfd; text-decoration: none; font-size: 0.9rem;' onclick="alert('Clique na aba RECUPERAR SENHA')">
                        Esqueceu a senha?
                    </a>
                </div>
                """, unsafe_allow_html=True)
            
            if submit_login:
                if not email or not senha:
                    st.error("❌ Preencha todos os campos!")
                else:
                    # Verificar rate limiting
                    client_ip = login_manager.get_client_ip()
                    rate_key = f"login:{client_ip}:{email}"
                    
                    if not security.check_rate_limit(rate_key):
                        st.error("❌ Muitas tentativas. Aguarde 15 minutos.")
                        logger.warning(f"Rate limit excedido para {email} ({client_ip})")
                    else:
                        with st.spinner("🔐 Verificando credenciais..."):
                            time.sleep(0.5)
                            
                            sucesso, resultado = verificar_login(email, senha, DB_PATH)
                            
                            login_manager.record_attempt(email, sucesso, user_agent="Streamlit App")
                            
                            if sucesso:
                                st.session_state.logado = True
                                st.session_state.usuario_id = resultado['usuario_id']
                                st.session_state.usuario_nome = resultado['usuario_nome']
                                st.session_state.usuario_email = resultado['usuario_email']
                                st.session_state.empresa_id = resultado.get('empresa_id')
                                st.session_state.nivel_acesso = resultado.get('nivel_acesso', 'membro')
                                st.session_state.pagina = 'inicio'
                                st.session_state.sessao_token = secrets.token_urlsafe(32)
                                st.session_state.last_activity = time.time()
                                st.session_state.session_start = time.time()
                                st.session_state.csrf_token = security.generate_csrf_token()
                                
                                # ===== CARREGAR PREFERÊNCIAS DO BANCO (CORRIGIDO) =====
                                prefs = carregar_preferencias_usuario(resultado['usuario_id'])
                                if prefs:
                                    st.session_state.tema = prefs['tema_preferido']
                                    st.session_state.moeda = prefs['moeda_preferida']
                                    st.session_state.cor_primaria = prefs['cor_primaria']
                                    st.session_state.foto_perfil = prefs.get('foto_perfil')
                                    st.session_state.telefone = prefs.get('telefone')
                                    st.session_state.cargo = prefs.get('cargo')
                                else:
                                    st.session_state.tema = "escuro"
                                    st.session_state.moeda = "BRL"
                                    st.session_state.cor_primaria = '#3d8bfd'
                                
                                # Salvar preferências atuais no banco
                                from database import salvar_preferencias_usuario
                                salvar_preferencias_usuario(
                                    resultado['usuario_id'],
                                    tema=st.session_state.tema,
                                    moeda=st.session_state.moeda,
                                    cor_primaria=st.session_state.cor_primaria
                                )
                                
                                registrar_evento_seguranca(
                                    resultado['usuario_id'],
                                    "LOGIN_SUCESSO",
                                    f"Login bem-sucedido - IP: {client_ip}",
                                    "INFO",
                                    {"ip": client_ip}
                                )
                                
                                st.success(f"✅ Bem-vindo, {resultado['usuario_nome']}!")
                                time.sleep(1.5)
                                st.rerun()
                            else:
                                remaining = security.get_remaining_attempts(rate_key)
                                st.error(f"❌ {resultado}")
                                
                                if remaining > 0:
                                    st.warning(f"⚠️ Tentativas restantes: {remaining}")
    
    # ============= ABA DE CADASTRO =============
    with tab2:
        st.markdown(f"""
        <div class='info-box fade-in'>
            <i class="fas fa-info-circle"></i> <strong>Cadastro Seguro</strong> • Senhas criptografadas • Validação em tempo real • Política de senha forte
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("cadastro_form", clear_on_submit=True):
            nome = st.text_input(
                "👤 **Nome Completo**",
                placeholder="Digite seu nome",
                help="Mínimo de 3 caracteres",
                key="cadastro_nome"
            )
            
            email = st.text_input(
                "📧 **Email**",
                placeholder="seu@email.com",
                help="Digite um email válido",
                key="cadastro_email"
            )
            
            senha = st.text_input(
                "🔒 **Senha**",
                type="password",
                placeholder="Crie uma senha forte",
                help="Mínimo 8 caracteres com letras maiúsculas, minúsculas, números e caracteres especiais",
                key="cadastro_senha"
            )
            
            confirmar_senha = st.text_input(
                "🔒 **Confirmar Senha**",
                type="password",
                placeholder="Digite a senha novamente",
                key="cadastro_confirmar"
            )
            
            if senha:
                validacao = security.validate_password_strength(senha)
                progresso = min(validacao['score'] * 20, 100)
                
                st.markdown(f"""
                <div class='password-strength-meter'>
                    <div style='display: flex; justify-content: space-between; margin-bottom: 5px;'>
                        <span>Força da senha:</span>
                        <span style='color: {validacao['color']}; font-weight: bold;'>{validacao['classification']}</span>
                    </div>
                    <div style='background: #ddd; height: 8px; border-radius: 4px;'>
                        <div style='width: {progresso}%; background: {validacao['color']}; height: 8px; border-radius: 4px; transition: width 0.3s;'></div>
                    </div>
                    <ul style='margin-top: 10px; font-size: 0.85rem;'>
                        <li style='color: {"green" if len(senha) >= 8 else "gray"};'>✓ Mínimo 8 caracteres</li>
                        <li style='color: {"green" if any(c.isupper() for c in senha) else "gray"};'>✓ Pelo menos uma letra maiúscula</li>
                        <li style='color: {"green" if any(c.islower() for c in senha) else "gray"};'>✓ Pelo menos uma letra minúscula</li>
                        <li style='color: {"green" if any(c.isdigit() for c in senha) else "gray"};'>✓ Pelo menos um número</li>
                        <li style='color: {"green" if any(c in "!@#$%^&*(),.?\":{{}}|<>" for c in senha) else "gray"};'>✓ Pelo menos um caractere especial</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            
            aceite_termos = st.checkbox(
                "Li e aceito os **Termos de Uso** e a **Política de Privacidade**",
                value=False,
                key="aceite_termos"
            )
            
            submit_cadastro = st.form_submit_button("📝 **CRIAR CONTA**", type="primary", use_container_width=True)
            
            if submit_cadastro:
                if not all([nome, email, senha, confirmar_senha]):
                    st.error("❌ Preencha todos os campos!")
                elif not aceite_termos:
                    st.error("❌ Você precisa aceitar os termos de uso!")
                elif senha != confirmar_senha:
                    st.error("❌ As senhas não coincidem!")
                else:
                    with st.spinner("🔐 Criando sua conta segura..."):
                        validacao = security.validate_password_strength(senha)
                        if not validacao['valid']:
                            st.error(f"❌ Senha muito fraca: {', '.join(validacao['feedback'][:2])}")
                        else:
                            sucesso, mensagem = registrar_usuario(email, senha, nome)
                            
                            if sucesso:
                                st.success(f"✅ {mensagem}")
                                st.balloons()
                                st.info("🔐 Agora faça login na aba LOGIN")
                                time.sleep(2)
                            else:
                                st.error(f"❌ {mensagem}")
    
    # ============= ABA DE RECUPERAÇÃO DE SENHA =============
    with tab3:
        st.markdown(f"""
        <div class='warning-box fade-in'>
            <i class="fas fa-exclamation-triangle"></i> <strong>Recuperação de Senha</strong> • Enviaremos um link seguro para seu email • Válido por 1 hora
        </div>
        """, unsafe_allow_html=True)
        
        if 'recuperacao_etapa' not in st.session_state:
            st.session_state.recuperacao_etapa = 'email'
        
        if st.session_state.recuperacao_etapa == 'email':
            with st.form("recuperar_email_form"):
                email_rec = st.text_input(
                    "📧 **Email Cadastrado**",
                    placeholder="Digite seu email",
                    help="Enviaremos um link de recuperação para este email",
                    key="recuperar_email"
                )
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    submit_rec = st.form_submit_button("📧 **ENVIAR LINK**", type="primary", use_container_width=True)
                with col2:
                    if st.form_submit_button("🔙 **VOLTAR**", use_container_width=True):
                        st.session_state.recuperacao_etapa = 'email'
                        st.rerun()
                
                if submit_rec:
                    if not email_rec or not security.validate_email(email_rec):
                        st.error("❌ Email inválido!")
                    else:
                        with st.spinner("🔐 Gerando link seguro..."):
                            client_ip = login_manager.get_client_ip()
                            rate_key = f"recuperacao:{client_ip}:{email_rec}"
                            
                            if not security.check_rate_limit(rate_key, max_attempts=3):
                                st.error("❌ Muitas tentativas. Aguarde 15 minutos.")
                            else:
                                token = gerar_token_recuperacao(email_rec)
                                
                                if token:
                                    sucesso, mensagem = enviar_email_recuperacao(email_rec, token)
                                    
                                    if sucesso:
                                        st.success(f"✅ {mensagem}")
                                        st.session_state.recuperacao_etapa = 'confirmacao'
                                        st.session_state.recuperacao_email = email_rec
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {mensagem}")
                                else:
                                    st.success("✅ Se o email estiver cadastrado, você receberá instruções.")
                                    logger.info(f"Tentativa de recuperação para email não cadastrado: {email_rec}")
        
        elif st.session_state.recuperacao_etapa == 'confirmacao':
            email_rec = st.session_state.get('recuperacao_email', '')
            
            st.markdown(f"""
            <div class='success-box'>
                <i class="fas fa-envelope"></i> <strong>Email Enviado!</strong><br><br>
                Enviamos instruções para:<br>
                <strong>{email_rec}</strong><br><br>
                Verifique sua caixa de entrada e pasta de spam.
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("📧 **REENVIAR**", use_container_width=True):
                    st.session_state.recuperacao_etapa = 'email'
                    st.rerun()
            
            with st.expander("📬 Não recebeu o email?"):
                st.markdown("""
                1. Verifique a pasta de **Spam** ou **Lixo Eletrônico**
                2. Adicione **noreply@dbmilesx.com** aos contatos
                3. Aguarde alguns minutos e tente novamente
                4. Certifique-se de usar o email cadastrado
                """)
                
                if st.button("🔁 **Tentar novamente**", use_container_width=True):
                    st.session_state.recuperacao_etapa = 'email'
                    st.rerun()
    
    # Selo de segurança
    st.markdown(f"""
    <div class='footer-links'>
        <div class='social-proof'>
            <span><i class="fas fa-lock"></i> Criptografia bcrypt</span>
            <span><i class="fas fa-shield-alt"></i> Tokens CSRF</span>
            <span><i class="fas fa-clock"></i> Sessão segura</span>
        </div>
        <div style='margin-top: 1rem;'>
            <span style='color: {cores['texto']}30;'>© 2024 DBMILESX - Todos os direitos reservados</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Versão do sistema
    st.markdown(f"""
    <div style='text-align: center; margin-top: 1rem; color: {cores['texto']}30; font-size: 0.75rem;'>
        v3.0.0 • Ambiente {'🌐 Cloud' if os.getenv('STREAMLIT_CLOUD') else '💻 Local'} • Segurança Nível A+
    </div>
    """, unsafe_allow_html=True)

def validar_forca_senha(senha: str) -> Dict[str, Any]:
    """Valida força da senha (wrapper seguro)"""
    senha = senha.strip()
    return security.validate_password_strength(senha)

def criar_cotacao(usuario_id: int, nome: str, origem: str, destino: str) -> Tuple[bool, Any]:
    """Cria uma nova cotação com verificação de segurança"""
    try:
        nome = security.sanitize_input(nome)
        origem = security.sanitize_input(origem)
        destino = security.sanitize_input(destino)
        
        if not nome.strip() or len(nome.strip()) < 3:
            return False, "Nome da cotação deve ter pelo menos 3 caracteres"
        
        if len(nome.strip()) > 100:
            return False, "Nome da cotação muito longo"
        
        if not origem.strip() or not destino.strip():
            return False, "Origem e destino são obrigatórios"
        
        if len(origem.strip()) > 50 or len(destino.strip()) > 50:
            return False, "Origem ou destino muito longos"
        
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM cotacoes WHERE usuario_id = ? AND date(data_criacao) = date("now")', (usuario_id,))
        cotacoes_hoje = cursor.fetchone()[0]
        
        if cotacoes_hoje >= 50:
            conn.close()
            return False, "Limite diário de cotações atingido"
        
        cursor.execute('''
        INSERT INTO cotacoes (usuario_id, nome, origem, destino) 
        VALUES (?, ?, ?, ?)
        ''', (usuario_id, nome.strip(), origem.strip(), destino.strip()))
        
        cotacao_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        registrar_evento_seguranca(
            usuario_id,
            "COTACAO_CRIADA",
            f"Cotação criada: {nome}",
            "INFO",
            {"cotacao_id": cotacao_id, "origem": origem, "destino": destino}
        )
        
        return True, cotacao_id
    except Exception as e:
        logger.error(f"Erro ao criar cotação: {e}")
        return False, f"Erro: {str(e)}"
# ===== NO ARQUIVO app.py, ATUALIZE a função salvar_calculo() =====
def salvar_calculo(dados: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Salva um cálculo no histórico com dados sensíveis criptografados.
    Versão completa e segura.
    """
    try:
        # ===== VALIDAÇÕES DE SEGURANÇA =====
        if not dados.get("usuario_id"):
            return False, "Usuário não identificado"
            
        if not dados.get("cotacao_id"):
            return False, "Cotação não identificada"
        
        # Validar valores numéricos para evitar injeção
        if dados.get("total_geral", 0) < 0 or dados.get("total_geral", 0) > 10000000:
            return False, "Valor total inválido"
        
        # Sanitizar strings
        companhia = security.sanitize_input(dados.get("companhia", ""))
        tipo_calculo = security.sanitize_input(dados.get("tipo_calculo", ""))
        moeda = security.sanitize_input(dados.get("moeda", "BRL"))
        
        # ===== CONEXÃO COM BANCO =====
        conn = criar_conexao()
        cursor = conn.cursor()
        
        # Verificar se usuário existe
        cursor.execute('SELECT id FROM usuarios WHERE id = ?', (dados['usuario_id'],))
        if not cursor.fetchone():
            conn.close()
            return False, "Usuário não encontrado"
        
        # Verificar se cotação existe e pertence ao usuário
        cursor.execute('SELECT id FROM cotacoes WHERE id = ? AND usuario_id = ?', 
                      (dados['cotacao_id'], dados['usuario_id']))
        if not cursor.fetchone():
            conn.close()
            return False, "Cotação não encontrada ou acesso negado"
        
        # ===== PREPARAR METADADOS PARA CRIPTOGRAFIA =====
        metadata = {
            # Dados da calculadora
            "passageiros": dados.get("passageiros", 1),
            "bebes": dados.get("bebes", 0),
            "num_bagagens": dados.get("num_bagagens", 0),
            "valor_bagagem_unitaria": dados.get("valor_bagagem_unitaria", 0),
            "timestamp": datetime.now().isoformat(),
            
            # Dados da viagem
            "tipo_viagem": st.session_state.get('tipo_viagem', 'Ida e Volta'),
            "data_ida": st.session_state.get('data_ida_para_cotacao', ''),
            "data_volta": st.session_state.get('data_volta_para_cotacao', ''),
            
            # Campos específicos LATAM
            "tipo_tarifa": dados.get('tipo_tarifa', ''),
            "bagagens_inclusas": dados.get('bagagens_inclusas', 0),
            "bagagens_adicionais": dados.get('bagagens_adicionais', 0),
            "milhas_por_pax": dados.get('milhas_por_pax', 0),
            
            # Campos específicos AZUL
            "desconto_taxa_aplicado": dados.get('desconto_taxa_aplicado', 0),
            "taxa_original": dados.get('taxa_original', 0),
            "taxa_com_desconto": dados.get('taxa_com_desconto', 0),
            
            # Dados adicionais da calculadora
            "milhas_total": dados.get("milhas_total", 0),
            "valor_milheiro": dados.get("valor_milheiro", 0),
            "taxa_embarque": dados.get("taxa_embarque", 0),
            "valor_base": dados.get("valor_base", 0),
            "valor_bagagens": dados.get("valor_bagagens", 0),
            "desagio_percentual": dados.get("desagio_percentual", 0)
        }
        
        # Remover campos vazios para economizar espaço
        metadata = {k: v for k, v in metadata.items() if v not in (None, '', 0)}
        
        # ===== CRIPTOGRAFAR METADADOS =====
        if metadata:
            # Converter para JSON e criptografar
            metadata_json = json.dumps(metadata, ensure_ascii=False, default=str)
            metadata_criptografado = data_crypto.encrypt(metadata_json)
        else:
            metadata_criptografado = None
        
        # ===== INSERIR NO BANCO =====
        cursor.execute('''
        INSERT INTO historico_cotacoes 
        (usuario_id, cotacao_id, companhia, tipo_calculo, milhas_total, valor_milheiro, 
         taxa_embarque, valor_base, valor_bagagens, desagio_percentual, total_geral, 
         moeda, passageiros, bebes, num_bagagens, metadata_criptografado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            dados["usuario_id"],
            dados["cotacao_id"],
            companhia,
            tipo_calculo,
            dados.get("milhas_total", 0),
            dados.get("valor_milheiro", 0),
            dados.get("taxa_embarque", 0),
            dados.get("valor_base", 0),
            dados.get("valor_bagagens", 0),
            dados.get("desagio_percentual", 0),
            dados["total_geral"],
            moeda,
            dados.get("passageiros", 1),
            dados.get("bebes", 0),
            dados.get("num_bagagens", 0),
            metadata_criptografado
        ))
        
        historico_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # ===== REGISTRAR EVENTO DE SEGURANÇA =====
        registrar_evento_seguranca(
            dados['usuario_id'], 
            "CALCULO_SALVO", 
            f"Cotação {dados['cotacao_id']} salva - {companhia}",
            "INFO",
            {
                "historico_id": historico_id,
                "cotacao_id": dados['cotacao_id'],
                "companhia": companhia,
                "total_geral": dados["total_geral"],
                "moeda": moeda,
                "tipo_viagem": st.session_state.get('tipo_viagem', 'Ida e Volta')
            }
        )
        
        logger.info(f"✅ Cálculo {historico_id} salvo com sucesso para usuário {dados['usuario_id']}")
        return True, "Cálculo salvo com sucesso!"
            
    except sqlite3.Error as e:
        logger.error(f"Erro SQL ao salvar cálculo: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False, f"Erro no banco de dados: {str(e)}"
        
    except Exception as e:
        logger.error(f"Erro ao salvar cálculo: {e}")
        logger.error(traceback.format_exc())
        if 'conn' in locals():
            try:
                conn.rollback()
                conn.close()
            except:
                pass
        return False, f"Erro interno: {str(e)[:100]}"
    

def adicionar_coluna_metadata_criptografado():
    """
    Adiciona a coluna metadata_criptografado à tabela historico_cotacoes.
    Executar UMA VEZ para migração.
    """
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        # Verificar se a coluna já existe
        cursor.execute("PRAGMA table_info(historico_cotacoes)")
        colunas = cursor.fetchall()
        colunas_nomes = [col[1] for col in colunas]
        
        if 'metadata_criptografado' not in colunas_nomes:
            # Adicionar nova coluna
            cursor.execute('''
            ALTER TABLE historico_cotacoes 
            ADD COLUMN metadata_criptografado TEXT
            ''')
            logger.info("✅ Coluna 'metadata_criptografado' adicionada à tabela historico_cotacoes")
            
            # Migrar dados existentes (opcional)
            cursor.execute('''
            SELECT id, metadata FROM historico_cotacoes 
            WHERE metadata IS NOT NULL AND metadata != ''
            ''')
            registros_antigos = cursor.fetchall()
            
            for row in registros_antigos:
                hist_id, metadata_antigo = row
                try:
                    # Criptografar o metadata antigo
                    if metadata_antigo:
                        metadata_criptografado = data_crypto.encrypt(metadata_antigo)
                        cursor.execute('''
                        UPDATE historico_cotacoes 
                        SET metadata_criptografado = ? 
                        WHERE id = ?
                        ''', (metadata_criptografado, hist_id))
                except Exception as e:
                    logger.error(f"Erro ao migrar registro {hist_id}: {e}")
            
            conn.commit()
            logger.info(f"✅ Migrados {len(registros_antigos)} registros antigos")
        else:
            logger.info("ℹ️ Coluna 'metadata_criptografado' já existe")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Erro ao adicionar coluna: {e}")
        return False

def listar_historico(usuario_id: int, filtro_companhia: Optional[str] = None, 
                    data_inicio: Optional[str] = None, data_fim: Optional[str] = None,
                    limite: int = 100) -> List[Dict[str, Any]]:
    """
    Lista histórico de cálculos do usuário com dados descriptografados.
    """
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        # Query com JOIN para pegar dados da cotação
        query = '''
        SELECT h.*, c.nome as nome_cotacao, c.origem, c.destino 
        FROM historico_cotacoes h
        JOIN cotacoes c ON h.cotacao_id = c.id
        WHERE h.usuario_id = ?
        '''
        params = [usuario_id]
        
        # Aplicar filtros
        if filtro_companhia and filtro_companhia != "Todas":
            query += ' AND h.companhia = ?'
            params.append(filtro_companhia)
        
        if data_inicio:
            query += ' AND date(h.data_calculo) >= ?'
            params.append(data_inicio)
        
        if data_fim:
            query += ' AND date(h.data_calculo) <= ?'
            params.append(data_fim)
        
        query += ' ORDER BY h.data_calculo DESC LIMIT ?'
        params.append(limite)
        
        # Executar query
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        
        # Obter nomes das colunas
        colunas = [desc[0] for desc in cursor.description]
        
        # Processar resultados
        historico = []
        for row in resultados:
            item = dict(zip(colunas, row))
            
            # ===== DESCRIPTOGRAFAR METADADOS =====
            if item.get('metadata_criptografado'):
                try:
                    # Descriptografar
                    metadata_json = data_crypto.decrypt(item['metadata_criptografado'])
                    # Converter JSON para dicionário
                    item['metadata'] = json.loads(metadata_json)
                    
                    # Mover dados do metadata para o nível principal para compatibilidade
                    if item['metadata']:
                        for key, value in item['metadata'].items():
                            # Não sobrescrever campos existentes
                            if key not in item or not item[key]:
                                item[key] = value
                    
                except Exception as e:
                    logger.error(f"Erro ao descriptografar metadata do histórico {item.get('id')}: {e}")
                    item['metadata'] = {}
            else:
                # Compatibilidade com registros antigos (não criptografados)
                if item.get('metadata'):
                    try:
                        if isinstance(item['metadata'], str):
                            item['metadata'] = json.loads(item['metadata'])
                        elif isinstance(item['metadata'], dict):
                            pass  # Já é dict
                        else:
                            item['metadata'] = {}
                    except:
                        item['metadata'] = {}
                else:
                    item['metadata'] = {}
            
            # Remover campo criptografado bruto
            if 'metadata_criptografado' in item:
                del item['metadata_criptografado']
            
            # Garantir valores padrão para campos que podem ser None
            item['passageiros'] = item.get('passageiros') or 1
            item['bebes'] = item.get('bebes') or 0
            item['num_bagagens'] = item.get('num_bagagens') or 0
            
            historico.append(item)
        
        conn.close()
        
        logger.info(f"📊 Listados {len(historico)} registros do histórico para usuário {usuario_id}")
        return historico
        
    except Exception as e:
        logger.error(f"Erro ao listar histórico: {e}")
        logger.error(traceback.format_exc())
        return []

def excluir_calculo(calculo_id: int, usuario_id: int) -> Tuple[bool, str]:
    """Exclui um cálculo do histórico com verificação de autorização"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('SELECT usuario_id FROM historico_cotacoes WHERE id = ?', (calculo_id,))
        resultado = cursor.fetchone()
        
        if not resultado:
            conn.close()
            return False, "Cálculo não encontrado"
        
        if resultado[0] != usuario_id:
            conn.close()
            registrar_evento_seguranca(
                usuario_id,
                "TENTATIVA_ACESSO_NAO_AUTORIZADO",
                f"Tentativa de excluir cálculo {calculo_id} de outro usuário",
                "WARNING"
            )
            return False, "Acesso não autorizado"
        
        cursor.execute('SELECT companhia, total_geral, moeda FROM historico_cotacoes WHERE id = ?', (calculo_id,))
        dados_calc = cursor.fetchone()
        
        cursor.execute('DELETE FROM historico_cotacoes WHERE id = ?', (calculo_id,))
        conn.commit()
        
        if dados_calc:
            registrar_evento_seguranca(
                usuario_id,
                "CALCULO_EXCLUIDO",
                f"Cálculo {calculo_id} excluído - {dados_calc[0]} {dados_calc[1]} {dados_calc[2]}",
                "INFO"
            )
        
        conn.close()
        return True, "Cotação excluída com sucesso!"
    except Exception as e:
        logger.error(f"Erro ao excluir cálculo: {e}")
        return False, f"Erro: {str(e)}"

def pagina_inicio():
    """Página inicial (Dashboard)"""
    cores = get_colors()
    logo_base64 = carregar_logo()
    
    st.markdown(f"""
    <div class="fade-in">
        <div style="text-align: center; margin-bottom: 2rem;">
            <img src="data:image/png;base64,{logo_base64}" style="max-width: 200px; margin-bottom: 1rem;">
            <h1 style='color: {cores['destaque']};'>✈️ Sistema Aéreo DBMILESX</h1>
            <p style='color: {cores['texto']}80;'>Sistema profissional para cotação de passagens aéreas</p>
            <div class='security-success'>
                <small>🔒 Sessão segura ativa • Último login: {datetime.now().strftime('%d/%m/%Y %H:%M')}</small>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"### 👋 Olá, {st.session_state.usuario_nome}!")
    
    col_acao1, col_acao2, col_acao3, col_acao4 = st.columns(4)
    
    with col_acao1:
        if st.button(f"🛫 Nova Cotação", use_container_width=True, type="primary", key="btn_nova_cotacao_inicio"):
            st.session_state.pagina = 'nova_cotacao'
            st.rerun()
    
    with col_acao2:
        if st.button(f"✈️ Ver Companhias", use_container_width=True, type="primary", key="btn_companhias_inicio"):
            st.session_state.pagina = 'companhias'
            st.rerun()
    
    with col_acao3:
        if st.button(f"📜 Ver Histórico", use_container_width=True, type="primary", key="btn_historico_inicio"):
            st.session_state.pagina = 'historico'
            st.rerun()
    
    with col_acao4:
        if st.button(f"⚙️ Configurações", use_container_width=True, type="primary", key="btn_config_inicio"):
            st.session_state.pagina = 'configuracoes'
            st.rerun()
    
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class='card'>
            <div style='text-align: center;'>
                <h3 style='color: {cores['destaque']}; margin-bottom: 0.5rem;'>📊</h3>
                <h4>Dashboard</h4>
                <p style='color: {cores['texto']}70;'>Resumo do sistema</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='card'>
            <div style='text-align: center;'>
                <h3 style='color: {cores['destaque']}; margin-bottom: 0.5rem;'>✈️</h3>
                <h4>Companhias</h4>
                <p style='color: {cores['texto']}70;'>4 disponíveis</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        tema_display = "🌙 Escuro" if st.session_state.tema == 'escuro' else "☀️ Claro"
        st.markdown(f"""
        <div class='card'>
            <div style='text-align: center;'>
                <h3 style='color: {cores['destaque']}; margin-bottom: 0.5rem;'>🎨</h3>
                <h4>Tema</h4>
                <p style='color: {cores['texto']}70;'>{tema_display}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        simbolo = get_currency_symbol(st.session_state.moeda)
        st.markdown(f"""
        <div class='card'>
            <div style='text-align: center;'>
                <h3 style='color: {cores['destaque']}; margin-bottom: 0.5rem;'>💰</h3>
                <h4>Moeda</h4>
                <p style='color: {cores['texto']}70;'>{simbolo}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
  
    st.markdown("### 📈 Estatísticas Rápidas")
    
    try:
        historico = listar_historico(st.session_state.usuario_id, limite=5)
        if historico:
            total_cotacoes = len(historico)
            total_gasto = sum(item['total_geral'] for item in historico)
            simbolo = get_currency_symbol(st.session_state.moeda)
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            
            with col_stat1:
                st.metric("Cotações Salvas", total_cotacoes)
            
            with col_stat2:
                st.metric("Total Gasto", f"{simbolo} {total_gasto:,.2f}")
            
            with col_stat3:
                companhias = len(set(item['companhia'] for item in historico))
                st.metric("Companhias Usadas", companhias)
            
            with st.expander("📋 Últimas Cotações", expanded=False):
                for item in historico[:3]:
                    data_formatada = item['data_calculo'][:16] if item['data_calculo'] else "N/A"
                    col_hist1, col_hist2 = st.columns([3, 1])
                    with col_hist1:
                        st.write(f"**{item['nome_cotacao']}**")
                        st.caption(f"{item['companhia']} • {data_formatada}")
                    with col_hist2:
                        st.write(f"**{simbolo} {item['total_geral']:,.2f}**")
                    st.divider()
        else:
            st.info("📭 Nenhuma cotação encontrada. Crie sua primeira cotação!")
    except:
        st.warning("Não foi possível carregar estatísticas.")
    
    with st.expander("🔒 Informações de Segurança", expanded=False):
        col_sec1, col_sec2 = st.columns(2)
        
        with col_sec1:
            st.markdown("""
            **Proteções Ativas:**
            ✅ Criptografada
            ✅ Rate limiting inteligente
            ✅ Timeout de sessão (30min)
            ✅ Tokens CSRF únicos
            ✅ Prevenção SQL injection
            ✅ Sanitização de inputs
            ✅ Delay anti-timing attacks
            """)
        
        with col_sec2:
            st.markdown("""
            **Recomendações:**
            ⭐ Use senhas de 16+ caracteres
            ⭐ Ative 2FA quando disponível
            ⭐ Não compartilhe sua senha
            ⭐ Faça logout em PCs públicos
            ⭐ Altere senha a cada 90 dias
            ⭐ Revise logs de acesso
            """)
    
    st.markdown("</div>", unsafe_allow_html=True)

def pagina_nova_cotacao():
    """Página para criar nova cotação - COM PRESERVAÇÃO DE VALORES AO ALTERAR"""
    from datetime import datetime, date, timedelta
    
    cores = get_colors()
    
    st.title("📋 Nova Cotação")
    
    # Verificar se há solicitação para preenchimento automático
    if 'solicitacao_para_cotacao' in st.session_state and st.session_state.solicitacao_para_cotacao:
        solicitacao = st.session_state.solicitacao_para_cotacao
        preencher_automaticamente = True
    else:
        solicitacao = None
        preencher_automaticamente = False
    
    # Mostrar dados da solicitação se existir
    if preencher_automaticamente:
        st.markdown(f"""
        <div class='config-card fade-in' style='background: {cores['success']}15; border-left: 4px solid {cores['success']};'>
            <h4 style='color: {cores['success']}; margin-bottom: 1rem;'>📋 Dados da Solicitação Recebida</h4>
            <div style='display: flex; gap: 2rem; flex-wrap: wrap;'>
                <div>
                    <p><strong>👤 Cliente:</strong> {solicitacao['nome_cliente']}</p>
                    <p><strong>📞 Contato:</strong> {solicitacao['celular']}</p>
                    <p><strong>📧 Email:</strong> {solicitacao['email']}</p>
                </div>
                <div>
                    <p><strong>📅 Datas:</strong> {solicitacao['data_ida']} → {solicitacao['data_volta']}</p>
                    <p><strong>👥 Passageiros:</strong> {solicitacao['passageiros']['total']} pessoas</p>
                    <p><strong>🧳 Bagagens:</strong> {solicitacao['bagagens']}</p>
                </div>
                <div>
                    <p><strong>📍 Rota:</strong> {solicitacao['origem']} → {solicitacao['destino']}</p>
                    {f"<p><strong>📝 Observações:</strong> {solicitacao['observacoes']}</p>" if solicitacao.get('observacoes') else ""}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Botão para cancelar alteração e voltar
    if st.session_state.get('cotacao_atual', 0) != 0:
        col_cancelar, _ = st.columns([1, 5])
        with col_cancelar:
            if st.button("❌ Cancelar Alteração", use_container_width=True, type="secondary"):
                st.session_state.pagina = 'companhias'
                st.rerun()
    
    st.markdown(f"""
    <div class='config-card fade-in'>
        <h4 style='color: {cores['destaque']}; margin-bottom: 1rem;'>📝 Informe os dados básicos da cotação</h4>
        <p style='color: {cores['texto']}80;'>Crie uma nova cotação para comparar preços entre companhias aéreas.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # INICIALIZAR ESTADOS
    if 'tipo_viagem_radio' not in st.session_state:
        st.session_state.tipo_viagem_radio = "🔄 Ida e Volta"
    
    if 'mostrar_data_volta' not in st.session_state:
        st.session_state.mostrar_data_volta = True
    
    with st.form(key="form_nova_cotacao"):
        
        # Nome da cotação - PRESERVAR VALOR EXISTENTE
        nome_atual = st.session_state.get('nome_cotacao', '')
        nome_padrao = ""
        if preencher_automaticamente:
            nome_padrao = f"Cotação para {solicitacao['nome_cliente']} - {solicitacao['data_ida']}"
        
        nome_cotacao = st.text_input(
            "**📝 Nome/Identificador da Cotação**",
            placeholder="Ex: Viagem família - Junho 2024",
            help="Dê um nome descritivo para sua cotação",
            value=nome_atual if nome_atual and not preencher_automaticamente else nome_padrao,
            key="nome_cotacao_input"
        )
        
        # Origem e Destino - PRESERVAR VALORES EXISTENTES
        origem_atual = st.session_state.get('origem', '')
        destino_atual = st.session_state.get('destino', '')
        
        col1, col2 = st.columns(2)
        
        with col1:
            origem_padrao = solicitacao['origem'] if preencher_automaticamente else origem_atual
            origem = st.text_input(
                "**📍 Origem**",
                placeholder="Ex: GRU (São Paulo)",
                help="Aeroporto ou cidade de origem",
                value=origem_padrao,
                key="origem_input"
            )
        
        with col2:
            destino_padrao = solicitacao['destino'] if preencher_automaticamente else destino_atual
            destino = st.text_input(
                "**🎯 Destino**",
                placeholder="Ex: JFK (Nova York)",
                help="Aeroporto ou cidade de destino",
                value=destino_padrao,
                key="destino_input"
            )
        
        st.markdown("---")
        st.markdown("### ✈️ Tipo de Viagem")
        
        # TIPO DE VIAGEM - PRESERVAR VALOR EXISTENTE
        tipo_atual = st.session_state.get('tipo_viagem', 'Ida e Volta')
        tipo_map_reverse = {
            "Ida e Volta": "🔄 Ida e Volta",
            "Somente Ida": "⬆️ Somente Ida",
            "Multitrecho": "🔁 Multitrecho"
        }
        tipo_radio_atual = tipo_map_reverse.get(tipo_atual, "🔄 Ida e Volta")
        
        tipo_viagem = st.radio(
            "**Selecione o tipo de viagem:**",
            options=["🔄 Ida e Volta", "⬆️ Somente Ida", "🔁 Multitrecho"],
            horizontal=True,
            key="tipo_viagem_radio",
            index=["🔄 Ida e Volta", "⬆️ Somente Ida", "🔁 Multitrecho"].index(tipo_radio_atual)
        )
        
        tipo_viagem_map = {
            "🔄 Ida e Volta": "Ida e Volta",
            "⬆️ Somente Ida": "Somente Ida",
            "🔁 Multitrecho": "Multitrecho"
        }
        tipo_viagem_valor = tipo_viagem_map[tipo_viagem]
        
        # DATAS
        with st.expander("📅 Datas do Voo (Opcional)", expanded=preencher_automaticamente):
            
            hoje = datetime.now().date()
            hoje_para_comparacao = date(hoje.year, hoje.month, hoje.day)
            
            col_data1, col_data2 = st.columns(2)
            
            with col_data1:
                # Data de Ida - PRESERVAR VALOR EXISTENTE
                data_ida_atual = st.session_state.get('data_ida_para_cotacao')
                data_ida_padrao = None
                
                if preencher_automaticamente and 'data_ida' in solicitacao:
                    try:
                        dia, mes, ano = map(int, solicitacao['data_ida'].split('/'))
                        data_ida_padrao = date(ano, mes, dia)
                    except:
                        data_ida_padrao = None
                elif data_ida_atual:
                    try:
                        data_ida_padrao = datetime.strptime(data_ida_atual, '%d/%m/%Y').date()
                    except:
                        data_ida_padrao = None
                
                data_ida = st.date_input(
                    "📅 Data de Ida",
                    value=data_ida_padrao,
                    min_value=None,  # Removido min_value para permitir datas passadas
                    key="data_ida_input"
                )
            
            with col_data2:
                if tipo_viagem_valor != "Somente Ida":
                    data_volta_atual = st.session_state.get('data_volta_para_cotacao')
                    data_volta_padrao = None
                    
                    if preencher_automaticamente and 'data_volta' in solicitacao:
                        try:
                            dia, mes, ano = map(int, solicitacao['data_volta'].split('/'))
                            data_volta_padrao = date(ano, mes, dia)
                        except:
                            data_volta_padrao = None
                    elif data_volta_atual:
                        try:
                            data_volta_padrao = datetime.strptime(data_volta_atual, '%d/%m/%Y').date()
                        except:
                            data_volta_padrao = None
                    
                    data_volta = st.date_input(
                        "📅 Data de Volta",
                        value=data_volta_padrao,
                        min_value=None,  # Removido min_value para permitir datas passadas
                        key="data_volta_input"
                    )
                else:
                    data_volta = None
                    st.info("ℹ️ Data de volta não disponível para viagens somente ida")
        
        # PASSAGEIROS E BAGAGENS - PRESERVAR VALORES EXISTENTES
        with st.expander("👥 Configurações de Passageiros e Bagagens", expanded=preencher_automaticamente):
            col_pass1, col_pass2, col_pass3 = st.columns(3)
            
            with col_pass1:
                passageiros_atual = st.session_state.get('passageiros_para_cotacao', 1)
                passageiros_total = 0
                if preencher_automaticamente and solicitacao:
                    passageiros_total = solicitacao['passageiros'].get('adultos', 0) + solicitacao['passageiros'].get('criancas', 0)
                
                passageiros = st.number_input(
                    "**👥 Total de Passageiros**",
                    min_value=1,
                    max_value=20,
                    step=1,
                    value=passageiros_total if preencher_automaticamente and passageiros_total > 0 else passageiros_atual,
                    help="Total de passageiros pagantes (adultos + crianças)",
                    key="passageiros_total_input"
                )
            
            with col_pass2:
                bebes_atual = st.session_state.get('bebes_para_cotacao', 0)
                bebes_padrao = 0
                if preencher_automaticamente and solicitacao:
                    bebes_padrao = solicitacao['passageiros'].get('bebes', 0)
                
                bebes = st.number_input(
                    "**👶 Bebês (até 2 anos)**",
                    min_value=0,
                    max_value=10,
                    step=1,
                    value=bebes_padrao if preencher_automaticamente else bebes_atual,
                    help="Bebês não pagam passagem, apenas taxas",
                    key="bebes_input"
                )
            
            with col_pass3:
                bagagens_atual = st.session_state.get('bagagens_para_cotacao', 0)
                num_bagagens = 0
                if preencher_automaticamente and solicitacao and solicitacao.get('bagagens'):
                    try:
                        num_bagagens = int(solicitacao['bagagens'])
                    except:
                        num_bagagens = 1
                
                bagagens = st.number_input(
                    "**🧳 Número de Bagagens**",
                    min_value=0,
                    max_value=20,
                    step=1,
                    value=num_bagagens if preencher_automaticamente and num_bagagens > 0 else bagagens_atual,
                    help="Número total de bagagens despachadas",
                    key="bagagens_input"
                )
        
        with st.expander("💡 Dicas para uma boa cotação", expanded=False):
            st.markdown("""
            - Use nomes descritivos que ajudem a identificar a cotação depois
            - Inclua datas ou propósitos no nome (ex: "Férias Julho - Família")
            - Use códigos de aeroporto (GRU, JFK) para maior precisão
            - Você pode criar múltiplas cotações para a mesma rota com diferentes datas
            - Os dados de passageiros e bagagens serão usados automaticamente na calculadora
            """)
        
        st.markdown("---")
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            submit = st.form_submit_button("💾 Salvar e Continuar", type="primary", use_container_width=True)
    
    if submit:
        if not all([nome_cotacao, origem, destino]):
            st.error("❌ Preencha todos os campos obrigatórios (Nome, Origem e Destino)!")
        else:
            with st.spinner("💾 Salvando cotação..."):
                
                # Validar apenas se a data de volta é anterior à data de ida (apenas se ambas existirem)
                if data_ida and data_volta:
                    if data_volta < data_ida:
                        st.error("❌ A data de volta não pode ser anterior à data de ida!")
                        st.stop()
                
                # Salvar todos os dados na sessão
                st.session_state.passageiros_para_cotacao = passageiros
                st.session_state.bebes_para_cotacao = bebes
                st.session_state.bagagens_para_cotacao = bagagens
                st.session_state.tipo_viagem = tipo_viagem_valor
                
                if data_ida:
                    st.session_state.data_ida_para_cotacao = data_ida.strftime('%d/%m/%Y')
                else:
                    st.session_state.data_ida_para_cotacao = None
                
                if data_volta and tipo_viagem_valor != "Somente Ida":
                    st.session_state.data_volta_para_cotacao = data_volta.strftime('%d/%m/%Y')
                else:
                    st.session_state.data_volta_para_cotacao = None
                
                # Se já existe uma cotação (modo edição), atualizar em vez de criar nova
                if st.session_state.get('cotacao_atual', 0) != 0:
                    # Atualizar cotação existente no banco
                    try:
                        conn = criar_conexao()
                        cursor = conn.cursor()
                        cursor.execute('''
                        UPDATE cotacoes 
                        SET nome = ?, origem = ?, destino = ? 
                        WHERE id = ? AND usuario_id = ?
                        ''', (nome_cotacao, origem, destino, st.session_state.cotacao_atual, st.session_state.usuario_id))
                        conn.commit()
                        conn.close()
                        
                        st.session_state.nome_cotacao = nome_cotacao
                        st.session_state.origem = origem
                        st.session_state.destino = destino
                        
                        st.success("✅ Cotação atualizada com sucesso!")
                        st.info("👉 Agora selecione uma companhia para calcular os valores.")
                        time.sleep(1)
                        st.session_state.pagina = 'companhias'
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao atualizar: {str(e)}")
                else:
                    # Criar nova cotação
                    sucesso, resultado = criar_cotacao(
                        st.session_state.usuario_id,
                        nome_cotacao,
                        origem,
                        destino
                    )
                    
                    if sucesso:
                        st.session_state.cotacao_atual = resultado
                        st.session_state.nome_cotacao = nome_cotacao
                        st.session_state.origem = origem
                        st.session_state.destino = destino
                        
                        if 'solicitacao_para_cotacao' in st.session_state:
                            del st.session_state.solicitacao_para_cotacao
                        
                        st.success("✅ Cotação criada com sucesso!")
                        st.info("👉 Agora selecione uma companhia para calcular os valores.")
                        time.sleep(1)
                        st.session_state.pagina = 'companhias'
                        st.rerun()
                    else:
                        st.error(f"❌ {resultado}")
                    
def criar_nova_cotacao_manual():
    """Limpa dados e prepara para nova cotação manual"""
    if 'solicitacao_para_cotacao' in st.session_state:
        del st.session_state.solicitacao_para_cotacao
    
    st.session_state.cotacao_atual = 0
    st.session_state.nome_cotacao = ""
    st.session_state.origem = ""
    st.session_state.destino = ""
    st.session_state.companhia_selecionada = None
    st.session_state.companhia_display = ""
    st.session_state.resultado_calculo = None
    
    st.session_state.passageiros_para_cotacao = 1
    st.session_state.bebes_para_cotacao = 0
    st.session_state.bagagens_para_cotacao = 0
    
    st.session_state.pagina = 'nova_cotacao'
    st.rerun()

def pagina_companhias():
    """Página para selecionar companhia aérea COM BOTÃO ALTERAR COTAÇÃO"""
    cores = get_colors()
    
    if not hasattr(st.session_state, 'cotacao_atual') or st.session_state.cotacao_atual == 0:
        st.warning("⚠️ Crie uma cotação primeiro!")
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            if st.button("📋 Criar Nova Cotação", type="primary", use_container_width=True):
                st.session_state.pagina = 'nova_cotacao'
                st.rerun()
        return
    
    st.title(f"✈️ Selecione uma Companhia Aérea")
    
    # ===== BOTÃO ALTERAR COTAÇÃO =====
    col_alterar, col_vazio = st.columns([1, 4])
    with col_alterar:
        if st.button("✏️ Alterar Cotação", type="secondary", use_container_width=True, key="btn_alterar_cotacao"):
            st.session_state.pagina = 'nova_cotacao'
            st.rerun()
    
    # Mostrar dados da cotação atual COM DATAS
    st.markdown(f"""
    <div class='config-card fade-in'>
        <div style='display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem; flex-wrap: wrap;'>
            <div style='background: {cores['destaque']}20; padding: 8px 12px; border-radius: 8px;'>
                📋
            </div>
            <div>
                <h4 style='margin: 0; color: {cores['destaque']};'>{st.session_state.nome_cotacao}</h4>
                <p style='margin: 0.25rem 0 0 0; color: {cores['texto']}80;'>
                    <strong>📍 Rota:</strong> {st.session_state.origem} → {st.session_state.destino}
                </p>
                <p style='margin: 0.25rem 0 0 0; color: {cores['texto']}80;'>
                    <strong>👥 Passageiros:</strong> {st.session_state.get('passageiros_para_cotacao', 1)} adultos, 
                    {st.session_state.get('bebes_para_cotacao', 0)} bebês
                </p>
                <p style='margin: 0.25rem 0 0 0; color: {cores['texto']}80;'>
                    <strong>📅 Datas:</strong> 
                    {'Ida: ' + st.session_state.get('data_ida_para_cotacao', '') if st.session_state.get('data_ida_para_cotacao') else 'Sem data definida'}
                    {' • Volta: ' + st.session_state.get('data_volta_para_cotacao', '') if st.session_state.get('data_volta_para_cotacao') else ''}
                    {'' if st.session_state.get('data_ida_para_cotacao') or st.session_state.get('data_volta_para_cotacao') else '(Sem data definida)'}
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"### 🏢 Companhias Disponíveis")
    st.info("Selecione uma companhia para calcular os valores da passagem")
    
    companhias = [
        {"nome": "LATAM Airlines", "codigo": "latam", "cor": "#1E88E5", "desc": "Milhas LATAM + Taxas", "detalhes": "Programa LATAM Pass"},
        {"nome": "GOL Linhas Aéreas", "codigo": "gol", "cor": "#FF6B00", "desc": "Smiles ou Deságio", "detalhes": "Programa Smiles"},
        {"nome": "Azul Linhas Aéreas", "codigo": "azul", "cor": "#00B0FF", "desc": "Pontos TudoAzul", "detalhes": "Programa TudoAzul"},
        {"nome": "American Airlines", "codigo": "american", "cor": "#002D72", "desc": "Milhas AAdvantage", "detalhes": "Programa AAdvantage"},
    ]
    
    col1, col2 = st.columns(2)
    
    for i, comp in enumerate(companhias):
        col = col1 if i % 2 == 0 else col2
        with col:
            logo_base64 = carregar_imagem_companhia(comp["codigo"])
            
            st.markdown(f"""
            <div class='card fade-in' style='border-left: 4px solid {comp['cor']};'>
                <div style='text-align: center;'>
                    <img src="data:image/png;base64,{logo_base64}" style='width: 100%; max-height: 140px; object-fit: contain; margin-bottom: 1rem;'>
                    <h4 style='margin: 0.5rem 0;'>{comp['nome']}</h4>
                    <p style='color: {cores['texto']}70; font-size: 0.9rem; margin: 0.5rem 0;'>{comp['desc']}</p>
                    <div style='background: {comp['cor']}15; padding: 8px; border-radius: 6px; margin: 0.5rem 0;'>
                        <small style='color: {comp['cor']};'>{comp['detalhes']}</small>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"📊 Calcular com {comp['nome']}", key=f"btn_{comp['codigo']}", use_container_width=True, type="primary"):
                st.session_state.companhia_selecionada = comp["codigo"]
                st.session_state.companhia_display = comp["nome"]
                st.session_state.pagina = 'calculadora'
                st.rerun()
    
    with st.expander("ℹ️ Sobre as companhias", expanded=False):
        st.markdown("""
        ### ✈️ Programas de Fidelidade
        
        **LATAM Pass:** Programa de milhas da LATAM, aceito em voos nacionais e internacionais.
        
        **Smiles:** Programa da GOL, um dos maiores do Brasil, com diversas parcerias.
        
        **TudoAzul:** Programa da Azul, conhecido por flexibilidade e baixa taxa de expiração.
        
        **AAdvantage:** Programa da American Airlines, uma das maiores redes globais.
        
        ### 💡 Dicas
        
        - Compare sempre os valores em diferentes companhias
        - Considere a disponibilidade de voos
        - Verifique as taxas e condições de bagagem
        - Programas de fidelidade têm regras diferentes
        """)
# ===== SUBSTITUA a função pagina_calculadora() inteira =====

def pagina_calculadora():
    """Página da calculadora - COM CUSTO ADICIONAL NOMEÁVEL"""
    cores = get_colors()
    
    # Inicializar estado para custo adicional
    if 'custo_adicional_nome' not in st.session_state:
        st.session_state.custo_adicional_nome = ""
    if 'custo_adicional_valor' not in st.session_state:
        st.session_state.custo_adicional_valor = 0.0
    
    if 'companhia_selecionada' not in st.session_state or not st.session_state.companhia_selecionada:
        st.warning("⚠️ Selecione uma companhia primeiro!")
        st.session_state.pagina = 'companhias'
        st.rerun()
    
    if 'cotacao_atual' not in st.session_state or st.session_state.cotacao_atual == 0:
        st.warning("⚠️ Crie uma cotação primeiro!")
        st.session_state.pagina = 'nova_cotacao'
        st.rerun()
    
    try:
        logo_companhia = carregar_imagem_companhia(st.session_state.companhia_selecionada)
    except:
        logo_companhia = ""
    
    passageiros_padrao = st.session_state.get('passageiros_para_cotacao', 1)
    bebes_padrao = st.session_state.get('bebes_para_cotacao', 0)
    bagagens_padrao = st.session_state.get('bagagens_para_cotacao', 0)
    
    nome_cotacao = st.session_state.get('nome_cotacao', 'Nova Cotação')
    origem = st.session_state.get('origem', '')
    destino = st.session_state.get('destino', '')
    companhia_display = st.session_state.get('companhia_display', 'Companhia Aérea')
    
    tipo_viagem = st.session_state.get('tipo_viagem', 'Ida e Volta')
    data_ida = st.session_state.get('data_ida_para_cotacao', 'Não informada')
    data_volta = st.session_state.get('data_volta_para_cotacao', 'Não informada')
    
    st.markdown(f"""
    <div class='fade-in'>
        <div style='background-color: {cores['card']}; padding: 1.5rem; border-radius: 15px; border: 1px solid {cores['borda']}; margin: 1rem 0;'>
            <div style='display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap;'>
                <div style='flex-shrink: 0;'>
                    <img src="data:image/png;base64,{logo_companhia}" style='width: 100px; height: auto; object-fit: contain;'>
                </div>
                <div style='flex: 1; min-width: 250px;'>
                    <h2 style='color: {cores['destaque']}; margin-bottom: 0.5rem;'>{companhia_display}</h2>
                    <p style='color: {cores['texto']}80; margin: 0;'>
                        📍 {origem} → 🎯 {destino}
                    </p>
                    <p style='color: {cores['texto']}80; margin: 0.5rem 0 0 0;'>
                        📋 <strong>Cotação:</strong> {nome_cotacao}
                    </p>
                    <p style='color: {cores['texto']}80; margin: 0.25rem 0 0 0;'>
                        👥 <strong>Passageiros:</strong> {passageiros_padrao} • 👶 <strong>Bebês:</strong> {bebes_padrao} • 🧳 <strong>Bagagens:</strong> {bagagens_padrao}
                    </p>
                    <p style='color: {cores['texto']}80; margin: 0.25rem 0 0 0;'>
                        📅 <strong>Viagem:</strong> {tipo_viagem} • Ida: {data_ida} • Volta: {data_volta}
                    </p>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Botão para voltar e alterar cotação
    col_back1, col_back2, col_back3 = st.columns([1, 1, 2])
    with col_back1:
        if st.button("← Voltar para Companhias", use_container_width=True, type="secondary"):
            st.session_state.pagina = 'companhias'
            st.rerun()
    with col_back2:
        if st.button("✏️ Alterar Cotação", use_container_width=True, type="secondary"):
            st.session_state.pagina = 'nova_cotacao'
            st.rerun()
    
    if 'resultado_calculo' not in st.session_state or st.session_state.resultado_calculo is None:
        st.session_state.resultado_calculo = {}
    
    companhia = st.session_state.companhia_selecionada
    simbolo = get_currency_symbol(st.session_state.get('moeda', 'BRL'))
    
    companhias_validas = ["latam", "gol", "azul", "american"]
    if companhia not in companhias_validas:
        st.error(f"❌ Companhia '{companhia}' não reconhecida!")
        st.session_state.pagina = 'companhias'
        st.rerun()
    
    with st.form(f"form_calculadora_{companhia}", clear_on_submit=False):
        st.markdown(f"""
        <div class='config-card'>
            <h4 style='color: {cores['destaque']}; margin-bottom: 1rem;'>🧮 Preencha os dados para cálculo</h4>
            <p style='color: {cores['texto']}80;'>Os dados de passageiros e bagagens foram preenchidos automaticamente. Você pode alterá-los se necessário.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 👥 Passageiros e Bagagens")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            passageiros = st.number_input(
                f"**👥 Passageiros (adultos/crianças)**",
                min_value=1,
                max_value=20,
                step=1,
                value=passageiros_padrao,
                help="Número de passageiros pagantes (adultos e crianças)",
                key="passageiros"
            )
            
            bebes = st.number_input(
                f"**👶 Bebês (até 2 anos)**",
                min_value=0,
                max_value=20,
                step=1,
                value=bebes_padrao,
                help="Bebês não pagam passagem, apenas taxas",
                key="bebes"
            )
        
        with col2:
            taxa_embarque = st.number_input(
                f"**🎫 Taxa de embarque ({simbolo})**",
                min_value=0.00,
                max_value=100000000.0,
                step=1.0,
                value=0.00,
                format="%.2f",
                help="Taxa de embarque por passageiro",
                key="taxa"
            )
        
        with col3:
            num_bagagens = st.number_input(
                f"**🧳 Bagagens adicionais**",
                min_value=0,
                max_value=20,
                step=1,
                value=bagagens_padrao,
                help="Número de bagagens adicionais (além das inclusas, se houver)",
                key="bagagens"
            )
        
        # ===== NOVO: CUSTO ADICIONAL NOMEÁVEL =====
        st.markdown("### 💰 Custos Adicionais")
        
        col_custo1, col_custo2 = st.columns(2)
        with col_custo1:
            custo_adicional_nome = st.text_input(
                "**Nome do custo adicional (opcional)**",
                placeholder="Ex: Taxa de serviço, seguro, etc.",
                key="custo_adicional_nome_input",
                value=st.session_state.get('custo_adicional_nome', '')
            )
        
        with col_custo2:
            custo_adicional_valor = st.number_input(
                f"**Valor do custo adicional ({simbolo})**",
                min_value=0.00,
                max_value=1000000.0,
                step=10.0,
                value=st.session_state.get('custo_adicional_valor', 0.0),
                format="%.2f",
                key="custo_adicional_valor_input"
            )
        
        st.markdown(f"### 💰 Configurações {st.session_state.companhia_display}")
        
        # Inicializar variáveis
        milhas_total = 0
        valor_milheiro = 0
        valor_gol = 0
        desagio = 0
        valor_bagagem_unitaria = 0
        tipo_calculo = "Padrão"
        desconto_taxa = 0
        
        # ===== LATAM =====
        if companhia == "latam":
            st.markdown("#### ✈️ LATAM Airlines - Milhas LATAM Pass")
            
            col_tarifa1, col_tarifa2 = st.columns(2)
            
            with col_tarifa1:
                tipo_tarifa = st.radio(
                    "**Selecione o tipo de tarifa:**",
                    options=["🎫 Standard (com bagagem inclusa)", "🎫 Light (sem bagagem inclusa)"],
                    horizontal=True,
                    key="tipo_tarifa_latam",
                    index=0,
                    help="Standard: bagagem de mão + 1 bagagem despachada inclusa | Light: apenas bagagem de mão"
                )
                
                tipo_tarifa_valor = "Standard" if "Standard" in tipo_tarifa else "Light"
            
            with col_tarifa2:
                bagagens_inclusas = passageiros if tipo_tarifa_valor == "Standard" else 0
                st.markdown(f"""
                <div style='background: {cores['info']}15; padding: 15px; border-radius: 10px; border-left: 4px solid {cores['info']};'>
                    <h5 style='margin: 0 0 5px 0; color: {cores['info']};'>ℹ️ Informações</h5>
                    <p style='margin: 0; font-size: 0.9rem;'>
                        <strong>Standard:</strong> Bagagem de mão + 1 bagagem despachada por passageiro<br>
                        <span style='color: #4CAF50;'>✅ {bagagens_inclusas} bagagem(ns) inclusa(s) (sem custo)</span><br>
                        <strong>Light:</strong> Apenas bagagem de mão<br>
                        <strong>Bagagem adicional:</strong> R$ 140 por unidade
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            col_latam1, col_latam2 = st.columns(2)
            
            with col_latam1:
                milhas_total = st.number_input(
                    f"**💎 Milhas necessárias (POR PASSAGEIRO)**",
                    min_value=0.000,
                    max_value=1000000.0,
                    step=100.0,
                    value=0.000,
                    format="%.3f",
                    help="Total de milhas necessárias POR PASSAGEIRO para o trecho",
                    key="milhas_latam"
                )
            
            with col_latam2:
                valor_milheiro = st.number_input(
                    f"**💰 Valor por milheiro ({simbolo})**",
                    min_value=0.00,
                    max_value=1000.0,
                    step=1.00,
                    value=0.00,
                    format="%.2f",
                    help="Custo por milheiro adquirido",
                    key="milheiro_latam"
                )
            
            valor_bagagem_unitaria = 140.0
            tipo_calculo = f"LATAM - {tipo_tarifa_valor}"
            
            st.info(f"""
            💡 **Informações:**
            - **Tarifa {tipo_tarifa_valor}**: {('Bagagem de mão + 1 bagagem despachada por passageiro INCLUSA' if tipo_tarifa_valor == 'Standard' else 'Apenas bagagem de mão')}
            - **Bagagens inclusas:** {bagagens_inclusas} (sem custo)
            - **Bagagens adicionais:** {num_bagagens} × {simbolo} {valor_bagagem_unitaria:,.2f}
            - **Total de passageiros:** {passageiros}
            """)
            
        # ===== GOL =====
        elif companhia == "gol":
            tipo_gol = st.radio(
                "**Selecione o tipo de cálculo GOL:**",
                ["💎 Smiles (Milhas)", "💰 Deságio"],
                key="tipo_gol",
                horizontal=True
            )
            
            if tipo_gol == "💎 Smiles (Milhas)":
                st.markdown("#### ✈️ GOL - Programa Smiles")
                
                col_gol1, col_gol2 = st.columns(2)
                
                with col_gol1:
                    milhas_total = st.number_input(
                        f"**💎 Milhas Smiles necessárias**",
                        min_value=0.000,
                        max_value=1000000.0,
                        step=100.0,
                        value=0.000,
                        format="%.3f",
                        help="Total de milhas Smiles necessárias",
                        key="milhas_gol"
                    )
                
                with col_gol2:
                    valor_milheiro = st.number_input(
                        f"**💰 Valor por milheiro ({simbolo})**",
                        min_value=0.00,
                        max_value=1000.0,
                        step=0.01,
                        value=0.00,
                        format="%.2f",
                        help="Custo por milheiro Smiles",
                        key="milheiro_gol"
                    )
                
                valor_bagagem_unitaria = 130.0 if st.session_state.get('moeda', 'BRL') == "BRL" else 26.0
                tipo_calculo = "GOL - SMILES"
                
                st.info(f"💡 **Valor bagagem adicional:** {simbolo} {valor_bagagem_unitaria:,.2f} por unidade")
            
            else:
                st.markdown("#### ✈️ GOL - Deságio em Passagem")
                
                col_gol3, col_gol4 = st.columns(2)
                
                with col_gol3:
                    valor_gol = st.number_input(
                        f"**💵 Valor cheio da passagem ({simbolo})**",
                        min_value=0.00,
                        max_value=100000.0,
                        step=1.0,
                        value=0.00,
                        format="%.2f",
                        help="Valor total da passagem sem desconto",
                        key="valor_gol"
                    )
                
                with col_gol4:
                    desagio = st.slider(
                        f"**📉 Percentual de deságio**",
                        min_value=0.0,
                        max_value=100.0,
                        value=0.0,
                        step=1.0,
                        format="%.2f%%",
                        help="Percentual de desconto sobre o valor cheio",
                        key="desagio_gol"
                    )
                
                valor_bagagem_unitaria = 0
                tipo_calculo = "GOL - DESAGIO"
                
                st.info(f"💡 **Deságio aplicado:** {desagio:.1f}% sobre {simbolo} {valor_gol:,.2f}")
       
        # ===== AZUL =====
        elif companhia == "azul":
            tipo_azul = st.radio(
                "**Selecione o tipo de cálculo AZUL:**",
                ["🔵 Pontos TudoAzul", "💵 Pontos + Dinheiro (5% OFF taxa)"],
                key="tipo_azul",
                horizontal=True
            )
            
            st.markdown("#### ✈️ Azul - Programa TudoAzul")
            
            col_azul1, col_azul2 = st.columns(2)
            
            with col_azul1:
                milhas_total = st.number_input(
                    f"**💎 Pontos TudoAzul necessários (TOTAL)**",
                    min_value=0.000,
                    max_value=1000000.0,
                    step=100.0,
                    value=0.000,
                    format="%.3f",
                    help="Total de pontos TudoAzul necessários para TODOS os passageiros",
                    key="milhas_azul"
                )
            
            with col_azul2:
                valor_milheiro = st.number_input(
                    f"**💰 Valor por ponto ({simbolo})**",
                    min_value=0.00,
                    max_value=1000.0,
                    step=0.01,
                    value=0.00,
                    format="%.2f",
                    help="Custo por ponto TudoAzul",
                    key="milheiro_azul"
                )
            
            valor_bagagem_unitaria = 175.0 if st.session_state.get('moeda', 'BRL') == "BRL" else 35.0
            
            if tipo_azul == "🔵 Pontos TudoAzul":
                tipo_calculo = "AZUL - PONTOS"
                desconto_taxa = 0
                desconto_porcentagem = 0
            else:
                tipo_calculo = "AZUL - PONTOS + DINHEIRO"
                desconto_taxa = 0.05
                desconto_porcentagem = 5
            
            st.markdown(f"""
            <div style='background: {cores['info']}15; padding: 15px; border-radius: 10px; margin: 10px 0;'>
                <h5 style='margin: 0 0 10px 0; color: {cores['info']};'>ℹ️ Informações</h5>
                <p><strong>Valor bagagem adicional:</strong> {simbolo} {valor_bagagem_unitaria:,.2f} por unidade</p>
                {f'<p><strong style="color: #4CAF50;">🎁 Desconto especial: {desconto_porcentagem}% OFF na taxa de embarque</strong></p>' if desconto_porcentagem > 0 else ''}
            </div>
            """, unsafe_allow_html=True)
        
        # ===== AMERICAN =====
        elif companhia == "american":
            st.markdown("#### 🇺🇸 American Airlines - Programa AAdvantage")
            
            col_am1, col_am2 = st.columns(2)
            
            with col_am1:
                milhas_total = st.number_input(
                    f"**💎 Milhas AAdvantage necessárias**",
                    min_value=0.000,
                    max_value=1000000.0,
                    step=100.0,
                    value=0.000,
                    format="%.3f",
                    help="Total de milhas AAdvantage necessárias",
                    key="milhas_am"
                )
            
            with col_am2:
                valor_milheiro = st.number_input(
                    f"**💰 Valor por milheiro ({simbolo})**",
                    min_value=0.00,
                    max_value=1000.0,
                    step=1.00,
                    value=0.00,
                    format="%.2f",
                    help="Custo por milheiro AAdvantage",
                    key="milheiro_am"
                )
            
            st.markdown("#### 🌍 Tipo de Rota")
            rota = st.selectbox(
                f"**Selecione o tipo de rota**",
                [
                    "Brasil ↔ EUA",
                    "EUA / Canadá / Caribe / México", 
                    "América do Sul ↔ EUA",
                    "EUA ↔ Panamá / Colômbia / Peru / Equador"
                ],
                help="O valor da bagagem varia conforme a rota",
                key="rota_am"
            )
            
            if rota == "Brasil ↔ EUA":
                valor_bagagem_unitaria = 60.0 if st.session_state.get('moeda', 'BRL') == "USD" else 300.0
            elif rota == "EUA / Canadá / Caribe / México":
                valor_bagagem_unitaria = 35.0 if st.session_state.get('moeda', 'BRL') == "USD" else 175.0
            elif rota == "América do Sul ↔ EUA":
                valor_bagagem_unitaria = 60.0 if st.session_state.get('moeda', 'BRL') == "USD" else 300.0
            else:
                valor_bagagem_unitaria = 45.0 if st.session_state.get('moeda', 'BRL') == "USD" else 225.0
            
            tipo_calculo = f"AMERICAN - {rota}"
            
            st.info(f"💡 **Valor bagagem adicional ({rota}):** {simbolo} {valor_bagagem_unitaria:,.2f} por unidade")
        
        col_btn_calc1, col_btn_calc2, col_btn_calc3 = st.columns([1, 2, 1])
        with col_btn_calc2:
            calcular = st.form_submit_button(
                f"🧮 CALCULAR COTAÇÃO", 
                type="primary", 
                use_container_width=True,
                key="btn_calcular_cotacao"
            )
    
    if calcular:
        try:
            # Salvar custo adicional na sessão
            if custo_adicional_nome and custo_adicional_valor > 0:
                st.session_state.custo_adicional_nome = custo_adicional_nome
                st.session_state.custo_adicional_valor = custo_adicional_valor
            
            valor_base = 0
            valor_bagagens_total = 0
            desagio_percentual = 0
            
            if companhia == "latam":
                valor_milhas = (milhas_total * valor_milheiro) * passageiros
                valor_taxas = taxa_embarque * passageiros
                valor_base = valor_milhas + valor_taxas
                valor_bagagens_total = num_bagagens * valor_bagagem_unitaria
                
                bagagens_inclusas = passageiros if tipo_tarifa_valor == "Standard" else 0
                tipo_calculo = f"LATAM - {tipo_tarifa_valor}"
                
                st.session_state.resultado_calculo = {}
                st.session_state.resultado_calculo['dados_sql'] = {
                    'milhas_total': milhas_total * passageiros,
                    'milhas_por_pax': milhas_total,
                    'tipo_tarifa': tipo_tarifa_valor,
                    'bagagens_inclusas': bagagens_inclusas,
                    'bagagens_adicionais': num_bagagens
                }
            
            elif companhia == "gol" and tipo_gol == "💎 Smiles (Milhas)":
                valor_milhas = milhas_total * valor_milheiro
                valor_taxas = taxa_embarque
                valor_base = valor_milhas + valor_taxas
                valor_bagagens_total = num_bagagens * valor_bagagem_unitaria
                tipo_calculo = "GOL - SMILES"
                st.session_state.resultado_calculo = {}
                st.session_state.resultado_calculo['dados_sql'] = {'milhas_total': milhas_total, 'tipo_calculo': tipo_calculo}
            
            elif companhia == "gol" and tipo_gol == "💰 Deságio":
                desconto = valor_gol * (desagio / 100)
                valor_base = valor_gol - desconto
                valor_bagagens_total = num_bagagens * valor_bagagem_unitaria
                tipo_calculo = "GOL - DESAGIO"
                st.session_state.resultado_calculo = {}
                st.session_state.resultado_calculo['dados_sql'] = {'valor_gol_original': valor_gol, 'desagio': desagio, 'tipo_calculo': tipo_calculo}
            
            elif companhia == "azul" and tipo_azul == "🔵 Pontos TudoAzul":
                valor_pontos = milhas_total * valor_milheiro
                valor_taxas = taxa_embarque
                valor_base = valor_pontos + valor_taxas
                valor_bagagens_total = num_bagagens * valor_bagagem_unitaria
                tipo_calculo = "AZUL - PONTOS"
                st.session_state.resultado_calculo = {}
                st.session_state.resultado_calculo['dados_sql'] = {'milhas_total': milhas_total, 'tipo_calculo': tipo_calculo}
            
            elif companhia == "azul" and tipo_azul == "💵 Pontos + Dinheiro (5% OFF taxa)":
                valor_pontos = milhas_total * valor_milheiro
                valor_taxas_com_desconto = taxa_embarque * 0.95
                valor_base = valor_pontos + valor_taxas_com_desconto
                valor_bagagens_total = num_bagagens * valor_bagagem_unitaria
                desconto_aplicado = taxa_embarque * 0.05
                tipo_calculo = "AZUL - PONTOS + DINHEIRO"
                st.session_state.resultado_calculo = {}
                st.session_state.resultado_calculo.update({'desconto_taxa_aplicado': desconto_aplicado, 'taxa_original': taxa_embarque, 'taxa_com_desconto': taxa_embarque * 0.95})
                st.session_state.resultado_calculo['dados_sql'] = {'milhas_total': milhas_total, 'tipo_calculo': tipo_calculo, 'desconto_taxa': desconto_aplicado}
            
            elif companhia == "american":
                valor_milhas = milhas_total * valor_milheiro
                valor_taxas = taxa_embarque
                valor_base = valor_milhas + valor_taxas
                valor_bagagens_total = num_bagagens * valor_bagagem_unitaria
                tipo_calculo = f"AMERICAN - {rota}"
                st.session_state.resultado_calculo = {}
                st.session_state.resultado_calculo['dados_sql'] = {'milhas_total': milhas_total, 'tipo_calculo': tipo_calculo, 'rota': rota}
            
            total_geral = valor_base + valor_bagagens_total
            
            # Adicionar custo adicional se existir
            if custo_adicional_valor > 0 and custo_adicional_nome:
                total_geral += custo_adicional_valor
                tipo_calculo += f" + {custo_adicional_nome}"
            
            st.session_state.resultado_calculo.update({
                'companhia': st.session_state.companhia_display,
                'tipo_calculo': tipo_calculo,
                'passageiros': passageiros,
                'bebes': bebes,
                'taxa_embarque': taxa_embarque,
                'num_bagagens': num_bagagens,
                'valor_bagagem_unitaria': valor_bagagem_unitaria,
                'milhas_total': milhas_total,
                'valor_milheiro': valor_milheiro,
                'valor_gol': valor_gol if 'valor_gol' in locals() else 0,
                'desagio_percentual': desagio if 'desagio' in locals() else 0,
                'valor_base': valor_base,
                'valor_bagagens_total': valor_bagagens_total,
                'custo_adicional_nome': custo_adicional_nome if custo_adicional_valor > 0 else None,
                'custo_adicional_valor': custo_adicional_valor if custo_adicional_valor > 0 else 0,
                'total_geral': total_geral,
                'simbolo': simbolo,
                'data_hora': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'dados_sql': st.session_state.resultado_calculo.get('dados_sql', {})
            })
            
            st.session_state.resultado_calculo['tipo_viagem'] = tipo_viagem
            st.session_state.resultado_calculo['data_ida'] = data_ida
            st.session_state.resultado_calculo['data_volta'] = data_volta
            
            st.success("✅ Cálculo realizado com sucesso!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Erro ao calcular: {str(e)}")
            logger.error(f"Erro na calculadora: {e}")
    
    # ... (restante da função pagina_calculadora continua igual - mostrar resultado)
            st.exception(e)  # Mostrar stack trace completo para debug
    
    # ===== MOSTRAR RESULTADO =====
    if st.session_state.resultado_calculo and st.session_state.resultado_calculo.get('total_geral'):
        try:
            resultado = st.session_state.resultado_calculo
            
            st.markdown(f"""
            <div class='resultado-cotacao fade-in'>
                <h2 style='color: {cores['destaque']}; text-align: center; margin-bottom: 1.5rem;'>📊 RESULTADO DA COTAÇÃO</h2>
            """, unsafe_allow_html=True)
            
            col_info1, col_info2, col_info3 = st.columns(3)
            
            with col_info1:
                st.markdown(f"""
                <div class='card-detalhe'>
                    <h4 style='color: {cores['texto']}70;'>Companhia</h4>
                    <h3>{resultado['companhia']}</h3>
                    <p style='color: {cores['destaque']};'>{resultado['tipo_calculo']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_info2:
                st.markdown(f"""
                <div class='card-detalhe'>
                    <h4 style='color: {cores['texto']}70;'>Rota</h4>
                    <h3>{origem} → {destino}</h3>
                    <p style='color: {cores['texto']}70;'>{resultado['data_hora']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_info3:
                # ===== NOVO: Mostrar dados da viagem =====
                st.markdown(f"""
                <div class='card-detalhe'>
                    <h4 style='color: {cores['texto']}70;'>Detalhes</h4>
                    <p><strong>👥 Passageiros:</strong> {resultado['passageiros']}</p>
                    <p><strong>👶 Bebês:</strong> {resultado['bebes']}</p>
                    <p><strong>🧳 Bagagens adicionais:</strong> {resultado['num_bagagens']}</p>
                    <p><strong>📅 {resultado.get('tipo_viagem', 'Viagem')}:</strong> {resultado.get('data_ida', 'N/I')} → {resultado.get('data_volta', 'N/I')}</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown(f"### 🧮 Detalhamento dos Custos")
            
            col_det1, col_det2 = st.columns(2)
            
            with col_det1:
                st.markdown(f"""
                <div class='card-detalhe'>
                    <h4 style='color: {cores['texto']}70;'>Custos Base</h4>
                    <div style='margin: 1rem 0;'>
                        <div style='display: flex; justify-content: space-between; margin: 0.5rem 0;'>
                            <span>Valor base das passagens:</span>
                            <strong>{resultado['simbolo']} {resultado['valor_base']:,.2f}</strong>
                        </div>
                        <div style='display: flex; justify-content: space-between; margin: 0.5rem 0;'>
                            <span>Taxa de embarque ({resultado['passageiros']} pass.):</span>
                            <strong>{resultado['simbolo']} {resultado['taxa_embarque'] * resultado['passageiros']:,.2f}</strong>
                        </div>
                        {f"<div style='display: flex; justify-content: space-between; margin: 0.5rem 0;'><span>Deságio aplicado:</span><strong>{resultado.get('desagio_percentual', 0):.1f}%</strong></div>" if resultado.get('desagio_percentual', 0) > 0 else ""}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_det2:
                valor_bagagens_total = resultado['valor_bagagens_total']
                st.markdown(f"""
                <div class='card-detalhe'>
                    <h4 style='color: {cores['texto']}70;'>Custos Adicionais</h4>
                    <div style='margin: 1rem 0;'>
                        {f"<div style='display: flex; justify-content: space-between; margin: 0.5rem 0;'><span>Bagagens adicionais ({resultado['num_bagagens']} × {resultado['simbolo']} {resultado.get('valor_bagagem_unitaria', 0):,.2f}):</span><strong>{resultado['simbolo']} {valor_bagagens_total:,.2f}</strong></div>" if resultado['num_bagagens'] > 0 else "<div style='margin: 0.5rem 0; color: #666;'>Sem bagagens adicionais</div>"}
                        <div style='display: flex; justify-content: space-between; margin: 0.5rem 0; border-top: 2px solid {cores['destaque']}; padding-top: 0.5rem;'>
                            <span style='font-size: 1.1rem;'>Subtotal:</span>
                            <strong style='font-size: 1.1rem;'>{resultado['simbolo']} {resultado['valor_base'] + valor_bagagens_total:,.2f}</strong>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown(f"""
            <div class='valor-destaque fade-in'>
                <h1 style='margin: 0; font-size: 2.5rem;'>TOTAL: {resultado['simbolo']} {resultado['total_geral']:,.2f}</h1>
                <div style='margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 1.1rem;'>
                    <div style='display: inline-block; margin-right: 1.5rem;'>
                        👤 {resultado['passageiros']} passageiros × {resultado['simbolo']} {(resultado['total_geral'] / resultado['passageiros']):,.2f}
                    </div>
                    <div style='display: inline-block;'>
                        👶 {resultado['bebes']} bebê(s) • Gratuito
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

            with col_btn1:
                if st.button("💾 Salvar cotação", use_container_width=True, type="primary", key="btn_salvar_calc"):
                    try:
                        dados_sql = resultado.get('dados_sql', {})
                        dados_sql.update({
                            "usuario_id": st.session_state.usuario_id,
                            "cotacao_id": st.session_state.cotacao_atual,
                            "companhia": resultado['companhia'],
                            "tipo_calculo": resultado['tipo_calculo'],
                            "milhas_total": resultado.get('milhas_total', 0),
                            "valor_milheiro": resultado.get('valor_milheiro', 0),
                            "taxa_embarque": resultado['taxa_embarque'],
                            "valor_base": resultado['valor_base'],
                            "valor_bagagens": resultado['valor_bagagens_total'],
                            "desagio_percentual": resultado.get('desagio_percentual', 0),
                            "total_geral": resultado['total_geral'],
                            "moeda": st.session_state.get('moeda', 'BRL'),
                            "passageiros": resultado['passageiros'],
                            "bebes": resultado['bebes'],
                            "num_bagagens": resultado['num_bagagens'],
                            "valor_bagagem_unitaria": resultado.get('valor_bagagem_unitaria', 0)
                        })
                        
                        sucesso, mensagem = salvar_calculo(dados_sql)
                        
                        if sucesso:
                            st.success(f"✅ {mensagem}")
                            st.session_state.resultado_calculo = None
                            st.session_state.pagina = "historico"
                            st.rerun()
                        else:
                            st.error(f"❌ {mensagem}")
                            
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar: {str(e)}")
            
            with col_btn2:
                if st.button("🔄 Refazer cálculo", use_container_width=True, key="btn_refazer"):
                    st.session_state.resultado_calculo = None
                    st.rerun()
            
            with col_btn3:
                if st.button("✈️ Outra companhia", use_container_width=True, key="btn_outra_comp"):
                    st.session_state.resultado_calculo = None
                    st.session_state.pagina = 'companhias'
                    st.rerun()
            
            with col_btn4:
                if st.button("📋 Nova cotação", use_container_width=True, key="btn_nova_calc"):
                    st.session_state.resultado_calculo = None
                    st.session_state.pagina = 'nova_cotacao'
                    st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"❌ Erro ao mostrar resultado: {str(e)}")
            logger.error(f"Erro ao mostrar resultado: {e}")
    
    st.markdown("</div>", unsafe_allow_html=True)

def testar_historico():
    """Função de teste para verificar se o histórico está funcionando"""
    st.title("🧪 Teste do Histórico")
    
    if not st.session_state.get('logado', False):
        st.error("Usuário não está logado!")
        return
    
    st.write(f"Usuário ID: {st.session_state.usuario_id}")
    st.write(f"Usuário Nome: {st.session_state.usuario_nome}")
    
    historico = listar_historico(st.session_state.usuario_id, limite=10)
    
    if historico:
        st.success(f"✅ Encontradas {len(historico)} cotações")
        st.json(historico[0] if historico else {})
    else:
        st.warning("❌ Nenhuma cotação encontrada")
        
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM historico_cotacoes")
        total = cursor.fetchone()[0]
        st.write(f"Total de registros na tabela: {total}")
        
        cursor.execute("SELECT COUNT(*) FROM historico_cotacoes WHERE usuario_id = ?", 
                      (st.session_state.usuario_id,))
        usuario_total = cursor.fetchone()[0]
        st.write(f"Registros do usuário {st.session_state.usuario_id}: {usuario_total}")
        
        conn.close()

def renderizar_cotacao_card(item, idx, total_items):
    """Renderiza uma cotação com visual moderno e emojis - VERSÃO CORRIGIDA (SEM F-STRINGS COM BACKSLASH)"""
    cores = get_colors()
    
    # Extrair dados com valores padrão
    passageiros = item.get('passageiros', 1) or 1
    bebes = item.get('bebes', 0) or 0
    num_bagagens = item.get('num_bagagens', 0) or 0
    
    # Formatar data
    data_calculo = item.get('data_calculo', '')
    if data_calculo and len(data_calculo) >= 16:
        data_formatada = data_calculo[:16].replace('T', ' ')
    else:
        data_formatada = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Nome da cotação
    nome_cotacao = item.get('nome_cotacao', item.get('companhia', 'Cotação'))
    
    # Rota
    origem = item.get('origem', '???')
    destino = item.get('destino', '???')
    
    # Valores
    simbolo = get_currency_symbol(item.get('moeda', 'BRL'))
    total = item['total_geral']
    valor_por_pax = total / max(passageiros, 1)
    
    # Tipo de cálculo e companhia
    tipo_calculo = item.get('tipo_calculo', 'Milhas + Taxa')
    companhia = item.get('companhia', 'LATAM Airlines')
    
    # Ícone da companhia
    if 'latam' in companhia.lower():
        icone_companhia = "🛫"
        cor_companhia = "#1E88E5"
    elif 'gol' in companhia.lower():
        icone_companhia = "🛬"
        cor_companhia = "#FF6B00"
    elif 'azul' in companhia.lower():
        icone_companhia = "🔵"
        cor_companhia = "#00B0FF"
    elif 'american' in companhia.lower():
        icone_companhia = "🇺🇸"
        cor_companhia = "#002D72"
    else:
        icone_companhia = "✈️"
        cor_companhia = cores['destaque']
    
    # HTML do card - USANDO .format() EM VEZ DE F-STRING
    html_card = '''
    <div style="
        background: linear-gradient(135deg, {cor_card} 0%, {cor_fundo} 100%);
        border-radius: 20px;
        padding: 25px;
        margin-bottom: 20px;
        border: 1px solid {cor_borda};
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        transition: transform 0.2s;
        position: relative;
        overflow: hidden;
    ">
        <!-- Efeito de brilho no canto -->
        <div style="
            position: absolute;
            top: -20px;
            right: -20px;
            width: 100px;
            height: 100px;
            background: {cor_destaque}20;
            border-radius: 50%;
            filter: blur(30px);
        "></div>
        
        <!-- Cabeçalho com número e badge -->
        <div style="
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        ">
            <div style="
                background: {cor_destaque}15;
                color: {cor_destaque};
                padding: 6px 16px;
                border-radius: 30px;
                font-size: 0.9rem;
                font-weight: 600;
                border: 1px solid {cor_destaque}30;
            ">
                📋 #{posicao}
            </div>
            <div style="
                background: {cor_success}15;
                color: {cor_success};
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: 500;
            ">
                ✅ Salvo
            </div>
        </div>
        
        <!-- Nome da cotação com ícone -->
        <div style="
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 20px;
        ">
            <div style="
                background: {cor_companhia}20;
                width: 50px;
                height: 50px;
                border-radius: 15px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 28px;
            ">
                {icone_companhia}
            </div>
            <div>
                <h2 style="
                    font-size: 2rem;
                    font-weight: 700;
                    margin: 0;
                    color: {cor_texto};
                    line-height: 1.2;
                ">
                    {nome_cotacao}
                </h2>
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    margin-top: 5px;
                ">
                    <span style="
                        background: {cor_companhia};
                        color: white;
                        padding: 4px 12px;
                        border-radius: 20px;
                        font-size: 0.8rem;
                        font-weight: 600;
                    ">
                        {tipo_calculo}
                    </span>
                    <span style="
                        color: {cor_texto}80;
                        font-size: 0.95rem;
                    ">
                        {companhia}
                    </span>
                </div>
            </div>
        </div>
        
        <!-- Grid de informações -->
        <div style="
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin: 20px 0;
            background: {cor_fundo}50;
            padding: 15px;
            border-radius: 15px;
        ">
            <div style="
                display: flex;
                align-items: center;
                gap: 10px;
            ">
                <div style="
                    background: {cor_destaque}15;
                    width: 35px;
                    height: 35px;
                    border-radius: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 18px;
                ">📍</div>
                <div>
                    <div style="font-size: 0.8rem; color: {cor_texto}60;">Rota</div>
                    <div style="font-weight: 600;">{origem} ✈️ {destino}</div>
                </div>
            </div>
            
            <div style="
                display: flex;
                align-items: center;
                gap: 10px;
            ">
                <div style="
                    background: {cor_destaque}15;
                    width: 35px;
                    height: 35px;
                    border-radius: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 18px;
                ">👥</div>
                <div>
                    <div style="font-size: 0.8rem; color: {cor_texto}60;">Passageiros</div>
                    <div style="font-weight: 600;">{passageiros} adulto(s)</div>
                </div>
            </div>
            
            <div style="
                display: flex;
                align-items: center;
                gap: 10px;
            ">
                <div style="
                    background: {cor_destaque}15;
                    width: 35px;
                    height: 35px;
                    border-radius: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 18px;
                ">👶</div>
                <div>
                    <div style="font-size: 0.8rem; color: {cor_texto}60;">Bebês</div>
                    <div style="font-weight: 600;">{bebes} bebê(s)</div>
                </div>
            </div>
            
            <div style="
                display: flex;
                align-items: center;
                gap: 10px;
            ">
                <div style="
                    background: {cor_destaque}15;
                    width: 35px;
                    height: 35px;
                    border-radius: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 18px;
                ">🧳</div>
                <div>
                    <div style="font-size: 0.8rem; color: {cor_texto}60;">Bagagens</div>
                    <div style="font-weight: 600;">{num_bagagens} unidade(s)</div>
                </div>
            </div>
            
            <div style="
                display: flex;
                align-items: center;
                gap: 10px;
                grid-column: span 2;
            ">
                <div style="
                    background: {cor_destaque}15;
                    width: 35px;
                    height: 35px;
                    border-radius: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 18px;
                ">📅</div>
                <div>
                    <div style="font-size: 0.8rem; color: {cor_texto}60;">Data do cálculo</div>
                    <div style="font-weight: 600;">{data_calculo_formatada}</div>
                </div>
            </div>
        </div>
        
        <!-- Card de valores em destaque -->
        <div style="
            background: linear-gradient(135deg, {cor_destaque} 0%, {cor_destaque}dd 100%);
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 15px {cor_destaque}40;
        ">
            <div>
                <div style="font-size: 0.9rem; opacity: 0.9;">💵 TOTAL DA COTAÇÃO</div>
                <div style="font-size: 2.5rem; font-weight: 700; line-height: 1.2;">
                    {simbolo} {total:.2f}
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.9rem; opacity: 0.9;">💰 POR PASSAGEIRO</div>
                <div style="font-size: 1.8rem; font-weight: 600;">
                    {simbolo} {valor_por_pax:.2f}
                </div>
                <div style="font-size: 0.8rem; opacity: 0.8;">👥 {passageiros} pax</div>
            </div>
        </div>
    </div>
    '''.format(
        cor_card=cores['card'],
        cor_fundo=cores['fundo'],
        cor_borda=cores['borda'],
        cor_destaque=cores['destaque'],
        cor_texto=cores['texto'],
        cor_success=cores['success'],
        cor_companhia=cor_companhia,
        icone_companhia=icone_companhia,
        posicao=total_items - idx,
        nome_cotacao=nome_cotacao,
        tipo_calculo=tipo_calculo,
        companhia=companhia,
        origem=origem,
        destino=destino,
        passageiros=passageiros,
        bebes=bebes,
        num_bagagens=num_bagagens,
        data_calculo_formatada=data_formatada,
        simbolo=simbolo,
        total=total,
        valor_por_pax=valor_por_pax
    )
    
    # IMPORTANTE: NÃO use st.markdown aqui! Retorne o HTML
    return html_card

def pagina_historico():
    """Página de histórico de cotações com visual bonito e botões funcionais"""
    try:
        cores = get_colors()
        
        st.title(f"📜 Histórico de Cotações")
        
        # Inicializar estado para seleção múltipla
        if 'itens_selecionados' not in st.session_state:
            st.session_state.itens_selecionados = set()
        
        # Botão para limpar seleção
        col_top1, col_top2, col_top3 = st.columns([1, 1, 2])
        with col_top1:
            if st.button("🗑️ Limpar Seleção", use_container_width=True):
                st.session_state.itens_selecionados = set()
                st.rerun()
        
        with col_top2:
            if len(st.session_state.itens_selecionados) > 0:
                st.info(f"📌 {len(st.session_state.itens_selecionados)} selecionado(s)")
        
        with st.expander("🔍 Filtros Avançados", expanded=True):
            col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
            
            with col_filtro1:
                companhias_opcoes = ["Todas", "LATAM Airlines", "GOL Linhas Aéreas", "Azul Linhas Aéreas", "American Airlines"]
                filtro_companhia = st.selectbox(
                    "Companhia aérea",
                    companhias_opcoes,
                    key="filtro_companhia"
                )
            
            with col_filtro2:
                periodo = st.selectbox(
                    "Período",
                    ["Últimos 30 dias", "Últimos 7 dias", "Este mês", "Mês anterior", "Personalizado", "Todos"],
                    key="filtro_periodo"
                )
            
            with col_filtro3:
                limite_resultados = st.slider(
                    "Máximo de resultados",
                    min_value=10,
                    max_value=500,
                    value=100,
                    step=10,
                    key="filtro_limite"
                )
            
            if periodo == "Personalizado":
                col_data1, col_data2 = st.columns(2)
                with col_data1:
                    data_inicio = st.date_input("Data início", value=None, key="data_inicio_hist")
                with col_data2:
                    data_fim = st.date_input("Data fim", value=None, key="data_fim_hist")
            else:
                data_inicio = None
                data_fim = None
        
        # Aplicar filtros
        filtro_companhia_db = None if filtro_companhia == "Todas" else filtro_companhia
        
        if periodo == "Últimos 30 dias":
            data_inicio_str = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            data_fim_str = None
        elif periodo == "Últimos 7 dias":
            data_inicio_str = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            data_fim_str = None
        elif periodo == "Este mês":
            hoje = datetime.now()
            data_inicio_str = hoje.replace(day=1).strftime("%Y-%m-%d")
            data_fim_str = None
        elif periodo == "Mês anterior":
            hoje = datetime.now()
            primeiro_mes_anterior = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)
            ultimo_mes_anterior = hoje.replace(day=1) - timedelta(days=1)
            data_inicio_str = primeiro_mes_anterior.strftime("%Y-%m-%d")
            data_fim_str = ultimo_mes_anterior.strftime("%Y-%m-%d")
        elif periodo == "Personalizado" and data_inicio:
            data_inicio_str = data_inicio.strftime("%Y-%m-%d")
            data_fim_str = data_fim.strftime("%Y-%m-%d") if data_fim else None
        else:
            data_inicio_str = None
            data_fim_str = None
        
        # Buscar histórico
        historico = listar_historico(
            st.session_state.usuario_id,
            filtro_companhia=filtro_companhia_db,
            data_inicio=data_inicio_str,
            data_fim=data_fim_str,
            limite=limite_resultados
        )
        
        if not historico:
            st.markdown(f"""
            <div class='fade-in' style='text-align: center; padding: 3rem; background: {cores['card']}; border-radius: 15px; border: 1px solid {cores['borda']};'>
                <h3 style='color: {cores['texto']}70; margin-bottom: 1rem;'>📭 Nenhuma cotação encontrada</h3>
                <p style='color: {cores['texto']}50; margin-bottom: 2rem;'>
                    {f"Não há cotações no período selecionado." if periodo != "Todos" else "Crie sua primeira cotação para ver o histórico aqui."}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            col_btn_empty1, col_btn_empty2 = st.columns(2)
            with col_btn_empty1:
                if st.button("📋 Criar primeira cotação", type="primary", use_container_width=True, key="btn_criar_primeira"):
                    st.session_state.pagina = 'nova_cotacao'
                    st.rerun()
            with col_btn_empty2:
                if st.button("✈️ Ver companhias", type="secondary", use_container_width=True, key="btn_ver_companhias"):
                    st.session_state.pagina = 'companhias'
                    st.rerun()
            
            return
        
        # Estatísticas
        total_cotacoes = len(historico)
        total_gasto = sum(item['total_geral'] for item in historico)
        media_por_cotacao = total_gasto / total_cotacoes if total_cotacoes > 0 else 0
        simbolo = get_currency_symbol(st.session_state.moeda)
        
        st.success(f"📊 Encontradas **{total_cotacoes}** cotações | Total gasto: **{simbolo} {total_gasto:,.2f}**")
        
        col_metric1, col_metric2, col_metric3 = st.columns(3)
        with col_metric1:
            st.metric("Total de Cotações", total_cotacoes)
        with col_metric2:
            st.metric("Total Gasto", f"{simbolo} {total_gasto:,.2f}")
        with col_metric3:
            st.metric("Média por Cotação", f"{simbolo} {media_por_cotacao:,.2f}")
        
        # BOTÃO DE RELATÓRIO DO GRUPO SELECIONADO
        if len(st.session_state.itens_selecionados) > 0:
            st.markdown("---")
            col_grupo1, col_grupo2, col_grupo3 = st.columns([1, 1, 2])
            
            with col_grupo1:
                if st.button("📊 Gerar Relatório do Grupo Selecionado", type="primary", use_container_width=True):
                    itens_selecionados_lista = [
                        item for item in historico 
                        if str(item['id']) in st.session_state.itens_selecionados
                    ]
                    
                    with st.spinner(f"🔄 Gerando PDF com {len(itens_selecionados_lista)} cotações..."):
                        deps = verificar_dependencias_exportacao()
                        
                        if not deps['reportlab']:
                            st.error("❌ ReportLab não instalado. Execute: pip install reportlab")
                        else:
                            pdf_buffer, nome_arquivo, qtd = gerar_relatorio_pdf_selecionados(
                                itens_selecionados_lista,
                                st.session_state.usuario_nome,
                                f"Relatório de {len(itens_selecionados_lista)} Cotações Selecionadas"
                            )
                            
                            if pdf_buffer:
                                registrar_evento_seguranca(
                                    st.session_state.usuario_id,
                                    "RELATORIO_GRUPO",
                                    f"Gerou relatório com {qtd} cotações selecionadas",
                                    "INFO"
                                )
                                
                                st.download_button(
                                    label="📥 Baixar PDF do Grupo",
                                    data=pdf_buffer,
                                    file_name=nome_arquivo,
                                    mime="application/pdf",
                                    use_container_width=True,
                                    key="download_grupo"
                                )
                                st.success(f"✅ PDF gerado com {qtd} cotações!")
                            else:
                                st.error("❌ Erro ao gerar PDF")
            
            with col_grupo2:
                if st.button("🗑️ Limpar Seleção", use_container_width=True):
                    st.session_state.itens_selecionados = set()
                    st.rerun()
            
            with col_grupo3:
                st.info(f"📌 {len(st.session_state.itens_selecionados)} cotações selecionadas para o relatório")
            
            st.markdown("---")
        
        # LISTAGEM DAS COTAÇÕES
        st.markdown(f"### 📋 Cotações ({total_cotacoes})")
        
        for idx, item in enumerate(historico):
            with st.container():
                # Criar chaves únicas para cada item
                item_id = str(item['id'])
                detalhes_key = f"detalhes_{item_id}"
                confirma_key = f"confirma_{item_id}"
                
                # Inicializar estados se não existirem
                if detalhes_key not in st.session_state:
                    st.session_state[detalhes_key] = False
                if confirma_key not in st.session_state:
                    st.session_state[confirma_key] = False
                
                # Checkbox para selecionar
                col_check, col_conteudo = st.columns([0.5, 9.5])
                
                with col_check:
                    is_selected = item_id in st.session_state.itens_selecionados
                    
                    if st.checkbox(
                        "✓" if is_selected else "□",
                        value=is_selected,
                        key=f"check_{item_id}",
                        label_visibility="collapsed"
                    ):
                        if not is_selected:
                            st.session_state.itens_selecionados.add(item_id)
                            st.rerun()
                    else:
                        if is_selected:
                            st.session_state.itens_selecionados.remove(item_id)
                            st.rerun()
                
                with col_conteudo:
                    # Dados da cotação
                    passageiros = item.get('passageiros', 1) or 1
                    bebes = item.get('bebes', 0) or 0
                    num_bagagens = item.get('num_bagagens', 0) or 0
                    
                    data_calculo = item.get('data_calculo', '')
                    if data_calculo and len(data_calculo) >= 16:
                        data_formatada = data_calculo[:16].replace('T', ' ')
                    else:
                        data_formatada = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    nome_cotacao = item.get('nome_cotacao', 'Cotação')
                    origem = item.get('origem', '???')
                    destino = item.get('destino', '???')
                    simbolo_item = get_currency_symbol(item.get('moeda', 'BRL'))
                    total = item['total_geral']
                    tipo_calculo = item.get('tipo_calculo', 'LATAM - Milhas + Taxa')
                    companhia = item.get('companhia', 'LATAM Airlines')
                    
                    # Extrair dados de milhas
                    milhas_total = item.get('milhas_total', 0)
                    valor_milheiro = item.get('valor_milheiro', 0)
                    
                    # ===== EXTRAIR DATAS DOS METADADOS =====
                    data_ida = "N/I"
                    data_volta = "N/I"
                    tipo_viagem = "N/I"
                    
                    if item.get('metadata'):
                        metadata = item['metadata']
                        data_ida = metadata.get('data_ida', 'N/I')
                        data_volta = metadata.get('data_volta', 'N/I')
                        tipo_viagem = metadata.get('tipo_viagem', 'N/I')
                    
                    # Card da cotação - USANDO TEMPLATE SEPARADO
                    card_template = '''
                    <div style="background: {cor_fundo}; border-radius: 12px; padding: 20px; margin-bottom: 15px; border: 1px solid {cor_borda};">
                        <div style="margin-bottom: 10px;">
                            <span style="color: {cor_destaque};"># {posicao}</span>
                        </div>
                        <h2 style="font-size: 1.8rem; margin: 5px 0;">{nome_cotacao}</h2>
                        <div style="margin-bottom: 15px;">
                            <span style="background: {cor_destaque}15; color: {cor_destaque}; padding: 4px 12px; border-radius: 20px;">{tipo_calculo}</span>
                            <span style="margin-left: 8px;">{companhia}</span>
                        </div>
                        <p style="margin: 5px 0;"><strong>Rota:</strong> {origem} → {destino}</p>
                        <p style="margin: 5px 0;"><strong>Passageiros:</strong> {passageiros} • <strong>👶 Bebês:</strong> {bebes} • <strong>🧳 Bagagens:</strong> {num_bagagens}</p>
                        <p style="margin: 5px 0;"><strong>📅 Viagem:</strong> {tipo_viagem} • Ida: {data_ida} • Volta: {data_volta}</p>
                        <p style="margin: 5px 0;"><strong>Data:</strong> {data_calculo}</p>
                        <hr style="margin: 15px 0;">
                        <div style="text-align: right;">
                            <h3 style="color: #3d8bfd; margin: 0;">{simbolo} {total:,.2f}</h3>
                            <p style="color: gray;">{simbolo} {valor_pax:,.2f}/pax</p>
                        </div>
                    </div>
                    '''
                    
                    card_html = card_template.format(
                        cor_fundo=cores['card'],
                        cor_borda=cores['borda'],
                        cor_destaque=cores['destaque'],
                        posicao=total_cotacoes - idx,
                        nome_cotacao=nome_cotacao,
                        tipo_calculo=tipo_calculo,
                        companhia=companhia,
                        origem=origem,
                        destino=destino,
                        passageiros=passageiros,
                        bebes=bebes,
                        num_bagagens=num_bagagens,
                        tipo_viagem=tipo_viagem,
                        data_ida=data_ida,
                        data_volta=data_volta,
                        data_calculo=data_formatada,
                        simbolo=simbolo_item,
                        total=total,
                        valor_pax=total/passageiros
                    )
                    
                    st.markdown(card_html, unsafe_allow_html=True)
                    
                    # Botões de ação
                    col1, col2, col3, col4, col5 = st.columns(5)
                    
                    with col1:
                        if st.button("📋 Detalhes", key=f"btn_detalhes_{item_id}", use_container_width=True):
                            st.session_state[detalhes_key] = not st.session_state[detalhes_key]
                            st.rerun()
                    
                    with col2:
                        if st.button("📋 Duplicar", key=f"btn_dup_{item_id}", use_container_width=True):
                            st.session_state.nome_cotacao = f"Cópia - {nome_cotacao}"
                            st.session_state.origem = origem
                            st.session_state.destino = destino
                            st.session_state.passageiros_para_cotacao = passageiros
                            st.session_state.bebes_para_cotacao = bebes
                            st.session_state.bagagens_para_cotacao = num_bagagens
                            
                            sucesso, resultado = criar_cotacao(
                                st.session_state.usuario_id,
                                st.session_state.nome_cotacao,
                                origem,
                                destino
                            )
                            
                            if sucesso:
                                st.session_state.cotacao_atual = resultado
                                st.success("✅ Cotação duplicada!")
                                time.sleep(1)
                                st.session_state.pagina = 'calculadora'
                                st.rerun()
                            else:
                                st.error(f"❌ {resultado}")
                    
                    with col3:
                        if st.button("🗑️ Excluir", key=f"btn_del_{item_id}", use_container_width=True):
                            st.session_state[confirma_key] = True
                            st.rerun()
                    
                    with col4:
                        if st.button("📊 Custo", key=f"btn_custo_{item_id}", use_container_width=True):
                            with st.spinner("Gerando PDF de custo..."):
                                try:
                                    pdf_buffer, nome_arquivo = gerar_relatorio_custo_pdf(
                                        item, 
                                        st.session_state.usuario_nome
                                    )
                                    
                                    if pdf_buffer is not None:
                                        st.success("✅ PDF de custo gerado!")
                                        st.download_button(
                                            "📥 Baixar PDF de Custo",
                                            pdf_buffer,
                                            nome_arquivo,
                                            "application/pdf",
                                            key=f"download_custo_{item_id}"
                                        )
                                    else:
                                        st.error("❌ Erro ao gerar PDF de custo")
                                        st.info("Verifique se o ReportLab está instalado: pip install reportlab")
                                except Exception as e:
                                    st.error(f"❌ Erro: {str(e)}")
                    
                    with col5:
                        with st.expander(f"💰 Venda - {nome_cotacao}", expanded=False):
                            # Logo da companhia no topo
                            logo_companhia_base64 = carregar_imagem_companhia(companhia.lower())
                            
                            col_logo1, col_logo2 = st.columns([1, 3])
                            with col_logo1:
                                logo_html = '''
                                <div style="background: {cor_fundo}; padding: 10px; border-radius: 10px; text-align: center;">
                                    <img src="data:image/png;base64,{logo}" style="width: 100%; max-width: 120px; height: auto; object-fit: contain;">
                                </div>
                                '''.format(
                                    cor_fundo=cores['card'],
                                    logo=logo_companhia_base64
                                )
                                st.markdown(logo_html, unsafe_allow_html=True)
                            
                            with col_logo2:
                                info_html = '''
                                <div style="padding: 10px;">
                                    <h4 style="margin: 0; color: {cor_destaque};">{companhia}</h4>
                                    <p style="margin: 5px 0 0 0; color: {cor_texto}80;">{tipo_calculo}</p>
                                    <p style="margin: 5px 0 0 0; font-size: 0.9rem;">{origem} ✈️ {destino}</p>
                                    <p style="margin: 5px 0 0 0; font-size: 0.85rem; color: {cor_info};">📅 {tipo_viagem} | Ida: {data_ida} | Volta: {data_volta}</p>
                                </div>
                                '''.format(
                                    cor_destaque=cores['destaque'],
                                    cor_texto=cores['texto'],
                                    cor_info=cores['info'],
                                    companhia=companhia,
                                    tipo_calculo=tipo_calculo,
                                    origem=origem,
                                    destino=destino,
                                    tipo_viagem=tipo_viagem,
                                    data_ida=data_ida,
                                    data_volta=data_volta
                                )
                                st.markdown(info_html, unsafe_allow_html=True)
                            
                            st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
                            
                            st.info(f"**CUSTO BASE:** {simbolo_item} {total:,.2f}")
                            
                            # Upload da logo da empresa
                            logo_file = st.file_uploader(
                                "🏢 Logo da sua empresa (para o PDF)",
                                type=['png', 'jpg', 'jpeg'],
                                key=f"logo_{item_id}"
                            )
                            
                            # Valor de venda
                            valor_venda = st.number_input(
                                "💰 Valor de Venda",
                                min_value=0.0,
                                value=float(total * 1.3),
                                step=10.0,
                                format="%.2f",
                                key=f"venda_input_{item_id}"
                            )
                            
                            # Cálculo do lucro
                            lucro = valor_venda - total
                            margem = (lucro / total * 100) if total > 0 else 0
                            
                            # Métricas em cards
                            col_m1, col_m2 = st.columns(2)
                            with col_m1:
                                st.metric("📊 LUCRO", f"{simbolo_item} {lucro:,.2f}", f"{margem:.2f}%")
                            with col_m2:
                                st.metric("👤 POR PASSAGEIRO", f"{simbolo_item} {(lucro/passageiros):,.2f}")
                            
                            # Detalhamento rápido com formatação HTML
                            with st.expander("📋 Detalhamento", expanded=False):
                                detalhes_template = '''
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; padding: 10px;">
                                    <div style="background: {cor_fundo}; padding: 10px; border-radius: 8px;">
                                        <h5 style="color: {cor_destaque}; margin: 0 0 10px 0; border-bottom: 1px solid {cor_borda}; padding-bottom: 5px;">📋 DADOS GERAIS</h5>
                                        <p><strong>👥 Passageiros:</strong> {passageiros}</p>
                                        <p><strong>👶 Bebês:</strong> {bebes}</p>
                                        <p><strong>🧳 Bagagens:</strong> {num_bagagens}</p>
                                        <p><strong>📅 Viagem:</strong> {tipo_viagem}</p>
                                        <p><strong>📆 Ida:</strong> {data_ida}</p>
                                        <p><strong>📆 Volta:</strong> {data_volta}</p>
                                        <p><strong>📅 Data cálculo:</strong> {data_calculo}</p>
                                    </div>
                                    <div style="background: {cor_fundo}; padding: 10px; border-radius: 8px;">
                                        <h5 style="color: {cor_destaque}; margin: 0 0 10px 0; border-bottom: 1px solid {cor_borda}; padding-bottom: 5px;">💰 VALORES</h5>
                                        <p><strong>💵 Custo total:</strong> {simbolo} {total:,.2f}</p>
                                        <p><strong>💲 Valor venda:</strong> {simbolo} {valor_venda:,.2f}</p>
                                        <p><strong>📈 Lucro:</strong> {simbolo} {lucro:,.2f}</p>
                                        <p><strong>📊 Margem:</strong> {margem:.1f}%</p>
                                    </div>
                                </div>
                                '''
                                
                                st.markdown(detalhes_template.format(
                                    cor_fundo=cores['fundo'],
                                    cor_destaque=cores['destaque'],
                                    cor_borda=cores['borda'],
                                    passageiros=passageiros,
                                    bebes=bebes,
                                    num_bagagens=num_bagagens,
                                    tipo_viagem=tipo_viagem,
                                    data_ida=data_ida,
                                    data_volta=data_volta,
                                    data_calculo=data_formatada,
                                    simbolo=simbolo_item,
                                    total=total,
                                    valor_venda=valor_venda,
                                    lucro=lucro,
                                    margem=margem
                                ), unsafe_allow_html=True)
                                
                                # Adicionar detalhes das milhas se existirem
                                if milhas_total > 0 or valor_milheiro > 0:
                                    milhas_template = '''
                                    <div style="background: {cor_info}15; padding: 10px; border-radius: 8px; margin-top: 10px; border-left: 4px solid {cor_info};">
                                        <h5 style="color: {cor_info}; margin: 0 0 10px 0;">💎 DETALHES DAS MILHAS</h5>
                                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                                            <p><strong>🔄 Milhas/Pontos:</strong> {milhas_total:,.0f}</p>
                                            <p><strong>💰 Valor/Milheiro:</strong> {simbolo} {valor_milheiro:,.2f}</p>
                                            <p><strong>🧮 Custo em milhas:</strong> {simbolo} {custo_milhas:,.2f}</p>
                                            <p><strong>📊 Custo médio/milha:</strong> {simbolo} {custo_milha:,.4f}</p>
                                        </div>
                                    </div>
                                    '''
                                    
                                    st.markdown(milhas_template.format(
                                        cor_info=cores['info'],
                                        milhas_total=milhas_total,
                                        simbolo=simbolo_item,
                                        valor_milheiro=valor_milheiro,
                                        custo_milhas=milhas_total * valor_milheiro,
                                        custo_milha=valor_milheiro
                                    ), unsafe_allow_html=True)
                            
                            # Botão gerar PDF de venda
                            if st.button("📄 Gerar PDF para Cliente", key=f"btn_venda_{item_id}"):
                                with st.spinner("Gerando PDF de venda..."):
                                    logo_path = None
                                    if logo_file:
                                        logo_path = f"temp_logo_{item_id}.png"
                                        with open(logo_path, "wb") as f:
                                            f.write(logo_file.getbuffer())
                                    
                                    try:
                                        pdf_buffer, nome_arquivo = gerar_relatorio_venda_pdf(
                                            item, 
                                            valor_venda, 
                                            st.session_state.usuario_nome,
                                            logo_empresa=logo_path
                                        )
                                        
                                        if pdf_buffer is not None:
                                            st.success("✅ PDF gerado com sucesso!")
                                            st.download_button(
                                                "📥 Baixar PDF para Cliente",
                                                pdf_buffer,
                                                nome_arquivo,
                                                "application/pdf",
                                                key=f"download_venda_{item_id}"
                                            )
                                        else:
                                            st.error("❌ Erro ao gerar PDF")
                                            st.info("Verifique se o ReportLab está instalado: pip install reportlab")
                                    
                                    except Exception as e:
                                        st.error(f"❌ Erro: {str(e)}")
                                    
                                    finally:
                                        if logo_path and os.path.exists(logo_path):
                                            os.remove(logo_path)
                    
                    # Detalhes expandidos com design responsivo
                    if st.session_state.get(detalhes_key, False):
                        with st.expander("📋 Detalhes completos", expanded=True):
                            
                            st.markdown(f"""
                            **🔍 Detalhes da Cotação #{item_id}**
                            
                            **✈️ Companhia:** {item.get('companhia', 'N/A')} - {item.get('tipo_calculo', 'N/A')}
                            
                            **📍 Rota:** {item.get('origem', '???')} → {item.get('destino', '???')}
                            
                            **👥 Viajantes:** {passageiros} passageiros, {bebes} bebês, {num_bagagens} bagagens
                            
                            **📅 Viagem:** {tipo_viagem} | Ida: {data_ida} | Volta: {data_volta}
                            
                            **💎 Milhas:** {item.get('milhas_total', 0):,.3f} | Valor/Milheiro: {simbolo_item} {item.get('valor_milheiro', 0):,.2f}
                            
                            **💰 Total:** {simbolo_item} {total:,.2f}
                            """)
                            
                            if st.button("🔽 Fechar detalhes", key=f"fechar_det_{item_id}", use_container_width=True):
                                st.session_state[detalhes_key] = False
                                st.rerun()
                    
                    # Confirmação de exclusão
                    if st.session_state.get(confirma_key, False):
                        col_sim, col_nao = st.columns(2)
                        with col_sim:
                            if st.button("✅ Sim, excluir", key=f"sim_{item_id}"):
                                sucesso, msg = excluir_calculo(item['id'], st.session_state.usuario_id)
                                if sucesso:
                                    st.success(msg)
                                    st.session_state[confirma_key] = False
                                    if item_id in st.session_state.itens_selecionados:
                                        st.session_state.itens_selecionados.remove(item_id)
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"❌ {msg}")
                        with col_nao:
                            if st.button("❌ Não, cancelar", key=f"nao_{item_id}"):
                                st.session_state[confirma_key] = False
                                st.rerun()
                    
                    if idx < len(historico) - 1:
                        st.markdown("---")
        
    except Exception as e:
        st.error(f"❌ Erro na página de histórico: {str(e)}")
        st.code(traceback.format_exc())
        if st.button("🔄 Recarregar"):
            st.rerun()
                
                
def executar_diagnostico():
    """Executa diagnóstico do sistema para identificar problemas"""
    st.title("🔧 Diagnóstico do Sistema")
    
    problemas = []
    sucessos = []
    
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabelas = cursor.fetchall()
        
        tabelas_necessarias = ['usuarios', 'cotacoes', 'historico_cotacoes', 'logs_seguranca']
        for tabela in tabelas_necessarias:
            if (tabela,) not in tabelas:
                problemas.append(f"Tabela '{tabela}' não encontrada no banco de dados")
            else:
                sucessos.append(f"Tabela '{tabela}' encontrada")
        
        cursor.execute('SELECT id FROM usuarios WHERE email = ?', ('admin@dbmilesx.com',))
        admin_existe = cursor.fetchone()
        if not admin_existe:
            problemas.append("Usuário admin não encontrado")
        else:
            sucessos.append(f"Usuário admin encontrado (ID: {admin_existe[0]})")
        
        conn.close()
    except Exception as e:
        problemas.append(f"Erro ao acessar banco de dados: {str(e)}")
    
    try:
        logo = carregar_logo()
        if logo:
            sucessos.append("Logo carregada com sucesso")
        else:
            problemas.append("Não foi possível carregar a logo")
    except Exception as e:
        problemas.append(f"Erro ao carregar logo: {str(e)}")
    
    import tempfile
    try:
        if os.getenv('STREAMLIT_CLOUD') or os.getenv('CLOUDFLARE'):
            temp_dir = tempfile.gettempdir()
            if os.access(temp_dir, os.W_OK):
                sucessos.append(f"Diretório temporário acessível: {temp_dir}")
            else:
                problemas.append(f"Diretório temporário não acessível: {temp_dir}")
    except Exception as e:
        problemas.append(f"Erro ao verificar diretórios: {str(e)}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✅ Sucessos")
        for sucesso in sucessos:
            st.success(sucesso)
    
    with col2:
        st.subheader("❌ Problemas")
        for problema in problemas:
            st.error(problema)
    
    if problemas:
        st.markdown("---")
        st.subheader("🛠️ Ações Corretivas")
        
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            if st.button("🔄 Recriar Banco de Dados", type="primary"):
                try:
                    if os.path.exists(DB_PATH):
                        os.remove(DB_PATH)
                        st.success("Banco de dados excluído")
                    
                    inicializar_banco()
                    st.success("Banco de dados recriado com sucesso!")
                    st.info("Recarregando página...")
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao recriar banco: {str(e)}")
        
        with col_btn2:
            if st.button("🔧 Criar Usuário de Teste", type="secondary"):
                try:
                    conn = criar_conexao()
                    cursor = conn.cursor()
                    
                    cursor.execute('SELECT id FROM usuarios WHERE email = ?', ('teste@dbmilesx.com',))
                    if not cursor.fetchone():
                        senha_hash = security.hash_password('Teste123!')
                        cursor.execute('''
                        INSERT INTO usuarios (email, senha_hash, nome, tema_preferido, moeda_preferida, csrf_token)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ''', ('teste@dbmilesx.com', senha_hash, 'Usuário Teste', 'escuro', 'BRL', 
                              security.generate_csrf_token()))
                        
                        conn.commit()
                        st.success("Usuário teste criado com sucesso!")
                        st.info("Email: teste@dbmilesx.com | Senha: Teste123!")
                    else:
                        st.info("Usuário teste já existe")
                    
                    conn.close()
                except Exception as e:
                    st.error(f"Erro ao criar usuário teste: {str(e)}")
        
        with col_btn3:
            if st.button("📋 Ver Logs de Erro", type="secondary"):
                st.text_area("Últimos logs do sistema:", value="Nenhum log disponível")
    
    else:
        st.balloons()
        st.success("✅ Sistema funcionando normalmente!")

def debug_login_system():
    """Função para debug do sistema de login"""
    import bcrypt
    
    print("\n" + "="*50)
    print("🔍 DEBUG SISTEMA DE LOGIN")
    print("="*50)
    
    print(f"1. Estado atual da sessão:")
    print(f"   - logado: {st.session_state.get('logado', 'NÃO DEFINIDO')}")
    print(f"   - pagina: {st.session_state.get('pagina', 'NÃO DEFINIDO')}")
    print(f"   - usuario_id: {st.session_state.get('usuario_id', 'NÃO DEFINIDO')}")
    
    print(f"\n2. Testando conexão com banco...")
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        count = cursor.fetchone()[0]
        conn.close()
        print(f"   ✅ Banco OK. Usuários: {count}")
        
        conn = criar_conexao()
        cursor = conn.cursor()
        cursor.execute("SELECT email, senha_hash FROM usuarios WHERE email = 'admin@dbmilesx.com'")
        admin = cursor.fetchone()
        conn.close()
        
        if admin:
            print(f"   ✅ Admin encontrado: {admin[0]}")
            print(f"   🔐 Hash admin: {admin[1][:30]}...")
        else:
            print(f"   ❌ Admin NÃO encontrado!")
            
    except Exception as e:
        print(f"   ❌ Erro no banco: {e}")
    
    print(f"\n3. Testando verificação de senha...")
    try:
        from database import verify_password_compativel
        test_senha = "Admin@DBMILESX123!"
        test_hash = bcrypt.hashpw(test_senha.encode(), bcrypt.gensalt()).decode()
        resultado = verify_password_compativel(test_senha, test_hash)
        print(f"   ✅ Teste bcrypt: {resultado}")
    except Exception as e:
        print(f"   ❌ Erro teste senha: {e}")
    
    print("\n" + "="*50)

def corrigir_senhas_emergencia():
    """Corrige todas as senhas para bcrypt"""
    import sqlite3
    import bcrypt
    
    print("🔧 CORRIGINDO SENHAS DO BANCO...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        senha_hash TEXT NOT NULL,
        nome TEXT NOT NULL,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        tema_preferido TEXT DEFAULT 'escuro',
        moeda_preferida TEXT DEFAULT 'BRL'
    )
    ''')
    
    senhas_usuarios = {
        'admin@dbmilesx.com': ('Admin@DBMILESX123!', 'Administrador'),
        'teste@dbmilesx.com': ('Teste123!', 'Usuário Teste')
    }
    
    for email, (senha, nome) in senhas_usuarios.items():
        senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
        
        cursor.execute('''
        INSERT OR REPLACE INTO usuarios (email, senha_hash, nome)
        VALUES (?, ?, ?)
        ''', (email, senha_hash, nome))
        
        print(f"✅ {email}: {senha}")
    
    conn.commit()
    conn.close()
    
    print("\n🎉 BANCO CORRIGIDO!")
    print("\n📋 USE ESTAS CREDENCIAIS:")
    print("👉 admin@dbmilesx.com / Admin@DBMILESX123!")
    print("👉 teste@dbmilesx.com / Teste123!")
    
    return True

# ============= WRAPPERS PARA FUNÇÕES FALTANTES =============

def redefinir_senha(email: str, nova_senha: str) -> Tuple[bool, str]:
    """Wrapper para redefinir senha"""
    from database import redefinir_senha_com_token
    # Gerar token temporário
    token = gerar_token_recuperacao(email)
    if token:
        return redefinir_senha_com_token(token, nova_senha)
    return False, "Erro ao gerar token"

def verificar_login(email: str, senha: str, db_path: str = None) -> Tuple[bool, Any]:
    """Wrapper para verificar login"""
    from database import verificar_login_simplificado
    return verificar_login_simplificado(email, senha)

def get_currency_symbol(moeda: str) -> str:
    """Wrapper para símbolo da moeda"""
    simbolos = {"BRL": "R$", "USD": "$", "EUR": "€", "GBP": "£"}
    return simbolos.get(moeda, "R$")

def main():
    """Função principal da aplicação"""
    aplicar_tema_atual()

    # Inicializar banco e tabelas
    if 'banco_verificado' not in st.session_state:
        try:
            reparar_tabela_usuarios()
            inicializar_tabela_tokens()
            inicializar_tabelas_solicitacoes()
            
            # Adicionar colunas faltantes
            from database import adicionar_coluna_updated_at, adicionar_coluna_data_atualizacao_cotacoes
            adicionar_coluna_updated_at()
            adicionar_coluna_data_atualizacao_cotacoes()
            adicionar_coluna_foto_perfil()
            
            st.session_state.banco_verificado = True
        except Exception as e:
            logger.error(f"Erro na verificação do banco: {e}")
        
    # Verificar parâmetros da URL - PRIORIDADE PARA FORMULÁRIO PÚBLICO
    query_params = get_query_params()
    
    if "token" in query_params and "form" in query_params:
        token = query_params["token"]
        if isinstance(token, list):
            token = token[0]
        
        form_type = query_params["form"]
        if isinstance(form_type, list):
            form_type = form_type[0]
        
        if form_type == "cotacao":
            from solicitacao import formulario_publico_cotacao
            formulario_publico_cotacao(token)
            return
    
    # Verificar token de recuperação de senha
    if "token" in query_params and "form" not in query_params:
        token = query_params["token"]
        if isinstance(token, list):
            token = token[0]
        pagina_redefinir_senha_com_token(token)
        return
    
    # Diagnóstico
    if "diagnostico" in query_params:
        valor_diagnostico = query_params["diagnostico"]
        if isinstance(valor_diagnostico, list):
            valor_diagnostico = valor_diagnostico[0]
        if valor_diagnostico == "true":
            executar_diagnostico()
            return

    # Inicializar sistema completo
    def inicializar_sistema_completo():
        try:
            if os.path.exists(DB_PATH):
                try:
                    conn = criar_conexao()
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
                    if not cursor.fetchone():
                        conn.close()
                        os.remove(DB_PATH)
                        inicializar_banco()
                    else:
                        conn.close()
                        reparar_tabela_usuarios()
                        reparar_tabela_historico()
                        limpar_dados_corrompidos()
                except Exception as e:
                    logger.error(f"Erro ao verificar banco: {e}")
                    if os.path.exists(DB_PATH):
                        os.remove(DB_PATH)
                    inicializar_banco()
            else:
                inicializar_banco()
            return True
        except Exception as e:
            logger.error(f"Erro fatal ao inicializar sistema: {e}")
            st.error(f"❌ Erro crítico ao inicializar sistema: {str(e)}")
            return False
    
    sucesso = inicializar_sistema_completo()
    
    if not sucesso:
        st.markdown("---")
        st.subheader("🛠️ Opções de Recuperação")
        
        col_rec1, col_rec2, col_rec3 = st.columns(3)
        
        with col_rec1:
            if st.button("🔧 Executar Diagnóstico", type="primary"):
                try:
                    if hasattr(st, 'query_params'):
                        st.query_params["diagnostico"] = "true"
                    else:
                        st.session_state.diagnostico = True
                except:
                    st.session_state.diagnostico = True
                st.rerun()
        
        with col_rec2:
            if st.button("🔄 Tentar Modo Simples", type="secondary"):
                try:
                    global DB_PATH
                    DB_PATH = ':memory:'
                    inicializar_banco()
                    st.success("✅ Modo simples ativado!")
                    st.info("Os dados serão perdidos ao recarregar a página.")
                    time.sleep(2)
                    st.rerun()
                except Exception as mem_error:
                    st.error(f"❌ Falha no modo simples: {mem_error}")
        
        with col_rec3:
            if st.button("🗑️ Limpar Banco e Recriar", type="secondary"):
                try:
                    if os.path.exists(DB_PATH):
                        os.remove(DB_PATH)
                        st.success("✅ Banco de dados removido!")
                    inicializar_banco()
                    st.success("✅ Novo banco criado!")
                    st.info("Recarregando página...")
                    time.sleep(2)
                    st.rerun()
                except Exception as clean_error:
                    st.error(f"❌ Erro ao limpar: {clean_error}")
        
        st.stop()
    
    # Inicializar estados da sessão
    estados_necessarios = {
        'logado': False,
        'usuario_id': None,
        'usuario_nome': "",
        'usuario_email': "",
        'sessao_token': "",
        'pagina': 'login',
        'tema': 'escuro',
        'moeda': 'BRL',
        'cotacao_atual': 0,
        'nome_cotacao': "",
        'origem': "",
        'destino': "",
        'solicitacao_para_cotacao': None,
        'passageiros_para_cotacao': 1,
        'bebes_para_cotacao': 0,
        'bagagens_para_cotacao': 0,
        'data_ida_para_cotacao': None,
        'data_volta_para_cotacao': None,
        'companhia_selecionada': None,
        'companhia_display': "",
        'resultado_calculo': None,
        'security_level': 'Média',
        'csrf_token': security.generate_csrf_token(),
        'last_activity': time.time(),
        'session_start': time.time()
    }
    
    for key, default_value in estados_necessarios.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
    
    logger.info(f"Session state inicializado: logado={st.session_state.logado}")
    
    # Verificar timeout da sessão
    if st.session_state.logado:
        elapsed = time.time() - st.session_state.last_activity
        if elapsed > 1800:
            st.warning("⏳ Sessão expirada por inatividade")
            
            registrar_evento_seguranca(
                st.session_state.usuario_id,
                "SESSAO_EXPIRADA",
                f"Sessão expirada por inatividade após {elapsed//60} minutos",
                "WARNING"
            )
            
            st.session_state.logado = False
            st.session_state.pagina = 'login'
            st.rerun()
        else:
            st.session_state.last_activity = time.time()
    
    aplicar_css()
    
    # ============= ÁREA DE LOGIN =============
    if not st.session_state.logado:
        pagina_login_melhorada()
    
    # ============= ÁREA LOGADA =============
    else:
        with st.sidebar:
            cores = get_colors()
            
            # Carregar foto de perfil do usuário se existir
            foto_perfil = st.session_state.get('foto_perfil')
            
            # Mostrar foto de perfil ou logo padrão
            if foto_perfil:
                st.markdown(f"""
                <div style='text-align: center; margin-bottom: 1rem;'>
                    <img src="{foto_perfil}" style='width: 120px; height: 120px; border-radius: 50%; object-fit: cover; border: 3px solid {cores['destaque']}; margin-bottom: 0.5rem;'>
                </div>
                """, unsafe_allow_html=True)
            else:
                logo_base64 = carregar_logo()
                st.markdown(f"""
                <div style='text-align: center; margin-bottom: 1rem;'>
                    <img src="data:image/png;base64,{logo_base64}" style='max-width: 120px; margin-bottom: 0.5rem; border-radius: 15px;'>
                </div>
                """, unsafe_allow_html=True)
            
            # Nome e email do usuário
            st.markdown(f"""
            <div class='fade-in' style='text-align: center; margin-bottom: 1.5rem;'>
                <h3 style='color: {cores['destaque']}; margin-bottom: 0.25rem;'>👤 {st.session_state.usuario_nome}</h3>
                <p style='color: {cores['texto']}70; font-size: 0.9rem; margin-bottom: 0.25rem;'>✉️ {st.session_state.usuario_email}</p>
                <div style='background: {cores['success']}20; padding: 5px 10px; border-radius: 5px; margin-top: 5px;'>
                    <small>🔒 Sessão segura • ID: {str(st.session_state.usuario_id)[:8]}</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### 📍 Navegação")
            
            menu_items = [
                ("🏠 Início", 'inicio', "Página inicial com resumo"),
                ("📋 Nova Cotação", 'nova_cotacao', "Criar nova cotação"),
                ("✈️ Companhias", 'companhias', "Selecionar companhia aérea"),
                ("📜 Histórico", 'historico', "Ver cotações anteriores"),
                ("⚙️ Configurações", 'configuracoes', "Ajustes do sistema"),
            ]
            
            for label, pagina, tooltip in menu_items:
                if st.button(label, use_container_width=True, key=f"sidebar_{pagina}", help=tooltip):
                    st.session_state.pagina = pagina
                    st.rerun()
            
            st.markdown("---")
            st.markdown("### 📨 Solicitações")
            
            from solicitacao import contar_notificacoes_nao_lidas
            notif_count = contar_notificacoes_nao_lidas(st.session_state.usuario_id)
            notif_badge = f" ({notif_count})" if notif_count > 0 else ""
            
            if st.button(f"🔗 Gerar Link", use_container_width=True, key="sidebar_gerar_link"):
                st.session_state.pagina = 'gerar_link'
                st.rerun()
            
            if st.button(f"📨 Solicitações{notif_badge}", use_container_width=True, key="sidebar_solicitacoes"):
                st.session_state.pagina = 'solicitacoes'
                st.rerun()
            
            if st.button(f"📋 Meus Links", use_container_width=True, key="sidebar_meus_links"):
                st.session_state.pagina = 'meus_links'
                st.rerun()
            
            st.markdown("---")
            
            with st.expander("🔐 Segurança da Sessão", expanded=False):
                tempo_restante = 1800 - (time.time() - st.session_state.last_activity)
                minutos_restantes = int(tempo_restante // 60)
                segundos_restantes = int(tempo_restante % 60)
                
                st.markdown(f"""
                <div style='font-size: 0.85rem;'>
                    <p><strong>🔒 Nível de segurança:</strong> {st.session_state.security_level}</p>
                    <p><strong>⏱️ Tempo restante:</strong> {minutos_restantes}:{segundos_restantes:02d}</p>
                    <p><strong>📅 Sessão iniciada:</strong> {datetime.fromtimestamp(st.session_state.session_start).strftime('%H:%M')}</p>
                    <p><strong>🔑 Criptografia:</strong> bcrypt (14 rounds)</p>
                    <p><strong>🆔 Sessão ID:</strong> {st.session_state.get('sessao_token', 'N/A')[:8]}...</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("🔄 Renovar Sessão", use_container_width=True, key="sidebar_renew"):
                    st.session_state.last_activity = time.time()
                    st.success("✅ Sessão renovada!")
                    time.sleep(1)
                    st.rerun()
            
            st.markdown("---")
            
            # Botão de logout
            if st.button("🚪 Sair do Sistema", type="secondary", use_container_width=True, key="sidebar_sair_unique"):
                with st.spinner("Saindo..."):
                    usuario_id = st.session_state.get('usuario_id')
                    usuario_email = st.session_state.get('usuario_email', '')
                    
                    if usuario_id:
                        registrar_evento_seguranca(
                            usuario_id, 
                            "LOGOUT_MANUAL", 
                            f"Usuário {usuario_email} saiu manualmente",
                            "INFO"
                        )
                    
                    # Salvar preferências atuais antes de sair
                    from database import salvar_preferencias_usuario
                    salvar_preferencias_usuario(
                        usuario_id,
                        tema=st.session_state.get('tema', 'escuro'),
                        moeda=st.session_state.get('moeda', 'BRL'),
                        cor_primaria=st.session_state.get('cor_primaria', '#3d8bfd')
                    )
                    
                    csrf_salvo = st.session_state.get('csrf_token')
                    
                    # Limpar sessão (mas dados já foram salvos no banco)
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    
                    if csrf_salvo:
                        st.session_state.csrf_token = csrf_salvo
                    
                    st.session_state.update({
                        'logado': False,
                        'pagina': 'login',
                        'tema': 'escuro',
                        'moeda': 'BRL',
                        'security_level': 'Média'
                    })
                    
                    st.success("✅ Logout realizado com sucesso!")
                    time.sleep(1)
                    st.rerun()
            
            st.markdown(f"""
            <div style='text-align: center; margin-top: 2rem; color: {cores['texto']}50; font-size: 0.75rem;'>
                <p>DBMILESX v3.0</p>
                <p>© 2024 - Todos os direitos reservados</p>
            </div>
            """, unsafe_allow_html=True)
        
        # ============= CONTROLE DE PÁGINAS =============
        try:
            if st.session_state.pagina == 'inicio':
                pagina_inicio()
            elif st.session_state.pagina == 'nova_cotacao':
                pagina_nova_cotacao()
            elif st.session_state.pagina == 'companhias':
                pagina_companhias()
            elif st.session_state.pagina == 'calculadora':
                pagina_calculadora()
            elif st.session_state.pagina == 'historico':
                pagina_historico()
            elif st.session_state.pagina == 'configuracoes':
                pagina_configuracoes_melhorada()
            elif st.session_state.pagina == 'gerar_link':
                from solicitacao import pagina_gerar_link
                pagina_gerar_link()
            elif st.session_state.pagina == 'solicitacoes':
                from solicitacao import pagina_minhas_solicitacoes
                pagina_minhas_solicitacoes()
            elif st.session_state.pagina == 'meus_links':
                from solicitacao import pagina_meus_links
                pagina_meus_links()
            else:
                st.error("Página não encontrada")
                st.session_state.pagina = 'inicio'
                st.rerun()

        except Exception as e:
            pagina_atual = st.session_state.get('pagina', 'desconhecida')
            usuario_id = st.session_state.get('usuario_id')
            
            logger.error(f"Erro ao carregar página {pagina_atual}: {e}")
            st.error(f"❌ Erro ao carregar a página {pagina_atual}. Recarregue o sistema.")
            
            if usuario_id:
                registrar_evento_seguranca(
                    usuario_id,
                    "ERRO_PAGINA",
                    f"Erro na página {pagina_atual}: {str(e)[:100]}",
                    "ERROR"
                )
            
            if st.button("🔄 Recarregar Sistema", type="primary"):
                st.rerun()


if __name__ == "__main__":
    main()
