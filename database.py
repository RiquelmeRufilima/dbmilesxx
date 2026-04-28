#!/usr/bin/env python3
"""
database.py - VERSÃO COMPLETA E CORRIGIDA
Sistema de gerenciamento de banco de dados DBMILESX
COM HIERARQUIA DE EMPRESAS (Mantendo todas as funções originais)
"""

import sqlite3
import os
import logging
import time
import secrets
import json
import bcrypt
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List, Union
from contextlib import contextmanager
import sqlite3


# ============= CONFIGURAÇÃO =============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuração para diferentes ambientes
import tempfile

IS_RENDER = os.getenv('RENDER', False) or os.getenv('RENDER_EXTERNAL_URL', False)

if IS_RENDER or os.getenv('STREAMLIT_CLOUD') or os.getenv('CLOUDFLARE'):
    DB_PATH = os.path.join(tempfile.gettempdir(), 'sistema_aereo_secure.db')
    logger.info(f"🚀 Modo Cloud ativado - Banco em: {DB_PATH}")
else:
    DB_PATH = 'sistema_aereo_secure.db'

# Constantes
BCRYPT_ROUNDS = 12
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15
SESSION_TIMEOUT_MINUTES = 30

# ============= CONTEXT MANAGER PARA CONEXÕES =============
@contextmanager
def get_db_connection():
    """Context manager para conexões com banco de dados"""
    conn = None
    try:
        conn = criar_conexao()
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Erro na conexão com banco: {e}")
        raise
    finally:
        if conn:
            conn.close()

@contextmanager
def get_db_cursor():
    """Context manager para cursors com auto-commit"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Erro no cursor: {e}")
            raise

# ============= FUNÇÕES DE CONEXÃO =============
def criar_conexao() -> sqlite3.Connection:
    
    """Cria conexão segura com o banco SQLite"""
    try:
        # Criar diretório se não existir
        db_dir = os.path.dirname(DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        # Conectar com timeout e sem threads concorrentes
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row  # Retornar dicionários

        # Testar conexão
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()

        # Configurações de segurança e performance
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA secure_delete = ON")
        conn.execute("PRAGMA cache_size = -2000")  # 2MB cache
        conn.execute("PRAGMA temp_store = MEMORY")

        logger.debug(f"Conexão com banco estabelecida: {DB_PATH}")
        return conn

    except Exception as e:
        logger.error(f"ERRO CRÍTICO ao conectar ao banco: {e}")
        return _criar_conexao_fallback()

def inicializar_banco():
    """Inicializa todas as tabelas do banco de dados"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Tabela de usuários
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                nome TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tema_preferido TEXT DEFAULT 'escuro',
                moeda_preferida TEXT DEFAULT 'BRL',
                csrf_token TEXT,
                sessao_token TEXT,
                sessao_criada TIMESTAMP,
                tentativas_login INTEGER DEFAULT 0,
                bloqueado_ate TIMESTAMP,
                empresa_id INTEGER,
                nivel_acesso TEXT DEFAULT 'membro',
                foto_perfil TEXT,
                telefone TEXT,
                cargo TEXT,
                ativo INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Tabela de empresas
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS empresas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cnpj TEXT UNIQUE,
                telefone TEXT,
                email TEXT,
                site TEXT,
                endereco TEXT,
                logo TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                criado_por INTEGER,
                ativo INTEGER DEFAULT 1
            )
            ''')
            
            # Tabela de cotações
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS cotacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                empresa_id INTEGER,
                nome TEXT NOT NULL,
                origem TEXT NOT NULL,
                destino TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE SET NULL
            )
            ''')
            
            # Tabela de histórico de cotações
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico_cotacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                cotacao_id INTEGER NOT NULL,
                empresa_id INTEGER,
                companhia TEXT NOT NULL,
                tipo_calculo TEXT,
                milhas_total REAL DEFAULT 0,
                valor_milheiro REAL DEFAULT 0,
                taxa_embarque REAL DEFAULT 0,
                valor_base REAL DEFAULT 0,
                valor_bagagens REAL DEFAULT 0,
                desagio_percentual REAL DEFAULT 0,
                total_geral REAL NOT NULL,
                moeda TEXT DEFAULT 'BRL',
                passageiros INTEGER DEFAULT 1,
                bebes INTEGER DEFAULT 0,
                num_bagagens INTEGER DEFAULT 0,
                metadata TEXT,
                metadata_criptografado TEXT,
                data_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario_nome TEXT,
                usuario_email TEXT,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (cotacao_id) REFERENCES cotacoes(id) ON DELETE CASCADE,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE SET NULL
            )
            ''')
            
            # Tabela de tokens de recuperação
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
            
            # Tabela de logs de segurança
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs_seguranca (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                empresa_id INTEGER,
                tipo_evento TEXT NOT NULL,
                nivel_severidade TEXT NOT NULL,
                descricao TEXT,
                ip TEXT,
                user_agent TEXT,
                metadata TEXT,
                data_evento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE SET NULL
            )
            ''')
            
            # Tabela de convites
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS convites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                nome TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                nivel_acesso TEXT DEFAULT 'membro',
                expiracao TIMESTAMP NOT NULL,
                usado INTEGER DEFAULT 0,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                criado_por INTEGER,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            )
            ''')
            
            # Tabela de códigos de acesso
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS codigos_acesso (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                codigo TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                criado_por INTEGER,
                usado INTEGER DEFAULT 0,
                expiracao TIMESTAMP NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            )
            ''')
            
            # Tabela de links públicos
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS links_publicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER,
                token TEXT UNIQUE NOT NULL,
                nome_campanha TEXT NOT NULL,
                empresas_data TEXT NOT NULL DEFAULT '[]',
                dias_validade INTEGER NOT NULL DEFAULT 30,
                limite_uso INTEGER NOT NULL DEFAULT 100,
                usos_restantes INTEGER NOT NULL DEFAULT 100,
                total_usos INTEGER DEFAULT 0,
                data_expiracao TIMESTAMP NOT NULL,
                usuario_criador_id INTEGER NOT NULL,
                email_criador TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                FOREIGN KEY (usuario_criador_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
            ''')
            
            # Tabela de solicitações
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS solicitacoes_cotacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER,
                dados_solicitacao TEXT NOT NULL,
                status TEXT DEFAULT 'RECEBIDA',
                link_id INTEGER,
                lido INTEGER DEFAULT 0,
                data_leitura TIMESTAMP,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                FOREIGN KEY (link_id) REFERENCES links_publicos(id) ON DELETE SET NULL
            )
            ''')
            
            # Índices
            indices = [
                'CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)',
                'CREATE INDEX IF NOT EXISTS idx_usuarios_empresa ON usuarios(empresa_id)',
                'CREATE INDEX IF NOT EXISTS idx_cotacoes_usuario ON cotacoes(usuario_id)',
                'CREATE INDEX IF NOT EXISTS idx_historico_usuario ON historico_cotacoes(usuario_id)',
                'CREATE INDEX IF NOT EXISTS idx_tokens_token ON tokens_recuperacao(token)',
                'CREATE INDEX IF NOT EXISTS idx_links_token ON links_publicos(token)',
                'CREATE INDEX IF NOT EXISTS idx_codigos_codigo ON codigos_acesso(codigo)'
            ]
            
            for idx in indices:
                try:
                    cursor.execute(idx)
                except:
                    pass
            
            # Criar usuário admin se não existir
            cursor.execute('SELECT id FROM usuarios WHERE email = ?', ('admin@dbmilesx.com',))
            if not cursor.fetchone():
                senha_hash = PasswordHasher.hash_password('Admin@DBMILESX123!')
                cursor.execute('''
                INSERT INTO usuarios (email, senha_hash, nome, nivel_acesso, csrf_token, sessao_token, sessao_criada)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', ('admin@dbmilesx.com', senha_hash, 'Administrador', 'admin', 
                      secrets.token_urlsafe(32), secrets.token_urlsafe(32)))
                print("✅ Usuário admin criado")
            
            conn.commit()
            print("✅ Banco de dados inicializado com sucesso")
            
    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {e}")
        raise

def _criar_conexao_fallback() -> sqlite3.Connection:
    """Cria conexão em memória como fallback"""
    try:
        logger.warning("Tentando conexão em memória como fallback...")
        conn = sqlite3.connect(':memory:', check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # Inicializar tabelas básicas
        _inicializar_tabelas_memoria(conn)

        logger.info("✅ Banco em memória criado com sucesso")
        return conn

    except Exception as mem_error:
        logger.error(f"ERRO até no banco em memória: {mem_error}")
        raise RuntimeError("Falha completa no banco de dados") from mem_error

def _inicializar_tabelas_memoria(conn):
    """Inicializa tabelas no banco em memória"""
    cursor = conn.cursor()

    # Tabela de usuários
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

    # Criar usuário admin
    senha_hash = hash_password_simple('Admin@DBMILESX123!')
    cursor.execute('''
    INSERT OR IGNORE INTO usuarios (email, senha_hash, nome)
    VALUES (?, ?, ?)
    ''', ('admin@dbmilesx.com', senha_hash, 'Administrador'))

    conn.commit()

# ============= SISTEMA DE HASH DE SENHA ROBUSTO =============
class PasswordHasher:
    """Classe unificada para gerenciamento de hashes de senha"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Gera hash seguro da senha usando bcrypt"""
        try:
            if not password or len(password) < 6:
                raise ValueError("Senha muito curta")

            # Usar bcrypt com salt de 12 rounds
            salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')

        except Exception as e:
            logger.error(f"Erro ao gerar hash bcrypt: {e}")
            # Fallback para SHA-256 com salt
            return PasswordHasher._hash_sha256_fallback(password)

    @staticmethod
    def _hash_sha256_fallback(password: str) -> str:
        """Fallback SHA-256 com salt"""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.sha256((password + salt).encode())
        return f"sha256:{hash_obj.hexdigest()}:{salt}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verifica senha contra hash em qualquer formato suportado"""
        try:
            if not password or not hashed:
                return False

            # Formato bcrypt
            if hashed.startswith('$2'):
                return bcrypt.checkpw(
                    password.encode('utf-8'),
                    hashed.encode('utf-8')
                )

            # Formato sha256 com salt (fallback)
            if hashed.startswith('sha256:'):
                parts = hashed.split(':')
                if len(parts) == 3:
                    _, hash_part, salt = parts
                    test_hash = hashlib.sha256((password + salt).encode()).hexdigest()
                    return test_hash == hash_part

            # Formato antigo (hash:salt)
            if ':' in hashed and not hashed.startswith('$'):
                hash_part, salt = hashed.split(':', 1)
                test_hash = hashlib.sha256((password + salt).encode()).hexdigest()
                return test_hash == hash_part

            # SHA-256 puro (legado)
            if len(hashed) == 64:
                test_hash = hashlib.sha256(password.encode()).hexdigest()
                return test_hash == hashed

            # Último recurso: comparar direto (NUNCA em produção!)
            if password == hashed:
                logger.warning("⚠️ Senha em texto puro detectada!")
                return True

            return False

        except Exception as e:
            logger.error(f"Erro na verificação de senha: {e}")
            return False

    @staticmethod
    def needs_rehash(hashed: str) -> bool:
        """Verifica se o hash precisa ser atualizado"""
        # Apenas bcrypt é considerado seguro
        if hashed.startswith('$2'):
            # Verificar rounds do bcrypt
            try:
                rounds = int(hashed.split('$')[2])
                return rounds < BCRYPT_ROUNDS
            except:
                return False
        return True  # Qualquer outro formato precisa ser atualizado

# Funções de compatibilidade
def hash_password_simple(password: str) -> str:
    """Wrapper para compatibilidade"""
    return PasswordHasher.hash_password(password)

def verify_password_simple(password: str, hashed: str) -> bool:
    """Wrapper para compatibilidade"""
    return PasswordHasher.verify_password(password, hashed)

def hash_password_compativel(password: str) -> str:
    """Wrapper para compatibilidade com security_manager"""
    return PasswordHasher.hash_password(password)

def verify_password_compativel(password: str, hashed: str) -> bool:
    """Wrapper para compatibilidade com security_manager"""
    return PasswordHasher.verify_password(password, hashed)

# ============= SISTEMA DE LOGIN =============
class LoginManager:
    """Gerenciador de login com rate limiting e bloqueio"""

    def __init__(self):
        self.attempts = {}  # email -> {'count': int, 'first_attempt': timestamp}
        self.lockouts = {}  # email -> unlock_time

    def record_attempt(self, email: str, success: bool):
        """Registra tentativa de login"""
        now = time.time()

        if success:
            # Limpar registros em caso de sucesso
            self.attempts.pop(email, None)
            self.lockouts.pop(email, None)
            return

        # Registrar falha
        if email not in self.attempts:
            self.attempts[email] = {
                'count': 1,
                'first_attempt': now
            }
        else:
            self.attempts[email]['count'] += 1

        # Verificar se deve bloquear
        if self.attempts[email]['count'] >= MAX_LOGIN_ATTEMPTS:
            self.lockouts[email] = now + (LOCKOUT_DURATION_MINUTES * 60)
            logger.warning(f"🔒 Usuário {email} bloqueado por {LOCKOUT_DURATION_MINUTES} minutos")

    def is_locked(self, email: str) -> Tuple[bool, Optional[str]]:
        """Verifica se usuário está bloqueado"""
        if email in self.lockouts:
            unlock_time = self.lockouts[email]
            if time.time() < unlock_time:
                remaining = int(unlock_time - time.time())
                minutes = remaining // 60
                seconds = remaining % 60
                return True, f"Bloqueado. Tente novamente em {minutes}:{seconds:02d}"
            else:
                # Bloqueio expirou
                self.lockouts.pop(email, None)
                self.attempts.pop(email, None)

        return False, None

    def get_attempt_count(self, email: str) -> int:
        """Retorna número de tentativas falhas"""
        return self.attempts.get(email, {}).get('count', 0)

# Instância global do gerenciador de login
login_manager = LoginManager()

def verificar_login_simplificado(email: str, senha: str) -> Tuple[bool, Any]:
    """Verificação de login simplificada e corrigida"""
    try:
        email = email.strip().lower()
        
        with get_db_cursor() as cursor:
            cursor.execute('''
                SELECT id, nome, senha_hash, nivel_acesso, empresa_id
                FROM usuarios 
                WHERE email = ?
            ''', (email,))
            
            usuario = cursor.fetchone()
            
            if usuario and PasswordHasher.verify_password(senha, usuario['senha_hash']):
                # Buscar dados da empresa
                empresa_nome = None
                empresa_logo = None
                if usuario['empresa_id']:
                    cursor.execute('SELECT nome, logo FROM empresas WHERE id = ?', (usuario['empresa_id'],))
                    empresa = cursor.fetchone()
                    if empresa:
                        empresa_nome = empresa['nome']
                        empresa_logo = empresa['logo']
                
                return True, {
                    'usuario_id': usuario['id'],
                    'usuario_nome': usuario['nome'],
                    'usuario_email': email,
                    'empresa_id': usuario['empresa_id'],
                    'nivel_acesso': usuario['nivel_acesso'] if usuario['nivel_acesso'] else 'membro',
                    'empresa_nome': empresa_nome,
                    'empresa_logo': empresa_logo
                }
            
            return False, "Email ou senha incorretos"
            
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        return False, f"Erro no sistema: {str(e)}"

def _autenticar_usuario(email: str, senha: str) -> Optional[Dict]:
    """Autentica usuário no banco de dados"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                'SELECT id, nome, senha_hash, empresa_id, nivel_acesso FROM usuarios WHERE email = ?',
                (email,)
            )
            usuario = cursor.fetchone()

            if usuario and PasswordHasher.verify_password(senha, usuario['senha_hash']):
                # Buscar dados da empresa
                empresa_nome = None
                empresa_logo = None
                if usuario['empresa_id']:
                    cursor.execute('SELECT nome, logo FROM empresas WHERE id = ?', 
                                 (usuario['empresa_id'],))
                    empresa = cursor.fetchone()
                    if empresa:
                        empresa_nome = empresa['nome']
                        empresa_logo = empresa['logo']

                return {
                    'usuario_id': usuario['id'],
                    'usuario_nome': usuario['nome'],
                    'usuario_email': email,
                    'empresa_id': usuario['empresa_id'],
                    'nivel_acesso': usuario['nivel_acesso'],
                    'empresa_nome': empresa_nome,
                    'empresa_logo': empresa_logo
                }

            return None

    except Exception as e:
        logger.error(f"Erro na autenticação: {e}")
        return None

def _atualizar_hash_usuario(usuario_id: int, senha: str):
    """Atualiza hash da senha para o formato mais seguro"""
    try:
        with get_db_cursor() as cursor:
            novo_hash = PasswordHasher.hash_password(senha)
            cursor.execute(
                'UPDATE usuarios SET senha_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (novo_hash, usuario_id)
            )
            logger.info(f"Hash atualizado para usuário {usuario_id}")
    except Exception as e:
        logger.error(f"Erro ao atualizar hash: {e}")

# ============= FUNÇÕES DE EMPRESAS (NOVO) =============
# NO ARQUIVO database.py - Adicionar:
# ============= FUNÇÕES DE EMPRESAS (NOVO) =============
# ============= FUNÇÕES DE EMPRESAS (NOVO) =============
def criar_empresa(nome: str, 
                  cnpj: Optional[str] = None, 
                  telefone: Optional[str] = None, 
                  email: Optional[str] = None,
                  site: Optional[str] = None,
                  endereco: Optional[str] = None,
                  logo: Optional[str] = None,
                  criado_por: Optional[int] = None) -> Tuple[bool, Any]:
    """Cria uma nova empresa e define o criador como admin"""
    try:
        import secrets
        import string
        from datetime import datetime, timedelta
        
        conn = criar_conexao()
        cursor = conn.cursor()
        
        # Verificar se já existe empresa com este nome
        cursor.execute('SELECT id FROM empresas WHERE nome = ?', (nome,))
        if cursor.fetchone():
            conn.close()
            return False, "Já existe uma empresa com este nome"
        
        # Criar empresa com TODOS os campos
        cursor.execute('''
        INSERT INTO empresas (
            nome, cnpj, telefone, email, site, endereco, logo, 
            criado_por, data_criacao
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ''', (nome, cnpj, telefone, email, site, endereco, logo, criado_por))
        
        empresa_id = cursor.lastrowid
        
        # Gerar código de acesso inicial
        def gerar_codigo_empresa(emp_id):
            random_part = secrets.token_hex(4).upper()
            emp_part = str(emp_id).zfill(4)
            return f"DBM-{emp_part}-{random_part}"
        
        def gerar_senha_acesso(tamanho=12):
            caracteres = string.ascii_letters + string.digits + "!@#$%"
            return ''.join(secrets.choice(caracteres) for _ in range(tamanho))
        
        codigo_acesso = gerar_codigo_empresa(empresa_id)
        senha_acesso = gerar_senha_acesso()
        
        # Verificar se tabela codigos_acesso existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='codigos_acesso'")
        if not cursor.fetchone():
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS codigos_acesso (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                codigo TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                criado_por INTEGER,
                usado INTEGER DEFAULT 0,
                expiracao TIMESTAMP NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_codigos_empresa ON codigos_acesso(empresa_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_codigos_codigo ON codigos_acesso(codigo)')
        
        # Inserir código de acesso
        expiracao = (datetime.now() + timedelta(days=7)).isoformat()
        cursor.execute('''
        INSERT INTO codigos_acesso (empresa_id, codigo, senha, criado_por, expiracao)
        VALUES (?, ?, ?, ?, ?)
        ''', (empresa_id, codigo_acesso, senha_acesso, criado_por, expiracao))
        
        # Se foi criado por um usuário, vincular ele como admin
        if criado_por:
            cursor.execute('''
            UPDATE usuarios 
            SET empresa_id = ?, nivel_acesso = 'admin'
            WHERE id = ?
            ''', (empresa_id, criado_por))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Empresa {nome} (ID: {empresa_id}) criada por usuário {criado_por}")
        return True, {
            'empresa_id': empresa_id,
            'codigo': codigo_acesso,
            'senha': senha_acesso
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar empresa: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Erro: {str(e)}"

# ============= FUNÇÕES DE CÓDIGOS DE ACESSO (NOVO) =============
def criar_tabela_codigos_acesso():
    """Cria a tabela de códigos de acesso se não existir"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS codigos_acesso (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                codigo TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                criado_por INTEGER,
                usado INTEGER DEFAULT 0,
                expiracao TIMESTAMP NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            )
            ''')
            
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_codigos_empresa ON codigos_acesso(empresa_id)
            ''')
            
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_codigos_codigo ON codigos_acesso(codigo)
            ''')
            
            conn.commit()
            logger.info("✅ Tabela codigos_acesso criada/verificada")
            return True
            
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabela codigos_acesso: {e}")
        return False

