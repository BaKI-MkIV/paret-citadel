import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.simpledialog as simpledialog
from tkinter import filedialog
import json
import numpy as np  # Для матриц и расчёта

class ConcordanceAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("Анализ коэффициента конкорданса Кендалла")
        self.root.geometry("1200x700")

        self.alternatives = []      # список названий альтернатив (объектов)
        self.experts = []           # список имён экспертов
        self.data = {}              # {alt: {exp_name: rank (int)}}

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

        # Добавление эксперта
        ttk.Label(top_frame, text="Эксперт:").grid(row=1, column=0, padx=5, sticky="e")
        self.exp_entry = ttk.Entry(top_frame, width=20)
        self.exp_entry.grid(row=1, column=1, padx=5)
        self.exp_entry.bind("<Return>", lambda e: self.add_expert())

        ttk.Button(top_frame, text="Добавить эксперта", command=self.add_expert).grid(row=1, column=2, padx=10)

        # Кнопки
        ttk.Button(top_frame, text="Загрузить JSON", command=self.load_json).grid(row=0, column=3, padx=10)
        ttk.Button(top_frame, text="Вычислить Конкорданс", command=self.compute_concordance, style="Accent.TButton").grid(row=0, column=4, padx=20)

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
        self.context_menu.add_command(label="Переименовать эксперта", command=self.rename_expert)
        self.context_menu.add_command(label="Удалить эксперта", command=self.delete_expert_from_menu)

        # === Результаты ===
        result_frame = ttk.LabelFrame(self.root, text="Результаты анализа конкорданса")
        result_frame.pack(fill="x", padx=10, pady=10)

        self.result_text = tk.Text(result_frame, height=10, wrap="word")
        self.result_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Стили
        style = ttk.Style()
        style.configure("Accent.TButton", foreground="white", background="#0078D7")

    def add_alternative(self):
        name = self.alt_entry.get().strip()
        if not name or name in self.alternatives:
            messagebox.showwarning("Ошибка", "Имя пустое или уже существует")
            return
        self.alternatives.append(name)
        self.data[name] = {exp: 0 for exp in self.experts}
        self.alt_entry.delete(0, "end")
        self.update_table()

    def add_expert(self):
        name = self.exp_entry.get().strip()
        if not name or name in self.experts:
            messagebox.showwarning("Ошибка", "Имя пустое или уже существует")
            return
        self.experts.append(name)
        for alt in self.alternatives:
            self.data[alt][name] = 0
        self.exp_entry.delete(0, "end")
        self.update_table()

    def load_json(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            # Эксперты
            existing_exp = set(self.experts)
            for exp in loaded.get('experts', []):
                if exp not in existing_exp:
                    self.experts.append(exp)
                    for alt in self.alternatives:
                        self.data[alt][exp] = 0
            # Альтернативы
            existing_alts = set(self.alternatives)
            for alt in loaded.get('alternatives', []):
                if alt not in existing_alts:
                    self.alternatives.append(alt)
                    self.data[alt] = {exp: 0 for exp in self.experts}
            # Данные
            for alt, exp_dict in loaded.get('data', {}).items():
                if alt not in self.alternatives:
                    self.alternatives.append(alt)
                    self.data[alt] = {exp: 0 for exp in self.experts}
                for exp_name, rank in exp_dict.items():
                    if exp_name in self.experts:
                        self.data[alt][exp_name] = int(rank)
            self.update_table()
            messagebox.showinfo("Успех", "JSON загружен")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить: {str(e)}")

    def update_table(self):
        self.tree.delete(*self.tree.get_children())

        self.tree["columns"] = ("alt",) + tuple(self.experts)
        self.tree.heading("alt", text="Альтернатива")
        self.tree.column("alt", width=180)

        for exp in self.experts:
            self.tree.heading(exp, text=exp)
            self.tree.column(exp, width=120, anchor="center")

        for alt in self.alternatives:
            values = [alt] + [self.data[alt].get(exp, "") for exp in self.experts]
            self.tree.insert("", "end", iid=alt, values=values)

    def on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item_id or column == "#0" or column == "#1":
            return

        col_idx = int(column[1:]) - 1
        if col_idx >= len(self.experts):
            return

        exp_name = self.experts[col_idx]
        alt_name = item_id

        x, y, width, height = self.tree.bbox(item_id, column)
        entry = ttk.Entry(self.tree)
        entry.insert(0, self.data[alt_name][exp_name])
        entry.select_range(0, "end")
        entry.focus()

        def save_edit(event=None):
            try:
                value = int(entry.get())
                if not 1 <= value <= len(self.alternatives):
                    raise ValueError(f"Ранг должен быть от 1 до {len(self.alternatives)}")
                # Проверка уникальности рангов для эксперта
                ranks_for_exp = [self.data[a][exp_name] for a in self.alternatives if a != alt_name]
                if value in ranks_for_exp:
                    raise ValueError("Ранги должны быть уникальными для эксперта (без ties)")
                self.data[alt_name][exp_name] = value
                self.update_table()
            except ValueError as e:
                messagebox.showerror("Ошибка", str(e))
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

    def rename_expert(self):
        col = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())
        if col in ("#0", "#1"):
            return
        col_idx = int(col[1:]) - 1
        if 0 <= col_idx < len(self.experts):
            old_name = self.experts[col_idx]
            new_name = simpledialog.askstring("Переименование", "Новое название:", initialvalue=old_name)
            if new_name and new_name != old_name and new_name not in self.experts:
                self.experts[col_idx] = new_name
                for alt in self.alternatives:
                    self.data[alt][new_name] = self.data[alt].pop(old_name)
                self.update_table()

    def delete_expert_from_menu(self):
        col = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())
        if col in ("#0", "#1"):
            return
        col_idx = int(col[1:]) - 1
        if 0 <= col_idx < len(self.experts):
            exp_name = self.experts[col_idx]
            if messagebox.askyesno("Удалить", f"Удалить «{exp_name}»?"):
                self.experts.pop(col_idx)
                for alt in self.alternatives:
                    self.data[alt].pop(exp_name, None)
                self.update_table()

    def compute_concordance(self):
        if len(self.alternatives) < 2 or len(self.experts) < 2:
            messagebox.showinfo("Результат", "Недостаточно данных (нужно минимум 2 альтернативы и 2 эксперта)")
            return

        # Проверка полноты данных и уникальности рангов
        try:
            n = len(self.alternatives)
            m = len(self.experts)
            ranks = np.zeros((n, m), dtype=int)
            alt_list = self.alternatives
            for i, alt in enumerate(alt_list):
                for j, exp in enumerate(self.experts):
                    rank = self.data[alt][exp]
                    if not 1 <= rank <= n:
                        raise ValueError(f"Неверный ранг для {alt} у {exp}")
                    ranks[i, j] = rank
            # Проверка уникальности по экспертам
            for j in range(m):
                if len(set(ranks[:, j])) != n:
                    raise ValueError(f"Ранги эксперта {self.experts[j]} не уникальны")
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e))
            return

        # Расчёт коэффициента Кендалла W
        sum_ranks = np.sum(ranks, axis=1)
        mean_sum = np.mean(sum_ranks)
        S = np.sum((sum_ranks - mean_sum)**2)
        W = 12 * S / (m**2 * (n**3 - n))

        # Chi-square для значимости (опционально)
        chi2 = m * (n - 1) * W
        from scipy.stats import chi2 as chi2_dist
        p_value = 1 - chi2_dist.cdf(chi2, n - 1)

        # Интерпретация
        interp = f"Коэффициент конкорданса W = {W:.3f}\n"
        if W < 0.3:
            interp += "Слабое согласие экспертов.\n"
        elif W < 0.7:
            interp += "Среднее согласие экспертов.\n"
        else:
            interp += "Сильное согласие экспертов.\n"
        interp += f"Хи-квадрат = {chi2:.2f}, p-value = {p_value:.4f} (степени свободы = {n-1})\n"
        if p_value < 0.05:
            interp += "Согласие статистически значимо (p < 0.05).\n"
        else:
            interp += "Согласие не статистически значимо (p >= 0.05).\n"

        # Средние ранги для ранжирования альтернатив
        mean_ranks = np.mean(ranks, axis=1)
        sorted_indices = np.argsort(mean_ranks)
        interp += "\nРанжирование альтернатив по среднему рангу (меньше - лучше):\n"
        for idx in sorted_indices:
            interp += f"{alt_list[idx]}: средний ранг {mean_ranks[idx]:.2f}\n"

        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, interp)
        messagebox.showinfo("Готово", f"Коэффициент W = {W:.3f}")

# Запуск
if __name__ == "__main__":
    root = tk.Tk()
    app = ConcordanceAnalyzer(root)
    root.mainloop()