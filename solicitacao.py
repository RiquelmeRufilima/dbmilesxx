# ============= SOLICITACOES.PY - VERSÃO COMPLETA E CORRIGIDA =============
# Módulo de Solicitações de Cotação - Apenas formulário público em modo claro

import streamlit as st
import time
import json
import secrets
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any, Optional
import sqlite3
import base64
from PIL import Image
import os

logger = logging.getLogger(__name__)

# ============= CORES FIXAS PARA MODO CLARO =============
CORES_CLARO = {
    'fundo': '#ffffff',
    'card': '#ffffff',
    'texto': '#000000',
    'destaque': '#3d8bfd',
    'borda': '#dee2e6',
    'hover': '#f8f9fa',
    'success': '#28a745',
    'warning': '#ffc107',
    'error': '#dc3545',
    'info': '#17a2b8',
    'botao_primary_gradient': 'linear-gradient(135deg, #3d8bfd, #2a5cbd)',
    'placeholder': '#969696',
    'texto_label': '#212529'
}


def get_cores_claro():
    """Retorna as cores fixas para modo claro"""
    return CORES_CLARO


def get_base_url():
    """Obtém a URL base do sistema"""
    try:
        if hasattr(st, 'secrets'):
            app_url = st.secrets.get("email", {}).get("APP_URL", "dbmilesx.streamlit.app")
        else:
            app_url = "dbmilesx.streamlit.app"
        
        if os.getenv('STREAMLIT_CLOUD'):
            return f"https://{app_url}"
        else:
            return "http://localhost:8501"
    except:
        return "http://localhost:8501"


def imagem_para_base64(uploaded_file) -> Optional[Dict]:
    """Converte uma imagem para base64 e retorna os dados"""
    try:
        file_bytes = uploaded_file.getvalue()
        imagem_base64 = base64.b64encode(file_bytes).decode('utf-8')
        
        return {
            "base64": imagem_base64,
            "nome": uploaded_file.name,
            "tipo": uploaded_file.type,
            "tamanho": len(file_bytes)
        }
    except Exception as e:
        logger.error(f"Erro ao converter imagem: {e}")
        return None


def carregar_dados_empresa_usuario(usuario_id: int) -> Optional[Dict]:
    """Carrega os dados da empresa do usuário logado"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, nome, cnpj, logo_base64, cor_primaria, site, telefone, email_contato
        FROM empresas WHERE usuario_id = ?
        ''', (usuario_id,))
        
        empresa = cursor.fetchone()
        conn.close()
        
        if empresa:
            return {
                'id': empresa['id'],
                'nome': empresa['nome'],
                'cnpj': empresa['cnpj'],
                'logo_base64': empresa['logo_base64'],
                'cor_primaria': empresa['cor_primaria'],
                'site': empresa['site'],
                'telefone': empresa['telefone'],
                'email_contato': empresa['email_contato']
            }
        return None
        
    except Exception as e:
        logger.error(f"Erro ao carregar empresa do usuário: {e}")
        return None


def registrar_notificacao_app(usuario_id: int, titulo: str, mensagem: str, dados: Dict = None):
    """Registra uma notificação no app para o usuário"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS notificacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            dados_json TEXT,
            lida INTEGER DEFAULT 0,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        dados_json = json.dumps(dados, ensure_ascii=False) if dados else None
        
        cursor.execute('''
        INSERT INTO notificacoes (usuario_id, titulo, mensagem, dados_json)
        VALUES (?, ?, ?, ?)
        ''', (usuario_id, titulo, mensagem, dados_json))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Notificação registrada para usuário {usuario_id}: {titulo}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao registrar notificação: {e}")
        return False