def gerar_codigo_empresa(empresa_id: int) -> str:
    """Gera código único para a empresa"""
    import hashlib
    timestamp = str(int(time.time()))
    random_part = secrets.token_hex(4).upper()
    empresa_part = str(empresa_id).zfill(4)
    return f"DBM-{empresa_part}-{random_part}"
def gerar_novo_codigo_acesso(empresa_id: int, usuario_id: int) -> Optional[Dict[str, str]]:
    """Gera um novo código de acesso para a empresa"""
    try:
        codigo = secrets.token_hex(4).upper()
        senha = secrets.token_hex(4).upper()
        expiracao = datetime.now() + timedelta(days=7)
        
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO codigos_acesso (empresa_id, codigo, senha, expiracao, criado_por)
        VALUES (?, ?, ?, ?, ?)
        ''', (empresa_id, codigo, senha, expiracao.isoformat(), usuario_id))
        
        conn.commit()
        conn.close()
        
        return {
            'codigo': codigo,
            'senha': senha,
            'expiracao': expiracao.strftime('%d/%m/%Y')
        }
    
    except Exception as e:
        logger.error(f"Erro ao gerar código de acesso: {e}")
        return None
    
def gerar_senha_acesso(tamanho: int = 12) -> str:
    """Gera senha aleatória para acesso"""
    import string
    caracteres = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(caracteres) for _ in range(tamanho))

def criar_codigo_acesso(empresa_id: int, criado_por: int) -> Optional[Dict]:
    """Cria um novo código de acesso para a empresa"""
    try:
        codigo = gerar_codigo_empresa(empresa_id)
        senha = gerar_senha_acesso()
        expiracao = (datetime.now() + timedelta(days=7)).isoformat()
        
        with get_db_cursor() as cursor:
            cursor.execute('''
            INSERT INTO codigos_acesso (empresa_id, codigo, senha, criado_por, expiracao)
            VALUES (?, ?, ?, ?, ?)
            ''', (empresa_id, codigo, senha, criado_por, expiracao))
            
            return {
                'codigo': codigo,
                'senha': senha,
                'expiracao': (datetime.now() + timedelta(days=7)).strftime('%d/%m/%Y')
            }
            
    except Exception as e:
        logger.error(f"❌ Erro ao criar código de acesso: {e}")
        return None

def verificar_codigo_acesso(codigo: str, senha: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Verifica a validade do código de acesso fornecido"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT e.id, e.nome, e.cnpj, e.telefone, e.email, e.endereco, 
               c.nivel_acesso, c.expiracao
        FROM codigos_acesso c
        JOIN empresas e ON c.empresa_id = e.id
        WHERE c.codigo = ? AND c.senha = ? AND c.expiracao > CURRENT_TIMESTAMP
        ''', (codigo, senha))
        
        resultado = cursor.fetchone()
        
        if resultado:
            empresa_id, empresa_nome, cnpj, telefone, email, endereco, nivel_acesso, expiracao = resultado
            
            # Converter expiracao para datetime
            expiracao_date = datetime.fromisoformat(expiracao)
            
            return True, {
                'empresa_id': empresa_id,
                'empresa_nome': empresa_nome,
                'cnpj': cnpj,
                'telefone': telefone,
                'email': email,
                'endereco': endereco,
                'nivel_acesso': nivel_acesso,
                'expiracao': expiracao_date
            }
        else:
            return False, None
    
    except Exception as e:
        logger.error(f"Erro ao verificar código de acesso: {e}")
        return False, None

def get_empresa(empresa_id: int) -> Optional[Dict]:
    """Retorna dados da empresa"""
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM empresas WHERE id = ?', (empresa_id,))
            empresa = cursor.fetchone()
            return dict(empresa) if empresa else None
    except Exception as e:
        logger.error(f"Erro ao buscar empresa: {e}")
        return None

def atualizar_empresa(empresa_id: int, **kwargs) -> bool:
    """Atualiza dados da empresa"""
    try:
        updates = []
        params = []
        for key, value in kwargs.items():
            if value is not None:
                updates.append(f"{key} = ?")
                params.append(value)
        
        if not updates:
            return False
        
        params.append(empresa_id)
        query = f"UPDATE empresas SET {', '.join(updates)} WHERE id = ?"
        
        with get_db_cursor() as cursor:
            cursor.execute(query, params)
            logger.info(f"✅ Empresa {empresa_id} atualizada")
            return True
            
    except Exception as e:
        logger.error(f"Erro ao atualizar empresa: {e}")
        return False

