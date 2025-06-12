import os
import re
import shutil
import datetime
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

# --- CONFIGURACIÓN INICIAL ---
# IMPORTANTE: Reemplaza esta ruta con la ruta ABSOLUTA a tu vault de Obsidian.
# Ejemplo: OBSIDIAN_VAULT_ROOT = Path("C:/Users/Wilber/Documents/Obsidian_Vault_Principal")
OBSIDIAN_VAULT_ROOT = Path("C:/Obsidian.Vaults") # ¡AJUSTA ESTO!

# Ruta por defecto donde se guardarán las carpetas de exportación.
# Se creará una subcarpeta con el nombre 'Export_from_obsidian_YYYYMMDDHHmm' dentro de esta ruta.
# Ejemplo: DEFAULT_EXPORT_BASE_DIR = Path("C:/Users/Wilber/Documents/Obsidian_Exports")
DEFAULT_EXPORT_BASE_DIR = Path("C:/Users/canto/OneDrive/Documents/Exportaciones de Obsidian") # ¡AJUSTA ESTO!

# Carpetas dentro de tu vault que quieres excluir de la búsqueda recursiva de wikilinks.
# Las notas de estas carpetas no se incluirán en la exportación si se enlazan.
EXCLUDE_FOLDERS = ["05 - Captura", "06 - Daily"]

# Patrones de expresiones regulares para encontrar enlaces
# Captura [[Nombre de la Nota]] o [[Nombre de la Nota|Alias]] o [[ruta/Nombre de la Nota]]
# El primer grupo de captura (grupo 1) obtiene "Nombre de la Nota" o "ruta/Nombre de la Nota"
WIKILINK_PATTERN = re.compile(r'\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]')
# Captura ![[Nombre de la Nota]] o ![[Nombre de la Nota|Alias]] o ![[ruta/Nombre de la Nota]]
EMBED_LINK_PATTERN = re.compile(r'!\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]')
# Captura ![Texto alternativo](ruta/a/imagen.png) o ![Título](ruta/a/imagen.jpg)
MARKDOWN_IMAGE_PATTERN = re.compile(r'!\[.*?\]\((.*?)\)')


# --- FUNCIONES DE UTILIDAD ---

def get_note_path_from_input():
    """
    Obtiene la ruta de la nota principal (índice) desde los argumentos de línea de comandos
    (cuando se ejecuta desde Obsidian Shell Commands) o mediante un diálogo de selección de archivo.
    """
    if len(sys.argv) > 1:
        # Si hay argumentos, asumimos que el primero es la ruta del archivo de Obsidian
        # (usando {{file_path:absolute}} del plugin Shell Commands).
        initial_note_path = Path(sys.argv[1])
        if initial_note_path.exists() and initial_note_path.is_file():
            print(f"DEBUG: Nota índice recibida desde la línea de comandos: {initial_note_path}")
            return initial_note_path
        else:
            print(f"Advertencia: La ruta de archivo proporcionada no es válida: {initial_note_path}")

    # Si no hay argumentos válidos o no se proporcionaron, abrimos un diálogo.
    root = tk.Tk()
    root.withdraw()  # Oculta la ventana principal de Tkinter

    messagebox.showinfo("Seleccionar Nota Índice", "Por favor, selecciona la nota de Obsidian que será el punto de partida (nota índice) para la exportación.")
    file_path = filedialog.askopenfilename(
        title="Selecciona tu Nota Índice de Obsidian",
        initialdir=OBSIDIAN_VAULT_ROOT if OBSIDIAN_VAULT_ROOT.exists() else os.getcwd(),
        filetypes=[("Markdown files", "*.md"), ("All files", "*.*")]
    )
    if file_path:
        return Path(file_path)
    else:
        messagebox.showwarning("Cancelado", "No se seleccionó ninguna nota. El script se cerrará.")
        sys.exit() # Cierra el script si el usuario cancela

