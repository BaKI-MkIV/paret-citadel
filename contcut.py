import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.simpledialog as simpledialog
from tkinter import filedialog
import json
import networkx as nx
from networkx.algorithms.dag import topological_sort

class NetworkOptimizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Оптимизация сетевого графика по сокращению длительности")
        self.root.geometry("1300x800")

        self.activities = []  # список имен активностей
        self.data = {}  # {act: {'normal_time': float, 'crash_time': float, 'normal_cost': float, 'crash_cost_per_day': float, 'predecessors': []}}
        self.graph = nx.DiGraph()  # Для моделирования зависимостей

        self.setup_ui()
        self.update_table()

    def setup_ui(self):
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=10)

        # Добавление активности
        ttk.Label(top_frame, text="Активность:").grid(row=0, column=0, padx=5, sticky="e")
        self.act_entry = ttk.Entry(top_frame, width=25)
        self.act_entry.grid(row=0, column=1, padx=5)
        self.act_entry.bind("<Return>", lambda e: self.add_activity())
        ttk.Button(top_frame, text="Добавить", command=self.add_activity).grid(row=0, column=2, padx=5)

        # Поле для целевой длительности
        ttk.Label(top_frame, text="Целевая длительность:").grid(row=0, column=3, padx=20, sticky="e")
        self.target_duration_entry = ttk.Entry(top_frame, width=10)
        self.target_duration_entry.insert(0, "0")
        self.target_duration_entry.grid(row=0, column=4, padx=5)

        # Кнопки
        ttk.Button(top_frame, text="Загрузить JSON", command=self.load_json).grid(row=0, column=5, padx=10)
        ttk.Button(top_frame, text="Оптимизировать график", command=self.optimize_network, style="Accent.TButton").grid(row=0, column=6, padx=20)

        # Таблица данных
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        cols = ("act", "predecessors", "normal_time", "crash_time", "normal_cost", "crash_cost_per_day")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=15)
        self.tree.heading("act", text="Активность")
        self.tree.heading("predecessors", text="Предшественники")
        self.tree.heading("normal_time", text="Норм. время")
        self.tree.heading("crash_time", text="Мин. время")
        self.tree.heading("normal_cost", text="Норм. стоимость")
        self.tree.heading("crash_cost_per_day", text="Доп. стоим./день")
        for col in cols:
            self.tree.column(col, width=150, anchor="center")

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
        self.context_menu.add_command(label="Переименовать активность", command=self.rename_activity)
        self.context_menu.add_command(label="Изменить предшественников", command=self.change_predecessors)
        self.context_menu.add_command(label="Удалить активность", command=self.delete_activity)

        # Результаты
        result_frame = ttk.LabelFrame(self.root, text="Результаты оптимизации")
        result_frame.pack(fill="x", padx=10, pady=10)

        self.result_text = tk.Text(result_frame, height=10, wrap="word")
        self.result_text.pack(fill="both", expand=True, padx=5, pady=5)

        style = ttk.Style()
        style.configure("Accent.TButton", foreground="white", background="#0078D7")

    def add_activity(self):
        name = self.act_entry.get().strip()
        if not name or name in self.activities:
            messagebox.showwarning("Ошибка", "Имя пустое или уже существует")
            return
        preds_str = simpledialog.askstring("Предшественники", "Предшественники (через запятую):")
        preds = [p.strip() for p in preds_str.split(",") if p.strip() and p.strip() in self.activities] if preds_str else []
        self.activities.append(name)
        self.data[name] = {
            'normal_time': 0.0,
            'crash_time': 0.0,
            'normal_cost': 0.0,
            'crash_cost_per_day': 0.0,
            'predecessors': preds
        }
        self.graph.add_node(name)
        for pred in preds:
            self.graph.add_edge(pred, name)
        if not nx.is_directed_acyclic_graph(self.graph):
            messagebox.showerror("Ошибка", "Добавление создает цикл в графе!")
            self.graph.remove_node(name)
            self.activities.remove(name)
            self.data.pop(name)
            return
        self.act_entry.delete(0, "end")
        self.update_table()

    def load_json(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            existing_acts = set(self.activities)
            for act in loaded.get('activities', []):
                if act not in existing_acts:
                    self.activities.append(act)
                    self.data[act] = loaded['data'][act]
                    self.graph.add_node(act)
            for act, info in loaded.get('data', {}).items():
                preds = info['predecessors']
                for pred in preds:
                    if pred in self.activities and act in self.activities:
                        self.graph.add_edge(pred, act)
            if not nx.is_directed_acyclic_graph(self.graph):
                messagebox.showerror("Ошибка", "Загруженный граф содержит цикл!")
                # Откат
                for act in loaded.get('activities', []):
                    if act not in existing_acts:
                        self.activities.remove(act)
                        self.data.pop(act)
                        self.graph.remove_node(act)
                return
            self.update_table()

            # --- Вот исправление: подставляем текущую длительность проекта ---
            current_times = {act: info['normal_time'] for act, info in self.data.items()}
            project_duration, _, _, _ = self.calculate_critical_path(current_times)
            self.target_duration_entry.delete(0, tk.END)
            self.target_duration_entry.insert(0, str(project_duration))  # автоматически ставим текущую длительность

            messagebox.showinfo("Успех", "JSON загружен")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить: {str(e)}")

    def update_table(self):
        self.tree.delete(*self.tree.get_children())
        for act in self.activities:
            info = self.data[act]
            preds = ", ".join(info['predecessors'])
            values = (act, preds, info['normal_time'], info['crash_time'], info['normal_cost'], info['crash_cost_per_day'])
            self.tree.insert("", "end", iid=act, values=values)

    def on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item_id or column == "#1" or column == "#2":  # act or predecessors
            return

        col_map = {"#3": "normal_time", "#4": "crash_time", "#5": "normal_cost", "#6": "crash_cost_per_day"}
        if column not in col_map:
            return

        key = col_map[column]
        act_name = item_id

        x, y, width, height = self.tree.bbox(item_id, column)
        entry = ttk.Entry(self.tree)
        entry.insert(0, self.data[act_name][key])
        entry.select_range(0, "end")
        entry.focus()

        def save_edit(event=None):
            try:
                value = float(entry.get())
                if value < 0:
                    raise ValueError("Значение не может быть отрицательным")
                if key == "crash_time" and value > self.data[act_name]['normal_time']:
                    raise ValueError("Минимальное время не может превышать нормальное")
                if key == "crash_cost_per_day" and value < 0:
                    raise ValueError("Дополнительная стоимость не может быть отрицательной")
                self.data[act_name][key] = value
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

    def rename_activity(self):
        item = self.tree.selection()
        if not item:
            return
        old_name = item[0]
        new_name = simpledialog.askstring("Переименование", "Новое название:", initialvalue=old_name)
        if new_name and new_name != old_name and new_name not in self.activities:
            # Обновляем данные и граф
            self.activities[self.activities.index(old_name)] = new_name
            self.data[new_name] = self.data.pop(old_name)
            self.graph = nx.relabel_nodes(self.graph, {old_name: new_name})
            # Обновляем предшественников в других активностях
            for act in self.activities:
                preds = self.data[act]['predecessors']
                if old_name in preds:
                    preds[preds.index(old_name)] = new_name
            self.update_table()

    def change_predecessors(self):
        item = self.tree.selection()
        if not item:
            return
        act = item[0]
        preds_str = simpledialog.askstring("Предшественники", "Новые предшественники (через запятую):", initialvalue=", ".join(self.data[act]['predecessors']))
        new_preds = [p.strip() for p in preds_str.split(",") if p.strip() and p.strip() in self.activities] if preds_str else []
        # Удаляем старые edges
        for pred in self.data[act]['predecessors']:
            self.graph.remove_edge(pred, act)
        # Добавляем новые
        for pred in new_preds:
            self.graph.add_edge(pred, act)
        if not nx.is_directed_acyclic_graph(self.graph):
            messagebox.showerror("Ошибка", "Изменение создает цикл в графе!")
            # Откат
            for pred in new_preds:
                self.graph.remove_edge(pred, act)
            for pred in self.data[act]['predecessors']:
                self.graph.add_edge(pred, act)
            return
        self.data[act]['predecessors'] = new_preds
        self.update_table()

    def delete_activity(self):
        item = self.tree.selection()
        if not item:
            return
        act = item[0]
        if messagebox.askyesno("Удалить", f"Удалить активность «{act}»?"):
            self.activities.remove(act)
            self.data.pop(act, None)
            self.graph.remove_node(act)
            # Удаляем ссылки в предшественниках других
            for other in self.activities:
                preds = self.data[other]['predecessors']
                if act in preds:
                    preds.remove(act)
            self.update_table()

    def calculate_critical_path(self, times):
        earliest = {}
        for act in topological_sort(self.graph):
            preds = self.data[act]['predecessors']
            earliest[act] = max(earliest.get(pred, 0) + times.get(pred, 0) for pred in preds) if preds else 0

        end_nodes = [n for n in self.graph.nodes if self.graph.out_degree(n) == 0]
        project_duration = max(earliest.get(act, 0) + times.get(act, 0) for act in self.graph.nodes)

        latest = {}
        for act in end_nodes:
            latest[act] = project_duration - times.get(act, 0)

        for act in reversed(list(topological_sort(self.graph))):
            succs = list(self.graph.successors(act))
            if succs:
                latest[act] = min(latest.get(succ, project_duration) - times.get(succ, 0) for succ in succs)

        critical_path = [act for act in self.activities if earliest.get(act, 0) == latest.get(act, 0)]
        return project_duration, critical_path, earliest, latest

    def optimize_network(self):
        try:
            target_duration = float(self.target_duration_entry.get())
            if target_duration <= 0:
                raise ValueError
        except:
            messagebox.showerror("Ошибка", "Целевая длительность должна быть положительной")
            return

        if not nx.is_directed_acyclic_graph(self.graph):
            messagebox.showerror("Ошибка", "Граф содержит цикл!")
            return

        # Инициализация текущих времен и стоимостей
        current_times = {act: info['normal_time'] for act, info in self.data.items()}
        current_costs = sum(info['normal_cost'] for info in self.data.values())

        project_duration, critical_path, _, _ = self.calculate_critical_path(current_times)

        if project_duration <= target_duration:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"Текущая длительность {project_duration} уже меньше или равна цели {target_duration}.\nОбщие затраты: {current_costs}")
            return

        steps = []
        while project_duration > target_duration:
            # Вычисляем slope для критических активностей
            candidates = []
            for act in critical_path:
                info = self.data[act]
                if current_times[act] > info['crash_time']:
                    max_reduce = current_times[act] - info['crash_time']
                    slope = info['crash_cost_per_day']
                    candidates.append((slope, act, min(1.0, max_reduce)))  # По 1, или меньше если осталось мало

            if not candidates:
                break  # Невозможно дальше сокращать

            # Выбираем с минимальным slope
            candidates.sort()
            _, act, reduce = candidates[0]

            # Ускоряем
            current_times[act] -= reduce
            additional_cost = reduce * self.data[act]['crash_cost_per_day']
            current_costs += additional_cost

            # Пересчитываем
            project_duration, critical_path, _, _ = self.calculate_critical_path(current_times)

            steps.append(f"Ускорить {act} на {reduce} день (стоимость {additional_cost}). Новая длительность: {project_duration}")

        self.result_text.delete(1.0, tk.END)
        if project_duration > target_duration:
            self.result_text.insert(tk.END, f"Невозможно сократить до цели. Минимальная длительность: {project_duration}\n")
        else:
            self.result_text.insert(tk.END, "Оптимизация завершена.\n")
        self.result_text.insert(tk.END, f"Финальная длительность: {project_duration}\nОбщие затраты: {current_costs}\n\nШаги:\n" + "\n".join(steps))

# Запуск
if __name__ == "__main__":
    root = tk.Tk()
    app = NetworkOptimizer(root)
    root.mainloop()