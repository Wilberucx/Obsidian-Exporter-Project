import sys
import re
import shutil
import os
from pathlib import Path
from datetime import datetime
import logging
from urllib.parse import unquote
import json

# --- Configuración del Logging ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s', stream=sys.stdout)

# --- Constantes y Patrones de Regex ---
CONFIG_FILE = Path("config.json")
ATTACHMENT_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.pdf'}
LINK_PATTERN = re.compile(r'(!?)\[\[([^|#\]]+)(?:\|([^\]]+))?\]\]')
MD_IMAGE_PATTERN = re.compile(r'!\[(.*?)\]\((.*?)\)')

class ExportBuilder:
    """
    Construye un paquete de exportación autocontenido a partir de una nota de inicio
    en un vault de Obsidian, explorando hasta una profundidad especificada.
    """
    def __init__(self, vault_path: Path, export_base_dir: Path, exclude_folders: list):
        self.vault_path = vault_path
        self.export_base_dir = export_base_dir
        self.exclude_folders = exclude_folders
        self.export_root = self._create_export_root()
        self.notes_dir = self.export_root / "Notes"
        self.assets_dir = self.export_root / "Assets"
        self.notes_dir.mkdir()
        self.assets_dir.mkdir()
        self.vault_index = self._build_vault_index()
        self.processed_notes = set()
        self.copied_assets = set()
        self.moc_content = "# Export Manuscript\n\nThis file lists the notes included in this export, in hierarchical order.\n\n"

    def _create_export_root(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_dir = self.export_base_dir / f"Export_{self.vault_path.name}_{timestamp}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Export folder created at: {dest_dir}")
        return dest_dir

    def _build_vault_index(self) -> dict:
        logging.info(f"Building index for vault: {self.vault_path}...")
        index = {}
        for root, dirs, files in os.walk(self.vault_path):
             dirs[:] = [d for d in dirs if d not in self.exclude_folders]
             for file in files:
                full_path = Path(root) / file
                index[full_path.stem.lower()] = full_path
                index[full_path.name.lower()] = full_path
        logging.info(f"Index built with {len(index)} entries.")
        return index
    
    def find_file_in_vault(self, target: str) -> Path | None:
        clean_target = unquote(target.strip()).lower()
        path = self.vault_index.get(clean_target)
        if path: return path
        path = self.vault_index.get(Path(clean_target).stem)
        return path

    def run(self, start_note_path: Path, max_depth: int):
        self.explore_and_copy(start_note_path, 0, max_depth)
        
        # Generar el MOC final con enlaces funcionales
        final_moc_content = ""
        for line in self.moc_content.splitlines():
            match = re.search(r'\[\[(.*?)\]\]', line)
            if match:
                note_stem = match.group(1)
                line = line.replace(f"[[{note_stem}]]", f"[{note_stem}](./{note_stem}.md)")
            final_moc_content += line + "\n"

        moc_path = self.notes_dir / "_MOC_Guide.md"
        moc_path.write_text(final_moc_content, encoding='utf-8')
        logging.info(f"MOC Guide generated at: {moc_path}")

    def explore_and_copy(self, note_path: Path, current_depth: int, max_depth: int):
        if (max_depth != -1 and current_depth > max_depth) or note_path in self.processed_notes:
            return
        
        logging.info(f"{'  ' * current_depth}📖 Processing (Level {current_depth}): {note_path.name}")
        self.processed_notes.add(note_path)

        indent = "    " * current_depth
        self.moc_content += f"{indent}- [[{note_path.stem}]]\n"
        
        try:
            content = note_path.read_text(encoding='utf-8')
        except Exception as e:
            logging.error(f"Could not read {note_path}: {e}"); return

        content = self._process_assets(content, LINK_PATTERN)
        content = self._process_assets(content, MD_IMAGE_PATTERN, is_md_link=True)

        destination_note_path = self.notes_dir / note_path.name
        destination_note_path.write_text(content, encoding='utf-8')
        
        original_content = note_path.read_text(encoding='utf-8')
        for match in LINK_PATTERN.finditer(original_content):
            is_embed, target, _ = match.groups()
            if not is_embed:
                linked_note_path = self.find_file_in_vault(target)
                if linked_note_path and linked_note_path.suffix.lower() == '.md':
                    self.explore_and_copy(linked_note_path, current_depth + 1, max_depth)

    def _process_assets(self, content: str, pattern: re.Pattern, is_md_link:bool=False) -> str:
        def asset_replacer(match):
            if is_md_link:
                alias, target = match.groups()
            else:
                is_embed, target, alias = match.groups()
                if not is_embed: return match.group(0)
            
            asset_path = self.find_file_in_vault(target)
            if asset_path and asset_path.suffix.lower() in ATTACHMENT_EXTENSIONS:
                if asset_path not in self.copied_assets:
                    shutil.copy(asset_path, self.assets_dir)
                    self.copied_assets.add(asset_path)
                
                new_path = f"../Assets/{asset_path.name}"
                return f"![{alias or asset_path.stem}]({new_path})"
            return match.group(0)
        return pattern.sub(asset_replacer, content)

