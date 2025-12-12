import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import networkx as nx
from networkx.algorithms.dag import topological_sort


class NetworkLab:
    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторная работа 2-3: Критический путь + 5 итераций оптимизации")
        self.root.geometry("1500x900")

        self.activities = []
        # data: { act: { 'predecessors': [...], 'duration': float, 'crash_duration': float,
        #                'cost_normal': float, 'cost_crash': float, 'slope': float } }
        self.data = {}
        self.graph = nx.DiGraph()

        self.setup_ui()

    def setup_ui(self):
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Button(top, text="Добавить работу", command=self.add_activity).grid(row=0, column=0, padx=5)
        ttk.Button(top, text="Загрузить JSON", command=self.load_json).grid(row=0, column=1, padx=5)
        ttk.Button(top, text="Рассчитать критический путь", command=self.calculate_cp).grid(row=0, column=2, padx=10)
        ttk.Button(top, text="Оптимизация за 5 итераций", command=self.optimize_5_steps, style="Accent.TButton").grid(row=0, column=3, padx=20)

        # Таблица
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        cols = ("act", "pred", "dur", "crash_dur", "cost_n", "cost_c", "slope")
        headings = ("Работа", "Предш.", "Длит.", "Мин.длит.", "Ст-ть норм.", "Ст-ть ускор.", "Цена/день")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=20)
        for c, h in zip(cols, headings):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=140, anchor="center")
        self.tree.column("act", width=160, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self.edit_cell)

        # Результаты
        result_frame = ttk.LabelFrame(self.root, text="Результаты")
        result_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.result = tk.Text(result_frame, font=("Consolas", 11), wrap="none")
        self.result.pack(fill="both", expand=True, padx=5, pady=5)

        style = ttk.Style()
        try:
            style.configure("Accent.TButton", foreground="white", background="#d32f2f")
        except Exception:
            pass

    def add_activity(self):
        name = simpledialog.askstring("Работа", "Название работы:")
        if not name:
            messagebox.showwarning("Ошибка", "Имя пустое")
            return
        if name in self.activities:
            messagebox.showwarning("Ошибка", "Имя уже есть")
            return

        preds_input = simpledialog.askstring("Предшественники", "Через запятую (можно пусто):")
        preds = []
        if preds_input:
            preds = [p.strip() for p in preds_input.split(",") if p.strip()]
            # оставить только те, которые уже есть
            preds = [p for p in preds if p in self.activities]

        dur = simpledialog.askfloat("Длительность", "Нормальная длительность (дни):", minvalue=0.01)
        if dur is None:
            return

        # Указать диапазон для crash_dur: от 0 до dur - небольшая дельта
        max_crash = max(0.0, dur - 0.01)
        crash_dur = simpledialog.askfloat("Мин. длительность", "Минимальная длительность:", minvalue=0.0, maxvalue=max_crash)
        if crash_dur is None:
            return
        if crash_dur >= dur:
            messagebox.showerror("Ошибка", "Минимальная длительность должна быть меньше нормальной")
            return

        cost_n = simpledialog.askfloat("Стоимость", "Нормальная стоимость:", minvalue=0.0)
        if cost_n is None:
            return
        cost_c = simpledialog.askfloat("Ускоренная стоимость", "Стоимость при ускорении (общая):", minvalue=cost_n)
        if cost_c is None:
            return

        crash_days = dur - crash_dur
        slope = (cost_c - cost_n) / crash_days if crash_days > 0 else float('inf')

        # Сохранение
        self.activities.append(name)
        self.data[name] = {
            'predecessors': preds,
            'duration': float(dur),
            'crash_duration': float(crash_dur),
            'cost_normal': float(cost_n),
            'cost_crash': float(cost_c),
            'slope': float(slope)
        }
        self.graph.add_node(name)
        for p in preds:
            self.graph.add_edge(p, name)

        if not nx.is_directed_acyclic_graph(self.graph):
            messagebox.showerror("Ошибка", "Добавление создает цикл — отменено")
            # откат
            self.activities.remove(name)
            self.data.pop(name, None)
            self.graph.remove_node(name)
            return

        self.update_table()

    def update_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for act in self.activities:
            d = self.data[act]
            self.tree.insert("", "end", iid=act, values=(
                act,
                ", ".join(d['predecessors']) if d['predecessors'] else "—",
                f"{d['duration']:.2f}",
                f"{d['crash_duration']:.2f}",
                f"{d['cost_normal']:.2f}",
                f"{d['cost_crash']:.2f}",
                f"{d['slope']:.2f}" if d['slope'] != float('inf') else "∞"
            ))

    def edit_cell(self, event):
        # Упрощённое редактирование: редактируем numeric поля через диалог
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item:
            return
        # определим индекс столбца
        idx = int(col.replace('#', '')) - 1
        # mapping: 0 act (не редактируем), 1 preds (редактируем через строку), 2 duration, 3 crash_dur, 4 cost_n, 5 cost_c, 6 slope (не редактируем напрямую)
        if idx == 0:
            return  # название не редактируем здесь
        if idx == 1:
            # изменить предшественников
            cur = ", ".join(self.data[item]['predecessors'])
            new = simpledialog.askstring("Предшественники", f"Предшественники для {item} (через запятую):", initialvalue=cur)
            if new is None:
                return
            new_preds = [p.strip() for p in new.split(",") if p.strip()]
            # оставить только существующие
            new_preds = [p for p in new_preds if p in self.activities]
            # откат запоминаем
            old_preds = list(self.data[item]['predecessors'])
            # убираем старые ребра
            for p in old_preds:
                if self.graph.has_edge(p, item):
                    self.graph.remove_edge(p, item)
            # добавляем новые
            self.data[item]['predecessors'] = new_preds
            for p in new_preds:
                self.graph.add_edge(p, item)
            if not nx.is_directed_acyclic_graph(self.graph):
                messagebox.showerror("Ошибка", "Изменение приводит к циклу — откат.")
                # откат
                for p in new_preds:
                    if self.graph.has_edge(p, item):
                        self.graph.remove_edge(p, item)
                self.data[item]['predecessors'] = old_preds
                for p in old_preds:
                    self.graph.add_edge(p, item)
            self.update_table()
            return
        # для числовых полей
        key_map = {2: 'duration', 3: 'crash_duration', 4: 'cost_normal', 5: 'cost_crash'}
        if idx not in key_map:
            return
        key = key_map[idx]
        cur_val = self.data[item][key]
        if key in ('duration', 'crash_duration'):
            new_val = simpledialog.askfloat("Редактирование", f"{key} для {item}:", initialvalue=cur_val, minvalue=0.0)
            if new_val is None:
                return
            # если меняем duration — нужно обеспечить crash_duration < duration
            if key == 'duration':
                if new_val <= self.data[item]['crash_duration']:
                    messagebox.showerror("Ошибка", "Нормальная длительность должна быть больше минимальной.")
                    return
                self.data[item]['duration'] = float(new_val)
            else:
                if new_val >= self.data[item]['duration']:
                    messagebox.showerror("Ошибка", "Минимальная длительность должна быть меньше нормальной.")
                    return
                self.data[item]['crash_duration'] = float(new_val)
        else:
            new_val = simpledialog.askfloat("Редактирование", f"{key} для {item}:", initialvalue=cur_val, minvalue=0.0)
            if new_val is None:
                return
            if key == 'cost_normal':
                if new_val > self.data[item]['cost_crash']:
                    messagebox.showerror("Ошибка", "Нормальная стоимость не может быть больше ускоренной.")
                    return
                self.data[item]['cost_normal'] = float(new_val)
            else:
                if new_val < self.data[item]['cost_normal']:
                    messagebox.showerror("Ошибка", "Ускоренная стоимость не может быть меньше нормальной.")
                    return
                self.data[item]['cost_crash'] = float(new_val)
        # пересчитать slope
        dur = self.data[item]['duration']
        crash = self.data[item]['crash_duration']
        crash_days = dur - crash if dur > crash else 0.0
        self.data[item]['slope'] = (self.data[item]['cost_crash'] - self.data[item]['cost_normal']) / crash_days if crash_days > 0 else float('inf')
        self.update_table()

    def calculate_cp(self):
        if not self.activities:
            messagebox.showinfo("Инфо", "Нет работ для расчета")
            return

        times = {a: self.data[a]['duration'] for a in self.activities}
        duration, cp, es, ef, ls, lf = self.calc_path(times)

        total_float = {a: ls[a] - es[a] for a in self.activities}
        free_float = {}
        for a in self.activities:
            succs = list(self.graph.successors(a))
            succ_es = min([es.get(s, duration) for s in succs], default=duration)
            free_float[a] = succ_es - ef[a]

        self.result.delete(1.0, tk.END)
        self.result.insert(tk.END, "КРИТИЧЕСКИЙ ПУТЬ И РЕЗЕРВЫ ВРЕМЕНИ\n")
        self.result.insert(tk.END, "="*70 + "\n")
        self.result.insert(tk.END, f"Длительность проекта: {duration:.2f} дней\n")
        self.result.insert(tk.END, f"Критический путь: {' → '.join(cp)}\n\n")

        self.result.insert(tk.END, f"{'Работа':<12} {'ES':>6} {'EF':>6} {'LS':>6} {'LF':>6} {'Резерв общ.':>12} {'Резерв своб.':>12}\n")
        self.result.insert(tk.END, "-"*90 + "\n")
        for a in self.activities:
            star = " ← КРИТИЧ." if a in cp else ""
            self.result.insert(tk.END,
                f"{a:<12} {es[a]:>6.2f} {ef[a]:>6.2f} {ls[a]:>6.2f} {lf[a]:>6.2f} "
                f"{total_float[a]:>12.2f} {free_float[a]:>12.2f}{star}\n")

    def calc_path(self, times):
        """
        Возвращает: duration, critical_list (в порядке топологической сортировки), ES, EF, LS, LF
        times: dict {act: duration}
        """
        es = {}
        ef = {}
        # Прямой проход
        for act in topological_sort(self.graph):
            preds = self.data[act]['predecessors']
            if not preds:
                es[act] = 0.0
            else:
                es[act] = max([ef.get(p, 0.0) for p in preds])
            dur = float(times.get(act, self.data[act]['duration']))
            ef[act] = es[act] + dur

        duration = max(ef.values()) if ef else 0.0

        # Обратный проход
        lf = {}
        ls = {}
        for act in reversed(list(topological_sort(self.graph))):
            succs = list(self.graph.successors(act))
            if not succs:
                lf[act] = duration
            else:
                lf[act] = min([ls.get(s, duration) for s in succs])
            dur = float(times.get(act, self.data[act]['duration']))
            ls[act] = lf[act] - dur

        # Критические — EF == LF
        critical = [a for a in self.activities if abs(ef[a] - lf[a]) < 1e-6]
        return duration, critical, es, ef, ls, lf

    def optimize_5_steps(self):
        if not self.activities:
            messagebox.showinfo("Ошибка", "Нет данных")
            return

        # копия текущих длительностей
        current_durations = {a: float(self.data[a]['duration']) for a in self.activities}
        initial_duration, _, _, _, _, _ = self.calc_path(current_durations)
        initial_cost = sum(self.data[a]['cost_normal'] for a in self.activities)

        self.result.insert(tk.END, "\n\nОПТИМИЗАЦИЯ ЗА 5 ИТЕРАЦИЙ (crashing)\n")
        self.result.insert(tk.END, "="*70 + "\n")
        self.result.insert(tk.END, f"Исходная длительность: {initial_duration:.2f} дней\n")
        self.result.insert(tk.END, f"Исходная стоимость: {initial_cost:.2f} у.е.\n\n")

        total_cost = initial_cost

        for step in range(1, 6):
            duration, cp, es, ef, ls, lf = self.calc_path(current_durations)

            # Выбор лучшей работы на критическом пути (минимальный slope и есть запас для ускорения)
            best_act = None
            best_slope = float('inf')
            for act in cp:
                possible_reduce = current_durations[act] - self.data[act]['crash_duration']
                if possible_reduce > 1e-9:
                    slope = self.data[act]['slope']
                    if slope < best_slope:
                        best_slope = slope
                        best_act = act

            if best_act is None:
                self.result.insert(tk.END, f"Итерация {step}: НЕЛЬЗЯ ускорить дальше!\n")
                break

            # Ускоряем на 1 день (или на возможный остаток, если меньше 1)
            possible_reduce = current_durations[best_act] - self.data[best_act]['crash_duration']
            reduce_by = min(1.0, possible_reduce)
            current_durations[best_act] -= reduce_by
            cost_increase = reduce_by * best_slope
            total_cost += cost_increase

            # пересчёт длительности проекта
            new_duration, new_cp, _, _, _, _ = self.calc_path(current_durations)

            self.result.insert(tk.END, f"Итерация {step}:\n")
            self.result.insert(tk.END, f"  Ускоряем работу: {best_act} (цена {best_slope:.2f} у.е./день), на {reduce_by:.2f} дн.\n")
            self.result.insert(tk.END, f"  Новая длительность проекта: {new_duration:.2f} дней\n")
            self.result.insert(tk.END, f"  Новая стоимость: {total_cost:.2f} у.е.\n")
            self.result.insert(tk.END, f"  Новый критический путь: {' → '.join(new_cp)}\n\n")

        final_duration, _, _, _, _, _ = self.calc_path(current_durations)
        self.result.insert(tk.END, f"Финальная длительность: {final_duration:.2f} дней\n")
        self.result.insert(tk.END, f"Финальная стоимость: {total_cost:.2f} у.е.\n")
        self.result.insert(tk.END, f"Сокращено на: {initial_duration - final_duration:.2f} дней\n")

    def load_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                d = json.load(f)
            # ожидаем формат: { "activities": [...], "data": { act: { ... } } }
            if not isinstance(d, dict) or 'activities' not in d or 'data' not in d:
                raise ValueError("Некорректный формат JSON: требуются ключи 'activities' и 'data'")

            activities = d['activities']
            data = d['data']
            if not isinstance(activities, list) or not isinstance(data, dict):
                raise ValueError("Некорректные типы для 'activities' или 'data'")

            # Очистка
            self.activities = []
            self.data = {}
            self.graph.clear()

            a_set = set(activities)
            # Добавим узлы и данные
            for act in activities:
                if act not in data:
                    raise ValueError(f"Нет описания работы '{act}' в 'data'")
                info = data[act]
                preds = info.get('predecessors', [])
                dur = float(info.get('duration'))
                crash_dur = float(info.get('crash_duration'))
                cost_n = float(info.get('cost_normal'))
                cost_c = float(info.get('cost_crash'))
                if crash_dur >= dur:
                    raise ValueError(f"Для работы {act}: crash_duration должен быть меньше duration")
                crash_days = dur - crash_dur
                slope = (cost_c - cost_n) / crash_days if crash_days > 0 else float('inf')
                self.activities.append(act)
                self.data[act] = {
                    'predecessors': [p for p in preds if p in a_set],
                    'duration': dur,
                    'crash_duration': crash_dur,
                    'cost_normal': cost_n,
                    'cost_crash': cost_c,
                    'slope': slope
                }
                self.graph.add_node(act)

            # Добавить рёбра
            for act in self.activities:
                for p in self.data[act]['predecessors']:
                    if p in a_set:
                        self.graph.add_edge(p, act)

            if not nx.is_directed_acyclic_graph(self.graph):
                raise ValueError("Загруженный граф содержит цикл")

            self.update_table()
            messagebox.showinfo("OK", f"Загружено {len(self.activities)} работ")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = NetworkLab(root)
    root.mainloop()