def get_usuarios_empresa(empresa_id: int, apenas_ativos: bool = True) -> List[Dict]:
    """Retorna todos os usuários de uma empresa"""
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT id, nome, email, nivel_acesso, data_criacao FROM usuarios WHERE empresa_id = ?'
            params = [empresa_id]
            
            if apenas_ativos:
                query += ' AND ativo = 1'
            
            query += ' ORDER BY nome'
            
            cursor.execute(query, params)
            usuarios = cursor.fetchall()
            
            return [dict(u) for u in usuarios]
            
    except Exception as e:
        logger.error(f"Erro ao listar usuários da empresa: {e}")
        return []

def atualizar_nivel_acesso(usuario_id: int, novo_nivel: str, admin_id: int) -> Tuple[bool, str]:
    """Admin altera nível de acesso de um membro"""
    niveis_validos = ['admin', 'gerente', 'membro']
    
    if novo_nivel not in niveis_validos:
        return False, "Nível de acesso inválido"
    
    try:
        with get_db_cursor() as cursor:
            # Verificar se admin tem permissão
            cursor.execute('''
            SELECT u.empresa_id, u.nivel_acesso 
            FROM usuarios u 
            WHERE u.id = ?
            ''', (admin_id,))
            
            admin = cursor.fetchone()
            if not admin or admin['nivel_acesso'] not in ['admin']:
                return False, "Apenas administradores podem alterar níveis de acesso"
            
            # Verificar se usuário alvo está na mesma empresa
            cursor.execute('''
            SELECT id FROM usuarios 
            WHERE id = ? AND empresa_id = ?
            ''', (usuario_id, admin['empresa_id']))
            
            if not cursor.fetchone():
                return False, "Usuário não pertence à sua empresa"
            
            cursor.execute('''
            UPDATE usuarios SET nivel_acesso = ? WHERE id = ?
            ''', (novo_nivel, usuario_id))
            
            logger.info(f"✅ Nível de acesso do usuário {usuario_id} alterado para {novo_nivel}")
            
            # Registrar no log de segurança
            registrar_evento_seguranca(
                admin_id,
                "NIVEL_ALTERADO",
                f"Nível de acesso do usuário {usuario_id} alterado para {novo_nivel}",
                "INFO",
                {"usuario_alterado": usuario_id, "novo_nivel": novo_nivel},
                empresa_id=admin['empresa_id']
            )
            
            return True, "Nível de acesso atualizado com sucesso"
            
    except Exception as e:
        logger.error(f"Erro ao atualizar nível de acesso: {e}")
        return False, str(e)

def convidar_membro(empresa_id: int, 
                    email: str, 
                    nome: str, 
                    nivel_acesso: str = 'membro', 
                    convidado_por: int = None,
                    config_email: Dict = None) -> Optional[str]:
    """
    Gera um convite para um novo membro da empresa
    
    Args:
        empresa_id: ID da empresa
        email: Email do convidado
        nome: Nome do convidado
        nivel_acesso: Nível de acesso
        convidado_por: ID de quem convidou
        config_email: Dicionário com configurações de email (opcional)
    
    Returns:
        Token do convite
    """
    try:
        import secrets
        from datetime import datetime, timedelta
        
        # Gerar token
        token = secrets.token_urlsafe(32)
        expiracao = datetime.now() + timedelta(days=7)
        
        conn = criar_conexao()
        cursor = conn.cursor()
        
        # Verificar se já existe convite pendente
        cursor.execute('''
        SELECT id FROM convites 
        WHERE email = ? AND empresa_id = ? AND usado = 0 AND expiracao > datetime('now')
        ''', (email, empresa_id))
        
        if cursor.fetchone():
            conn.close()
            return None
        
        # Verificar se já existe usuário com este email
        cursor.execute('SELECT id, empresa_id FROM usuarios WHERE email = ?', (email,))
        usuario_existente = cursor.fetchone()
        
        if usuario_existente:
            usuario_id, empresa_atual = usuario_existente
            if empresa_atual == empresa_id:
                conn.close()
                return None  # Já é membro
            elif empresa_atual is not None:
                conn.close()
                return None  # Já tem outra empresa
        
        # Buscar nome de quem convidou
        nome_convidador = "Sistema"
        if convidado_por:
            cursor.execute('SELECT nome FROM usuarios WHERE id = ?', (convidado_por,))
            result = cursor.fetchone()
            if result:
                nome_convidador = result[0]
        
        # Buscar nome da empresa
        cursor.execute('SELECT nome FROM empresas WHERE id = ?', (empresa_id,))
        empresa = cursor.fetchone()
        nome_empresa = empresa[0] if empresa else "Empresa"
        
        # Inserir convite
        cursor.execute('''
        INSERT INTO convites (empresa_id, email, nome, token, nivel_acesso, expiracao, criado_por)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (empresa_id, email, nome, token, nivel_acesso, expiracao.isoformat(), convidado_por))
        
        conn.commit()
        conn.close()
        
        # ===== ENVIAR EMAIL SOMENTE SE CONFIGURAÇÕES FORNECIDAS =====
        if config_email and config_email.get('user') and config_email.get('password'):
            try:
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                
                base_url = config_email.get('base_url', 'http://localhost:8501')
                link_convite = f"{base_url}/?convite={token}"
                
                # Montar email
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f"📨 Convite para {nome_empresa} - DBMILESX"
                msg['From'] = config_email.get('from', 'noreply@dbmilesx.com')
                msg['To'] = email
                
                # Versão texto
                text = f"""
                Olá {nome},
                
                Você foi convidado por {nome_convidador} para fazer parte da empresa {nome_empresa} no DBMILESX!
                
                Nível de acesso: {nivel_acesso}
                
                Clique no link abaixo para aceitar o convite:
                {link_convite}
                
                Este convite expira em 7 dias.
                """
                
                # Versão HTML
                html = f"""
                <!DOCTYPE html>
                <html>
                <body style="font-family: Arial, sans-serif;">
                    <div style="background: linear-gradient(135deg, #3d8bfd, #2a5cbd); padding: 20px; text-align: center;">
                        <h2 style="color: white;">DBMILESX</h2>
                    </div>
                    <div style="padding: 30px;">
                        <h3>Olá {nome}!</h3>
                        <p><strong>{nome_convidador}</strong> te convidou para <strong>{nome_empresa}</strong>!</p>
                        <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <p><strong>Nível:</strong> {nivel_acesso}</p>
                        </div>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{link_convite}" 
                               style="background-color: #3d8bfd; color: white; padding: 15px 30px; 
                                      text-decoration: none; border-radius: 8px; font-weight: bold;">
                                ✅ ACEITAR CONVITE
                            </a>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                part1 = MIMEText(text, 'plain')
                part2 = MIMEText(html, 'html')
                msg.attach(part1)
                msg.attach(part2)
                
                # Enviar
                server = smtplib.SMTP(
                    config_email.get('host', 'smtp.gmail.com'),
                    config_email.get('port', 587),
                    timeout=30
                )
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(config_email['user'], config_email['password'])
                server.send_message(msg)
                server.quit()
                
                logger.info(f"📧 Email enviado para {email}")
                
            except Exception as email_error:
                logger.error(f"⚠️ Erro ao enviar email: {email_error}")
        
        logger.info(f"✅ Convite gerado para {email} (empresa: {empresa_id})")
        return token
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar convite: {e}")
        return None
    
def aceitar_convite(token: str, senha: str) -> Tuple[bool, str]:
    """Aceita convite e cria usuário"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM convites 
            WHERE token = ? AND usado = 0 AND expiracao > CURRENT_TIMESTAMP
            ''', (token,))
            
            convite = cursor.fetchone()
            if not convite:
                return False, "Convite inválido ou expirado"
            
            # Verificar se email já existe
            cursor.execute('SELECT id FROM usuarios WHERE email = ?', (convite['email'],))
            if cursor.fetchone():
                return False, "Email já cadastrado"
            
            # Criar usuário
            senha_hash = PasswordHasher.hash_password(senha)
            cursor.execute('''
            INSERT INTO usuarios (email, senha_hash, nome, empresa_id, nivel_acesso)
            VALUES (?, ?, ?, ?, ?)
            ''', (convite['email'], senha_hash, convite['nome'], 
                  convite['empresa_id'], convite['nivel_acesso']))
            
            usuario_id = cursor.lastrowid
            
            # Marcar convite como usado
            cursor.execute('UPDATE convites SET usado = 1 WHERE id = ?', (convite['id'],))
            
            conn.commit()
            
            logger.info(f"✅ Novo membro aceitou convite: {convite['email']}")
            
            # Registrar no log
            registrar_evento_seguranca(
                usuario_id,
                "CONVITE_ACEITO",
                f"Convite aceito para {convite['email']}",
                "INFO",
                empresa_id=convite['empresa_id']
            )
            
            return True, "Conta criada com sucesso!"
            
    except Exception as e:
        logger.error(f"Erro ao aceitar convite: {e}")
        return False, str(e)

def sair_da_empresa(usuario_id: int, empresa_id: int) -> Tuple[bool, str]:
    """Usuário sai da empresa"""
    try:
        with get_db_cursor() as cursor:
            # Verificar se é o último admin
            cursor.execute('''
            SELECT COUNT(*) FROM usuarios 
            WHERE empresa_id = ? AND nivel_acesso IN ('admin') AND id != ?
            ''', (empresa_id, usuario_id))
            
            outros_admins = cursor.fetchone()[0]
            
            # Se for o último admin, não pode sair
            if outros_admins == 0:
                return False, "Você é o último administrador. Promova alguém antes de sair."
            
            # Remover usuário da empresa
            cursor.execute('''
            UPDATE usuarios 
            SET empresa_id = NULL, nivel_acesso = 'membro'
            WHERE id = ?
            ''', (usuario_id,))
            
            logger.info(f"👤 Usuário {usuario_id} saiu da empresa {empresa_id}")
            
            # Registrar no log
            registrar_evento_seguranca(
                usuario_id,
                "SAIU_EMPRESA",
                f"Usuário saiu da empresa",
                "INFO",
                empresa_id=empresa_id
            )
            
            return True, "Você saiu da empresa com sucesso!"
            
    except Exception as e:
        logger.error(f"Erro ao sair da empresa: {e}")
        return False, f"Erro: {str(e)}"

def get_empresa(empresa_id: int) -> Optional[Dict]:
    """Retorna dados da empresa"""
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM empresas WHERE id = ?', (empresa_id,))
            empresa = cursor.fetchone()
            return dict(empresa) if empresa else None
    except Exception as e:
        logger.error(f"Erro ao buscar empresa: {e}")
        return None

def atualizar_empresa(empresa_id: int, **kwargs) -> bool:
    """Atualiza dados da empresa"""
    try:
        updates = []
        params = []
        for key, value in kwargs.items():
            if value is not None:
                updates.append(f"{key} = ?")
                params.append(value)
        
        if not updates:
            return False
        
        params.append(empresa_id)
        query = f"UPDATE empresas SET {', '.join(updates)} WHERE id = ?"
        
        with get_db_cursor() as cursor:
            cursor.execute(query, params)
            logger.info(f"✅ Empresa {empresa_id} atualizada")
            return True
            
    except Exception as e:
        logger.error(f"Erro ao atualizar empresa: {e}")
        return False

def get_usuarios_empresa(empresa_id: int, apenas_ativos: bool = True) -> List[Dict]:
    """Retorna todos os usuários de uma empresa"""
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM usuarios WHERE empresa_id = ?'
            params = [empresa_id]
            
            if apenas_ativos:
                query += ' AND ativo = 1'
            
            cursor.execute(query, params)
            usuarios = cursor.fetchall()
            
            return [dict(u) for u in usuarios]
            
    except Exception as e:
        logger.error(f"Erro ao listar usuários da empresa: {e}")
        return []

def atualizar_nivel_acesso(usuario_id: int, novo_nivel: str, admin_id: int) -> Tuple[bool, str]:
    """Admin altera nível de acesso de um membro"""
    niveis_validos = ['admin', 'gerente', 'membro', 'visualizador']
    
    if novo_nivel not in niveis_validos:
        return False, "Nível de acesso inválido"
    
    try:
        with get_db_cursor() as cursor:
            # Verificar se admin tem permissão
            cursor.execute('''
            SELECT u.empresa_id, u.nivel_acesso 
            FROM usuarios u 
            WHERE u.id = ?
            ''', (admin_id,))
            
            admin = cursor.fetchone()
            if not admin or admin['nivel_acesso'] not in ['admin', 'gerente']:
                return False, "Apenas administradores e gerentes podem alterar níveis de acesso"
            
            # Verificar se usuário alvo está na mesma empresa
            cursor.execute('''
            SELECT id FROM usuarios 
            WHERE id = ? AND empresa_id = ?
            ''', (usuario_id, admin['empresa_id']))
            
            if not cursor.fetchone():
                return False, "Usuário não pertence à sua empresa"
            
            cursor.execute('''
            UPDATE usuarios SET nivel_acesso = ? WHERE id = ?
            ''', (novo_nivel, usuario_id))
            
            logger.info(f"✅ Nível de acesso do usuário {usuario_id} alterado para {novo_nivel}")
            
            # Registrar no log de segurança
            registrar_evento_seguranca(
                admin_id,
                "NIVEL_ALTERADO",
                f"Nível de acesso do usuário {usuario_id} alterado para {novo_nivel}",
                "INFO",
                {"usuario_alterado": usuario_id, "novo_nivel": novo_nivel}
            )
            
            return True, "Nível de acesso atualizado com sucesso"
            
    except Exception as e:
        logger.error(f"Erro ao atualizar nível de acesso: {e}")
        return False, str(e)