def find_file_in_vault(target_name_or_path: str, vault_root: Path, file_extensions: list = [".md"]) -> Path | None:
    """
    Busca un archivo por su nombre (con o sin extensión) o por una ruta relativa/completa
    dentro del vault de Obsidian. Devuelve la primera ruta completa encontrada.
    
    Args:
        target_name_or_path (str): Nombre del archivo (ej. "Mi Nota", "Mi Nota.md") 
                                   o ruta relativa (ej. "SubCarpeta/Mi Nota.md").
        vault_root (Path): Ruta al directorio raíz del vault de Obsidian.
        file_extensions (list): Lista de extensiones válidas a buscar (ej. [".md", ".png"]).
                                Si target_name_or_path ya tiene una extensión, se prioriza esa.
    """
    # Limpiar el target_name_or_path para manejar alias o secciones (ej. "Mi Nota#Seccion")
    # Si contiene '/', asumir que es una ruta parcial dentro del vault.
    is_path_like = '/' in target_name_or_path or '\\' in target_name_or_path
    
    # Extraer el nombre base del archivo y su posible extensión
    # Esto maneja tanto "Mi Nota" como "SubCarpeta/Mi Nota.md"
    target_path_obj = Path(target_name_or_path)
    base_name_no_ext = target_path_obj.stem # "Mi Nota" de "Mi Nota.md"
    potential_ext = target_path_obj.suffix.lower() # ".md" de "Mi Nota.md"

    search_filenames = []
    if potential_ext and potential_ext in [ext.lower() for ext in file_extensions]:
        search_filenames.append(target_path_obj.name.lower()) # "Mi Nota.md"
    else: # Si no hay extensión o no coincide con las esperadas, añadir todas las extensiones
        for ext in file_extensions:
            search_filenames.append(f"{base_name_no_ext.lower()}{ext.lower()}")
    
    print(f"DEBUG: Buscando '{target_name_or_path}' (base: '{base_name_no_ext}', ext: '{potential_ext}') con nombres: {search_filenames}")

    for root_dir, _, files in os.walk(vault_root):
        current_dir_path = Path(root_dir)
        
        # OMITIR las carpetas de EXCLUDE_FOLDERS durante la búsqueda recursiva.
        # No queremos que el script intente seguir enlaces o encontrar archivos dentro de ellas.
        try:
            relative_to_vault = current_dir_path.relative_to(vault_root)
            if any(folder_name in relative_to_vault.parts for folder_name in EXCLUDE_FOLDERS):
                print(f"DEBUG: Saltando directorio excluido: {relative_to_vault}")
                continue
        except ValueError:
            # Esto ocurre si current_dir_path no es descendiente de vault_root, lo cual no debería pasar con os.walk
            pass 

        for file in files:
            file_path = current_dir_path / file
            
            # Comprobar si el archivo coincide con alguno de los nombres que buscamos
            if file.lower() in search_filenames:
                print(f"DEBUG: Posible coincidencia encontrada: {file_path}")
                # Si el target era una ruta parcial (ej. "SubCarpeta/Mi Nota.md"), verificar que la ruta relativa coincida
                if is_path_like:
                    try:
                        # Crear una ruta relativa de la coincidencia encontrada desde el vault_root
                        relative_found_path = file_path.relative_to(vault_root)
                        # Comprobar si termina con la ruta parcial del target
                        if str(relative_found_path).lower().endswith(target_name_or_path.lower()):
                            print(f"DEBUG: Coincidencia de ruta parcial exitosa: {file_path}")
                            return file_path
                    except ValueError:
                        # Si no es relativo al vault_root, algo está mal, ignorar.
                        pass
                else: # Si el target era solo un nombre de archivo, devolver la primera coincidencia
                    print(f"DEBUG: Coincidencia de nombre de archivo exitosa: {file_path}")
                    return file_path

    print(f"DEBUG: find_file_in_vault no encontró '{target_name_or_path}' en {vault_root} con extensiones {file_extensions}")
    return None

