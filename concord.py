import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.simpledialog as simpledialog
from tkinter import filedialog
import json
import numpy as np  # Для матриц и нормализации

class ConcordanceAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("Анализ по методу Конкорданса (ELECTRE I)")
        self.root.geometry("1200x700")

        self.alternatives = []      # список названий альтернатив
        self.criteria = []          # список словарей: {'name': str, 'direction': 'max' или 'min', 'weight': float}
        self.data = {}              # {alt: {crit_name: value}}

        self.concordance_threshold = 0.75
        self.discordance_threshold = 0.25

        self.setup_ui()
        self.update_table()

    def setup_ui(self):
        # === Верхняя панель ===
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=10)

        # Добавление альтернативы
        ttk.Label(top_frame, text="Альтернатива:").grid(row=0, column=0, padx=5, sticky="e")
        self.alt_entry = ttk.Entry(top_frame, width=25)
        self.alt_entry.grid(row=0, column=1, padx=5)
        self.alt_entry.bind("<Return>", lambda e: self.add_alternative())
        ttk.Button(top_frame, text="Добавить", command=self.add_alternative).grid(row=0, column=2, padx=5)

        # Добавление критерия
        ttk.Label(top_frame, text="Критерий:").grid(row=1, column=0, padx=5, sticky="e")
        self.crit_entry = ttk.Entry(top_frame, width=20)
        self.crit_entry.grid(row=1, column=1, padx=5)
        self.crit_entry.bind("<Return>", lambda e: self.add_criterion())

        self.direction_var = tk.StringVar(value="max")
        ttk.Radiobutton(top_frame, text="↑ Максимизация", variable=self.direction_var, value="max").grid(row=1, column=2, padx=5)
        ttk.Radiobutton(top_frame, text="↓ Минимизация", variable=self.direction_var, value="min").grid(row=1, column=3, padx=5)

        ttk.Label(top_frame, text="Вес:").grid(row=1, column=4, padx=5, sticky="e")
        self.weight_entry = ttk.Entry(top_frame, width=10)
        self.weight_entry.insert(0, "1.0")
        self.weight_entry.grid(row=1, column=5, padx=5)

        ttk.Button(top_frame, text="Добавить критерий", command=self.add_criterion).grid(row=1, column=6, padx=10)

        # Пороги
        ttk.Label(top_frame, text="Порог конкорданса (c*):").grid(row=0, column=3, padx=20, sticky="e")
        self.c_thresh_entry = ttk.Entry(top_frame, width=10)
        self.c_thresh_entry.insert(0, str(self.concordance_threshold))
        self.c_thresh_entry.grid(row=0, column=4, padx=5)

        ttk.Label(top_frame, text="Порог дискорданса (d*):").grid(row=0, column=5, padx=5, sticky="e")
        self.d_thresh_entry = ttk.Entry(top_frame, width=10)
        self.d_thresh_entry.insert(0, str(self.discordance_threshold))
        self.d_thresh_entry.grid(row=0, column=6, padx=5)

        # Кнопки
        ttk.Button(top_frame, text="Загрузить JSON", command=self.load_json).grid(row=0, column=7, padx=10)
        ttk.Button(top_frame, text="Вычислить Конкорданс", command=self.compute_concordance, style="Accent.TButton").grid(row=0, column=8, padx=20)

        # === Основная таблица ===
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(table_frame, columns=("alt",), show="headings", height=15)
        self.tree.heading("alt", text="Альтернатива")
        self.tree.column("alt", width=180, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # Контекстное меню
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Переименовать альтернативу", command=self.rename_alternative)
        self.context_menu.add_command(label="Удалить альтернативу", command=self.delete_alternative)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Переименовать критерий", command=self.rename_criterion)
        self.context_menu.add_command(label="Изменить направление критерия", command=self.change_criterion_direction)
        self.context_menu.add_command(label="Изменить вес критерия", command=self.change_criterion_weight)
        self.context_menu.add_command(label="Удалить критерий", command=self.delete_criterion_from_menu)

        # === Результаты ===
        result_frame = ttk.LabelFrame(self.root, text="Конкорданс-оптимальные альтернативы (kernel)")
        result_frame.pack(fill="x", padx=10, pady=10)

        self.result_tree = ttk.Treeview(result_frame, columns=("alt",), show="headings", height=5)
        self.result_tree.heading("alt", text="Оптимальные альтернативы")
        self.result_tree.column("alt", anchor="center")
        self.result_tree.pack(fill="x", padx=5, pady=5)

        # Стили
        style = ttk.Style()
        style.configure("Accent.TButton", foreground="white", background="#0078D7")

    def add_alternative(self):
        name = self.alt_entry.get().strip()
        if not name or name in self.alternatives:
            messagebox.showwarning("Ошибка", "Имя пустое или уже существует")
            return
        self.alternatives.append(name)
        self.data[name] = {crit["name"]: 0.0 for crit in self.criteria}
        self.alt_entry.delete(0, "end")
        self.update_table()

    def add_criterion(self):
        name = self.crit_entry.get().strip()
        if not name or any(c["name"] == name for c in self.criteria):
            messagebox.showwarning("Ошибка", "Имя пустое или уже существует")
            return
        direction = self.direction_var.get()
        try:
            weight = float(self.weight_entry.get())
            if weight <= 0:
                raise ValueError
        except:
            messagebox.showwarning("Ошибка", "Вес должен быть положительным числом")
            return
        self.criteria.append({"name": name, "direction": direction, "weight": weight})
        for alt in self.alternatives:
            self.data[alt][name] = 0.0
        self.crit_entry.delete(0, "end")
        self.weight_entry.delete(0, "end")
        self.weight_entry.insert(0, "1.0")
        self.update_table()

    def load_json(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            # Критерии
            existing_crit_names = {c['name'] for c in self.criteria}
            for crit in loaded.get('criteria', []):
                if crit['name'] not in existing_crit_names:
                    self.criteria.append(crit)
                    for alt in self.alternatives:
                        self.data[alt][crit['name']] = 0.0
            # Альтернативы
            existing_alts = set(self.alternatives)
            for alt in loaded.get('alternatives', []):
                if alt not in existing_alts:
                    self.alternatives.append(alt)
                    self.data[alt] = {c['name']: 0.0 for c in self.criteria}
            # Данные
            for alt, crit_dict in loaded.get('data', {}).items():
                if alt not in self.alternatives:
                    self.alternatives.append(alt)
                    self.data[alt] = {c['name']: 0.0 for c in self.criteria}
                for crit_name, value in crit_dict.items():
                    if crit_name in [c['name'] for c in self.criteria]:
                        self.data[alt][crit_name] = value
            self.update_table()
            messagebox.showinfo("Успех", "JSON загружен")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить: {str(e)}")

    def update_table(self):
        self.tree.delete(*self.tree.get_children())
        crit_names = [crit["name"] for crit in self.criteria]

        self.tree["columns"] = ("alt",) + tuple(crit_names)
        self.tree.heading("alt", text="Альтернатива")
        self.tree.column("alt", width=180)

        for crit in self.criteria:
            symbol = "↑" if crit["direction"] == "max" else "↓"
            self.tree.heading(crit["name"], text=f"{crit['name']} {symbol} (вес: {crit['weight']:.2f})")
            self.tree.column(crit["name"], width=120, anchor="center")

        for alt in self.alternatives:
            values = [alt] + [self.data[alt].get(c["name"], "") for c in self.criteria]
            self.tree.insert("", "end", iid=alt, values=values)

    def on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item_id or column == "#0" or column == "#1":
            return

        col_idx = int(column[1:]) - 1
        if col_idx >= len(self.criteria):
            return

        crit_name = self.criteria[col_idx - 1]["name"]
        alt_name = item_id

        x, y, width, height = self.tree.bbox(item_id, column)
        entry = ttk.Entry(self.tree)
        entry.insert(0, self.data[alt_name][crit_name])
        entry.select_range(0, "end")
        entry.focus()

        def save_edit(event=None):
            try:
                value = float(entry.get())
                self.data[alt_name][crit_name] = value
                self.update_table()
            except ValueError:
                messagebox.showerror("Ошибка", "Введите число!")
            entry.destroy()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)
        entry.place(x=x, y=y, width=width, height=height)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def rename_alternative(self):
        item = self.tree.selection()
        if not item:
            return
        old_name = item[0]
        new_name = simpledialog.askstring("Переименование", "Новое название:", initialvalue=old_name)
        if new_name and new_name != old_name and new_name not in self.alternatives:
            idx = self.alternatives.index(old_name)
            self.alternatives[idx] = new_name
            self.data[new_name] = self.data.pop(old_name)
            self.update_table()

    def delete_alternative(self):
        item = self.tree.selection()
        if not item:
            return
        alt = item[0]
        if messagebox.askyesno("Удалить", f"Удалить «{alt}»?"):
            self.alternatives.remove(alt)
            self.data.pop(alt, None)
            self.update_table()

    def rename_criterion(self):
        col = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())
        if col in ("#0", "#1"):
            return
        col_idx = int(col[1:]) - 2
        if 0 <= col_idx < len(self.criteria):
            old_name = self.criteria[col_idx]["name"]
            new_name = simpledialog.askstring("Переименование", "Новое название:", initialvalue=old_name)
            if new_name and new_name != old_name and not any(c["name"] == new_name for c in self.criteria):
                self.criteria[col_idx]["name"] = new_name
                for alt in self.alternatives:
                    self.data[alt][new_name] = self.data[alt].pop(old_name)
                self.update_table()

    def change_criterion_direction(self):
        col = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())
        if col in ("#0", "#1"):
            return
        col_idx = int(col[1:]) - 2
        if 0 <= col_idx < len(self.criteria):
            crit = self.criteria[col_idx]
            new_dir = "min" if crit["direction"] == "max" else "max"
            if messagebox.askyesno("Изменить", f"Изменить на {'↓ Мин' if new_dir == 'min' else '↑ Макс'}?"):
                crit["direction"] = new_dir
                self.update_table()

    def change_criterion_weight(self):
        col = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())
        if col in ("#0", "#1"):
            return
        col_idx = int(col[1:]) - 2
        if 0 <= col_idx < len(self.criteria):
            crit = self.criteria[col_idx]
            new_weight = simpledialog.askfloat("Изменить вес", "Новый вес (>0):", initialvalue=crit["weight"])
            if new_weight and new_weight > 0:
                crit["weight"] = new_weight
                self.update_table()

    def delete_criterion_from_menu(self):
        col = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())
        if col in ("#0", "#1"):
            return
        col_idx = int(col[1:]) - 2
        if 0 <= col_idx < len(self.criteria):
            crit_name = self.criteria[col_idx]["name"]
            if messagebox.askyesno("Удалить", f"Удалить «{crit_name}»?"):
                self.criteria.pop(col_idx)
                for alt in self.alternatives:
                    self.data[alt].pop(crit_name, None)
                self.update_table()

    def compute_concordance(self):
        if len(self.alternatives) < 2 or not self.criteria:
            messagebox.showinfo("Результат", "Недостаточно данных")
            return

        try:
            self.concordance_threshold = float(self.c_thresh_entry.get())
            self.discordance_threshold = float(self.d_thresh_entry.get())
            if not (0 <= self.concordance_threshold <= 1 and 0 <= self.discordance_threshold <= 1):
                raise ValueError
        except:
            messagebox.showerror("Ошибка", "Пороги должны быть в [0,1]")
            return

        n = len(self.alternatives)
        m = len(self.criteria)
        alt_list = self.alternatives

        # Матрица значений
        values = np.zeros((n, m))
        weights = np.array([c["weight"] for c in self.criteria])
        directions = [1 if c["direction"] == "max" else -1 for c in self.criteria]

        for i, alt in enumerate(alt_list):
            for j, crit in enumerate(self.criteria):
                values[i, j] = self.data[alt][crit["name"]] * directions[j]  # Инвертируем min

        # Нормализация (min-max)
        min_vals = values.min(axis=0)
        max_vals = values.max(axis=0)
        denom = max_vals - min_vals
        denom[denom == 0] = 1  # Избежать деления на 0
        norm_values = (values - min_vals) / denom

        # Concordance matrix
        concordance = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                better = norm_values[i] >= norm_values[j]
                concordance[i, j] = weights[better].sum() / weights.sum()

        # Discordance matrix
        discordance = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                worse = norm_values[j] - norm_values[i]
                discordance[i, j] = worse.max() if worse.max() > 0 else 0

        # Outranking matrix
        outranking = (concordance >= self.concordance_threshold) & (discordance <= self.discordance_threshold)

        # Kernel: альтернативы, которые не outranked никем
        dominated = np.any(outranking, axis=0)  # Если кто-то outranks j
        kernel = [alt_list[j] for j in range(n) if not dominated[j]]

        # Вывод
        self.result_tree.delete(*self.result_tree.get_children())
        if not kernel:
            self.result_tree.insert("", "end", values=("Нет оптимальных альтернатив",))
        else:
            for alt in sorted(kernel):
                self.result_tree.insert("", "end", values=(alt,))

        messagebox.showinfo("Готово", f"Найдено {len(kernel)} оптимальных альтернатив")

# Запуск
if __name__ == "__main__":
    root = tk.Tk()
    app = ConcordanceAnalyzer(root)
    root.mainloop()