# database.py - CORREÇÃO: Remover dependência do st

def convidar_membro(empresa_id: int, 
                    email: str, 
                    nome: str, 
                    nivel_acesso: str = 'membro', 
                    convidado_por: int = None,
                    config_email: Dict = None) -> Optional[str]:  # <--- NOVO PARÂMETRO
    """
    Gera um convite para um novo membro da empresa
    
    Args:
        empresa_id: ID da empresa
        email: Email do convidado
        nome: Nome do convidado
        nivel_acesso: Nível de acesso
        convidado_por: ID de quem convidou
        config_email: Dicionário com configurações de email (opcional)
    
    Returns:
        Token do convite
    """
    try:
        import secrets
        from datetime import datetime, timedelta
        
        # Gerar token
        token = secrets.token_urlsafe(32)
        expiracao = datetime.now() + timedelta(days=7)
        
        conn = criar_conexao()
        cursor = conn.cursor()
        
        # [ ... validações existentes ... ]
        
        # Buscar nome de quem convidou
        nome_convidador = "Sistema"
        if convidado_por:
            cursor.execute('SELECT nome FROM usuarios WHERE id = ?', (convidado_por,))
            result = cursor.fetchone()
            if result:
                nome_convidador = result[0]
        
        # Buscar nome da empresa
        cursor.execute('SELECT nome FROM empresas WHERE id = ?', (empresa_id,))
        empresa = cursor.fetchone()
        nome_empresa = empresa[0] if empresa else "Empresa"
        
        # Inserir convite
        cursor.execute('''
        INSERT INTO convites (empresa_id, email, nome, token, nivel_acesso, expiracao, criado_por)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (empresa_id, email, nome, token, nivel_acesso, expiracao.isoformat(), convidado_por))
        
        conn.commit()
        conn.close()
        
        # ===== ENVIAR EMAIL SOMENTE SE CONFIGURAÇÕES FORNECIDAS =====
        if config_email and config_email.get('user') and config_email.get('password'):
            try:
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                
                base_url = config_email.get('base_url', 'http://localhost:8501')
                link_convite = f"{base_url}/?convite={token}"
                
                # Montar email
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f"📨 Convite para {nome_empresa} - DBMILESX"
                msg['From'] = config_email.get('from', 'noreply@dbmilesx.com')
                msg['To'] = email
                
                # Versão texto
                text = f"""
                Olá {nome},
                
                Você foi convidado por {nome_convidador} para fazer parte da empresa {nome_empresa} no DBMILESX!
                
                Nível de acesso: {nivel_acesso}
                
                Clique no link abaixo para aceitar o convite:
                {link_convite}
                
                Este convite expira em 7 dias.
                """
                
                # Versão HTML
                html = f"""
                <!DOCTYPE html>
                <html>
                <body style="font-family: Arial, sans-serif;">
                    <div style="background: linear-gradient(135deg, #3d8bfd, #2a5cbd); padding: 20px; text-align: center;">
                        <h2 style="color: white;">DBMILESX</h2>
                    </div>
                    <div style="padding: 30px;">
                        <h3>Olá {nome}!</h3>
                        <p><strong>{nome_convidador}</strong> te convidou para <strong>{nome_empresa}</strong>!</p>
                        <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <p><strong>Nível:</strong> {nivel_acesso}</p>
                        </div>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{link_convite}" 
                               style="background-color: #3d8bfd; color: white; padding: 15px 30px; 
                                      text-decoration: none; border-radius: 8px; font-weight: bold;">
                                ✅ ACEITAR CONVITE
                            </a>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                part1 = MIMEText(text, 'plain')
                part2 = MIMEText(html, 'html')
                msg.attach(part1)
                msg.attach(part2)
                
                # Enviar
                server = smtplib.SMTP(
                    config_email.get('host', 'smtp.gmail.com'),
                    config_email.get('port', 587),
                    timeout=30
                )
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(config_email['user'], config_email['password'])
                server.send_message(msg)
                server.quit()
                
                logger.info(f"📧 Email enviado para {email}")
                
            except Exception as email_error:
                logger.error(f"⚠️ Erro ao enviar email: {email_error}")
        
        logger.info(f"✅ Convite gerado para {email} (empresa: {empresa_id})")
        return token
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar convite: {e}")
        return None
    
def aceitar_convite(token: str, senha: str) -> Tuple[bool, str]:
    """Aceita convite e cria usuário"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM convites 
            WHERE token = ? AND usado = 0 AND expiracao > CURRENT_TIMESTAMP
            ''', (token,))
            
            convite = cursor.fetchone()
            if not convite:
                return False, "Convite inválido ou expirado"
            
            # Verificar se email já existe
            cursor.execute('SELECT id FROM usuarios WHERE email = ?', (convite['email'],))
            if cursor.fetchone():
                return False, "Email já cadastrado"
            
            # Criar usuário
            senha_hash = PasswordHasher.hash_password(senha)
            cursor.execute('''
            INSERT INTO usuarios (email, senha_hash, nome, empresa_id, nivel_acesso)
            VALUES (?, ?, ?, ?, ?)
            ''', (convite['email'], senha_hash, convite['nome'], 
                  convite['empresa_id'], convite['nivel_acesso']))
            
            usuario_id = cursor.lastrowid
            
            # Marcar convite como usado
            cursor.execute('UPDATE convites SET usado = 1 WHERE id = ?', (convite['id'],))
            
            conn.commit()
            
            logger.info(f"✅ Novo membro aceitou convite: {convite['email']}")
            
            # Registrar no log
            registrar_evento_seguranca(
                usuario_id,
                "CONVITE_ACEITO",
                f"Convite aceito para {convite['email']}",
                "INFO"
            )
            
            return True, "Conta criada com sucesso!"
            
    except Exception as e:
        logger.error(f"Erro ao aceitar convite: {e}")
        return False, str(e)

# ============= FUNÇÕES DE USUÁRIOS =============
def carregar_preferencias_usuario(usuario_id: int):
    """Carrega preferências do usuário do banco"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                'SELECT tema_preferido, moeda_preferida, cor_primaria, tema_personalizado FROM usuarios WHERE id = ?',
                (usuario_id,)
            )
            pref = cursor.fetchone()

        # Importar streamlit aqui para evitar circular
        import streamlit as st

        if pref:
            tema = pref['tema_preferido'] if pref['tema_preferido'] in ['escuro', 'claro'] else "escuro"
            moeda = pref['moeda_preferida'] if pref['moeda_preferida'] in ['BRL', 'USD', 'EUR', 'GBP'] else "BRL"
            cor_primaria = pref['cor_primaria'] if pref['cor_primaria'] else '#3d8bfd'

            st.session_state.tema = tema
            st.session_state.moeda = moeda
            st.session_state.cor_primaria = cor_primaria
            st.session_state.security_level = "Alta"
            
            # Se houver tema personalizado completo, carregar
            if pref['tema_personalizado']:
                try:
                    tema_personalizado = json.loads(pref['tema_personalizado'])
                    st.session_state.tema_cores = tema_personalizado.get('cores', {})
                except:
                    pass

            logger.info(f"Preferências carregadas para usuário {usuario_id}: tema={tema}, moeda={moeda}")
        else:
            # Valores padrão
            st.session_state.tema = "escuro"
            st.session_state.moeda = "BRL"
            st.session_state.cor_primaria = '#3d8bfd'
            st.session_state.security_level = "Alta"
            logger.warning(f"Usuário {usuario_id} não encontrado, usando valores padrão")

    except Exception as e:
        logger.error(f"Erro ao carregar preferências: {e}")
        # Garantir valores padrão
        import streamlit as st
        st.session_state.tema = "escuro"
        st.session_state.moeda = "BRL"
        st.session_state.cor_primaria = '#3d8bfd'
        st.session_state.security_level = "Média"

def salvar_preferencias_usuario(usuario_id: int, tema: Optional[str] = None, 
                                moeda: Optional[str] = None, cor_primaria: Optional[str] = None,
                                tema_completo: Optional[Dict] = None) -> bool:
    """Salva preferências do usuário"""
    try:
        with get_db_cursor() as cursor:
            updates = []
            params = []
            
            if tema:
                updates.append('tema_preferido = ?')
                params.append(tema)
            
            if moeda:
                updates.append('moeda_preferida = ?')
                params.append(moeda)
            
            if cor_primaria:
                updates.append('cor_primaria = ?')
                params.append(cor_primaria)
            
            if tema_completo:
                updates.append('tema_personalizado = ?')
                params.append(json.dumps(tema_completo))
            
            if updates:
                updates.append('updated_at = CURRENT_TIMESTAMP')
                params.append(usuario_id)
                query = f'UPDATE usuarios SET {", ".join(updates)} WHERE id = ?'
                cursor.execute(query, params)
                
                logger.info(f"Preferências atualizadas para usuário {usuario_id}")
                return True
            
            return False

    except Exception as e:
        logger.error(f"Erro ao atualizar preferências: {e}")
        return False
    
def registrar_usuario(email: str, senha: str, nome: str) -> Tuple[bool, str]:
    """Registra novo usuário - VERSÃO SIMPLIFICADA SEM ERROS"""
    try:
        email = email.strip().lower()
        nome = nome.strip()
        
        # Validações simples (sem usar SecurityManager)
        if '@' not in email or '.' not in email:
            return False, "Email inválido"
        
        if len(nome) < 3:
            return False, "Nome deve ter pelo menos 3 caracteres"
        
        if len(senha) < 6:
            return False, "Senha deve ter pelo menos 6 caracteres"
        
        with get_db_cursor() as cursor:
            # Verificar se email já existe
            cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
            if cursor.fetchone():
                return False, "Email já cadastrado"
            
            # Gerar hash da senha
            senha_hash = PasswordHasher.hash_password(senha)
            
            # Gerar tokens
            csrf_token = secrets.token_urlsafe(32)
            sessao_token = secrets.token_urlsafe(32)
            
            # Inserir usuário
            cursor.execute('''
            INSERT INTO usuarios (
                email, senha_hash, nome, csrf_token, sessao_token, sessao_criada
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (email, senha_hash, nome, csrf_token, sessao_token))
            
            usuario_id = cursor.lastrowid
            
            logger.info(f"✅ Novo usuário registrado: {email}")
            
            # Registrar evento de segurança
            try:
                registrar_evento_seguranca(
                    usuario_id,
                    "REGISTRO_SUCESSO",
                    f"Novo usuário registrado: {email}",
                    "INFO"
                )
            except:
                pass
            
            return True, "Conta criada com sucesso!"
            
    except Exception as e:
        logger.error(f"Erro ao registrar usuário: {e}")
        return False, f"Erro: {str(e)}"
    
    
def atualizar_perfil_usuario(usuario_id: int, dados: Dict[str, Any]) -> Tuple[bool, str]:
    """Atualiza dados do perfil do usuário"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        # Construir query dinamicamente
        campos = []
        valores = []
        
        campos_permitidos = ['nome', 'telefone', 'cargo', 'foto_perfil', 'data_nascimento']
        
        for campo in campos_permitidos:
            if campo in dados:
                campos.append(f"{campo} = ?")
                valores.append(dados[campo])
        
        if not campos:
            conn.close()
            return False, "Nenhum dado para atualizar"
        
        valores.append(usuario_id)
        query = f"UPDATE usuarios SET {', '.join(campos)} WHERE id = ?"
        
        cursor.execute(query, valores)
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Perfil do usuário {usuario_id} atualizado")
        return True, "Perfil atualizado com sucesso!"
        
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar perfil: {e}")
        return False, f"Erro: {str(e)}"
