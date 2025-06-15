import sys
import os
import subprocess
from pathlib import Path
from tkinter import Tk, filedialog, messagebox
import logging

# --- CONFIGURACIÓN ---
DEFAULT_SEARCH_DIR = Path("Ruta del vault")
OUTPUT_SUBFOLDER_NAME = "_Converted"

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s', stream=sys.stdout)

# --- FUNCIONES AUXILIARES ---
def select_export_folder() -> Path | None:
    logging.info("Abriendo diálogo para seleccionar la carpeta de exportación...")
    try:
        root = Tk(); root.withdraw()
        folder_path_str = filedialog.askdirectory(
            title="Selecciona la carpeta 'Export_from_obsidian_...' a convertir",
            initialdir=DEFAULT_SEARCH_DIR
        )
        if not folder_path_str:
            logging.warning("Operación cancelada por el usuario."); return None
        selected_path = Path(folder_path_str)
        logging.info(f"Carpeta seleccionada: {selected_path}")
        return selected_path
    except Exception as e:
        logging.error(f"Ocurrió un error al seleccionar la carpeta: {e}"); return None

def find_root_note(export_folder: Path) -> Path | None:
    logging.info("Buscando la nota raíz en la carpeta de exportación...")
    min_depth, root_note = float('inf'), None
    for md_file in export_folder.rglob('*.md'):
        if OUTPUT_SUBFOLDER_NAME in md_file.parts: continue
        depth = len(md_file.relative_to(export_folder).parts)
        if depth < min_depth:
            min_depth, root_note = depth, md_file
    if root_note:
        logging.info(f"Nota raíz encontrada: {root_note.name}")
    else:
        logging.error("No se encontró ningún archivo .md en la carpeta seleccionada.")
    return root_note

def run_pandoc_command(command: list):
    command_str = [str(c) for c in command]
    logging.info(f"Ejecutando comando Pandoc: {' '.join(command_str)}")
    try:
        result = subprocess.run(
            command_str, check=True, capture_output=True, text=True, encoding='utf-8'
        )
        logging.info("Pandoc se ejecutó con éxito.")
        if result.stderr: logging.info(f"Salida de Pandoc (stderr):\n{result.stderr}")
        return True
    except FileNotFoundError:
        messagebox.showerror("Error", "No se pudo encontrar 'pandoc'. Asegúrate de que está instalado y en el PATH.")
        return False
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error de Pandoc", f"Pandoc falló:\n\n{e.stderr}")
        return False
    except Exception as e:
        messagebox.showerror("Error Inesperado", f"Ocurrió un error:\n\n{e}")
        return False

# --- FUNCIÓN DE CONVERSIÓN A PDF ---
def convert_to_pdf(input_files: list[Path], export_folder: Path, output_dir: Path):
    """Genera un archivo PDF profesional aprovechando los metadatos YAML."""
    output_file = output_dir / f"{export_folder.name}.pdf"
    command = [
        "pandoc",
        *input_files,
        "-o", output_file,
        "--from", "markdown+yaml_metadata_block", # Leer metadatos YAML
        "--resource-path", str(export_folder),
        "--standalone",
        "--toc", # Tabla de Contenidos
        "--number-sections", # Numerar secciones
        "--pdf-engine=xelatex",
    ]
    if run_pandoc_command(command):
        messagebox.showinfo("Éxito", f"PDF generado con éxito en:\n{output_file}")
    else:
        messagebox.showwarning("Fallo", "No se pudo generar el PDF. Revisa la consola para ver los errores de Pandoc.")

# --- FUNCIÓN PRINCIPAL ---
def main():
    export_folder = select_export_folder()
    if not export_folder: return

    output_dir = export_folder / OUTPUT_SUBFOLDER_NAME
    output_dir.mkdir(exist_ok=True)
    logging.info(f"Los archivos convertidos se guardarán en: {output_dir}")

    root_note = find_root_note(export_folder)
    if not root_note:
        messagebox.showerror("Error", f"No se pudo encontrar una nota .md raíz en la carpeta:\n{export_folder}")
        return

    logging.info("Recopilando todos los archivos .md para la conversión...")
    all_md_files = []
    for md_file in export_folder.rglob('*.md'):
        if OUTPUT_SUBFOLDER_NAME not in md_file.parts:
            all_md_files.append(md_file)
    
    pandoc_input_files = [root_note]
    for md_file in all_md_files:
        if md_file != root_note:
            pandoc_input_files.append(md_file)
    
    logging.info(f"Se procesarán {len(pandoc_input_files)} archivos para la conversión a PDF.")

    convert_to_pdf(pandoc_input_files, export_folder, output_dir)
    
    logging.info("Proceso de conversión finalizado.")

if __name__ == "__main__":
    main()
