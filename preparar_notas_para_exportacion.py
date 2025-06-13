import sys
import re
import shutil
import os
from pathlib import Path
from datetime import datetime
import logging
from urllib.parse import unquote
import io

# --- CONFIGURACIÓN ---
OBSIDIAN_VAULT_ROOT = Path("C:/Obsidian.Vaults")
DEFAULT_EXPORT_BASE_DIR = Path("C:/Users/canto/OneDrive/Documents/Exportaciones de Obsidian")
EXCLUDE_FOLDERS = ["05 - Captura", "06 - Daily", ".obsidian", ".trash"]
# --- FIN DE LA CONFIGURACIÓN ---

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s', stream=sys.stdout)

ATTACHMENT_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.pdf', '.mp3', '.wav', '.mp4', '.mov', '.webm'}
LINK_PATTERN = re.compile(r'(!?)\[\[([^|#\]]+)(?:\|([^\]]+))?\]\]')

def build_vault_index(vault_root: Path, exclude_folders: list) -> dict:
    logging.info(f"Construyendo índice del vault en: {vault_root}")
    file_index = {}
    for root, dirs, files in os.walk(vault_root, topdown=True):
        dirs[:] = [d for d in dirs if d not in exclude_folders and not any(part in exclude_folders for part in Path(root).relative_to(vault_root).parts)]
        for file in files:
            full_path = Path(root) / file
            base_name_key = full_path.stem.lower()
            if base_name_key not in file_index: file_index[base_name_key] = full_path
            relative_path_str = str(full_path.relative_to(vault_root))
            relative_key = os.path.splitext(relative_path_str)[0].lower().replace('\\', '/')
            file_index[relative_key] = full_path
            full_name_key = full_path.name
            if full_name_key not in file_index: file_index[full_name_key] = full_path
    logging.info(f"Índice construido con {len(file_index)} entradas únicas.")
    return file_index

def find_file_in_vault(target: str, vault_index: dict) -> Path | None:
    clean_target = unquote(target.strip())
    if clean_target in vault_index: return vault_index[clean_target]
    search_key = os.path.splitext(clean_target)[0].lower().replace('\\', '/')
    if search_key in vault_index: return vault_index[search_key]
    logging.warning(f"  -> No se pudo encontrar el archivo en el índice para el target: '{target}'")
    return None

def process_note_content(note_path: Path, vault_root: Path, vault_index: dict, visited_notes: set, notes_to_process: dict, attachments_to_copy: set):
    if note_path in visited_notes: return
    logging.info(f"--- 📖 Procesando nota: {note_path.relative_to(vault_root)} ---")
    visited_notes.add(note_path)
    
    try:
        content = note_path.read_text(encoding='utf-8')
    except Exception as e:
        logging.error(f"No se pudo leer el archivo {note_path}. Error: {e}"); return

    code_blocks = {}
    def preserve_code_block(match):
        key = f"__CODEBLOCK_{len(code_blocks)}__"
        code_blocks[key] = match.group(0)
        return key
    content = re.sub(r'(```.*?```|`.*?`)', preserve_code_block, content, flags=re.DOTALL)

    def link_replacer(match):
        is_embed_char, target, alias = match.groups()
        is_embed = (is_embed_char == '!')
        target = target.strip()
        alias = alias.strip() if alias else target

        linked_file = find_file_in_vault(target, vault_index)

        if not linked_file:
            logging.warning(f"  -> No se pudo resolver el enlace: [[{target}]]")
            return f"`Enlace Roto: {target}`"

        if is_embed and linked_file.suffix.lower() == '.md':
            logging.info(f"  -> Resolviendo transclusión: ![[{target}]]")
            process_note_content(linked_file, vault_root, vault_index, visited_notes, notes_to_process, attachments_to_copy)
            try:
                transcluded_content = notes_to_process.get(linked_file, linked_file.read_text(encoding='utf-8'))
                return f"\n\n---\n> *Contenido transcluido de `[[{linked_file.name}]]`*\n\n{transcluded_content}\n\n---\n"
            except Exception as e:
                return f"`Error al transcluir {linked_file.name}: {e}`"

        try:
            relative_path = os.path.relpath(linked_file, note_path.parent).replace('\\', '/')
        except ValueError:
            relative_path = linked_file.name

        if not is_embed and linked_file.suffix.lower() == '.md':
            logging.info(f"  -> Resolviendo wikilink: [[{target}]] -> {linked_file.name}")
            process_note_content(linked_file, vault_root, vault_index, visited_notes, notes_to_process, attachments_to_copy)
            return f"[{alias}]({relative_path})"
        
        if linked_file.suffix.lower() in ATTACHMENT_EXTENSIONS:
            if is_embed:
                logging.info(f"  -> Resolviendo adjunto embebido: ![[{target}]] -> {linked_file.name}")
                attachments_to_copy.add(linked_file)
                return f"![{alias}]({relative_path})"
            else: # Enlace de texto a un adjunto
                logging.info(f"  -> Resolviendo enlace a adjunto: [[{target}]]")
                attachments_to_copy.add(linked_file)
                return f"[{alias}]({relative_path})"

        return match.group(0)

    content = LINK_PATTERN.sub(link_replacer, content)

    for key, block in code_blocks.items():
        content = content.replace(key, block)

    notes_to_process[note_path] = content

