
# Obsidian Exporter Project

Este proyecto es un conjunto de herramientas de Python diseñadas para exportar conocimiento estructurado desde [Obsidian](https://obsidian.md/) a formatos de documentos portátiles como PDF, DOCX y EPUB. La herramienta está pensada para ser flexible, potente y fácil de usar, dándole al usuario un control total sobre el contenido y la estructura de la exportación final.

## Visión General

El flujo de trabajo se divide en dos fases principales, cada una manejada por un script dedicado:

1.  **Construcción del Paquete de Exportación (`export_builder.py`):** Este script toma una nota de inicio de tu vault y, basándose en tus especificaciones, recopila todas las notas y adjuntos relevantes en una carpeta autocontenida y limpia.
2.  **Conversión del Documento (`document_converter.py`):** Este script toma el "paquete de exportación" generado y utiliza la potente herramienta [Pandoc](https://pandoc.org/) para convertirlo en un documento final pulido.

## Características Principales

- **Configuración Intuitiva:** Una herramienta gráfica (`config_tool.py`) para configurar tus vaults, directorios de exportación y carpetas excluidas sin necesidad de editar código.
- **Soporte para Múltiples Vaults:** Configura todos tus vaults de Obsidian y la herramienta detectará automáticamente a cuál pertenece la nota que estás exportando.
- **Dos Modos de Exportación:**
    - **Modo Automático:** Exporta una red de notas basándote en un nivel de profundidad que tú defines (ej. solo enlaces directos, hasta 2 niveles de profundidad, etc.). Ideal para exploraciones rápidas de un tema.
    - **Modo Manual (Recomendado):** Te da control absoluto. Creas una nota "Mapa de Contenido" (MOC) en Obsidian, y la herramienta usará la estructura de esa nota para construir tu documento final, con capítulos y secciones tal como los definiste.
- **Manejo Inteligente de Adjuntos:** Todas las imágenes y otros archivos adjuntos se recopilan y sus rutas se corrigen automáticamente para funcionar en la exportación.
- **Conversión Flexible:** Convierte tus notas a formatos profesionales (PDF, DOCX, EPUB) con características como tabla de contenidos, numeración de secciones y metadatos (título, autor).

## Requisitos

- **Python 3.9+**
- **Librerías de Python:**
  - `PyYAML`: Para procesar los metadatos de las notas.
  - `panflute`: El paquete de filtros de Pandoc que incluye la funcionalidad de inclusión de archivos.
  - Instala ambas con:
    ```bash
    pip install PyYAML panflute
    ```
- **Pandoc:** La herramienta universal de conversión de documentos. Debe estar instalada y accesible en el `PATH` de tu sistema. [Instrucciones de instalación de Pandoc](https://pandoc.org/installing.html).
- **Motor de PDF (Solo para exportar a PDF):** Pandoc necesita un motor de LaTeX. Se recomienda:
  - **MiKTeX** para Windows.
  - **MacTeX** para macOS.
  - **TeX Live** para Linux.
  (Se recomienda usar `xelatex` como motor, que suele venir incluido en estas distribuciones).

### **Configuración del Entorno (¡Importante!)**

Para que esta herramienta funcione correctamente, los filtros de Pandoc que se instalan con Python (como `pandoc-include`) deben ser localizables por Pandoc. Esto requiere que la carpeta de `Scripts` de tu instalación de Python esté en la variable de entorno `PATH` de tu sistema.

**1. Encuentra tu carpeta de Scripts:**

Abre una terminal (CMD o PowerShell) y ejecuta el siguiente comando para obtener la ruta exacta:

```powershell
python -c "import sysconfig; print(sysconfig.get_path('scripts'))"

## Guía de Uso Rápido

**Paso 1: Configuración Inicial (Solo se hace una vez)**

1.  Ejecuta la herramienta de configuración:
    ```bash
    python config_tool.py
    ```
2.  Usa la interfaz gráfica para:
    - Añadir la(s) ruta(s) a tu(s) vault(s) de Obsidian.
    - Seleccionar un directorio donde se guardarán todas las exportaciones.
    - Añadir los nombres de las carpetas que deseas excluir del procesamiento (ej. `_templates`, `Daily Notes`).
3.  Haz clic en "Guardar y Salir". Esto creará un archivo `config.json`.

**Paso 2: Construir un Paquete de Exportación**

1.  Ejecuta el constructor de exportaciones:
    ```bash
    python export_builder.py
    ```
2.  **Selecciona una nota de inicio** desde el diálogo de archivos. La herramienta detectará automáticamente a qué vault pertenece.
3.  **Elige un modo:**
    - **Para el Modo Automático:** La herramienta te pedirá en la consola que elijas un nivel de profundidad.
    - **Para el Modo Manual:** Asegúrate de que tu nota de inicio (tu MOC) contenga el siguiente bloque de metadatos YAML al principio:
      ```yaml
      ---
      export_mode: manual
      export_title: "El Título de Mi Libro"
      export_author: "Tu Nombre"
      ---
      ```
4.  El script creará una nueva carpeta `Export_...` en tu directorio de exportaciones configurado.

**Paso 3: Convertir el Paquete a un Documento Final**

1.  Ejecuta el conversor de documentos:
    ```bash
    python document_converter.py
    ```
2.  **Selecciona la carpeta `Export_...`** que acabas de crear.
3.  Introduce el formato deseado (`pdf`, `docx`, o `epub`) en la ventana que aparece.
4.  ¡Listo! Tu documento final aparecerá en una subcarpeta llamada `_Converted` dentro del paquete de exportación.

---
*Este proyecto está en desarrollo activo. Contribuciones y sugerencias son bienvenidas.*
