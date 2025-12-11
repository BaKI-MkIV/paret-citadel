import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.simpledialog as simpledialog
from tkinter import filedialog
import json

class JohnsonScheduler:
    def __init__(self, root):
        self.root = root
        self.root.title("Планирование по методу Джонсона (две машины) — с Гантом")
        self.root.geometry("1300x800")

        self.jobs = []
        self.criteria = [
            {'name': 'Машина 1', 'direction': 'min'},
            {'name': 'Машина 2', 'direction': 'min'}
        ]
        self.data = {}

        self.setup_ui()
        self.update_table()

    def setup_ui(self):
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(top_frame, text="Задача:").grid(row=0, column=0, padx=5, sticky="e")
        self.job_entry = ttk.Entry(top_frame, width=25)
        self.job_entry.grid(row=0, column=1, padx=5)
        self.job_entry.bind("<Return>", lambda e: self.add_job())
        ttk.Button(top_frame, text="Добавить", command=self.add_job).grid(row=0, column=2, padx=5)

        ttk.Button(top_frame, text="Загрузить JSON", command=self.load_json).grid(row=0, column=3, padx=10)
        ttk.Button(top_frame, text="Вычислить расписание Джонсона", command=self.compute_johnson,
                   style="Accent.TButton").grid(row=0, column=4, padx=20)

        # === Таблица ввода ===
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(table_frame, columns=("job",), show="headings", height=12)
        self.tree.heading("job", text="Задача")
        self.tree.column("job", width=180, anchor="w")

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

        # === Таблица результатов ===
        result_frame = ttk.LabelFrame(self.root, text="Оптимальное расписание (детали)")
        result_frame.pack(fill="both", expand=True, padx=10, pady=10)

        cols = ("№", "Задача", "М1: начало", "М1: конец", "М2: начало", "М2: конец", "Простой М2")
        self.result_tree = ttk.Treeview(result_frame, columns=cols, show="headings", height=12)
        for col in cols:
            self.result_tree.heading(col, text=col)
            if col in ("Задача", "№"):
                self.result_tree.column(col, width=120, anchor="w")
            else:
                self.result_tree.column(col, width=100, anchor="center")
        self.result_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Подпись с makespan
        self.makespan_label = ttk.Label(result_frame, text="Makespan: —", font=("Arial", 12, "bold"), foreground="blue")
        self.makespan_label.pack(pady=5)

        # Контекстное меню
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Переименовать задачу", command=self.rename_job)
        self.context_menu.add_command(label="Удалить задачу", command=self.delete_job)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Переименовать критерий", command=self.rename_criterion)
        self.context_menu.add_command(label="Изменить направление критерия", command=self.change_criterion_direction)

        style = ttk.Style()
        style.configure("Accent.TButton", foreground="white", background="#0078D7")

    def add_job(self):
        name = self.job_entry.get().strip()
        if not name or name in self.jobs:
            messagebox.showwarning("Ошибка", "Имя пустое или уже существует")
            return
        self.jobs.append(name)
        self.data[name] = {c["name"]: 0.0 for c in self.criteria}
        self.job_entry.delete(0, "end")
        self.update_table()

    def load_json(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not file_path: return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)

            loaded_criteria = loaded.get('criteria', [])
            if len(loaded_criteria) >= 2:
                self.criteria = loaded_criteria[:2]

            for job in loaded.get('jobs', []):
                if job not in self.jobs:
                    self.jobs.append(job)
                    self.data[job] = {c['name']: 0.0 for c in self.criteria}

            for job, times in loaded.get('data', {}).items():
                if job not in self.data:
                    self.jobs.append(job)
                    self.data[job] = {}
                for crit_name, val in times.items():
                    if crit_name in [c['name'] for c in self.criteria]:
                        self.data[job][crit_name] = float(val)

            self.update_table()
            messagebox.showinfo("Успех", "Данные из JSON загружены")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить: {e}")

    def update_table(self):
        self.tree.delete(*self.tree.get_children())
        crit_names = [c["name"] for c in self.criteria]
        self.tree["columns"] = ("job",) + tuple(crit_names)
        self.tree.heading("job", text="Задача")
        self.tree.column("job", width=180)

        for i, crit in enumerate(self.criteria):
            symbol = "↓" if crit["direction"] == "min" else "↑"
            self.tree.heading(crit["name"], text=f"{crit['name']} {symbol}")
            self.tree.column(crit["name"], width=130, anchor="center")

        for job in self.jobs:
            values = [job] + [self.data[job].get(c["name"], "") for c in self.criteria]
            self.tree.insert("", "end", iid=job, values=values)

    def on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item_id or column in ("#0", "#1"): return

        col_idx = int(column[1:]) - 1
        if col_idx >= len(self.criteria) + 1: return

        crit_name = self.criteria[col_idx - 1]["name"]
        job_name = item_id

        x, y, width, height = self.tree.bbox(item_id, column)
        entry = ttk.Entry(self.tree)
        entry.insert(0, self.data[job_name][crit_name])
        entry.select_range(0, "end")
        entry.focus()

        def save_edit(e=None):
            try:
                val = float(entry.get())
                if val < 0: raise ValueError()
                self.data[job_name][crit_name] = val
                self.update_table()
            except:
                messagebox.showerror("Ошибка", "Введите положительное число")
            entry.destroy()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)
        entry.place(x=x, y=y, width=width, height=height)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def rename_job(self):
        item = self.tree.selection()[0] if self.tree.selection() else None
        if not item: return
        old = item
        new = simpledialog.askstring("Переименование", "Новое имя:", initialvalue=old)
        if new and new != old and new not in self.jobs:
            idx = self.jobs.index(old)
            self.jobs[idx] = new
            self.data[new] = self.data.pop(old)
            self.update_table()

    def delete_job(self):
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item and messagebox.askyesno("Удаление", f"Удалить задачу «{item}»?"):
            self.jobs.remove(item)
            self.data.pop(item, None)
            self.update_table()

    def rename_criterion(self):
        col = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())
        if col in ("#0", "#1"): return
        idx = int(col[1:]) - 2
        if 0 <= idx < len(self.criteria):
            old = self.criteria[idx]["name"]
            new = simpledialog.askstring("Переименование", "Новое имя:", initialvalue=old)
            if new and new != old:
                self.criteria[idx]["name"] = new
                for job in self.jobs:
                    self.data[job][new] = self.data[job].pop(old)
                self.update_table()

    def change_criterion_direction(self):
        col = self.tree.identify_column(self.tree.winfo_pointerx() - self.tree.winfo_rootx())
        if col in ("#0", "#1"): return
        idx = int(col[1:]) - 2
        if 0 <= idx < len(self.criteria):
            crit = self.criteria[idx]
            crit["direction"] = "max" if crit["direction"] == "min" else "min"
            self.update_table()

    def compute_johnson(self):
        if len(self.jobs) < 2 or len(self.criteria) != 2:
            messagebox.showwarning("Ошибка", "Нужны минимум 2 задачи и ровно 2 машины")
            return

        m1_name = self.criteria[0]["name"]
        m2_name = self.criteria[1]["name"]

        group1, group2 = [], []
        for job in self.jobs:
            t1 = self.data[job][m1_name]
            t2 = self.data[job][m2_name]
            if t1 < t2:
                group1.append((t1, job))
            else:
                group2.append((t2, job))

        group1.sort()  # по t1 ↑
        group2.sort(reverse=True)  # по t2 ↓

        schedule = [job for _, job in group1] + [job for _, job in group2]

        # Симуляция выполнения
        time_m1 = 0
        time_m2 = 0
        details = []

        for i, job in enumerate(schedule, 1):
            t1 = self.data[job][m1_name]
            t2 = self.data[job][m2_name]

            start_m1 = time_m1
            end_m1 = time_m1 + t1
            time_m1 = end_m1

            start_m2 = max(time_m2, end_m1)
            idle = start_m2 - time_m2 if start_m2 > time_m2 else 0
            end_m2 = start_m2 + t2
            time_m2 = end_m2

            details.append({
                "num": i,
                "job": job,
                "m1_start": start_m1,
                "m1_end": end_m1,
                "m2_start": start_m2,
                "m2_end": end_m2,
                "idle": idle
            })

        makespan = time_m2

        # Вывод результата
        self.result_tree.delete(*self.result_tree.get_children())
        for d in details:
            idle_str = f"{d['idle']}" if d['idle'] > 0 else "—"
            self.result_tree.insert("", "end", values=(
                d["num"], d["job"],
                d["m1_start"], d["m1_end"],
                d["m2_start"], d["m2_end"],
                idle_str
            ))

        self.makespan_label.config(text=f"Makespan: {makespan} единиц времени")

        messagebox.showinfo("Готово!",
                            f"Оптимальное расписание построено!\n"
                            f"Порядок: {' → '.join(schedule)}\n"
                            f"Makespan = {makespan}")

# Запуск
if __name__ == "__main__":
    root = tk.Tk()
    app = JohnsonScheduler(root)
    root.mainloop()