def get_export_destination_dir(base_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_dir = base_dir / f"Export_from_obsidian_{timestamp}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir

def main():
    logging.info("--- Iniciando el Proceso de Exportación de Obsidian ---")
    vault_index = build_vault_index(OBSIDIAN_VAULT_ROOT, EXCLUDE_FOLDERS)
    if len(sys.argv) > 1:
        # Usamos el nombre del archivo del argumento para buscar en el índice
        initial_note_name = Path(sys.argv[1]).name
        initial_note_path = find_file_in_vault(initial_note_name, vault_index)
        if not initial_note_path:
            logging.error(f"La nota inicial '{sys.argv[1]}' no se encontró en el vault."); return
    else:
        try:
            from tkinter import Tk, filedialog
            root = Tk(); root.withdraw()
            file_path = filedialog.askopenfilename(title="Selecciona la nota de inicio", initialdir=OBSIDIAN_VAULT_ROOT, filetypes=[("Markdown files", "*.md")])
            if not file_path: logging.info("Operación cancelada."); return
            initial_note_path = Path(file_path)
        except ImportError:
            logging.error("Tkinter no está instalado. Proporciona la ruta como argumento."); return
    if not initial_note_path or not initial_note_path.exists():
        logging.error(f"El archivo de inicio no existe: {initial_note_path}"); return
    export_target_dir = get_export_destination_dir(DEFAULT_EXPORT_BASE_DIR)
    logging.info(f"Carpeta de exportación creada en: {export_target_dir}")
    visited_notes, notes_to_process, attachments_to_copy = set(), {}, set()
    
    # ### ESTA ES LA LÍNEA CORREGIDA ###
    process_note_content(initial_note_path, OBSIDIAN_VAULT_ROOT, vault_index, visited_notes, notes_to_process, attachments_to_copy)
    
    logging.info("\n--- 🚀 Iniciando la fase de copiado de archivos ---")
    
    def get_long_path_aware_str(path: Path) -> str:
        if os.name == 'nt' and path.is_absolute(): return "\\\\?\\" + str(path).replace('/', '\\')
        return str(path)

    for original_path, processed_content in notes_to_process.items():
        relative_path = original_path.relative_to(OBSIDIAN_VAULT_ROOT)
        destination_path = export_target_dir / relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with io.open(get_long_path_aware_str(destination_path), "w", encoding='utf-8') as f: f.write(processed_content)
            logging.info(f"Nota copiada y procesada: {relative_path}")
        except Exception as e:
            logging.error(f"FALLÓ la escritura de la nota: {relative_path}. Error: {e}\nRuta problemática: {destination_path}")

    for original_path in attachments_to_copy:
        relative_path = original_path.relative_to(OBSIDIAN_VAULT_ROOT)
        destination_path = export_target_dir / relative_path
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy(get_long_path_aware_str(original_path), get_long_path_aware_str(destination_path))
            logging.info(f"Adjunto copiado: {relative_path}")
        except Exception as e:
            logging.error(f"FALLÓ la copia del adjunto: {relative_path}. Error: {e}\nRuta problemática (destino): {destination_path}")
            
    logging.info("\n--- ✅ Proceso de exportación completado con éxito ---")
    logging.info(f"Todos los archivos han sido recopilados en: {export_target_dir}")

if __name__ == "__main__":
    if not OBSIDIAN_VAULT_ROOT.exists() or not OBSIDIAN_VAULT_ROOT.is_dir():
        logging.error(f"Ruta de bóveda no válida: {OBSIDIAN_VAULT_ROOT}")
    else:
        main()