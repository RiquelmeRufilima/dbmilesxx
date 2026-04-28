"""
empresa.py - Gerenciamento de Empresas DBMILESX
Sistema completo para criar, acessar e gerenciar empresas
"""

import streamlit as st
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import base64
import re

from database import (
    criar_conexao,
    get_usuarios_empresa,
    atualizar_nivel_acesso,
    convidar_membro,
    criar_empresa,
    get_empresa as get_info_empresa,
    verificar_codigo_acesso,
    sair_da_empresa,
    registrar_evento_seguranca
)
from theme_manager import get_cores

logger = logging.getLogger(__name__)


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def validar_cnpj(cnpj: str) -> bool:
    """Valida formato do CNPJ"""
    if not cnpj:
        return True
    # Remover caracteres não numéricos
    cnpj = re.sub(r'\D', '', cnpj)
    return len(cnpj) == 14


def formatar_cnpj(cnpj: str) -> str:
    """Formata CNPJ para exibição"""
    if not cnpj:
        return ""
    cnpj = re.sub(r'\D', '', cnpj)
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
    return cnpj


def formatar_telefone(telefone: str) -> str:
    """Formata telefone para exibição"""
    if not telefone:
        return ""
    telefone = re.sub(r'\D', '', telefone)
    if len(telefone) == 10:
        return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:10]}"
    elif len(telefone) == 11:
        return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:11]}"
    return telefone


# ============================================================================
# PÁGINA PRINCIPAL DA EMPRESA
# ============================================================================