# Adicione esta função e chame no inicializar_banco
def adicionar_coluna_foto_perfil():
    """Adiciona coluna foto_perfil na tabela usuarios"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("PRAGMA table_info(usuarios)")
            colunas = cursor.fetchall()
            colunas_nomes = [col[1] for col in colunas]
            
            if 'foto_perfil' not in colunas_nomes:
                cursor.execute('ALTER TABLE usuarios ADD COLUMN foto_perfil TEXT')
                conn.commit()
                logger.info("✅ Coluna foto_perfil adicionada")
                return True
            return False
            
    except Exception as e:
        logger.error(f"Erro ao adicionar foto_perfil: {e}")
        return False
    
def alterar_senha(usuario_id: int, senha_atual: str, nova_senha: str) -> Tuple[bool, str]:
    """Altera senha do usuário com segurança"""
    try:
        # Validar nova senha
        if len(nova_senha) < 8:
            return False, "Nova senha deve ter pelo menos 8 caracteres"

        if senha_atual == nova_senha:
            return False, "A nova senha deve ser diferente da atual"

        with get_db_cursor() as cursor:
            # Obter hash atual
            cursor.execute('SELECT senha_hash FROM usuarios WHERE id = ?', (usuario_id,))
            resultado = cursor.fetchone()

            if not resultado:
                return False, "Usuário não encontrado"

            # Verificar senha atual
            if not PasswordHasher.verify_password(senha_atual, resultado['senha_hash']):
                return False, "Senha atual incorreta"

            # Validar força da nova senha
            from securitymax import SecurityManager
            validacao = SecurityManager().validate_password_strength(nova_senha)
            if not validacao['valid']:
                return False, "Nova senha muito fraca: " + ", ".join(validacao['feedback'][:2])

            # Gerar novo hash
            nova_senha_hash = PasswordHasher.hash_password(nova_senha)

            # Atualizar senha
            cursor.execute('''
            UPDATE usuarios 
            SET senha_hash = ?, 
                data_ultima_alteracao = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (nova_senha_hash, usuario_id))

            logger.info(f"Senha alterada para usuário {usuario_id}")

            # Registrar evento
            registrar_evento_seguranca(
                usuario_id,
                "SENHA_ALTERADA",
                "Senha alterada com sucesso",
                "INFO"
            )

            return True, "Senha alterada com sucesso!"

    except Exception as e:
        logger.error(f"Erro ao alterar senha: {e}")
        registrar_evento_seguranca(
            usuario_id,
            "ERRO_ALTERACAO_SENHA",
            f"Erro ao alterar senha: {str(e)}",
            "ERROR"
        )
        return False, f"Erro interno: {str(e)}"

def obter_dados_usuario(usuario_id: int) -> Optional[Dict]:
    """Obtém dados do usuário"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute('''
                SELECT nome, email, data_criacao, tema_preferido, moeda_preferida,
                       empresa_id, nivel_acesso
                FROM usuarios 
                WHERE id = ?
            ''', (usuario_id,))

            usuario = cursor.fetchone()
            return dict(usuario) if usuario else None

    except Exception as e:
        logger.error(f"Erro ao obter dados do usuário: {e}")
        return None

def atualizar_nome_usuario(usuario_id: int, novo_nome: str) -> bool:
    """Atualiza nome do usuário"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute('''
                UPDATE usuarios 
                SET nome = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (novo_nome.strip(), usuario_id))

            logger.info(f"Nome atualizado para usuário {usuario_id}: {novo_nome}")
            return True

    except Exception as e:
        logger.error(f"Erro ao atualizar nome: {e}")
        return False

def obter_estatisticas_usuario(usuario_id: int) -> Dict[str, Any]:
    """Obtém estatísticas do usuário"""
    try:
        with get_db_cursor() as cursor:
            # Contar cotações
            cursor.execute('SELECT COUNT(*) FROM cotacoes WHERE usuario_id = ?', (usuario_id,))
            total_cotacoes = cursor.fetchone()[0]

            # Contar cálculos no histórico
            cursor.execute('SELECT COUNT(*) FROM historico_cotacoes WHERE usuario_id = ?', (usuario_id,))
            total_calculos = cursor.fetchone()[0]

            # Total gasto
            cursor.execute('''
                SELECT COALESCE(SUM(total_geral), 0) 
                FROM historico_cotacoes 
                WHERE usuario_id = ?
            ''', (usuario_id,))
            total_gasto = cursor.fetchone()[0]

            # Último login
            cursor.execute('''
                SELECT data_ultimo_login 
                FROM usuarios 
                WHERE id = ?
            ''', (usuario_id,))
            ultimo_login = cursor.fetchone()

            return {
                'total_cotacoes': total_cotacoes,
                'total_calculos': total_calculos,
                'total_gasto': float(total_gasto),
                'ultimo_login': dict(ultimo_login)['data_ultimo_login'] if ultimo_login else None
            }

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return {
            'total_cotacoes': 0,
            'total_calculos': 0,
            'total_gasto': 0,
            'ultimo_login': None
        }

def registrar_ultimo_login(usuario_id: int):
    """Registra data/hora do último login"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute('''
                UPDATE usuarios 
                SET data_ultimo_login = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (usuario_id,))

    except Exception as e:
        logger.error(f"Erro ao registrar último login: {e}")

# ============= FUNÇÕES DE INICIALIZAÇÃO =============
def inicializar_banco():
    """Inicializa tabelas do banco de dados"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Adicionar coluna foto_perfil se não existir
            cursor.execute("PRAGMA table_info(usuarios)")
            colunas = cursor.fetchall()
            colunas_nomes = [col[1] for col in colunas]
            
            if 'foto_perfil' not in colunas_nomes:
                try:
                    cursor.execute('ALTER TABLE usuarios ADD COLUMN foto_perfil TEXT')
                    logger.info("✅ Coluna foto_perfil adicionada")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao adicionar foto_perfil: {e}")
            
            # Adicionar coluna site na tabela empresas se não existir
            cursor.execute("PRAGMA table_info(empresas)")
            colunas_empresas = cursor.fetchall()
            colunas_empresas_nomes = [col[1] for col in colunas_empresas]
            
            if 'site' not in colunas_empresas_nomes:
                try:
                    cursor.execute('ALTER TABLE empresas ADD COLUMN site TEXT')
                    logger.info("✅ Coluna site adicionada na tabela empresas")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao adicionar site: {e}")
            
            # Tabela de empresas
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS empresas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cnpj TEXT UNIQUE,
                telefone TEXT,
                email TEXT,
                site TEXT,
                endereco TEXT,
                logo TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                criado_por INTEGER,
                ativo INTEGER DEFAULT 1
            )
            ''')

            # Tabela de convites
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS convites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                nome TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                nivel_acesso TEXT DEFAULT 'membro',
                expiracao TIMESTAMP NOT NULL,
                usado INTEGER DEFAULT 0,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                criado_por INTEGER,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE
            )
            ''')

            # Tabela de usuários
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER,
                email TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                nome TEXT NOT NULL,
                foto_perfil TEXT,
                telefone TEXT,
                cargo TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_ultimo_login TIMESTAMP,
                data_ultima_alteracao TIMESTAMP,
                tema_preferido TEXT DEFAULT 'escuro',
                moeda_preferida TEXT DEFAULT 'BRL',
                cor_primaria TEXT DEFAULT '#3d8bfd',
                tema_personalizado TEXT,
                csrf_token TEXT,
                sessao_token TEXT,
                sessao_criada TIMESTAMP,
                tentativas_login INTEGER DEFAULT 0,
                bloqueado_ate TIMESTAMP,
                user_agent TEXT,
                ip_ultimo_login TEXT,
                dois_fa TEXT,
                dois_fa_backup_codes TEXT,
                nivel_acesso TEXT DEFAULT 'membro',
                ativo INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE SET NULL
            )
            ''')

            # Tabela de logs de segurança
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs_seguranca (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                empresa_id INTEGER,
                tipo_evento TEXT NOT NULL,
                nivel_severidade TEXT NOT NULL,
                descricao TEXT,
                ip TEXT,
                user_agent TEXT,
                metadata TEXT,
                data_evento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE SET NULL
            )
            ''')

            # Tabela de cotações
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS cotacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER,
                usuario_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                origem TEXT NOT NULL,
                destino TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
            ''')

            # Tabela de histórico de cotações
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico_cotacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER,
                usuario_id INTEGER NOT NULL,
                cotacao_id INTEGER NOT NULL,
                companhia TEXT NOT NULL,
                tipo_calculo TEXT NOT NULL,
                milhas_total REAL DEFAULT 0,
                valor_milheiro REAL DEFAULT 0,
                taxa_embarque REAL DEFAULT 0,
                valor_base REAL DEFAULT 0,
                valor_bagagens REAL DEFAULT 0,
                desagio_percentual REAL DEFAULT 0,
                total_geral REAL NOT NULL,
                moeda TEXT NOT NULL,
                passageiros INTEGER DEFAULT 1,
                bebes INTEGER DEFAULT 0,
                num_bagagens INTEGER DEFAULT 0,
                metadata TEXT,
                metadata_criptografado TEXT,
                data_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                FOREIGN KEY (cotacao_id) REFERENCES cotacoes(id) ON DELETE CASCADE
            )
            ''')

            # Tabela de tokens de recuperação
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

            # Tabela de links públicos
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS links_publicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER,
                token TEXT UNIQUE NOT NULL,
                nome_campanha TEXT NOT NULL,
                empresas_data TEXT NOT NULL DEFAULT '[]',
                dias_validade INTEGER NOT NULL DEFAULT 30,
                limite_uso INTEGER NOT NULL DEFAULT 100,
                usos_restantes INTEGER NOT NULL DEFAULT 100,
                total_usos INTEGER DEFAULT 0,
                data_expiracao TIMESTAMP NOT NULL,
                usuario_criador_id INTEGER NOT NULL,
                email_criador TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                FOREIGN KEY (usuario_criador_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
            ''')

            # Tabela de solicitações de cotação
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS solicitacoes_cotacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER,
                dados_solicitacao TEXT NOT NULL,
                status TEXT DEFAULT 'RECEBIDA',
                link_id INTEGER,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                FOREIGN KEY (link_id) REFERENCES links_publicos(id) ON DELETE SET NULL
            )
            ''')

            # Tabela de códigos de acesso
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS codigos_acesso (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                codigo TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                criado_por INTEGER,
                usado INTEGER DEFAULT 0,
                expiracao TIMESTAMP NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            )
            ''')

            # Criar índices para performance
            indices = [
                'CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)',
                'CREATE INDEX IF NOT EXISTS idx_usuarios_sessao ON usuarios(sessao_token)',
                'CREATE INDEX IF NOT EXISTS idx_usuarios_empresa ON usuarios(empresa_id)',
                'CREATE INDEX IF NOT EXISTS idx_empresas_cnpj ON empresas(cnpj)',
                'CREATE INDEX IF NOT EXISTS idx_convites_token ON convites(token)',
                'CREATE INDEX IF NOT EXISTS idx_cotacoes_usuario ON cotacoes(usuario_id)',
                'CREATE INDEX IF NOT EXISTS idx_cotacoes_empresa ON cotacoes(empresa_id)',
                'CREATE INDEX IF NOT EXISTS idx_historico_usuario ON historico_cotacoes(usuario_id)',
                'CREATE INDEX IF NOT EXISTS idx_historico_empresa ON historico_cotacoes(empresa_id)',
                'CREATE INDEX IF NOT EXISTS idx_historico_data ON historico_cotacoes(data_calculo)',
                'CREATE INDEX IF NOT EXISTS idx_logs_usuario ON logs_seguranca(usuario_id)',
                'CREATE INDEX IF NOT EXISTS idx_logs_empresa ON logs_seguranca(empresa_id)',
                'CREATE INDEX IF NOT EXISTS idx_logs_data ON logs_seguranca(data_evento)',
                'CREATE INDEX IF NOT EXISTS idx_tokens_token ON tokens_recuperacao(token)',
                'CREATE INDEX IF NOT EXISTS idx_tokens_email ON tokens_recuperacao(email)',
                'CREATE INDEX IF NOT EXISTS idx_links_token ON links_publicos(token)',
                'CREATE INDEX IF NOT EXISTS idx_links_usuario ON links_publicos(usuario_criador_id)',
                'CREATE INDEX IF NOT EXISTS idx_links_empresa ON links_publicos(empresa_id)',
                'CREATE INDEX IF NOT EXISTS idx_solicitacoes_link ON solicitacoes_cotacao(link_id)',
                'CREATE INDEX IF NOT EXISTS idx_solicitacoes_empresa ON solicitacoes_cotacao(empresa_id)',
                'CREATE INDEX IF NOT EXISTS idx_codigos_empresa ON codigos_acesso(empresa_id)',
                'CREATE INDEX IF NOT EXISTS idx_codigos_codigo ON codigos_acesso(codigo)'
            ]

            for idx in indices:
                try:
                    cursor.execute(idx)
                except Exception as e:
                    logger.warning(f"Erro ao criar índice (ignorado): {e}")

            # Verificar se usuário admin existe
            cursor.execute('SELECT id FROM usuarios WHERE email = ?', ('admin@dbmilesx.com',))
            if not cursor.fetchone():
                senha_hash = PasswordHasher.hash_password('Admin@DBMILESX123!')
                csrf_token = secrets.token_urlsafe(32)
                sessao_token = secrets.token_urlsafe(32)

                cursor.execute('''
                INSERT INTO usuarios (
                    email, senha_hash, nome, tema_preferido, moeda_preferida,
                    csrf_token, sessao_token, sessao_criada, nivel_acesso
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'admin')
                ''', (
                    'admin@dbmilesx.com', senha_hash, 'Administrador Global',
                    'escuro', 'BRL', csrf_token, sessao_token
                ))

                logger.info("✅ Usuário admin global criado")

            # Verificar se usuário teste existe
            cursor.execute('SELECT id FROM usuarios WHERE email = ?', ('teste@dbmilesx.com',))
            if not cursor.fetchone():
                senha_hash = PasswordHasher.hash_password('Teste123!')
                csrf_token = secrets.token_urlsafe(32)
                sessao_token = secrets.token_urlsafe(32)

                cursor.execute('''
                INSERT INTO usuarios (
                    email, senha_hash, nome, tema_preferido, moeda_preferida,
                    csrf_token, sessao_token, sessao_criada, nivel_acesso
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'membro')
                ''', (
                    'teste@dbmilesx.com', senha_hash, 'Usuário Teste',
                    'escuro', 'BRL', csrf_token, sessao_token
                ))

                logger.info("✅ Usuário teste criado")

            conn.commit()
            logger.info("✅ Banco de dados inicializado com sucesso")

    except Exception as e:
        logger.error(f"❌ Erro ao inicializar banco: {e}")
        raise
    
def verificar_status_banco() -> Dict[str, Any]:
    """Verifica status detalhado do banco de dados"""
    status = {
        'existe': False,
        'caminho': DB_PATH,
        'tamanho': 0,
        'tabelas': {},
        'usuarios': 0,
        'empresas': 0,
        'erro': None
    }

    try:
        if os.path.exists(DB_PATH):
            status['existe'] = True
            status['tamanho'] = os.path.getsize(DB_PATH)

            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Listar tabelas
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                for tabela in cursor.fetchall():
                    nome = tabela['name']
                    cursor.execute(f"SELECT COUNT(*) FROM {nome}")
                    count = cursor.fetchone()[0]
                    status['tabelas'][nome] = count

                # Contar usuários
                cursor.execute("SELECT COUNT(*) FROM usuarios")
                status['usuarios'] = cursor.fetchone()[0]
                
                # Contar empresas
                cursor.execute("SELECT COUNT(*) FROM empresas")
                status['empresas'] = cursor.fetchone()[0]

        return status

    except Exception as e:
        status['erro'] = str(e)
        logger.error(f"Erro ao verificar status: {e}")
        return status

# ============= FUNÇÕES DE LOG =============
def registrar_evento_seguranca(
    usuario_id: Optional[int],
    tipo: str,
    descricao: str,
    nivel_severidade: str = "INFO",
    metadata: Optional[Dict] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    empresa_id: Optional[int] = None
):
    """Registra evento de segurança com metadados"""
    try:
        with get_db_cursor() as cursor:
            metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

            cursor.execute('''
            INSERT INTO logs_seguranca (
                usuario_id, empresa_id, tipo_evento, nivel_severidade, descricao,
                metadata, ip, user_agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (usuario_id, empresa_id, tipo, nivel_severidade, descricao,
                  metadata_json, ip, user_agent))

        # Log no console
        log_msg = f"[{nivel_severidade}] {tipo}: {descricao}"
        if nivel_severidade in ['ERROR', 'CRITICAL']:
            logger.error(log_msg)
        elif nivel_severidade == 'WARNING':
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

    except Exception as e:
        logger.error(f"Erro ao registrar evento: {e}")

