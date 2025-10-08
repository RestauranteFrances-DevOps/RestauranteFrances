import re, sys, os

src_path = "ai_actions.py"
new_func_path = "new_buscar_clinicas.py"

if not os.path.isfile(src_path):
    print(f"ERRO: não encontrei '{src_path}' no diretório atual ({os.getcwd()})"); sys.exit(1)
if not os.path.isfile(new_func_path):
    print(f"ERRO: não encontrei '{new_func_path}' no diretório atual ({os.getcwd()})"); sys.exit(1)

with open(src_path, "r", encoding="utf-8") as f: src = f.read()
with open(new_func_path, "r", encoding="utf-8") as f: newfunc = f.read()

pattern = re.compile(r"(def\s+buscar_clinicas_veterinarias\s*\(.*?\):\n)(?:\s+.*\n)*?(?=(\ndef\s+|\Z))", re.S)
if not pattern.search(src):
    print("ERRO: não encontrei 'def buscar_clinicas_veterinarias' em ai_actions.py"); sys.exit(1)

backup_path = src_path + ".bak_auto"
with open(backup_path, "w", encoding="utf-8") as f: f.write(src)
print(f"Backup criado: {backup_path}")

new_src = pattern.sub("\n" + newfunc + "\n\n", src, count=1)
with open(src_path + ".new", "w", encoding="utf-8") as f: f.write(new_src)
os.replace(src_path + ".new", src_path)
print("Substituição concluída com sucesso.")