def contar_notificacoes_nao_lidas(usuario_id: int) -> int:
    """Conta notificações não lidas do usuário"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT COUNT(*) FROM notificacoes 
        WHERE usuario_id = ? AND lida = 0
        ''', (usuario_id,))
        
        count = cursor.fetchone()[0]
        conn.close()
        return count
        
    except Exception as e:
        logger.error(f"Erro ao contar notificações: {e}")
        return 0


def criar_conexao():
    """Cria conexão com o banco de dados SQLite"""
    import tempfile
    
    if os.getenv('STREAMLIT_CLOUD') or os.getenv('CLOUDFLARE'):
        db_path = os.path.join(tempfile.gettempdir(), 'sistema_aereo_secure.db')
    else:
        db_path = 'sistema_aereo_secure.db'
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_tabelas_solicitacoes():
    """Inicializa as tabelas necessárias para o sistema de solicitações"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='links_publicos'")
        if not cursor.fetchone():
            cursor.execute('''
            CREATE TABLE links_publicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                nome_campanha TEXT NOT NULL,
                empresas_data TEXT NOT NULL DEFAULT '[]',
                dias_validade INTEGER NOT NULL DEFAULT 30,
                limite_uso INTEGER NOT NULL DEFAULT 100,
                usos_restantes INTEGER NOT NULL DEFAULT 100,
                total_usos INTEGER DEFAULT 0,
                data_expiracao TIMESTAMP NOT NULL,
                usuario_criador_id INTEGER NOT NULL,
                email_criador TEXT NOT NULL DEFAULT 'sistema@dbmilesx.com',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_criador_id) REFERENCES usuarios (id)
            )
            ''')
            logger.info("Tabela links_publicos criada")
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS solicitacoes_cotacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dados_solicitacao TEXT NOT NULL,
            status TEXT DEFAULT 'RECEBIDA',
            link_id INTEGER,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (link_id) REFERENCES links_publicos (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS notificacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            dados_json TEXT,
            lida INTEGER DEFAULT 0,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_links_token ON links_publicos(token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_links_usuario ON links_publicos(usuario_criador_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_solicitacoes_link ON solicitacoes_cotacao(link_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_notificacoes_usuario ON notificacoes(usuario_id)')
        
        conn.commit()
        conn.close()
        logger.info("Tabelas inicializadas")
        
    except Exception as e:
        logger.error(f"Erro ao inicializar tabelas: {e}")


def enviar_notificacao_criador(link_data: Dict, dados_solicitacao: Dict):
    """Envia notificação para o criador do link sobre nova solicitação"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, email, nome FROM usuarios WHERE id = ?', 
                      (link_data['usuario_criador_id'],))
        usuario = cursor.fetchone()
        
        if usuario:
            usuario_id, email, nome = usuario
            
            titulo = f"📨 Nova Solicitação - {link_data['nome_campanha']}"
            mensagem = f"{dados_solicitacao.get('nome_cliente')} solicitou cotação de {dados_solicitacao.get('origem')} → {dados_solicitacao.get('destino')}"
            
            registrar_notificacao_app(
                usuario_id,
                titulo,
                mensagem,
                {
                    'solicitacao_id': dados_solicitacao.get('solicitacao_id'),
                    'cliente': dados_solicitacao.get('nome_cliente'),
                    'celular': dados_solicitacao.get('celular'),
                    'email': dados_solicitacao.get('email'),
                    'origem': dados_solicitacao.get('origem'),
                    'destino': dados_solicitacao.get('destino'),
                    'link_campanha': link_data['nome_campanha']
                }
            )
            
            logger.info(f"📨 NOTIFICAÇÃO: Nova solicitação para {nome}")
            return True
        
        conn.close()
        return False
        
    except Exception as e:
        logger.error(f"Erro ao enviar notificação: {e}")
        return False


def exibir_notificacoes_sidebar():
    """Exibe notificações na barra lateral"""
    if not st.session_state.get('logado'):
        return
    
    usuario_id = st.session_state.usuario_id
    notificacoes_nao_lidas = contar_notificacoes_nao_lidas(usuario_id)
    
    with st.expander(f"🔔 Notificações ({notificacoes_nao_lidas})", expanded=False):
        try:
            conn = criar_conexao()
            cursor = conn.cursor()
            cursor.execute('''
            SELECT id, titulo, mensagem, dados_json, lida, data_criacao
            FROM notificacoes WHERE usuario_id = ? ORDER BY data_criacao DESC LIMIT 10
            ''', (usuario_id,))
            
            notificacoes = cursor.fetchall()
            conn.close()
            
            if not notificacoes:
                st.info("📭 Nenhuma notificação")
            else:
                for notif in notificacoes:
                    icone = "🆕" if not notif['lida'] else "📌"
                    st.markdown(f"""
                    <div style='background: #e8f5e9; border-left: 4px solid #28a745; padding: 10px; margin: 5px 0; border-radius: 5px;'>
                        <b>{icone} {notif['titulo']}</b><br>
                        <small>{notif['mensagem']}</small><br>
                        <small>{notif['data_criacao'][:16]}</small>
                    </div>
                    """, unsafe_allow_html=True)
        except Exception as e:
            logger.error(f"Erro ao exibir notificações: {e}")


# ============= PÁGINA DE GERAR LINK =============

def pagina_gerar_link():
    """Página para gerar links públicos - segue tema do sistema"""
    st.title("🔗 Gerar Link de Solicitação")
    
    col_btn_voltar, col_btn_solic = st.columns(2)
    with col_btn_voltar:
        if st.button("🏠 Início", type="secondary", use_container_width=True):
            st.session_state.pagina = 'inicio'
            st.rerun()
    with col_btn_solic:
        if st.button("📨 Ver Solicitações", type="secondary", use_container_width=True):
            st.session_state.pagina = 'solicitacoes'
            st.rerun()
    
    with st.form("form_gerar_link"):
        nome_campanha = st.text_input(
            "**Nome da Campanha/Origem ***",
            placeholder="Ex: Promoção Verão 2024, Cliente João Silva, etc."
        )
        
        email_criador = st.text_input(
            "**Seu Email para Receber Solicitações ***",
            value=st.session_state.get('usuario_email', ''),
            placeholder="seu@email.com"
        )
        
        st.markdown("### 🏢 Adicionar Empresas")
        st.info("Adicione as empresas que aparecerão no formulário para o cliente")
        
        if 'empresas_temp' not in st.session_state:
            st.session_state.empresas_temp = []
        
        num_empresas = st.number_input(
            "**Quantidade de empresas**",
            min_value=1,
            max_value=10,
            value=max(1, len(st.session_state.empresas_temp))
        )
        
        while len(st.session_state.empresas_temp) < num_empresas:
            st.session_state.empresas_temp.append({"nome": f"Empresa {len(st.session_state.empresas_temp) + 1}", "logo": None})
        
        while len(st.session_state.empresas_temp) > num_empresas:
            st.session_state.empresas_temp.pop()
        
        for i, empresa in enumerate(st.session_state.empresas_temp):
            st.markdown(f"---")
            st.markdown(f"#### 🏢 Empresa {i+1}")
            
            col_nome, col_logo = st.columns([2, 1])
            
            with col_nome:
                nome_empresa = st.text_input(
                    f"**Nome da Empresa {i+1}**",
                    value=empresa['nome'],
                    placeholder=f"Ex: LATAM, GOL, ou sua agência",
                    key=f"emp_nome_{i}"
                )
                st.session_state.empresas_temp[i]['nome'] = nome_empresa
            
            with col_logo:
                uploaded_file = st.file_uploader(
                    f"Logo da Empresa {i+1}",
                    type=['png', 'jpg', 'jpeg', 'gif'],
                    key=f"emp_logo_{i}"
                )
                
                if uploaded_file:
                    logo_data = imagem_para_base64(uploaded_file)
                    if logo_data:
                        st.session_state.empresas_temp[i]['logo'] = logo_data
                        st.image(uploaded_file, width=80)
                else:
                    st.session_state.empresas_temp[i]['logo'] = None
                    st.info("Sem logo")
        
        st.markdown("### ⚙️ Configurações do Link")
        
        col_val1, col_val2 = st.columns(2)
        
        with col_val1:
            dias_validade = st.number_input("**Dias de validade**", min_value=1, max_value=365, value=30)
        
        with col_val2:
            limite_uso = st.number_input("**Limite de usos**", min_value=1, max_value=1000, value=100)
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            gerar = st.form_submit_button("🔗 Gerar Link Público", type="primary", use_container_width=True)
    
    if gerar:
        if not nome_campanha:
            st.error("❌ Dê um nome à campanha/origem!")
        elif not email_criador or '@' not in email_criador:
            st.error("❌ Informe um email válido!")
        elif not st.session_state.empresas_temp:
            st.error("❌ Adicione pelo menos uma empresa!")
        else:
            with st.spinner("🔗 Gerando link..."):
                token = secrets.token_urlsafe(32)
                data_expiracao = datetime.now() + timedelta(days=dias_validade)
                
                empresas_data = []
                for empresa in st.session_state.empresas_temp:
                    empresas_data.append({
                        "nome": empresa['nome'],
                        "logo": empresa['logo']
                    })
                
                try:
                    conn = criar_conexao()
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                    INSERT INTO links_publicos 
                    (token, nome_campanha, empresas_data, dias_validade, 
                     limite_uso, usos_restantes, data_expiracao, usuario_criador_id, email_criador)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        token,
                        nome_campanha,
                        json.dumps(empresas_data, ensure_ascii=False),
                        dias_validade,
                        limite_uso,
                        limite_uso,
                        data_expiracao.isoformat(),
                        st.session_state.usuario_id,
                        email_criador
                    ))
                    
                    conn.commit()
                    conn.close()
                    
                    base_url = get_base_url()
                    link_publico = f"{base_url}/?token={token}&form=cotacao"
                    
                    st.success("✅ Link gerado com sucesso!")
                    
                    st.markdown("---")
                    st.markdown(f"""
                    <div style='background: #e3f2fd; padding: 1.5rem; border-radius: 10px; border: 2px solid #3d8bfd;'>
                        <h3 style='color: #3d8bfd; margin-top: 0;'>🔗 Link Público Gerado</h3>
                        <div style='background: white; padding: 1rem; border-radius: 5px; margin: 1rem 0;'>
                            <code style='font-size: 1rem; word-break: break-all;'>{link_publico}</code>
                        </div>
                        <p><strong>📝 Nome:</strong> {nome_campanha}</p>
                        <p><strong>📧 Email:</strong> {email_criador}</p>
                        <p><strong>🏢 Empresas:</strong> {len(empresas_data)} empresas</p>
                        <p><strong>📅 Validade:</strong> {data_expiracao.strftime('%d/%m/%Y')}</p>
                        <p><strong>🔢 Usos restantes:</strong> {limite_uso}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.code(link_publico, language="text")
                    
                    if 'empresas_temp' in st.session_state:
                        del st.session_state.empresas_temp
                    
                except Exception as e:
                    st.error(f"❌ Erro ao gerar link: {str(e)}")


# ============= PÁGINA DE SOLICITAÇÕES RECEBIDAS =============

def pagina_minhas_solicitacoes():
    """Página para ver solicitações recebidas - segue tema do sistema"""
    st.title("📨 Minhas Solicitações Recebidas")
    
    col_btn_voltar, col_btn_links = st.columns(2)
    with col_btn_voltar:
        if st.button("🏠 Início", type="secondary", use_container_width=True):
            st.session_state.pagina = 'inicio'
            st.rerun()
    with col_btn_links:
        if st.button("🔗 Meus Links", type="secondary", use_container_width=True):
            st.session_state.pagina = 'meus_links'
            st.rerun()
    
    notif_count = contar_notificacoes_nao_lidas(st.session_state.usuario_id)
    if notif_count > 0:
        st.info(f"🔔 Você tem {notif_count} nova(s) notificação(ões)!")
    
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT l.id, l.nome_campanha, COUNT(s.id) as total_solicitacoes
        FROM links_publicos l
        LEFT JOIN solicitacoes_cotacao s ON s.link_id = l.id
        WHERE l.usuario_criador_id = ?
        GROUP BY l.id
        ORDER BY l.data_criacao DESC
        ''', (st.session_state.usuario_id,))
        
        meus_links = cursor.fetchall()
        
        if not meus_links:
            st.info("🔗 Você ainda não criou nenhum link.")
            return
        
        total_links = len(meus_links)
        total_solicitacoes = sum(link['total_solicitacoes'] for link in meus_links)
        
        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            st.metric("📊 Meus Links", total_links)
        with col_stat2:
            st.metric("📨 Total de Solicitações", total_solicitacoes)
        
        for link in meus_links:
            link_id = link['id']
            nome_campanha = link['nome_campanha']
            total_sol = link['total_solicitacoes']
            
            with st.expander(f"🔗 {nome_campanha} - {total_sol} solicitações", expanded=True):
                cursor.execute('''
                SELECT id, dados_solicitacao, status, data_criacao
                FROM solicitacoes_cotacao
                WHERE link_id = ?
                ORDER BY data_criacao DESC
                ''', (link_id,))
                
                for sol in cursor.fetchall():
                    sol_id = sol['id']
                    dados = json.loads(sol['dados_solicitacao'])
                    status = sol['status']
                    data_criacao = sol['data_criacao']
                    
                    st.markdown(f"""
                    <div style='border: 1px solid #ddd; border-radius: 10px; padding: 15px; margin: 15px 0;'>
                        <div style='display: flex; justify-content: space-between; flex-wrap: wrap;'>
                            <div>
                                <h4>👤 {dados.get('nome_cliente', 'Cliente')}</h4>
                                <p>📞 {dados.get('celular', 'N/A')} | 📧 {dados.get('email', 'N/A')}</p>
                                <p>✈️ {dados.get('origem', 'N/A')} → {dados.get('destino', 'N/A')}</p>
                                <p>📅 {dados.get('data_ida', 'N/A')} → {dados.get('data_volta', 'N/A')}</p>
                            </div>
                            <div>
                                <span style='background: #28a74520; color: #28a745; padding: 4px 8px; border-radius: 4px;'>{status}</span>
                                <p><small>📅 {data_criacao[:10]}</small></p>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"📊 Criar Cotação", key=f"cotacao_{sol_id}", use_container_width=True, type="primary"):
                        st.session_state.solicitacao_para_cotacao = dados
                        st.session_state.pagina = 'nova_cotacao'
                        st.success("📊 Preparando para criar cotação...")
                        time.sleep(1)
                        st.rerun()
        
        conn.close()
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar solicitações: {str(e)}")


# ============= PÁGINA DE MEUS LINKS =============

def pagina_meus_links():
    """Página para ver links já gerados - segue tema do sistema"""
    st.title("📋 Meus Links Gerados")
    
    col_btn_voltar, col_btn_novo = st.columns(2)
    with col_btn_voltar:
        if st.button("🏠 Início", type="secondary", use_container_width=True):
            st.session_state.pagina = 'inicio'
            st.rerun()
    with col_btn_novo:
        if st.button("🆕 Novo Link", type="primary", use_container_width=True):
            st.session_state.pagina = 'gerar_link'
            st.rerun()
    
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, token, nome_campanha, empresas_data, limite_uso, 
               usos_restantes, total_usos, data_expiracao, data_criacao, email_criador
        FROM links_publicos 
        WHERE usuario_criador_id = ?
        ORDER BY data_criacao DESC
        ''', (st.session_state.usuario_id,))
        
        links = cursor.fetchall()
        conn.close()
        
        if not links:
            st.info("🔗 Você ainda não criou nenhum link.")
            return
        
        st.success(f"✅ **{len(links)}** links criados")
        
        for link in links:
            link_id = link['id']
            token = link['token']
            nome_campanha = link['nome_campanha']
            limite_uso = link['limite_uso']
            usos_restantes = link['usos_restantes']
            total_usos = link['total_usos'] or 0
            data_criacao = link['data_criacao']
            email_criador = link['email_criador']
            
            base_url = get_base_url()
            link_url = f"{base_url}/?token={token}&form=cotacao"
            
            st.markdown(f"""
            <div style='border: 1px solid #ddd; border-radius: 10px; padding: 15px; margin: 15px 0;'>
                <h4>{nome_campanha}</h4>
                <p><strong>🔗 Link:</strong> <code>{link_url[:80]}...</code></p>
                <p><strong>📧 Email:</strong> {email_criador}</p>
                <p><strong>📊 Usos:</strong> {total_usos}/{limite_uso} ({usos_restantes} restantes)</p>
                <p><strong>📅 Criação:</strong> {data_criacao[:10]}</p>
            </div>
            """, unsafe_allow_html=True)
            
            col_copy, col_delete = st.columns(2)
            
            with col_copy:
                if st.button("📋 Copiar Link", key=f"copy_{link_id}", use_container_width=True):
                    st.code(link_url, language="text")
                    st.success("Link copiado!")
            
            with col_delete:
                if st.button("🗑️ Excluir", key=f"delete_{link_id}", use_container_width=True):
                    confirm = st.checkbox(f"Confirmar exclusão?", key=f"confirm_{link_id}")
                    if confirm:
                        conn2 = criar_conexao()
                        cursor2 = conn2.cursor()
                        cursor2.execute('DELETE FROM links_publicos WHERE id = ?', (link_id,))
                        conn2.commit()
                        conn2.close()
                        st.success("✅ Link excluído!")
                        time.sleep(1)
                        st.rerun()
            
            st.markdown("---")
                
    except Exception as e:
        st.error(f"❌ Erro ao carregar links: {str(e)}")


def formulario_publico_cotacao(token: str):
    """Formulário público - Segue o tema do sistema (claro/escuro)"""
    
    # Função local para obter cores do tema
    def get_tema_cores():
        tema = st.session_state.get("tema", "escuro")
        if tema == "claro":
            return {
                'fundo': '#ffffff',
                'card': '#ffffff',
                'texto': '#212529',
                'destaque': '#3d8bfd',
                'destaque_hover': '#2a5cbd',
                'borda': '#dee2e6',
                'success': '#28a745',
                'error': '#dc3545',
                'warning': '#ffc107',
                'info': '#17a2b8'
            }
        else:
            return {
                'fundo': '#0e0e0e',
                'card': '#1e1e1e',
                'texto': '#f0f0f0',
                'destaque': '#3d8bfd',
                'destaque_hover': '#2a5cbd',
                'borda': '#333333',
                'success': '#4CAF50',
                'error': '#f44336',
                'warning': '#ff9800',
                'info': '#2196F3'
            }
    
    # Verificar link
    with st.spinner("🔍 Verificando link..."):
        try:
            conn = criar_conexao()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, nome_campanha, empresas_data, usos_restantes, data_expiracao, 
                   usuario_criador_id, email_criador
            FROM links_publicos 
            WHERE token = ? AND usos_restantes > 0 AND data_expiracao > CURRENT_TIMESTAMP
            ''', (token,))
            
            link_data = cursor.fetchone()
            
            if not link_data:
                st.error("❌ Link inválido, expirado ou já utilizado!")
                return
            
            link_id = link_data['id']
            nome_campanha = link_data['nome_campanha']
            empresas_json = link_data['empresas_data']
            usuario_criador_id = link_data['usuario_criador_id']
            email_criador = link_data['email_criador']
            
            empresas_data = json.loads(empresas_json)
            
            if not empresas_data:
                st.error("❌ Nenhuma empresa configurada!")
                return
                
        except Exception as e:
            st.error(f"❌ Erro: {str(e)}")
            return
    
    empresa_principal = empresas_data[0]
    empresas_adicionais = empresas_data[1:] if len(empresas_data) > 1 else []
    
    # Cores do tema atual
    cores = get_tema_cores()
    
    # Header
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: {cores['destaque']};">✈️ {empresa_principal['nome']}</h1>
        <p style="color: {cores['texto']};">Preencha os dados abaixo para receber uma cotação personalizada</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Card da empresa principal (usando tema)
    if empresa_principal.get('logo') and isinstance(empresa_principal['logo'], dict) and empresa_principal['logo'].get('base64'):
        st.markdown(f'''
        <div style="background: linear-gradient(135deg, {cores['destaque']}, {cores['destaque_hover']}); border-radius: 12px; padding: 20px; margin: 20px 0; display: flex; align-items: center; gap: 20px;">
            <div style="width: 60px; height: 60px; background: white; border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                <img src="data:{empresa_principal['logo'].get('tipo', 'image/png')};base64,{empresa_principal['logo']['base64']}" 
                     style="width:50px;height:50px;object-fit:contain;">
            </div>
            <div>
                <h2 style="color: white; margin: 0;">{empresa_principal['nome']}</h2>
                <p style="color: rgba(255,255,255,0.9); margin: 0;">Solicitação de Orçamento</p>
            </div>
        </div>
        ''', unsafe_allow_html=True)
    else:
        st.markdown(f'''
        <div style="background: linear-gradient(135deg, {cores['destaque']}, {cores['destaque_hover']}); border-radius: 12px; padding: 20px; margin: 20px 0; display: flex; align-items: center; gap: 20px;">
            <div style="width: 60px; height: 60px; background: white; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 30px;">✈️</div>
            <div>
                <h2 style="color: white; margin: 0;">{empresa_principal['nome']}</h2>
                <p style="color: rgba(255,255,255,0.9); margin: 0;">Solicitação de Orçamento</p>
            </div>
        </div>
        ''', unsafe_allow_html=True)
    
    # Empresas adicionais
    if empresas_adicionais:
        with st.expander(f"🏢 +{len(empresas_adicionais)} empresas parceiras", expanded=False):
            for empresa in empresas_adicionais:
                st.markdown(f"**✈️ {empresa['nome']}**")
    
    # Info segurança
    st.info(f"🔒 Seus dados são protegidos e serão enviados apenas para {empresa_principal['nome']}")
    
    # Formulário
    with st.form("form_cotacao"):
        st.markdown("### 👤 Seus Dados")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            nome = st.text_input("Nome Completo *", placeholder="Digite seu nome")
        with col2:
            celular = st.text_input("Celular/WhatsApp *", placeholder="(11) 99999-9999")
        with col3:
            email = st.text_input("E-mail *", placeholder="seu@email.com")
        
        st.markdown("### ✈️ Dados da Viagem")
        
        col4, col5 = st.columns(2)
        with col4:
            origem = st.text_input("Origem *", placeholder="Cidade de partida")
        with col5:
            destino = st.text_input("Destino *", placeholder="Cidade de destino")
        
        col6, col7 = st.columns(2)
        with col6:
            data_ida = st.date_input("Data de Ida *", format="DD/MM/YYYY")
        with col7:
            data_volta = st.date_input("Data de Volta", format="DD/MM/YYYY")
        
        flexibilidade = st.checkbox("Tenho flexibilidade nas datas (±3 dias)")
        
        st.markdown("### 👥 Passageiros")
        
        col8, col9, col10 = st.columns(3)
        with col8:
            adultos = st.number_input("Adultos", min_value=1, value=1)
        with col9:
            criancas = st.number_input("Crianças (2-11 anos)", min_value=0, value=0)
        with col10:
            bebes = st.number_input("Bebês (até 2 anos)", min_value=0, value=0)
        
        st.markdown("### 🧳 Bagagens")
        bagagens = st.number_input("Número de bagagens despachadas", min_value=0, value=0, step=1)
        
        st.markdown("### 🛎️ Serviços Adicionais")
        
        col11, col12, col13, col14 = st.columns(4)
        with col11:
            hospedagem = st.checkbox("🏨 Hospedagem")
        with col12:
            transporte = st.checkbox("🚗 Transporte")
        with col13:
            passeios = st.checkbox("🏖️ Passeios")
        with col14:
            seguros = st.checkbox("🛡️ Seguros")
        
        st.markdown("### 📝 Observações")
        observacoes = st.text_area("Observações", placeholder="Alguma informação adicional?", height=80)
        
        # Botão
        enviar = st.form_submit_button("📨 Enviar Solicitação", use_container_width=True, type="primary")
    
    if enviar:
        if not all([nome, celular, email, origem, destino]):
            st.error("❌ Preencha todos os campos obrigatórios!")
        elif data_volta <= data_ida:
            st.error("❌ A data de volta deve ser depois da data de ida!")
        else:
            with st.spinner("Enviando..."):
                try:
                    dados = {
                        "nome_cliente": nome,
                        "celular": celular,
                        "email": email,
                        "origem": origem,
                        "destino": destino,
                        "data_ida": data_ida.strftime("%d/%m/%Y"),
                        "data_volta": data_volta.strftime("%d/%m/%Y"),
                        "flexibilidade": flexibilidade,
                        "passageiros": {"adultos": adultos, "criancas": criancas, "bebes": bebes, "total": adultos + criancas + bebes},
                        "bagagens": bagagens,
                        "servicos_adicionais": {"hospedagem": hospedagem, "transporte": transporte, "passeios": passeios, "seguros": seguros},
                        "observacoes": observacoes,
                        "link_id": link_id,
                        "nome_campanha": nome_campanha,
                        "email_destinatario": email_criador
                    }
                    
                    cursor.execute('''
                    INSERT INTO solicitacoes_cotacao (dados_solicitacao, status, link_id)
                    VALUES (?, ?, ?)
                    ''', (json.dumps(dados, ensure_ascii=False), 'RECEBIDA', link_id))
                    
                    solicitacao_id = cursor.lastrowid
                    dados['solicitacao_id'] = solicitacao_id
                    
                    cursor.execute('''
                    UPDATE links_publicos SET usos_restantes = usos_restantes - 1, total_usos = COALESCE(total_usos, 0) + 1
                    WHERE id = ?
                    ''', (link_id,))
                    
                    cursor.execute('''
                    UPDATE solicitacoes_cotacao SET dados_solicitacao = ? WHERE id = ?
                    ''', (json.dumps(dados, ensure_ascii=False), solicitacao_id))
                    
                    conn.commit()
                    conn.close()
                    
                    enviar_notificacao_criador({
                        'usuario_criador_id': usuario_criador_id,
                        'nome_campanha': nome_campanha,
                        'email_criador': email_criador
                    }, dados)
                    
                    st.success("✅ Solicitação enviada com sucesso!")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ Erro ao enviar: {str(e)}")

# ============= FUNÇÃO PRINCIPAL =============

def mostrar_solicitacoes():
    """Função principal para mostrar o módulo de solicitações"""
    
    inicializar_tabelas_solicitacoes()
    
    query_params = st.query_params
    if 'token' in query_params and 'form' in query_params and query_params['form'] == 'cotacao':
        token = query_params['token']
        formulario_publico_cotacao(token)
        return
    
    if 'pagina_solicitacoes' not in st.session_state:
        st.session_state.pagina_solicitacoes = 'gerar_link'
    
    exibir_notificacoes_sidebar()
    
    st.sidebar.markdown("### 📊 Módulo de Solicitações")
    
    menu_opcoes = {
        "🔗 Gerar Link": "gerar_link",
        "📋 Meus Links": "meus_links",
        "📨 Minhas Solicitações": "minhas_solicitacoes"
    }
    
    selecionada = st.sidebar.selectbox("Navegação", list(menu_opcoes.keys()))
    st.session_state.pagina_solicitacoes = menu_opcoes[selecionada]
    
    if st.session_state.pagina_solicitacoes == 'gerar_link':
        pagina_gerar_link()
    elif st.session_state.pagina_solicitacoes == 'meus_links':
        pagina_meus_links()
    elif st.session_state.pagina_solicitacoes == 'minhas_solicitacoes':
        pagina_minhas_solicitacoes()