def obter_logs_seguranca(
    usuario_id: Optional[int] = None,
    empresa_id: Optional[int] = None,
    nivel: Optional[str] = None,
    limite: int = 100
) -> List[Dict]:
    """Obtém logs de segurança com filtros"""
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM logs_seguranca WHERE 1=1"
            params = []

            if usuario_id:
                query += " AND usuario_id = ?"
                params.append(usuario_id)
            
            if empresa_id:
                query += " AND empresa_id = ?"
                params.append(empresa_id)

            if nivel:
                query += " AND nivel_severidade = ?"
                params.append(nivel)

            query += " ORDER BY data_evento DESC LIMIT ?"
            params.append(limite)

            cursor.execute(query, params)
            resultados = cursor.fetchall()

            return [dict(row) for row in resultados]

    except Exception as e:
        logger.error(f"Erro ao obter logs: {e}")
        return []

# ============= FUNÇÕES PARA APP.PY =============
def registrar_usuario_simples(email: str, senha: str, nome: str) -> Tuple[bool, str]:
    """Registra novo usuário (versão simples)"""
    try:
        from securitymax import SecurityManager

        email = email.strip().lower()
        nome = nome.strip()

        # Validações
        if not SecurityManager.validate_email(email):
            return False, "Formato de email inválido"

        if len(nome) < 3:
            return False, "Nome deve ter pelo menos 3 caracteres"

        # Validar força da senha
        security = SecurityManager()
        validacao = security.validate_password_strength(senha)
        if not validacao['valid']:
            return False, "Senha muito fraca: " + ", ".join(validacao['feedback'][:2])

        with get_db_cursor() as cursor:
            # Verificar se email já existe
            cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
            if cursor.fetchone():
                return False, "Email já cadastrado"

            # Gerar hash
            senha_hash = PasswordHasher.hash_password(senha)

            # Gerar tokens
            csrf_token = secrets.token_urlsafe(32)
            sessao_token = secrets.token_urlsafe(32)

            # Inserir usuário
            cursor.execute('''
            INSERT INTO usuarios (
                email, senha_hash, nome, csrf_token, sessao_token, sessao_criada
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (email, senha_hash, nome, csrf_token, sessao_token))

            usuario_id = cursor.lastrowid

            logger.info(f"✅ Novo usuário registrado: {email}")

            # Registrar evento
            registrar_evento_seguranca(
                usuario_id,
                "REGISTRO_SUCESSO",
                f"Novo usuário registrado",
                "INFO",
                {"email": email, "nome": nome}
            )

            return True, "Conta criada com sucesso!"

    except sqlite3.IntegrityError:
        return False, "Email já cadastrado"
    except Exception as e:
        logger.error(f"Erro ao registrar usuário: {e}")
        return False, f"Erro interno: {str(e)}"

# ============= FUNÇÕES DE RECUPERAÇÃO DE SENHA =============
def gerar_token_recuperacao(email: str) -> Optional[str]:
    """Gera token seguro para recuperação de senha"""
    try:
        email = email.strip().lower()

        # Verificar se email existe
        with get_db_cursor() as cursor:
            cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
            if not cursor.fetchone():
                logger.warning(f"Tentativa de recuperação para email não cadastrado: {email}")
                return None

            # Gerar token
            token = secrets.token_urlsafe(48)
            expiracao = datetime.now() + timedelta(hours=1)

            # Remover tokens antigos
            cursor.execute('DELETE FROM tokens_recuperacao WHERE email = ?', (email,))

            # Inserir novo token
            cursor.execute('''
                INSERT INTO tokens_recuperacao (email, token, expiracao)
                VALUES (?, ?, ?)
            ''', (email, token, expiracao))

            logger.info(f"Token de recuperação gerado para {email}")
            return token

    except Exception as e:
        logger.error(f"Erro ao gerar token: {e}")
        return None

def validar_token_recuperacao(token: str) -> Tuple[bool, Optional[str]]:
    """Valida token de recuperação"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute('''
                SELECT email, expiracao 
                FROM tokens_recuperacao 
                WHERE token = ? AND usado = 0
            ''', (token,))

            resultado = cursor.fetchone()

            if not resultado:
                return False, "Token inválido ou já utilizado"

            email = resultado['email']
            expiracao = datetime.fromisoformat(resultado['expiracao'])

            if datetime.now() > expiracao:
                # Marcar como usado se expirado
                cursor.execute('UPDATE tokens_recuperacao SET usado = 1 WHERE token = ?', (token,))
                return False, "Token expirado"

            return True, email

    except Exception as e:
        logger.error(f"Erro ao validar token: {e}")
        return False, "Erro ao validar token"

def marcar_token_como_usado(token: str):
    """Marca token como utilizado"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute('UPDATE tokens_recuperacao SET usado = 1 WHERE token = ?', (token,))
    except Exception as e:
        logger.error(f"Erro ao marcar token como usado: {e}")

def redefinir_senha_com_token(token: str, nova_senha: str) -> Tuple[bool, str]:
    """Redefine senha usando token de recuperação"""
    try:
        # Validar token
        valido, resultado = validar_token_recuperacao(token)

        if not valido:
            return False, resultado

        email = resultado

        # Validar nova senha
        from securitymax import SecurityManager
        validacao = SecurityManager().validate_password_strength(nova_senha)
        if not validacao['valid']:
            return False, "Senha muito fraca"

        with get_db_cursor() as cursor:
            # Obter ID do usuário
            cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
            usuario = cursor.fetchone()

            if not usuario:
                return False, "Usuário não encontrado"

            usuario_id = usuario['id']

            # Gerar novo hash
            novo_hash = PasswordHasher.hash_password(nova_senha)

            # Atualizar senha e invalidar sessões
            cursor.execute('''
                UPDATE usuarios 
                SET senha_hash = ?,
                    sessao_token = ?,
                    csrf_token = ?,
                    data_ultima_alteracao = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                novo_hash,
                secrets.token_urlsafe(32),
                secrets.token_urlsafe(32),
                usuario_id
            ))

            # Marcar token como usado
            cursor.execute('UPDATE tokens_recuperacao SET usado = 1 WHERE token = ?', (token,))

            logger.info(f"Senha redefinida via token para usuário {usuario_id}")

            # Registrar evento
            registrar_evento_seguranca(
                usuario_id,
                "SENHA_REDEFINIDA_TOKEN",
                "Senha redefinida via token de recuperação",
                "INFO"
            )

            return True, "Senha redefinida com sucesso!"

    except Exception as e:
        logger.error(f"Erro ao redefinir senha: {e}")
        return False, f"Erro interno: {str(e)}"

