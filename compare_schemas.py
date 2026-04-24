import psycopg2

ANCIENNE = "postgresql://neondb_owner:npg_h5QpiZzw2dvx@ep-patient-hall-aldsd3g4-pooler.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require"
NOUVELLE = "postgresql://neondb_owner:npg_Z1bLohDN3nmG@ep-late-rain-algv7iht.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require"

def get_schema(url):
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name, column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    schema = {}
    for table, col, dtype, nullable, default in rows:
        if table not in schema:
            schema[table] = {}
        schema[table][col] = {"type": dtype, "nullable": nullable, "default": default}
    return schema

print("Connexion aux deux bases...")
ancienne = get_schema(ANCIENNE)
nouvelle = get_schema(NOUVELLE)

print("\n" + "="*60)
print("TABLES MANQUANTES dans la nouvelle base :")
print("="*60)
for table in ancienne:
    if table not in nouvelle:
        print(f"  ❌ TABLE MANQUANTE : {table}")

print("\n" + "="*60)
print("TABLES en trop dans la nouvelle base (pas dans l'ancienne) :")
print("="*60)
for table in nouvelle:
    if table not in ancienne:
        print(f"  ➕ TABLE SUPPLÉMENTAIRE : {table}")

print("\n" + "="*60)
print("COLONNES MANQUANTES par table :")
print("="*60)

sql_corrections = []

for table in ancienne:
    if table not in nouvelle:
        continue
    for col, info in ancienne[table].items():
        if col not in nouvelle[table]:
            print(f"  ❌ {table}.{col}  ({info['type']}, nullable={info['nullable']}, default={info['default']})")
            nullable_sql = "" if info['nullable'] == 'YES' else " NOT NULL"
            default_sql = f" DEFAULT {info['default']}" if info['default'] else ""
            sql_corrections.append(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {info['type']}{nullable_sql}{default_sql};"
            )

print("\n" + "="*60)
print("COLONNES DIFFÉRENTES (type changé) :")
print("="*60)
for table in ancienne:
    if table not in nouvelle:
        continue
    for col, info in ancienne[table].items():
        if col in nouvelle[table]:
            if info['type'] != nouvelle[table][col]['type']:
                print(f"  ⚠️  {table}.{col} : ancienne={info['type']} → nouvelle={nouvelle[table][col]['type']}")

if sql_corrections:
    print("\n" + "="*60)
    print("SQL POUR CORRIGER LA NOUVELLE BASE :")
    print("="*60)
    for sql in sql_corrections:
        print(sql)

    with open("corrections.sql", "w") as f:
        f.write("-- Corrections à appliquer sur la nouvelle base\n")
        f.write("-- Généré automatiquement par compare_schemas.py\n\n")
        for sql in sql_corrections:
            f.write(sql + "\n")
    print("\n✅ Fichier corrections.sql généré !")
else:
    print("\n✅ Aucune colonne manquante détectée.")