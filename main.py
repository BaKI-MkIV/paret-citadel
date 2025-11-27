import tkinter as tk

# рот ебал этот ваш ткинкер угараем короче с помощью 30 ai

from tkinter import ttk, messagebox
import tkinter.simpledialog as simpledialog
from tkinter import filedialog
import json

class ParetoAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("Анализ по методу Парето (многокритериальный выбор)")
        self.root.geometry("1200x700")

        self.alternatives = []      # список названий альтернатив
        self.criteria = []          # список словарей: {'name': str, 'direction': 'max' или 'min'}
        self.data = {}              # {alt: {crit_name: value}}

        self.setup_ui()
        self.update_table()

    def setup_ui(self):
        # === Верхняя панель: добавление альтернатив и критериев ===
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=10)

        # Добавление альтернативы
        ttk.Label(top_frame, text="Альтернатива:").grid(row=0, column=0, padx=5, sticky="e")
        self.alt_entry = ttk.Entry(top_frame, width=25)
        self.alt_entry.grid(row=0, column=1, padx=5)
        self.alt_entry.bind("<Return>", lambda e: self.add_alternative())
        ttk.Button(top_frame, text="Добавить", command=self.add_alternative).grid(row=0, column=2, padx=5)

        # Добавление критерия
        ttk.Label(top_frame, text="Критерий:").grid(row=0, column=3, padx=20, sticky="e")
        self.crit_entry = ttk.Entry(top_frame, width=20)
        self.crit_entry.grid(row=0, column=4, padx=5)
        self.crit_entry.bind("<Return>", lambda e: self.add_criterion())

        self.direction_var = tk.StringVar(value="max")
        ttk.Radiobutton(top_frame, text="↑ Максимизация", variable=self.direction_var, value="max").grid(row=0, column=5, padx=5)
        ttk.Radiobutton(top_frame, text="↓ Минимизация", variable=self.direction_var, value="min").grid(row=0, column=6, padx=5)

        ttk.Button(top_frame, text="Добавить критерий", command=self.add_criterion).grid(row=0, column=7, padx=10)

        # Кнопка загрузки JSON
        ttk.Button(top_frame, text="Загрузить JSON", command=self.load_json).grid(row=0, column=8, padx=10)

        # Кнопка расчёта
        ttk.Button(top_frame, text="Вычислить Парето-фронт", command=self.compute_pareto, style="Accent.TButton").grid(row=0, column=9, padx=20)

        # === Основная таблица ===
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        cols = ("alt",)
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=15)
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

        # Редактирование по двойному клику
        self.tree.bind("<Double-1>", self.on_double_click)

        # Контекстное меню для удаления/переименования/изменения направления
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Переименовать альтернативу", command=self.rename_alternative)
        self.context_menu.add_command(label="Удалить альтернативу", command=self.delete_alternative)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Переименовать критерий", command=self.rename_criterion)
        self.context_menu.add_command(label="Изменить направление критерия", command=self.change_criterion_direction)
        self.context_menu.add_command(label="Удалить критерий", command=self.delete_criterion_from_menu)
        self.tree.bind("<Button-3>", self.show_context_menu)  # Правая кнопка

        # === Таблица результатов ===
        result_frame = ttk.LabelFrame(self.root, text="Парето-оптимальные альтернативы")
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
        if not name:
            return
        if name in self.alternatives:
            messagebox.showwarning("Ошибка", "Такая альтернатива уже существует")
            return
        self.alternatives.append(name)
        self.data[name] = {crit["name"]: 0.0 for crit in self.criteria}
        self.alt_entry.delete(0, "end")
        self.update_table()

    def add_criterion(self):
        name = self.crit_entry.get().strip()
        if not name:
            return
        if any(c["name"] == name for c in self.criteria):
            messagebox.showwarning("Ошибка", "Такой критерий уже существует")
            return
        direction = self.direction_var.get()
        self.criteria.append({"name": name, "direction": direction})
        for alt in self.alternatives:
            self.data[alt][name] = 0.0
        self.crit_entry.delete(0, "end")
        self.update_table()

    def load_json(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            # Добавляем критерии (если не существуют)
            existing_crit_names = {c['name'] for c in self.criteria}
            for crit in loaded.get('criteria', []):
                if crit['name'] not in existing_crit_names:
                    self.criteria.append(crit)
                    # Добавляем новый критерий к существующим альтернативам
                    for alt in self.alternatives:
                        self.data[alt][crit['name']] = 0.0
            # Добавляем альтернативы (если не существуют)
            existing_alts = set(self.alternatives)
            for alt in loaded.get('alternatives', []):
                if alt not in existing_alts:
                    self.alternatives.append(alt)
                    self.data[alt] = {c['name']: 0.0 for c in self.criteria}
            # Обновляем данные (перезаписываем существующие значения, добавляем новые)
            for alt, crit_dict in loaded.get('data', {}).items():
                if alt not in self.alternatives:
                    # Добавляем новую альтернативу, если она есть только в data
                    self.alternatives.append(alt)
                    self.data[alt] = {c['name']: 0.0 for c in self.criteria}
                for crit_name, value in crit_dict.items():
                    if crit_name not in [c['name'] for c in self.criteria]:
                        # Добавляем новый критерий, если он есть только в data (с default 'max')
                        self.criteria.append({'name': crit_name, 'direction': 'max'})
                        for a in self.alternatives:
                            if a != alt:
                                self.data[a][crit_name] = 0.0
                    self.data[alt][crit_name] = value
            self.update_table()
            messagebox.showinfo("Успех", "JSON успешно загружен и добавлен к существующим данным")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить JSON: {str(e)}")

    def update_table(self):
        # Очищаем и перестраиваем столбцы
        self.tree.delete(*self.tree.get_children())
        crit_names = [crit["name"] for crit in self.criteria]

        self.tree["columns"] = ("alt",) + tuple(crit_names)
        self.tree.heading("alt", text="Альтернатива")
        self.tree.column("alt", width=180)

        for crit in self.criteria:
            symbol = "↑" if crit["direction"] == "max" else "↓"
            self.tree.heading(crit["name"], text=f"{crit['name']} {symbol}")
            self.tree.column(crit["name"], width=120, anchor="center")

        for alt in self.alternatives:
            values = [alt] + [self.data[alt].get(c["name"], "") for c in self.criteria]
            self.tree.insert("", "end", iid=alt, values=values)

    def on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item_id or column == "#0" or column == "#1":  # #1 — это "alt"
            return

        col_idx = int(column[1:]) - 1  # #2 → 1 и т.д.
        if col_idx >= len(self.criteria) + 1:
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
        new_name = simpledialog.askstring("Переименование альтернативы", "Новое название:", initialvalue=old_name)
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
        if messagebox.askyesno("Удалить", f"Удалить альтернативу «{alt}»?"):
            self.alternatives.remove(alt)
            self.data.pop(alt, None)
            self.update_table()

    def rename_criterion(self):
        # Определяем столбец по позиции мыши
        col = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())
        if col in ("#0", "#1"):
            return
        col_idx = int(col[1:]) - 2
        if 0 <= col_idx < len(self.criteria):
            old_name = self.criteria[col_idx]["name"]
            new_name = simpledialog.askstring("Переименование критерия", "Новое название:", initialvalue=old_name)
            if new_name and new_name != old_name and not any(c["name"] == new_name for c in self.criteria):
                # Обновляем критерий
                self.criteria[col_idx]["name"] = new_name
                # Обновляем данные
                for alt in self.alternatives:
                    self.data[alt][new_name] = self.data[alt].pop(old_name)
                self.update_table()

    def change_criterion_direction(self):
        # Определяем столбец по позиции мыши
        col = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())
        if col in ("#0", "#1"):
            return
        col_idx = int(col[1:]) - 2
        if 0 <= col_idx < len(self.criteria):
            crit = self.criteria[col_idx]
            current_dir = crit["direction"]
            new_dir = "min" if current_dir == "max" else "max"
            if messagebox.askyesno("Изменить направление", f"Изменить направление для «{crit['name']}» на {'↓ Минимизация' if new_dir == 'min' else '↑ Максимизация'}?"):
                crit["direction"] = new_dir
                self.update_table()

    def delete_criterion_from_menu(self):
        col = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())
        if col in ("#0", "#1"):
            return
        col_idx = int(col[1:]) - 2
        if 0 <= col_idx < len(self.criteria):
            crit_name = self.criteria[col_idx]["name"]
            if messagebox.askyesno("Удалить", f"Удалить критерий «{crit_name}»?"):
                self.criteria.pop(col_idx)
                for alt in self.alternatives:
                    self.data[alt].pop(crit_name, None)
                self.update_table()

    def dominates(self, a, b):
        """Возвращает True, если альтернатива a доминирует над b"""
        better_in_at_least_one = False
        for crit in self.criteria:
            val_a = self.data[a][crit["name"]]
            val_b = self.data[b][crit["name"]]
            if crit["direction"] == "max":
                if val_a > val_b:
                    better_in_at_least_one = True
                elif val_a < val_b:
                    return False
            else:  # min
                if val_a < val_b:
                    better_in_at_least_one = True
                elif val_a > val_b:
                    return False
        return better_in_at_least_one

    def compute_pareto(self):
        if len(self.alternatives) < 2 or not self.criteria:
            messagebox.showinfo("Результат", "Недостаточно данных для анализа")
            return

        pareto_front = []
        for a in self.alternatives:
            dominated = any(self.dominates(b, a) for b in self.alternatives if b != a)
            if not dominated:
                pareto_front.append(a)

        # Очищаем и заполняем таблицу результатов
        self.result_tree.delete(*self.result_tree.get_children())
        if not pareto_front:
            self.result_tree.insert("", "end", values=("Нет Парето-оптимальных альтернатив",))
        else:
            for alt in sorted(pareto_front):
                self.result_tree.insert("", "end", values=(alt,))

        messagebox.showinfo("Готово", f"Найдено {len(pareto_front)} Парето-оптимальных альтернатив")

# Запуск
if __name__ == "__main__":
    root = tk.Tk()
    app = ParetoAnalyzer(root)
    root.mainloop()