# ============= FUNÇÕES DE HISTÓRICO =============
def listar_historico(usuario_id: int, filtro_companhia: Optional[str] = None, 
                    data_inicio: Optional[str] = None, data_fim: Optional[str] = None,
                    limite: int = 100, admin_visualizando: bool = False,
                    empresa_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Lista histórico de cálculos do usuário com dados descriptografados.
    Se admin_visualizando=True, mostra de todos da empresa
    """
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Se admin_visualizando, mostra todos da empresa
            if admin_visualizando and empresa_id:
                query = '''
                SELECT h.*, c.nome as nome_cotacao, c.origem, c.destino,
                       u.nome as usuario_nome, u.email as usuario_email
                FROM historico_cotacoes h
                JOIN cotacoes c ON h.cotacao_id = c.id
                JOIN usuarios u ON h.usuario_id = u.id
                WHERE u.empresa_id = ?
                '''
                params = [empresa_id]
            else:
                # Mostra apenas do usuário específico
                query = '''
                SELECT h.*, c.nome as nome_cotacao, c.origem, c.destino
                FROM historico_cotacoes h
                JOIN cotacoes c ON h.cotacao_id = c.id
                WHERE h.usuario_id = ?
                '''
                params = [usuario_id]

            # Aplicar filtros comuns
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

            cursor.execute(query, params)
            resultados = cursor.fetchall()

            colunas = [desc[0] for desc in cursor.description]

            historico = []
            for row in resultados:
                item = dict(zip(colunas, row))

                # Descriptografar metadados se existirem
                if item.get('metadata_criptografado'):
                    try:
                        from securitymax import data_crypto
                        metadata_json = data_crypto.decrypt(item['metadata_criptografado'])
                        item['metadata'] = json.loads(metadata_json)
                        
                        # Mover dados do metadata para o nível principal
                        if item['metadata']:
                            for key, value in item['metadata'].items():
                                if key not in item or not item[key]:
                                    item[key] = value
                            
                    except Exception as e:
                        logger.error(f"Erro ao descriptografar metadata: {e}")
                        item['metadata'] = {}
                else:
                    # Compatibilidade com registros antigos
                    if item.get('metadata'):
                        try:
                            if isinstance(item['metadata'], str):
                                item['metadata'] = json.loads(item['metadata'])
                        except:
                            item['metadata'] = {}
                    else:
                        item['metadata'] = {}

                # Remover campo criptografado bruto
                if 'metadata_criptografado' in item:
                    del item['metadata_criptografado']

                # Garantir valores padrão
                item['passageiros'] = item.get('passageiros') or 1
                item['bebes'] = item.get('bebes') or 0
                item['num_bagagens'] = item.get('num_bagagens') or 0

                historico.append(item)

            logger.info(f"📊 Listados {len(historico)} registros do histórico")
            return historico

    except Exception as e:
        logger.error(f"Erro ao listar histórico: {e}")
        return []

def excluir_calculo(calculo_id: int, usuario_id: int) -> Tuple[bool, str]:
    """Exclui um cálculo do histórico com verificação de autorização"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute('SELECT usuario_id FROM historico_cotacoes WHERE id = ?', (calculo_id,))
            resultado = cursor.fetchone()

            if not resultado:
                return False, "Cálculo não encontrado"

            if resultado[0] != usuario_id:
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

            if dados_calc:
                registrar_evento_seguranca(
                    usuario_id,
                    "CALCULO_EXCLUIDO",
                    f"Cálculo {calculo_id} excluído - {dados_calc[0]} {dados_calc[1]} {dados_calc[2]}",
                    "INFO"
                )

            return True, "Cotação excluída com sucesso!"

    except Exception as e:
        logger.error(f"Erro ao excluir cálculo: {e}")
        return False, f"Erro: {str(e)}"

# ============= FUNÇÕES DE 2FA =============
def obter_usuario_2fa_status(usuario_id: int) -> Dict[str, Any]:
    """Obtém status do 2FA para um usuário"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                'SELECT dois_fa, dois_fa_backup_codes FROM usuarios WHERE id = ?',
                (usuario_id,)
            )
            resultado = cursor.fetchone()

            if resultado and resultado['dois_fa']:
                return {
                    'ativo': True,
                    'segredo': resultado['dois_fa'],
                    'backup_codes': json.loads(resultado['dois_fa_backup_codes']) if resultado['dois_fa_backup_codes'] else []
                }
            else:
                return {'ativo': False, 'segredo': None, 'backup_codes': []}

    except Exception as e:
        logger.error(f"Erro ao obter status 2FA: {e}")
        return {'ativo': False, 'segredo': None, 'backup_codes': []}

def ativar_2fa_usuario(usuario_id: int, segredo: str) -> bool:
    """Ativa 2FA para um usuário"""
    try:
        from securitymax import TwoFactorAuth

        # Gerar códigos de backup
        backup_codes = TwoFactorAuth.generate_backup_codes()
        backup_codes_hashed = [TwoFactorAuth.hash_backup_code(code) for code in backup_codes]

        with get_db_cursor() as cursor:
            cursor.execute('''
                UPDATE usuarios 
                SET dois_fa = ?,
                    dois_fa_backup_codes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                segredo,
                json.dumps(backup_codes_hashed),
                usuario_id
            ))

            logger.info(f"✅ 2FA ativado para usuário {usuario_id}")
            return True

    except Exception as e:
        logger.error(f"Erro ao ativar 2FA: {e}")
        return False

def desativar_2fa_usuario(usuario_id: int) -> bool:
    """Desativa 2FA para um usuário"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute('''
                UPDATE usuarios 
                SET dois_fa = NULL,
                    dois_fa_backup_codes = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (usuario_id,))

            logger.info(f"✅ 2FA desativado para usuário {usuario_id}")
            return True

    except Exception as e:
        logger.error(f"Erro ao desativar 2FA: {e}")
        return False

def obter_segredo_2fa(usuario_id: int) -> Optional[str]:
    """Obtém segredo 2FA do usuário"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute('SELECT dois_fa FROM usuarios WHERE id = ?', (usuario_id,))
            resultado = cursor.fetchone()
            return resultado['dois_fa'] if resultado else None

    except Exception as e:
        logger.error(f"Erro ao obter segredo 2FA: {e}")
        return None

def verificar_backup_code(usuario_id: int, codigo: str) -> bool:
    """Verifica se um código de backup é válido e o remove se usado"""
    try:
        from securitymax import TwoFactorAuth

        with get_db_cursor() as cursor:
            cursor.execute(
                'SELECT dois_fa_backup_codes FROM usuarios WHERE id = ?',
                (usuario_id,)
            )
            resultado = cursor.fetchone()

            if not resultado or not resultado['dois_fa_backup_codes']:
                return False

            backup_codes = json.loads(resultado['dois_fa_backup_codes'])

            # Verificar cada código
            for i, hashed_code in enumerate(backup_codes):
                if TwoFactorAuth.verify_backup_code(codigo, hashed_code):
                    # Remover código usado
                    backup_codes.pop(i)

                    # Atualizar no banco
                    cursor.execute('''
                        UPDATE usuarios 
                        SET dois_fa_backup_codes = ? 
                        WHERE id = ?
                    ''', (json.dumps(backup_codes) if backup_codes else None, usuario_id))

                    return True

            return False

    except Exception as e:
        logger.error(f"Erro ao verificar backup code: {e}")
        return False

# ============= FUNÇÕES DE TEMA =============
# ============= FUNÇÕES PARA SALVAR TEMA DO USUÁRIO =============

def salvar_preferencias_tema(usuario_id: int, tema_id: str, modo: str, cores_json: str):
    """Salva as preferências de tema do usuário no banco de dados"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        # Verificar se já existe registro
        cursor.execute('''
            SELECT id FROM preferencias_tema WHERE usuario_id = ?
        ''', (usuario_id,))
        
        existe = cursor.fetchone()
        
        if existe:
            # Atualizar existente
            cursor.execute('''
                UPDATE preferencias_tema 
                SET tema_id = ?, modo = ?, cores_json = ?, data_atualizacao = CURRENT_TIMESTAMP
                WHERE usuario_id = ?
            ''', (tema_id, modo, cores_json, usuario_id))
        else:
            # Inserir novo
            cursor.execute('''
                INSERT INTO preferencias_tema (usuario_id, tema_id, modo, cores_json)
                VALUES (?, ?, ?, ?)
            ''', (usuario_id, tema_id, modo, cores_json))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Preferências de tema salvas para usuário {usuario_id}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao salvar preferências de tema: {e}")
        return False


def carregar_preferencias_tema(usuario_id: int) -> Optional[Dict]:
    """Carrega as preferências de tema do usuário do banco de dados"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT tema_id, modo, cores_json FROM preferencias_tema WHERE usuario_id = ?
        ''', (usuario_id,))
        
        resultado = cursor.fetchone()
        conn.close()
        
        if resultado:
            return {
                'tema_id': resultado['tema_id'],
                'modo': resultado['modo'],
                'cores': json.loads(resultado['cores_json']) if resultado['cores_json'] else {}
            }
        return None
        
    except Exception as e:
        logger.error(f"Erro ao carregar preferências de tema: {e}")
        return None


def criar_tabela_preferencias_tema():
    """Cria a tabela de preferências de tema no banco de dados"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS preferencias_tema (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL UNIQUE,
                tema_id TEXT DEFAULT 'default',
                modo TEXT DEFAULT 'escuro',
                cores_json TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Tabela preferencias_tema criada")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao criar tabela preferencias_tema: {e}")
        return False
    
def get_temas_personalizados(usuario_id: int) -> List[Dict]:
    """Carrega temas personalizados do usuário"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute('''
                SELECT tema_personalizado FROM usuarios WHERE id = ?
            ''', (usuario_id,))
            resultado = cursor.fetchone()

            if resultado and resultado[0]:
                return json.loads(resultado[0])
            return []
    except:
        return []

# ============= FUNÇÕES UTILITÁRIAS =============
def reset_all_passwords_to_compatible_hash():
    """Reset all passwords to use compatible hash - RUN THIS ONCE"""
    try:
        with get_db_cursor() as cursor:
            # Buscar todos os usuários
            cursor.execute('SELECT id, email FROM usuarios')
            usuarios = cursor.fetchall()

            senha_padrao = "Teste@123"
            atualizados = 0

            for usuario in usuarios:
                usuario_id = usuario['id']
                email = usuario['email']

                # Gerar hash compatível
                senha_hash = PasswordHasher.hash_password(senha_padrao)

                # Atualizar senha
                cursor.execute(
                    'UPDATE usuarios SET senha_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                    (senha_hash, usuario_id)
                )

                logger.info(f"✅ Usuário {email} resetado. Nova senha: {senha_padrao}")
                atualizados += 1

            logger.info(f"🎉 {atualizados} senhas resetadas com sucesso!")
            logger.info(f"📝 Use a senha: {senha_padrao} para todos os usuários")

            return True

    except Exception as e:
        logger.error(f"❌ Erro ao resetar senhas: {e}")
        return False

def mostrar_status_banco():
    """Mostra status detalhado do banco"""
    status = verificar_status_banco()

    print("\n" + "=" * 60)
    print("📊 STATUS DO BANCO DE DADOS")
    print("=" * 60)

    print(f"Caminho: {status['caminho']}")
    print(f"Existe: {'✅' if status['existe'] else '❌'}")

    if status['existe']:
        print(f"Tamanho: {status['tamanho'] / 1024:.2f} KB")
        print(f"Usuários: {status['usuarios']}")
        print(f"Empresas: {status['empresas']}")

        print("\n📋 Tabelas:")
        for tabela, count in status['tabelas'].items():
            print(f"  - {tabela}: {count} registros")

    if status.get('erro'):
        print(f"\n❌ Erro: {status['erro']}")

    print("=" * 60)

def backup_banco() -> Optional[str]:
    """Cria backup do banco de dados"""
    try:
        if not os.path.exists(DB_PATH):
            logger.error("Banco não encontrado para backup")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backup_{timestamp}_{os.path.basename(DB_PATH)}"

        import shutil
        shutil.copy2(DB_PATH, backup_path)

        logger.info(f"✅ Backup criado: {backup_path}")
        return backup_path

    except Exception as e:
        logger.error(f"Erro ao criar backup: {e}")
        return None

def otimizar_banco():
    """Otimiza o banco de dados (VACUUM)"""
    try:
        with get_db_connection() as conn:
            conn.execute("VACUUM")
            conn.execute("ANALYZE")
            logger.info("✅ Banco otimizado com sucesso")
            return True

    except Exception as e:
        logger.error(f"Erro ao otimizar banco: {e}")
        return False

# ============= FUNÇÕES DE MIGRAÇÃO =============
def adicionar_coluna_metadata_criptografado():
    """
    Adiciona a coluna metadata_criptografado à tabela historico_cotacoes
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(historico_cotacoes)")
            colunas = cursor.fetchall()
            colunas_nomes = [col[1] for col in colunas]

            if 'metadata_criptografado' not in colunas_nomes:
                cursor.execute('''
                ALTER TABLE historico_cotacoes 
                ADD COLUMN metadata_criptografado TEXT
                ''')
                logger.info("✅ Coluna 'metadata_criptografado' adicionada")
                conn.commit()
                return True
            else:
                logger.info("ℹ️ Coluna 'metadata_criptografado' já existe")
                return True

    except Exception as e:
        logger.error(f"❌ Erro ao adicionar coluna: {e}")
        return False