def pagina_minha_empresa():
    """Página principal da empresa"""
    
    cores = get_cores()
    
    st.markdown(f"""
    <div style='
        background: linear-gradient(135deg, {cores['destaque']}, {cores['destaque']}dd);
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 25px;
        text-align: center;
    '>
        <h1 style='color: white; margin: 0;'>🏢 Minha Empresa</h1>
        <p style='color: rgba(255,255,255,0.9); margin: 5px 0 0 0;'>
            Gerencie sua empresa e equipe
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    empresa_id = st.session_state.get('empresa_id')
    
    if not empresa_id:
        _render_sem_empresa()
    else:
        _render_com_empresa(empresa_id)

def gerar_codigo_empresa(empresa_id: int) -> str:
    """Gera código único para a empresa"""
    import secrets
    random_part = secrets.token_hex(4).upper()
    emp_part = str(empresa_id).zfill(4)
    return f"DBM-{emp_part}-{random_part}"


def gerar_senha_acesso(tamanho: int = 12) -> str:
    """Gera senha aleatória para acesso"""
    import secrets
    import string
    caracteres = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(caracteres) for _ in range(tamanho))


def criar_codigo_acesso(empresa_id: int, criado_por: int) -> Optional[Dict]:
    """Cria um novo código de acesso para a empresa"""
    try:
        import secrets
        from datetime import datetime, timedelta
        
        codigo = gerar_codigo_empresa(empresa_id)
        senha = gerar_senha_acesso()
        expiracao = (datetime.now() + timedelta(days=7)).isoformat()
        
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO codigos_acesso (empresa_id, codigo, senha, criado_por, expiracao)
        VALUES (?, ?, ?, ?, ?)
        ''', (empresa_id, codigo, senha, criado_por, expiracao))
        
        conn.commit()
        conn.close()
        
        return {
            'codigo': codigo,
            'senha': senha,
            'expiracao': (datetime.now() + timedelta(days=7)).strftime('%d/%m/%Y')
        }
        
    except Exception as e:
        logger.error(f"Erro ao criar código de acesso: {e}")
        return None

def gerar_novo_codigo_acesso(empresa_id: int, usuario_id: int) -> Optional[Dict[str, str]]:
    """Gera um novo código de acesso para a empresa"""
    try:
        import secrets
        from datetime import datetime, timedelta
        
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
        print(f"Erro ao gerar código: {e}")
        return None
    
def verificar_codigo_acesso(codigo: str, senha: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Verifica a validade do código de acesso fornecido"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT e.id, e.nome, e.cnpj, e.telefone, e.email, e.endereco
        FROM codigos_acesso c
        JOIN empresas e ON c.empresa_id = e.id
        WHERE c.codigo = ? AND c.senha = ? AND c.expiracao > CURRENT_TIMESTAMP
        ''', (codigo, senha))
        
        resultado = cursor.fetchone()
        conn.close()
        
        if resultado:
            return True, {
                'empresa_id': resultado[0],
                'empresa_nome': resultado[1],
                'cnpj': resultado[2],
                'telefone': resultado[3],
                'email': resultado[4],
                'endereco': resultado[5]
            }
        else:
            return False, None
    
    except Exception as e:
        logger.error(f"Erro ao verificar código de acesso: {e}")
        return False, None


def sair_da_empresa(usuario_id: int, empresa_id: int) -> Tuple[bool, str]:
    """Usuário sai da empresa"""
    try:
        conn = criar_conexao()
        cursor = conn.cursor()
        
        # Verificar se é o último admin
        cursor.execute('''
        SELECT COUNT(*) FROM usuarios 
        WHERE empresa_id = ? AND nivel_acesso = 'admin' AND id != ?
        ''', (empresa_id, usuario_id))
        
        outros_admins = cursor.fetchone()[0]
        
        if outros_admins == 0:
            conn.close()
            return False, "Você é o último administrador. Promova alguém antes de sair."
        
        cursor.execute('''
        UPDATE usuarios 
        SET empresa_id = NULL, nivel_acesso = 'membro'
        WHERE id = ?
        ''', (usuario_id,))
        
        conn.commit()
        conn.close()
        
        return True, "Você saiu da empresa com sucesso!"
        
    except Exception as e:
        logger.error(f"Erro ao sair da empresa: {e}")
        return False, f"Erro: {str(e)}"
    
def _render_sem_empresa():
    """Renderiza tela para usuário sem empresa"""
    
    cores = get_cores()
    
    st.markdown(f"""
    <div style='
        background: {cores['card']};
        padding: 40px;
        border-radius: 20px;
        text-align: center;
        margin: 20px 0;
        border: 2px dashed {cores['borda']};
    '>
        <span style='font-size: 64px;'>🏢</span>
        <h2 style='color: {cores['texto']}; margin: 10px 0;'>Você ainda não está em nenhuma empresa</h2>
        <p style='color: {cores['texto']}80;'>
            Crie sua própria empresa ou acesse uma existente com código
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 CRIAR EMPRESA", type="primary", use_container_width=True):
            st.session_state.pagina_empresa = 'criar'
            st.rerun()
    
    with col2:
        if st.button("🔐 ACESSAR EMPRESA", type="secondary", use_container_width=True):
            st.session_state.pagina_empresa = 'acessar'
            st.rerun()


def _render_criar_empresa():
    """Renderiza formulário para criar empresa"""
    
    cores = get_cores()
    
    # Botão voltar
    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Voltar", use_container_width=True):
            st.session_state.pagina_empresa = None
            st.rerun()
    
    st.markdown(f"""
    <div style='
        background: linear-gradient(135deg, {cores['success']}20, {cores['success']}10);
        padding: 20px;
        border-radius: 15px;
        margin: 20px 0;
        border-left: 4px solid {cores['success']};
    '>
        <h3 style='margin: 0;'>🆕 Criar Nova Empresa</h3>
        <p style='margin: 5px 0 0 0; opacity: 0.8;'>Preencha os dados abaixo. Você se tornará ADMINISTRADOR da empresa.</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("form_criar_empresa"):
        col1, col2 = st.columns(2)
        
        with col1:
            nome = st.text_input(
                "**Nome da Empresa** *",
                placeholder="Ex: Minha Agência de Viagens",
                help="Nome oficial da sua empresa"
            )
            
            cnpj = st.text_input(
                "**CNPJ**",
                placeholder="00.000.000/0000-00",
                help="Opcional - CNPJ da empresa"
            )
            
            telefone = st.text_input(
                "**Telefone**",
                placeholder="(11) 99999-9999",
                help="Opcional - Telefone de contato"
            )
        
        with col2:
            email = st.text_input(
                "**Email da empresa**",
                placeholder="contato@minhaempresa.com",
                help="Opcional - Email para contato"
            )
            
            site = st.text_input(
                "**Site**",
                placeholder="www.minhaempresa.com",
                help="Opcional - Website da empresa"
            )
            
            endereco = st.text_area(
                "**Endereço**",
                placeholder="Rua, número, bairro, cidade - UF",
                height=80,
                help="Opcional - Endereço completo"
            )
        
        st.markdown("---")
        st.markdown("#### 📸 Logo da Empresa")
        st.caption("Faça upload do logo (aparecerá nos relatórios e na interface)")
        
        logo = st.file_uploader(
            "Selecione uma imagem",
            type=['png', 'jpg', 'jpeg'],
            key="upload_logo_empresa",
            help="Formatos: PNG, JPG, JPEG"
        )
        
        if logo:
            st.image(logo, width=150, caption="Preview do logo")
        
        st.markdown("---")
        
        # Termos
        st.markdown(f"""
        <div style='
            background: {cores['info']}15;
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid {cores['info']};
            margin: 15px 0;
        '>
            <p style='margin: 0;'><strong>📌 Ao criar uma empresa:</strong></p>
            <ul style='margin: 10px 0 0 20px;'>
                <li>Você se torna <strong>ADMINISTRADOR</strong> da empresa</li>
                <li>Poderá convidar membros e gerenciar a equipe</li>
                <li>Será responsável pelos dados da empresa</li>
                <li>Poderá gerar códigos de acesso para novos membros</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        aceite = st.checkbox("✅ Confirmo que sou responsável por esta empresa")
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            criar = st.form_submit_button(
                "🏢 CRIAR EMPRESA",
                type="primary",
                use_container_width=True,
                disabled=not (nome and aceite)
            )
        
        if criar:
            # Validações
            if not nome:
                st.error("❌ Nome da empresa é obrigatório")
            elif len(nome) < 3:
                st.error("❌ Nome muito curto (mínimo 3 caracteres)")
            elif len(nome) > 100:
                st.error("❌ Nome muito longo (máximo 100 caracteres)")
            else:
                with st.spinner("🔄 Criando sua empresa..."):
                    # Processar logo
                    logo_base64 = None
                    if logo:
                        bytes_data = logo.getvalue()
                        logo_base64 = base64.b64encode(bytes_data).decode()
                    
                    # Criar empresa
                    sucesso, resultado = criar_empresa(
                        nome=nome.strip(),
                        cnpj=cnpj if cnpj else None,
                        telefone=telefone if telefone else None,
                        email=email if email else None,
                        site=site if site else None,
                        endereco=endereco if endereco else None,
                        logo=logo_base64,
                        criado_por=st.session_state.usuario_id
                    )
                    
                    if sucesso:
                        # Atualizar sessão
                        st.session_state.empresa_id = resultado['empresa_id']
                        st.session_state.empresa_nome = nome.strip()
                        st.session_state.empresa_logo = logo_base64
                        st.session_state.nivel_acesso = 'admin'
                        
                        # Registrar evento
                        registrar_evento_seguranca(
                            st.session_state.usuario_id,
                            "EMPRESA_CRIADA",
                            f"Empresa '{nome}' criada",
                            "INFO",
                            {"empresa_id": resultado['empresa_id']}
                        )
                        
                        st.success("✅ Empresa criada com sucesso!")
                        
                        # Mostrar código de acesso
                        st.markdown(f"""
                        <div style='
                            background: {cores['success']}15;
                            padding: 20px;
                            border-radius: 15px;
                            margin: 20px 0;
                            border: 1px solid {cores['success']};
                        '>
                            <h4 style='margin: 0 0 10px 0;'>🔑 Código de Acesso da Empresa</h4>
                            <p><strong>Código:</strong> <code style='font-size: 1.2rem;'>{resultado['codigo']}</code></p>
                            <p><strong>Senha:</strong> <code style='font-size: 1.2rem;'>{resultado['senha']}</code></p>
                            <p style='margin: 10px 0 0 0; font-size: 0.9rem;'>⚠️ Guarde estas informações! Use para novos membros acessarem a empresa.</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.balloons()
                        time.sleep(3)
                        
                        # Limpar estado e redirecionar
                        st.session_state.pagina_empresa = None
                        st.rerun()
                    else:
                        st.error(f"❌ {resultado}")


def _render_acessar_empresa():
    """Renderiza formulário para acessar empresa com código"""
    
    cores = get_cores()
    
    # Botão voltar
    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Voltar", use_container_width=True):
            st.session_state.pagina_empresa = None
            st.rerun()
    
    st.markdown(f"""
    <div style='
        background: linear-gradient(135deg, {cores['info']}20, {cores['info']}10);
        padding: 20px;
        border-radius: 15px;
        margin: 20px 0;
        border-left: 4px solid {cores['info']};
    '>
        <h3 style='margin: 0;'>🔑 Acessar Empresa Existente</h3>
        <p style='margin: 5px 0 0 0; opacity: 0.8;'>Digite o código e senha fornecidos pelo administrador da empresa.</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("form_acessar_empresa"):
        codigo = st.text_input(
            "**Código de acesso**",
            placeholder="Ex: DBM-0001-A7B3",
            help="Código fornecido pelo administrador da empresa"
        )
        
        senha = st.text_input(
            "**Senha de acesso**",
            type="password",
            placeholder="••••••••",
            help="Senha fornecida junto com o código"
        )
        
        st.markdown(f"""
        <div style='
            background: {cores['aviso']}15;
            padding: 10px;
            border-radius: 8px;
            margin: 10px 0;
            font-size: 0.9rem;
        '>
            💡 <strong>Não tem código?</strong> Peça ao administrador da empresa para gerar um código de acesso.
        </div>
        """, unsafe_allow_html=True)
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            acessar = st.form_submit_button(
                "🔓 ACESSAR EMPRESA",
                type="primary",
                use_container_width=True
            )
        
        if acessar:
            if not codigo or not senha:
                st.error("❌ Preencha código e senha")
            else:
                with st.spinner("🔍 Verificando código..."):
                    valido, dados = verificar_codigo_acesso(codigo, senha)
                    
                    if valido and dados:
                        empresa_id = dados.get('empresa_id')
                        
                        if empresa_id:
                            # Atualizar usuário
                            conn = criar_conexao()
                            cursor = conn.cursor()
                            cursor.execute('''
                            UPDATE usuarios 
                            SET empresa_id = ?, nivel_acesso = 'membro'
                            WHERE id = ?
                            ''', (empresa_id, st.session_state.usuario_id))
                            conn.commit()
                            conn.close()
                            
                            # Atualizar sessão
                            st.session_state.empresa_id = empresa_id
                            st.session_state.empresa_nome = dados.get('empresa_nome')
                            st.session_state.nivel_acesso = 'membro'
                            
                            # Registrar evento
                            registrar_evento_seguranca(
                                st.session_state.usuario_id,
                                "EMPRESA_ACESSADA",
                                f"Acessou empresa {dados.get('empresa_nome')} via código",
                                "INFO",
                                {"empresa_id": empresa_id}
                            )
                            
                            st.success(f"✅ Bem-vindo à empresa {dados.get('empresa_nome')}!")
                            time.sleep(2)
                            
                            st.session_state.pagina_empresa = None
                            st.rerun()
                    else:
                        st.error("❌ Código ou senha inválidos")


def _render_com_empresa(empresa_id: int):
    """Renderiza tela para usuário com empresa"""
    
    cores = get_cores()
    nivel = st.session_state.get('nivel_acesso', 'membro')
    info = get_info_empresa(empresa_id)
    
    if not info:
        st.error("❌ Erro ao carregar informações da empresa")
        return
    
    # Header com logo e informações
    col_logo, col_info = st.columns([1, 3])
    
    with col_logo:
        if info.get('logo'):
            st.image(f"data:image/png;base64,{info['logo']}", width=120)
        else:
            st.markdown(f"""
            <div style='
                width: 120px;
                height: 120px;
                background: linear-gradient(135deg, {cores['destaque']}, {cores['destaque']}dd);
                border-radius: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
            '>
                <span style='font-size: 48px; color: white;'>🏢</span>
            </div>
            """, unsafe_allow_html=True)
    
    with col_info:
        st.markdown(f"### {info['nome']}")
        
        # Informações de contato
        contatos = []
        if info.get('cnpj'):
            contatos.append(f"📄 CNPJ: {formatar_cnpj(info['cnpj'])}")
        if info.get('telefone'):
            contatos.append(f"📞 {formatar_telefone(info['telefone'])}")
        if info.get('email'):
            contatos.append(f"✉️ {info['email']}")
        if info.get('site'):
            contatos.append(f"🌐 {info['site']}")
        
        if contatos:
            st.markdown(" | ".join(contatos))
        
        # Endereço
        if info.get('endereco'):
            st.caption(f"📍 {info['endereco']}")
        
        # Badge de nível
        if nivel == 'admin':
            st.markdown(f"<span style='background: {cores['destaque']}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem;'>👑 ADMINISTRADOR</span>", unsafe_allow_html=True)
        elif nivel == 'gerente':
            st.markdown(f"<span style='background: {cores['success']}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem;'>📋 GERENTE</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"<span style='background: {cores['info']}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem;'>👤 MEMBRO</span>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # AÇÕES BASEADAS NO NÍVEL
    if nivel in ['admin', 'gerente']:
        st.subheader("⚙️ Administração da Empresa")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("👥 MEMBROS", use_container_width=True):
                st.session_state.pagina = 'admin_empresa'
                st.session_state.admin_aba = 'membros'
                st.rerun()
        
        with col2:
            if st.button("📨 CONVIDAR", use_container_width=True):
                st.session_state.pagina = 'admin_empresa'
                st.session_state.admin_aba = 'convidar'
                st.rerun()
        
        with col3:
            if st.button("🔑 CÓDIGO DE ACESSO", use_container_width=True):
                st.session_state.mostrar_codigo = True
        
        # GERAR CÓDIGO DE ACESSO
        if st.session_state.get('mostrar_codigo', False):
            with st.container():
                st.markdown("---")
                st.markdown("#### 🔑 Gerar Código de Acesso")
                st.caption("Código para novos membros acessarem a empresa")
                
                dias = st.slider("Dias de validade", 1, 30, 7)
                
                if st.button("✅ GERAR CÓDIGO", type="primary", use_container_width=True):
                    from database import gerar_novo_codigo_acesso
                    novo_codigo = gerar_novo_codigo_acesso(empresa_id, st.session_state.usuario_id)
                    
                    if novo_codigo:
                        st.success("✅ Código gerado com sucesso!")
                        
                        col_code1, col_code2 = st.columns(2)
                        with col_code1:
                            st.markdown("**Código:**")
                            st.code(novo_codigo['codigo'], language="text")
                        with col_code2:
                            st.markdown("**Senha:**")
                            st.code(novo_codigo['senha'], language="text")
                        
                        st.info(f"⏰ Expira em: {novo_codigo['expiracao']}")
                        
                        if st.button("✅ OK", use_container_width=True):
                            st.session_state.mostrar_codigo = False
                            st.rerun()
    
    # Membros da empresa (todos podem ver)
    st.subheader("👥 Membros da Equipe")
    
    membros = get_usuarios_empresa(empresa_id)
    
    if membros:
        for membro in membros:
            col_m1, col_m2, col_m3 = st.columns([3, 1.5, 1])
            with col_m1:
                st.write(f"**{membro['nome']}**")
                st.caption(membro['email'])
            with col_m2:
                nivel_m = membro['nivel_acesso']
                if nivel_m == 'admin':
                    st.markdown("👑 **Admin**")
                elif nivel_m == 'gerente':
                    st.markdown("📋 Gerente")
                else:
                    st.markdown("👤 Membro")
            with col_m3:
                if nivel in ['admin', 'gerente'] and membro['id'] != st.session_state.usuario_id:
                    if nivel == 'admin':
                        novo_nivel = st.selectbox(
                            "Nível",
                            ['membro', 'gerente', 'admin'],
                            index=['membro', 'gerente', 'admin'].index(nivel_m),
                            key=f"nivel_{membro['id']}",
                            label_visibility="collapsed"
                        )
                        if novo_nivel != nivel_m:
                            sucesso, msg = atualizar_nivel_acesso(membro['id'], novo_nivel, st.session_state.usuario_id)
                            if sucesso:
                                st.success(f"Nível alterado para {novo_nivel}")
                                time.sleep(1)
                                st.rerun()
            st.divider()
    else:
        st.info("Nenhum membro encontrado")
    
    st.markdown("---")
    
    # SAIR DA EMPRESA
    st.subheader("🚪 Sair da Empresa")
    
    with st.expander("⚠️ Sair desta empresa", expanded=False):
        st.warning("Ao sair, você perderá acesso a todos os dados da empresa.")
        st.caption("Se você for o único administrador, promova outro membro antes de sair.")
        
        confirmar = st.checkbox("Entendo e quero sair", key="confirm_sair")
        
        if st.button("🚪 SAIR DA EMPRESA", type="secondary", use_container_width=True, disabled=not confirmar):
            sucesso, msg = sair_da_empresa(st.session_state.usuario_id, empresa_id)
            
            if sucesso:
                st.session_state.empresa_id = None
                st.session_state.empresa_nome = None
                st.session_state.empresa_logo = None
                st.session_state.nivel_acesso = 'membro'
                
                st.success(msg)
                time.sleep(2)
                st.rerun()
            else:
                st.error(msg)


# ============================================================================
# FUNÇÃO PRINCIPAL - PONTO DE ENTRADA ÚNICO
# ============================================================================

def render_pagina_empresa():
    """Função principal para renderizar a página de empresa"""
    
    # Inicializar estado
    if 'pagina_empresa' not in st.session_state:
        st.session_state.pagina_empresa = None
    
    # Roteamento interno
    if st.session_state.pagina_empresa == 'criar':
        _render_criar_empresa()
    elif st.session_state.pagina_empresa == 'acessar':
        _render_acessar_empresa()
    else:
        pagina_minha_empresa()


# ============================================================================
# TESTE DO MÓDULO
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 TESTANDO MÓDULO EMPRESA")
    print("=" * 60)
    
    # Testar formatação
    print("\n1. Testando formatação...")
    print(f"   CNPJ: {formatar_cnpj('12345678000199')}")
    print(f"   Telefone: {formatar_telefone('11999999999')}")
    
    print("\n✅ MÓDULO EMPRESA OK!")
    print("=" * 60)