def get_export_destination_dir(initial_note_name: str) -> Path:
    """
    Genera la ruta completa de la carpeta de exportación temporal.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
    # El nombre de la carpeta no usará el nombre de la nota, solo la marca de tiempo.
    folder_name = f"Export_from_obsidian_{timestamp}"

    # Asegurarse de que la ruta base exista
    DEFAULT_EXPORT_BASE_DIR.mkdir(parents=True, exist_ok=True)

    return DEFAULT_EXPORT_BASE_DIR / folder_name

# --- LÓGICA DE PROCESAMIENTO DE NOTAS ---

def process_note_content(note_path: Path, visited_notes: set, notes_to_copy_content: dict, attachments_to_copy: set):
    """
    Procesa una nota: extrae enlaces, resuelve transclusiones y adjuntos recursivamente.
    visited_notes: Conjunto de rutas de notas ya procesadas para evitar bucles infinitos.
    notes_to_copy_content: Diccionario para almacenar el contenido modificado de las notas. {Path_original: Contenido_modificado}
    attachments_to_copy: Conjunto de rutas de adjuntos a copiar.
    """
    if note_path in visited_notes:
        print(f"DEBUG: Nota ya visitada, saltando recursión para: {note_path.name}")
        return "" # Ya procesada, no necesitamos procesarla de nuevo ni añadirla al contenido

    visited_notes.add(note_path)
    print(f"DEBUG: Procesando nota: {note_path.name}")

    try:
        content = note_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"ERROR: No se pudo leer la nota {note_path}: {e}")
        return f""

    # --- Resolver transclusiones (lo hacemos primero para que sus enlaces también se procesen) ---
    def replace_embed(match):
        embed_target_full = match.group(1).strip()
        # Limpiar el target: eliminar aliases, secciones (#), o bloques (^)
        # Ejemplo: "Mi Nota|Alias" -> "Mi Nota"
        # "Mi Nota#Seccion" -> "Mi Nota"
        embed_target_clean = re.split(r'[#\|]', embed_target_full)[0].strip()
        
        print(f"DEBUG: Transclusión detectada: '{embed_target_full}' -> Limpio: '{embed_target_clean}' en '{note_path.name}'")

        if not embed_target_clean:
            print(f"DEBUG: Target de transclusión vacío en '{note_path.name}'.")
            return match.group(0) # Mantiene el enlace original si está vacío

        # Buscar la nota transcluida (solo archivos .md)
        embedded_note_path = find_file_in_vault(embed_target_clean, OBSIDIAN_VAULT_ROOT, file_extensions=[".md"])
        if embedded_note_path and embedded_note_path != note_path: # Evitar transcluirse a sí misma
            print(f"DEBUG: Transcluyendo contenido de: {embedded_note_path.name}")
            # Procesar recursivamente la nota incrustada y obtener su contenido.
            # El contenido devuelto ya estará procesado y sin sus propias transclusiones.
            # No se añade a notes_to_copy_content aquí, ya que se incrusta.
            embedded_content = process_note_content(embedded_note_path, visited_notes, notes_to_copy_content, attachments_to_copy)
            return embedded_content
        else:
            print(f"Advertencia: No se pudo encontrar o transcluir la nota '{embed_target_full}' (limpio: '{embed_target_clean}') desde '{note_path.name}'.")
            # Podríamos mantener el enlace original o un mensaje de error para el PDF
            return match.group(0) 
            # O f"" # Para un marcador visible

    content = EMBED_LINK_PATTERN.sub(replace_embed, content)

    # --- Extraer y procesar wikilinks (después de transclusiones para que no se dupliquen) ---
    for match in WIKILINK_PATTERN.finditer(content):
        linked_target_full = match.group(1).strip()
        # Limpiar el target: eliminar aliases, secciones (#), o bloques (^)
        linked_target_clean = re.split(r'[#\|]', linked_target_full)[0].strip()
        
        print(f"DEBUG: Wikilink detectado: '{linked_target_full}' -> Limpio: '{linked_target_clean}' en '{note_path.name}'")

        if not linked_target_clean:
            print(f"DEBUG: Target de wikilink vacío en '{note_path.name}'.")
            continue

        found_linked_note_path = find_file_in_vault(linked_target_clean, OBSIDIAN_VAULT_ROOT, file_extensions=[".md"])
        if found_linked_note_path and found_linked_note_path not in visited_notes:
            print(f"DEBUG: Enlace a nueva nota, iniciando recursión para: {found_linked_note_path.name}")
            process_note_content(found_linked_note_path, visited_notes, notes_to_copy_content, attachments_to_copy)
        elif found_linked_note_path and found_linked_note_path in visited_notes:
            print(f"DEBUG: Enlace a nota ya procesada: {found_linked_note_path.name} en '{note_path.name}'.")
        else:
            print(f"Advertencia: No se encontró la nota enlazada '{linked_target_full}' (limpio: '{linked_target_clean}') desde '{note_path.name}'.")


    # --- Extraer y procesar adjuntos ---
    # Para ![[adjunto.png]] (embebidos de Obsidian que son adjuntos)
    for match in EMBED_LINK_PATTERN.finditer(content):
        attachment_name_or_path = match.group(1).strip()
        # No procesar si es un wikilink a una nota markdown (ya lo hicimos arriba)
        # Una forma más robusta es intentar resolverlo como archivo MD primero.
        if find_file_in_vault(attachment_name_or_path, OBSIDIAN_VAULT_ROOT, file_extensions=[".md"]):
            continue 

        # Intentar buscar el adjunto con varias extensiones posibles
        # Esto busca en el vault un archivo con ese nombre y cualquier de las extensiones listadas
        found_attachment_path = find_file_in_vault(attachment_name_or_path, OBSIDIAN_VAULT_ROOT, 
                                                   file_extensions=[".png", ".jpg", ".jpeg", ".gif", ".pdf", ".html", ".mp4", ".mov", ".webm", ".webp", ".mp3", ".wav"]) # Añade más extensiones si es necesario

        if found_attachment_path:
            attachments_to_copy.add(found_attachment_path)
            print(f"DEBUG: Adjunto Obsidian detectado y añadido: {found_attachment_path.name} en '{note_path.name}'")
            # Modificar la ruta del adjunto en el contenido para que sea relativa a la nueva ubicación
            # Ejemplo: ![[03 - Resources/Assets/imagen.png]] -> ![[Assets/imagen.png]]
            # Asumimos que replicaremos la estructura del vault o de 03 - Resources
            
            # Calcular la ruta que será relativa a la carpeta de exportación
            # Para esto, simplemente usamos la ruta relativa al vault_root
            relative_to_vault = found_attachment_path.relative_to(OBSIDIAN_VAULT_ROOT)
            
            # El reemplazo debe ser sobre el patrón original completo del embed para evitar errores
            # Ejemplo: ![[ruta/a/imagen.png|alias]] -> ![[ruta/a/imagen.png]] si el alias no es deseado en la salida
            # O simplemente reemplazar la parte interna de la ruta si el formato es fijo
            
            # Vamos a reemplazar el texto interno del embed por la ruta relativa desde la carpeta de exportación.
            # Esto asume que el script de copia replicará esa estructura.
            # match.group(0) es el string completo del embed, ej. ![[03 - Resources/Assets/imagen.png]]
            # match.group(1) es la parte interna, ej. 03 - Resources/Assets/imagen.png
            content = content.replace(f"![[{attachment_name_or_path}]]", f"![[{relative_to_vault}]]")
            print(f"DEBUG: Ruta de adjunto Obsidian modificada de '{attachment_name_or_path}' a '{relative_to_vault}'")

        else:
            print(f"Advertencia: No se encontró el adjunto de Obsidian '{attachment_name_or_path}' desde '{note_path.name}'.")
    
    # Para ![Texto alternativo](ruta/a/imagen.png) (Markdown estándar)
    for match in MARKDOWN_IMAGE_PATTERN.finditer(content):
        image_path_in_md = match.group(1).strip()
        print(f"DEBUG: Adjunto Markdown detectado: '{image_path_in_md}' en '{note_path.name}'")
        
        full_image_path = None
        # Intento 1: Es una ruta absoluta
        if Path(image_path_in_md).is_absolute():
            if Path(image_path_in_md).exists():
                full_image_path = Path(image_path_in_md)
        # Intento 2: Es una ruta relativa a la nota actual
        elif (note_path.parent / image_path_in_md).exists():
            full_image_path = (note_path.parent / image_path_in_md).resolve()
        else:
            # Intento 3: Buscar por nombre de archivo en todo el vault (especialmente 03 - Resources)
            image_name_from_path = Path(image_path_in_md).name # Extraer solo el nombre del archivo
            full_image_path = find_file_in_vault(image_name_from_path, OBSIDIAN_VAULT_ROOT, 
                                               file_extensions=[".png", ".jpg", ".jpeg", ".gif", ".pdf", ".webp"]) # Añade más extensiones

        if full_image_path and full_image_path.exists():
            attachments_to_copy.add(full_image_path)
            print(f"DEBUG: Adjunto Markdown estándar añadido: {full_image_path.name} en '{note_path.name}'")
            
            # Ajustar la ruta en el contenido para que Pandoc pueda encontrarla en la carpeta temporal
            # Similar a como lo hicimos con los embeds de Obsidian
            relative_to_vault = full_image_path.relative_to(OBSIDIAN_VAULT_ROOT)
            
            # match.group(1) es la ruta original dentro de los paréntesis del enlace
            content = content.replace(f"({image_path_in_md})", f"({relative_to_vault})")
            print(f"DEBUG: Ruta de adjunto Markdown estándar modificada de '{image_path_in_md}' a '{relative_to_vault}'")
        else:
            print(f"Advertencia: No se encontró el adjunto de Markdown estándar '{image_path_in_md}' desde '{note_path.name}'.")


    # Almacenar el contenido modificado de la nota
    notes_to_copy_content[note_path] = content
    return content # Retorna el contenido procesado para transclusiones anidadas

# --- LÓGICA PRINCIPAL DEL SCRIPT ---
if __name__ == "__main__":
    print("Iniciando script de preparación de notas para exportación...")

    # 1. Obtener la ruta del vault de Obsidian
    if not OBSIDIAN_VAULT_ROOT.exists() or not OBSIDIAN_VAULT_ROOT.is_dir():
        messagebox.showerror("Error de Configuración", f"La ruta de tu vault de Obsidian configurada no es válida: {OBSIDIAN_VAULT_ROOT}\nPor favor, edita el script y ajusta la variable OBSIDIAN_VAULT_ROOT.")
        sys.exit()

    # 2. Obtener la nota índice
    index_note_path = get_note_path_from_input()
    if not index_note_path: # Si el usuario cierra el diálogo
        sys.exit("Script terminado porque no se seleccionó ninguna nota.")
    print(f"Procesando nota índice: {index_note_path}")

    # 3. Preparar la carpeta de destino de la exportación
    export_target_dir = get_export_destination_dir(index_note_path.name)
    export_target_dir.mkdir(parents=True, exist_ok=True)
    print(f"Las notas y adjuntos se copiarán a: {export_target_dir}")

    # 4. Inicializar estructuras para la recopilación recursiva
    collected_processed_notes_content = {} # {ruta_original_Path: contenido_procesado_str}
    collected_attachments = set() # {ruta_original_Path}
    visited_notes_set = set() # Para evitar bucles infinitos en la recursión

    # 5. Iniciar el procesamiento recursivo desde la nota índice
    print("\nIniciando recopilación recursiva de notas y adjuntos...")
    # Asegúrate de que la nota índice sea procesada por la función recursiva
    process_note_content(index_note_path, visited_notes_set, collected_processed_notes_content, collected_attachments)
    
    print(f"\n--- Recopilación Finalizada ---")
    print(f"Notas Markdown encontradas y procesadas: {len(collected_processed_notes_content)}")
    for note_path_item in collected_processed_notes_content.keys():
        print(f"  - {note_path_item.relative_to(OBSIDIAN_VAULT_ROOT)}")
    print(f"Adjuntos encontrados: {len(collected_attachments)}")
    for att_path_item in collected_attachments:
        print(f"  - {att_path_item.relative_to(OBSIDIAN_VAULT_ROOT)}")
    print("--------------------------------")


    # 6. Copiar los archivos procesados y adjuntos a la carpeta temporal
    print("\nCopiando archivos a la carpeta temporal...")
    try:
        # Copiar notas Markdown procesadas
        for original_path, content in collected_processed_notes_content.items():
            # Replicar la estructura de carpetas de la nota dentro de la carpeta de destino
            relative_path_from_vault = original_path.relative_to(OBSIDIAN_VAULT_ROOT)
            destination_path = export_target_dir / relative_path_from_vault
            
            destination_path.parent.mkdir(parents=True, exist_ok=True) # Asegura que la subcarpeta exista
            
            # Escribir el contenido procesado en el archivo de destino
            destination_path.write_text(content, encoding='utf-8')
            print(f"Copiado y procesado nota: {original_path.name} -> {destination_path.relative_to(export_target_dir)}")

        # Copiar adjuntos, replicando su estructura relativa al vault
        for attachment_path in collected_attachments:
            relative_path_from_vault = attachment_path.relative_to(OBSIDIAN_VAULT_ROOT)
            destination_attachment_path = export_target_dir / relative_path_from_vault

            destination_attachment_path.parent.mkdir(parents=True, exist_ok=True) # Asegura que la subcarpeta exista
            shutil.copy2(attachment_path, destination_attachment_path)
            print(f"Copiado adjunto: {attachment_path.name} -> {destination_attachment_path.relative_to(export_target_dir)}")

        messagebox.showinfo("Proceso Completo", f"¡La preparación de notas ha finalizado!\n\nSe han copiado {len(collected_processed_notes_content)} notas y {len(collected_attachments)} adjuntos a:\n{export_target_dir}\n\nAhora puedes usar los scripts de conversión.")

    except Exception as e:
        messagebox.showerror("Error al Copiar Archivos", f"Ocurrió un error durante el copiado de notas/adjuntos: {e}")
        print(f"ERROR fatal durante el copiado: {e}")

    print("Script de preparación finalizado.")