def load_app_config() -> dict | None:
    if not CONFIG_FILE.exists():
        logging.error(f"Configuration file '{CONFIG_FILE}' not found.")
        logging.error("Please run 'config_tool.py' first to set up the application.")
        return None
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

# ### NUEVA FUNCIÓN PARA SELECCIONAR LA PROFUNDIDAD ###
def select_depth_from_menu() -> int | None:
    """Muestra un menú numerado al usuario y devuelve la profundidad seleccionada."""
    print("\n--- Selecciona el Nivel de Profundidad de la Exportación ---")
    print("1: Nivel 0 (Solo la nota inicial)")
    print("2: Nivel 1 (Nota inicial + enlaces directos)")
    print("3: Nivel 2 (Hasta los enlaces de los enlaces)")
    print("4: Nivel 3 (Exploración profunda del tema)")
    print("5: Infinito (Toda la red conectada, ¡cuidado!)")
    
    options = {
        "1": 0,
        "2": 1,
        "3": 2,
        "4": 3,
        "5": -1
    }
    
    while True:
        choice = input("Elige una opción (1-5): ")
        if choice in options:
            return options[choice]
        else:
            print("Opción no válida. Por favor, introduce un número del 1 al 5.")

def main():
    """Función principal del script."""
    config = load_app_config()
    if not config:
        sys.exit(1)

    if not config.get("vault_paths") or not config.get("export_dir"):
        logging.error("Vault paths or export directory are not configured.")
        logging.error("Please run 'config_tool.py' to complete the setup.")
        sys.exit(1)

    vault_path = Path(config["vault_paths"][0])
    export_dir = Path(config["export_dir"])
    exclude_folders = config.get("exclude_folders", [])

    logging.info(f"Using Vault: {vault_path}")
    
    from tkinter import Tk, filedialog
    try:
        root = Tk(); root.withdraw()
        start_note_str = filedialog.askopenfilename(
            title=f"Select the starting note from '{vault_path.name}'",
            initialdir=vault_path,
            filetypes=[("Markdown files", "*.md")]
        )
        if not start_note_str:
            logging.warning("No note selected. Exiting."); return
        start_note_path = Path(start_note_str)
    except (ImportError, RuntimeError) as e:
        logging.error(f"Could not display file dialog: {e}.")
        sys.exit(1)

    # ### CAMBIO: Usar el nuevo menú en lugar de la entrada libre ###
    max_depth = select_depth_from_menu()
    if max_depth is None: # Teóricamente no debería pasar con el bucle, pero es buena práctica
        logging.error("No depth selected. Exiting.")
        return

    # --- Iniciar el Proceso ---
    builder = ExportBuilder(vault_path, export_dir, exclude_folders)
    builder.run(start_note_path, max_depth)
    
    logging.info("\n--- ✅ Export build process completed successfully! ---")

if __name__ == "__main__":
    main()