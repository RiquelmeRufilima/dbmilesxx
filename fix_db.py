# fix_db.py
from database import criar_conexao

conn = criar_conexao()
cursor = conn.cursor()

# Lista de colunas para adicionar
colunas = [
    ("nivel_acesso", "TEXT DEFAULT 'membro'"),
    ("empresa_id", "INTEGER"),
    ("telefone", "TEXT"),
    ("cargo", "TEXT"),
    ("foto_perfil", "TEXT")
]

for coluna, tipo in colunas:
    try:
        cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {coluna} {tipo}")
        print(f"✅ {coluna} adicionada")
    except Exception as e:
        print(f"⚠️ {coluna} já existe ou erro: {e}")

conn.commit()
conn.close()
print("✅ Banco atualizado!")

# Verificar colunas
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(usuarios)")
colunas_existentes = [c[1] for c in cursor.fetchall()]
print(f"\n📋 Colunas na tabela usuarios: {colunas_existentes}")
conn.close()