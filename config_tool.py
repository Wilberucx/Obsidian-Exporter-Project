import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import json

CONFIG_FILE = Path("config.json")

class ConfigApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Herramienta de Configuración - Obsidian Exporter")
        self.root.geometry("600x450")

        self.config = self.load_config()

        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Sección de Vaults ---
        vault_frame = tk.LabelFrame(main_frame, text="Rutas de los Vaults de Obsidian", padx=5, pady=5)
        vault_frame.pack(fill=tk.X, pady=5)
        self.vault_listbox = tk.Listbox(vault_frame, height=5)
        self.vault_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.update_vault_listbox()
        vault_buttons_frame = tk.Frame(vault_frame)
        vault_buttons_frame.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Button(vault_buttons_frame, text="Añadir Vault", command=self.add_vault).pack(fill=tk.X, pady=2)
        tk.Button(vault_buttons_frame, text="Quitar Seleccionado", command=self.remove_vault).pack(fill=tk.X, pady=2)

        # --- Sección de Carpeta de Exportación ---
        export_frame = tk.LabelFrame(main_frame, text="Directorio de Exportación por Defecto", padx=5, pady=5)
        export_frame.pack(fill=tk.X, pady=5)
        self.export_dir_var = tk.StringVar(value=self.config.get("export_dir", "No seleccionado"))
        tk.Entry(export_frame, textvariable=self.export_dir_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(export_frame, text="Seleccionar...", command=self.select_export_dir).pack(side=tk.RIGHT)

        # --- Sección de Carpetas Excluidas ---
        exclude_frame = tk.LabelFrame(main_frame, text="Carpetas a Excluir (por nombre)", padx=5, pady=5)
        exclude_frame.pack(fill=tk.X, pady=5)
        self.exclude_listbox = tk.Listbox(exclude_frame, height=5)
        self.exclude_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.update_exclude_listbox()
        exclude_buttons_frame = tk.Frame(exclude_frame)
        exclude_buttons_frame.pack(side=tk.RIGHT, fill=tk.Y)
        # ### CAMBIO: El botón ahora llama a una función diferente ###
        tk.Button(exclude_buttons_frame, text="Añadir Exclusión", command=self.add_exclude_by_selection).pack(fill=tk.X, pady=2)
        tk.Button(exclude_buttons_frame, text="Quitar Seleccionada", command=self.remove_exclude).pack(fill=tk.X, pady=2)
        
        tk.Button(main_frame, text="Guardar y Salir", command=self.save_and_exit, bg="lightblue").pack(pady=20)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_config(self):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {"vault_paths": [], "export_dir": "", "exclude_folders": [".obsidian", ".trash"]}

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)

    def update_vault_listbox(self):
        self.vault_listbox.delete(0, tk.END)
        for path in self.config.get("vault_paths", []):
            self.vault_listbox.insert(tk.END, path)

    def update_exclude_listbox(self):
        self.exclude_listbox.delete(0, tk.END)
        for folder in self.config.get("exclude_folders", []):
            self.exclude_listbox.insert(tk.END, folder)
            
    def add_vault(self):
        path = filedialog.askdirectory(title="Selecciona la carpeta raíz de un Vault de Obsidian")
        if path:
            standard_path = str(Path(path).as_posix())
            if standard_path not in self.config["vault_paths"]:
                self.config["vault_paths"].append(standard_path)
                self.update_vault_listbox()

    def remove_vault(self):
        selected_indices = self.vault_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Advertencia", "Por favor, selecciona un vault de la lista para quitar.")
            return
        for i in sorted(selected_indices, reverse=True):
            del self.config["vault_paths"][i]
        self.update_vault_listbox()
    
    def select_export_dir(self):
        path = filedialog.askdirectory(title="Selecciona la carpeta donde se guardarán las exportaciones")
        if path:
            standard_path = str(Path(path).as_posix())
            self.config["export_dir"] = standard_path
            self.export_dir_var.set(standard_path)
            
    # ### CAMBIO: Nueva función para añadir exclusiones por selección de carpeta ###
    def add_exclude_by_selection(self):
        """Abre un diálogo para seleccionar una carpeta y añade su nombre a la lista de exclusión."""
        vaults = self.config.get("vault_paths", [])
        if not vaults:
            messagebox.showerror("Error", "Debes configurar al menos un vault antes de añadir exclusiones.")
            return

        # Usar la ruta del primer vault como punto de partida para el diálogo
        initial_dir = vaults[0]
        
        folder_path_str = filedialog.askdirectory(
            title="Selecciona una carpeta para excluir su nombre",
            initialdir=initial_dir
        )
        
        if folder_path_str:
            # Extraer solo el nombre de la carpeta de la ruta seleccionada
            folder_name = Path(folder_path_str).name
            if folder_name and folder_name not in self.config["exclude_folders"]:
                self.config["exclude_folders"].append(folder_name)
                self.update_exclude_listbox()
                messagebox.showinfo("Exclusión Añadida", f"Se ha añadido '{folder_name}' a la lista de exclusiones.")
            elif folder_name in self.config["exclude_folders"]:
                 messagebox.showinfo("Información", f"La carpeta '{folder_name}' ya está en la lista de exclusiones.")
            else:
                messagebox.showwarning("Advertencia", "No se pudo obtener un nombre de carpeta válido.")
    
    def remove_exclude(self):
        selected_indices = self.exclude_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Advertencia", "Por favor, selecciona una carpeta de la lista para quitar.")
            return
        for i in sorted(selected_indices, reverse=True):
            del self.config["exclude_folders"][i]
        self.update_exclude_listbox()

    def save_and_exit(self):
        self.save_config()
        messagebox.showinfo("Guardado", "La configuración ha sido guardada con éxito.")
        self.root.destroy()
        
    def on_closing(self):
        if messagebox.askokcancel("Salir", "¿Quieres salir sin guardar los cambios?"):
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ConfigApp(root)
    root.mainloop()