def reparar_tabela_historico():
    """Repara a tabela historico_cotacoes adicionando colunas faltantes"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='historico_cotacoes'")
            if not cursor.fetchone():
                logger.warning("Tabela historico_cotacoes não encontrada")
                return False

            cursor.execute("PRAGMA table_info(historico_cotacoes)")
            colunas = cursor.fetchall()
            colunas_nomes = [col[1] for col in colunas]

            colunas_necessarias = [
                ('passageiros', 'INTEGER DEFAULT 1'),
                ('bebes', 'INTEGER DEFAULT 0'),
                ('num_bagagens', 'INTEGER DEFAULT 0'),
                ('metadata', 'TEXT'),
                ('metadata_criptografado', 'TEXT'),
                ('empresa_id', 'INTEGER')
            ]

            for coluna, tipo in colunas_necessarias:
                if coluna not in colunas_nomes:
                    try:
                        cursor.execute(f'ALTER TABLE historico_cotacoes ADD COLUMN {coluna} {tipo}')
                        logger.info(f"✅ Coluna {coluna} adicionada")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao adicionar coluna {coluna}: {e}")

            conn.commit()
            return True

    except Exception as e:
        logger.error(f"❌ Erro ao reparar tabela: {e}")
        return False
# ============= FUNÇÕES DE COTAÇÃO (FALTANTES) =============

def criar_cotacao(usuario_id: int, nome: str, origem: str, destino: str) -> Tuple[bool, Any]:
    """Cria uma nova cotação com verificação de segurança"""
    try:
        from securitymax import SecurityManager
        
        nome = SecurityManager.sanitize_input(nome) if hasattr(SecurityManager, 'sanitize_input') else nome.strip()
        origem = SecurityManager.sanitize_input(origem) if hasattr(SecurityManager, 'sanitize_input') else origem.strip()
        destino = SecurityManager.sanitize_input(destino) if hasattr(SecurityManager, 'sanitize_input') else destino.strip()
        
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
        
        # Limite diário
        cursor.execute('SELECT COUNT(*) FROM cotacoes WHERE usuario_id = ? AND date(data_criacao) = date("now")', (usuario_id,))
        cotacoes_hoje = cursor.fetchone()[0]
        
        if cotacoes_hoje >= 50:
            conn.close()
            return False, "Limite diário de cotações atingido"
        
        # Buscar empresa_id do usuário
        cursor.execute('SELECT empresa_id FROM usuarios WHERE id = ?', (usuario_id,))
        usuario = cursor.fetchone()
        empresa_id = usuario['empresa_id'] if usuario else None
        
        cursor.execute('''
        INSERT INTO cotacoes (usuario_id, empresa_id, nome, origem, destino) 
        VALUES (?, ?, ?, ?, ?)
        ''', (usuario_id, empresa_id, nome.strip(), origem.strip(), destino.strip()))
        
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


def salvar_calculo(dados: Dict[str, Any]) -> Tuple[bool, str]:
    """Salva um cálculo no histórico"""
    try:
        if not dados.get("usuario_id"):
            return False, "Usuário não identificado"
            
        if not dados.get("cotacao_id"):
            return False, "Cotação não identificada"
        
        from securitymax import SecurityManager, data_crypto
        
        companhia = SecurityManager.sanitize_input(dados.get("companhia", "")) if hasattr(SecurityManager, 'sanitize_input') else dados.get("companhia", "")
        tipo_calculo = SecurityManager.sanitize_input(dados.get("tipo_calculo", "")) if hasattr(SecurityManager, 'sanitize_input') else dados.get("tipo_calculo", "")
        moeda = SecurityManager.sanitize_input(dados.get("moeda", "BRL")) if hasattr(SecurityManager, 'sanitize_input') else dados.get("moeda", "BRL")
        
        conn = criar_conexao()
        cursor = conn.cursor()
        
        # Verificar usuário e pegar empresa_id
        cursor.execute('SELECT id, empresa_id, nome, email FROM usuarios WHERE id = ?', (dados['usuario_id'],))
        usuario = cursor.fetchone()
        if not usuario:
            conn.close()
            return False, "Usuário não encontrado"
        
        usuario_nome = usuario['nome']
        usuario_email = usuario['email']
        empresa_id = usuario['empresa_id']
        
        # Verificar cotação
        cursor.execute('SELECT id FROM cotacoes WHERE id = ? AND usuario_id = ?', 
                      (dados['cotacao_id'], dados['usuario_id']))
        if not cursor.fetchone():
            conn.close()
            return False, "Cotação não encontrada ou acesso negado"
        
        # Preparar metadata
        metadata = {
            "passageiros": dados.get("passageiros", 1),
            "bebes": dados.get("bebes", 0),
            "num_bagagens": dados.get("num_bagagens", 0),
            "valor_bagagem_unitaria": dados.get("valor_bagagem_unitaria", 0),
            "timestamp": datetime.now().isoformat()
        }
        
        metadata = {k: v for k, v in metadata.items() if v not in (None, '', 0)}
        metadata_json = json.dumps(metadata, ensure_ascii=False, default=str)
        
        # Criptografar metadata se possível
        metadata_criptografado = None
        if data_crypto and hasattr(data_crypto, 'encrypt'):
            try:
                metadata_criptografado = data_crypto.encrypt(metadata_json)
            except:
                metadata_criptografado = None
        
        # Inserir no banco
        cursor.execute('''
        INSERT INTO historico_cotacoes 
        (usuario_id, cotacao_id, empresa_id, companhia, tipo_calculo, 
         milhas_total, valor_milheiro, taxa_embarque, valor_base, 
         valor_bagagens, desagio_percentual, total_geral, moeda, 
         passageiros, bebes, num_bagagens, metadata, metadata_criptografado,
         usuario_nome, usuario_email)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            dados["usuario_id"], dados["cotacao_id"], empresa_id, companhia, tipo_calculo,
            dados.get("milhas_total", 0), dados.get("valor_milheiro", 0),
            dados.get("taxa_embarque", 0), dados.get("valor_base", 0),
            dados.get("valor_bagagens", 0), dados.get("desagio_percentual", 0),
            dados["total_geral"], moeda, dados.get("passageiros", 1),
            dados.get("bebes", 0), dados.get("num_bagagens", 0),
            metadata_json, metadata_criptografado, usuario_nome, usuario_email
        ))
        
        historico_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Cálculo {historico_id} salvo com sucesso")
        return True, "Cálculo salvo com sucesso!"
            
    except Exception as e:
        logger.error(f"Erro ao salvar cálculo: {e}")
        if 'conn' in locals():
            conn.close()
        return False, f"Erro interno: {str(e)[:100]}"


def atualizar_preferencias_usuario(usuario_id: int, tema: Optional[str] = None, 
                                   moeda: Optional[str] = None, **kwargs) -> bool:
    """Atualiza preferências do usuário (alias para salvar_preferencias_usuario)"""
    return salvar_preferencias_usuario(usuario_id, tema=tema, moeda=moeda, **kwargs)


def atualizar_perfil_usuario(usuario_id: int, dados: Dict[str, Any]) -> Tuple[bool, str]:
    """Atualiza perfil do usuário (nome, telefone, cargo, foto)"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        campos_permitidos = ['nome', 'telefone', 'cargo', 'foto_perfil']
        
        for campo in campos_permitidos:
            if campo in dados and dados[campo] is not None:
                updates.append(f"{campo} = ?")
                params.append(dados[campo])
        
        if not updates:
            conn.close()
            return False, "Nenhum dado para atualizar"
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(usuario_id)
        
        query = f"UPDATE usuarios SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Perfil do usuário {usuario_id} atualizado")
        return True, "Perfil atualizado com sucesso!"
        
    except Exception as e:
        logger.error(f"Erro ao atualizar perfil: {e}")
        return False, f"Erro: {str(e)}"


def redefinir_senha(email: str, nova_senha: str) -> Tuple[bool, str]:
    """Redefine senha (wrapper para compatibilidade com app.py)"""
    try:
        from securitymax import SecurityManager
        
        # Validar força da senha
        if hasattr(SecurityManager, 'validate_password_strength'):
            validacao = SecurityManager.validate_password_strength(nova_senha)
            if not validacao.get('valid', False):
                return False, "Senha muito fraca"
        
        if len(nova_senha) < 8:
            return False, "Senha deve ter pelo menos 8 caracteres"
        
        with get_db_cursor() as cursor:
            cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
            usuario = cursor.fetchone()
            
            if not usuario:
                return False, "Usuário não encontrado"
            
            novo_hash = PasswordHasher.hash_password(nova_senha)
            
            cursor.execute('''
                UPDATE usuarios 
                SET senha_hash = ?,
                    sessao_token = ?,
                    csrf_token = ?,
                    data_ultima_alteracao = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE email = ?
            ''', (
                novo_hash,
                secrets.token_urlsafe(32),
                secrets.token_urlsafe(32),
                email
            ))
            
            logger.info(f"✅ Senha redefinida para {email}")
            return True, "Senha redefinida com sucesso!"
            
    except Exception as e:
        logger.error(f"Erro ao redefinir senha: {e}")
        return False, f"Erro: {str(e)}"


def get_currency_symbol(moeda: str) -> str:
    """Retorna o símbolo da moeda"""
    simbolos = {
        'BRL': 'R$',
        'USD': '$',
        'EUR': '€',
        'GBP': '£'
    }
    return simbolos.get(moeda, 'R$')


# Adicionar ao __all__
__all__ = [
    # ... (itens existentes) ...
    'criar_cotacao',
    'salvar_calculo',
    'atualizar_preferencias_usuario',
    'atualizar_perfil_usuario',
    'redefinir_senha',
    'get_currency_symbol'
]
def migrar_metadata_para_criptografado():
    """
    Migra dados existentes da coluna metadata para metadata_criptografado
    """
    try:
        from securitymax import data_crypto

        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, metadata FROM historico_cotacoes 
                WHERE metadata IS NOT NULL AND metadata != '' 
                AND (metadata_criptografado IS NULL OR metadata_criptografado = '')
            ''')

            registros = cursor.fetchall()
            migrados = 0

            for row in registros:
                hist_id = row['id']
                metadata = row['metadata']

                try:
                    if isinstance(metadata, str):
                        json.loads(metadata)
                    elif isinstance(metadata, dict):
                        metadata = json.dumps(metadata)

                    metadata_criptografado = data_crypto.encrypt(metadata)

                    cursor.execute('''
                        UPDATE historico_cotacoes 
                        SET metadata_criptografado = ? 
                        WHERE id = ?
                    ''', (metadata_criptografado, hist_id))

                    migrados += 1

                except Exception as e:
                    logger.error(f"Erro ao migrar registro {hist_id}: {e}")

            conn.commit()
            logger.info(f"✅ Migrados {migrados} registros para metadata_criptografado")
            return migrados

    except Exception as e:
        logger.error(f"❌ Erro na migração: {e}")
        return 0

# ============= EXPORTAÇÕES =============
__all__ = [
    'criar_conexao',
    'get_db_connection',
    'get_db_cursor',
    'inicializar_banco',
    'verificar_status_banco',
    'carregar_preferencias_usuario',
    'salvar_preferencias_usuario',
    'alterar_senha',
    'obter_dados_usuario',
    'atualizar_nome_usuario',
    'obter_estatisticas_usuario',
    'registrar_ultimo_login',
    'registrar_evento_seguranca',
    'obter_logs_seguranca',
    'registrar_usuario_simples',
    'gerar_token_recuperacao',
    'validar_token_recuperacao',
    'marcar_token_como_usado',
    'redefinir_senha_com_token',
    'verificar_login_simplificado',
    'listar_historico',
    'excluir_calculo',
    'obter_usuario_2fa_status',
    'ativar_2fa_usuario',
    'desativar_2fa_usuario',
    'obter_segredo_2fa',
    'verificar_backup_code',
    'salvar_preferencias_tema',
    'get_temas_personalizados',
    'reset_all_passwords_to_compatible_hash',
    'mostrar_status_banco',
    'backup_banco',
    'otimizar_banco',
    'adicionar_coluna_metadata_criptografado',
    'reparar_tabela_historico',
    'migrar_metadata_para_criptografado',
    'PasswordHasher',
    'login_manager',
    'hash_password_simple',
    'verify_password_simple',
    'hash_password_compativel',
    'verify_password_compativel',
    # Novas funções de empresa
    'criar_empresa',
    'get_empresa',
    'atualizar_empresa',
    'get_usuarios_empresa',
    'atualizar_nivel_acesso',
    'convidar_membro',
    'aceitar_convite'
]

# ============= TESTE DO MÓDULO =============
if __name__ == "__main__":
    """Teste do módulo database"""

    print("\n" + "=" * 60)
    print("🧪 TESTANDO MÓDULO DATABASE")
    print("=" * 60)

    try:
        # 1. Testar conexão
        print("\n1. Testando conexão...")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            print("✅ Conexão OK")

        # 2. Inicializar banco
        print("\n2. Inicializando banco...")
        inicializar_banco()
        print("✅ Banco inicializado")

        # 3. Testar verificar_status_banco
        print("\n3. Testando verificar_status_banco...")
        status = verificar_status_banco()
        print(f"✅ Banco existe: {status['existe']}")
        print(f"✅ Tabelas: {len(status['tabelas'])}")
        print(f"✅ Usuários: {status['usuarios']}")
        print(f"✅ Empresas: {status['empresas']}")

        # 4. Executar migrações
        print("\n4. Executando migrações...")
        adicionar_coluna_metadata_criptografado()
        reparar_tabela_historico()
        print("✅ Migrações executadas")

        # 5. Testar sistema de hash
        print("\n5. Testando sistema de hash...")
        senha_teste = "Teste@123"
        hash_bcrypt = PasswordHasher.hash_password(senha_teste)
        print(f"✅ Hash bcrypt: {hash_bcrypt[:50]}...")
        assert PasswordHasher.verify_password(senha_teste, hash_bcrypt), "Falha na verificação bcrypt"
        print("✅ Verificação bcrypt OK")

        # 6. Testar login
        print("\n6. Testando login...")
        sucesso, resultado = verificar_login_simplificado('admin@dbmilesx.com', 'Admin@DBMILESX123!')
        if sucesso:
            print(f"✅ Login admin OK - ID: {resultado['usuario_id']}")
        else:
            print(f"❌ Login admin falhou: {resultado}")

        # 7. Mostrar status
        print("\n7. Status do banco:")
        mostrar_status_banco()

        print("\n" + "=" * 60)
        print("✅ Módulo database testado com sucesso!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()

