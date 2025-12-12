import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.simpledialog as simpledialog
from tkinter import filedialog
import json
import networkx as nx
from networkx.algorithms.dag import topological_sort


class NetworkAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("Сетевые графики: Критический путь и оптимизация по стоимости")
        self.root.geometry("1400x900")

        # activities: порядок отображения (список имён)
        self.activities = []
        # data: словарь по работе
        # { act: {
        #     'predecessors': [...],
        #     'duration': float,
        #     'crash_duration': float,
        #     'cost_normal': float,
        #     'cost_crash': float,
        #     'max_crash_days': float,
        #     'slope': float
        # } }
        self.data = {}
        self.graph = nx.DiGraph()

        self.setup_ui()

    def setup_ui(self):
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Label(top, text="Работа:").grid(row=0, column=0, padx=5, sticky="e")
        self.act_entry = ttk.Entry(top, width=15)
        self.act_entry.grid(row=0, column=1, padx=5)
        self.act_entry.bind("<Return>", lambda e: self.add_activity())

        ttk.Button(top, text="Добавить работу", command=self.add_activity).grid(row=0, column=2, padx=5)
        ttk.Button(top, text="Загрузить JSON", command=self.load_json).grid(row=0, column=5, padx=10)
        ttk.Button(top, text="Рассчитать критический путь", command=self.calculate_cp).grid(row=0, column=6, padx=10)
        ttk.Button(top, text="Оптимизировать по стоимости", command=self.optimize_cost, style="Accent.TButton").grid(row=0, column=7, padx=20)

        ttk.Label(top, text="Целевая длительность:").grid(row=1, column=0, padx=5, sticky="e")
        self.target_entry = ttk.Entry(top, width=10)
        self.target_entry.grid(row=1, column=1, padx=5, sticky="w")

        # Таблица
        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        cols = ("act", "pred", "dur", "cost_n", "cost_c", "crash_days", "slope")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=18)
        headings = ["Работа", "Предш.", "Длительность", "Ст-ть норм.", "Ст-ть ускор.", "Макс. ускорение", "Цена/день"]
        for c, h in zip(cols, headings):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=120, anchor="center")
        self.tree.column("act", width=140, anchor="w")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self.edit_cell)
        self.tree.bind("<Button-3>", self.context_menu)

        # Результаты
        result_frame = ttk.LabelFrame(self.root, text="Результаты расчёта")
        result_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.result_text = tk.Text(result_frame, height=20, font=("Consolas", 10))
        self.result_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Контекстное меню
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Удалить работу", command=self.delete_activity)
        self.menu.add_command(label="Изменить предшественников", command=self.change_predecessors)

        style = ttk.Style()
        # Accent.TButton may not exist on all platforms; safe configure
        try:
            style.configure("Accent.TButton", foreground="white", background="#0078D7")
        except Exception:
            pass

    def add_activity(self):
        name = self.act_entry.get().strip()
        if not name:
            messagebox.showwarning("Ошибка", "Имя пустое")
            return
        if name in self.activities:
            messagebox.showwarning("Ошибка", "Имя уже существует")
            return

        preds_str = simpledialog.askstring("Предшественники", "Через запятую (пусто — стартовая):")
        preds = []
        if preds_str:
            preds = [p.strip() for p in preds_str.split(",") if p.strip()]
            # оставить только те предшественники, которые уже существуют
            preds = [p for p in preds if p in self.activities]

        dur = simpledialog.askfloat("Длительность", "Нормальная длительность (дни):", minvalue=0.01)
        if dur is None:
            return
        cost_n = simpledialog.askfloat("Стоимость", "Стоимость при нормальной длительности:", minvalue=0.0)
        if cost_n is None:
            return
        crash_dur = simpledialog.askfloat("Ускорение", "Минимальная длительность (≤ нормальной):", minvalue=0.0, maxvalue=dur)
        if crash_dur is None:
            return
        cost_c = simpledialog.askfloat("Стоимость ускоренная", "Стоимость при ускорении (общая стоимость):", minvalue=cost_n)
        if cost_c is None:
            return

        if crash_dur >= dur:
            messagebox.showerror("Ошибка", "Минимальная длительность должна быть меньше нормальной!")
            return

        crash_days = dur - crash_dur
        slope = (cost_c - cost_n) / crash_days if crash_days > 0 else float('inf')

        self.activities.append(name)
        self.data[name] = {
            'predecessors': preds,
            'duration': float(dur),
            'crash_duration': float(crash_dur),
            'cost_normal': float(cost_n),
            'cost_crash': float(cost_c),
            'max_crash_days': float(crash_days),
            'slope': float(slope)
        }
        self.graph.add_node(name)
        for p in preds:
            self.graph.add_edge(p, name)

        if not nx.is_directed_acyclic_graph(self.graph):
            messagebox.showerror("Ошибка", "Создаётся цикл! Добавление отменено.")
            # удалить добавленное
            self.activities.remove(name)
            self.data.pop(name, None)
            self.graph.remove_node(name)
            return

        self.act_entry.delete(0, tk.END)
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
                f"{d['cost_normal']:.2f}",
                f"{d['cost_crash']:.2f}",
                f"{d['max_crash_days']:.2f}",
                f"{d['slope']:.2f}" if d['slope'] != float('inf') else "∞"
            ))

    def edit_cell(self, event):
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item or column == "#1":  # запрещаем редактировать название прямо
            return

        col_idx = int(column[1:]) - 1
        # Маппинг столбцов на ключи в self.data
        keys = [None, None, 'duration', 'cost_normal', 'cost_crash', None, None]
        key = keys[col_idx]
        if not key:
            return

        x, y, w, h = self.tree.bbox(item, column)
        entry = ttk.Entry(self.tree)
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, str(self.data[item][key]))
        entry.focus()

        def save(event=None):
            try:
                val = float(entry.get())
                if val < 0:
                    raise ValueError
                if key == 'duration':
                    # Нормальная длительность не может быть меньше crash_duration
                    if val <= self.data[item]['crash_duration']:
                        messagebox.showerror("Ошибка", "Нормальная длительность не может быть меньше или равна ускоренной.")
                        entry.destroy()
                        return
                    self.data[item]['duration'] = val
                    # пересчитать max_crash_days
                    self.data[item]['max_crash_days'] = self.data[item]['duration'] - self.data[item]['crash_duration']
                elif key == 'cost_normal':
                    # cost_normal не должен быть больше cost_crash
                    if val > self.data[item]['cost_crash']:
                        messagebox.showerror("Ошибка", "Нормальная стоимость не может быть больше ускоренной.")
                        entry.destroy()
                        return
                    self.data[item]['cost_normal'] = val
                elif key == 'cost_crash':
                    if val < self.data[item]['cost_normal']:
                        messagebox.showerror("Ошибка", "Ускоренная стоимость не может быть меньше нормальной.")
                        entry.destroy()
                        return
                    self.data[item]['cost_crash'] = val

                # пересчитать наклон (slope)
                crash_days = self.data[item]['duration'] - self.data[item]['crash_duration']
                self.data[item]['slope'] = (self.data[item]['cost_crash'] - self.data[item]['cost_normal']) / crash_days if crash_days > 0 else float('inf')

                self.update_table()
            except Exception:
                # тихо игнорируем неверный ввод
                pass
            finally:
                entry.destroy()

        entry.bind("<Return>", save)
        entry.bind("<FocusOut>", save)

    def context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            try:
                self.menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.menu.grab_release()

    def delete_activity(self):
        sel = self.tree.selection()
        if not sel:
            return
        act = sel[0]
        if not messagebox.askyesno("Удалить", f"Удалить работу {act}?"):
            return

        # удаляем работу
        if act in self.activities:
            self.activities.remove(act)
        self.data.pop(act, None)
        if self.graph.has_node(act):
            self.graph.remove_node(act)

        # убираем из предшественников у остальных
        for a in list(self.activities):
            if act in self.data.get(a, {}).get('predecessors', []):
                self.data[a]['predecessors'].remove(act)
                # удалить ребро если есть
                if self.graph.has_edge(act, a):
                    self.graph.remove_edge(act, a)

        self.update_table()

    def change_predecessors(self):
        sel = self.tree.selection()
        if not sel:
            return
        act = sel[0]
        cur = ", ".join(self.data[act]['predecessors'])
        prompt = f"Предшественники для {act} (через запятую):"
        new = simpledialog.askstring("Предшественники", prompt, initialvalue=cur)
        if new is None:
            return
        new_preds = [p.strip() for p in new.split(",") if p.strip() in self.activities]

        # Сохраним старые значения на случай отката
        old_preds = list(self.data[act]['predecessors'])
        old_edges = []
        for p in old_preds:
            if self.graph.has_edge(p, act):
                old_edges.append((p, act))

        # Удаляем старые рёбра
        for p in old_preds:
            if self.graph.has_edge(p, act):
                self.graph.remove_edge(p, act)

        # Применяем новые предшественники
        self.data[act]['predecessors'] = new_preds
        for p in new_preds:
            self.graph.add_edge(p, act)

        # Проверка на цикл
        if not nx.is_directed_acyclic_graph(self.graph):
            messagebox.showerror("Ошибка", "Цикл! Изменение предшественников откатывается.")
            # Откат
            for p in new_preds:
                if self.graph.has_edge(p, act):
                    self.graph.remove_edge(p, act)
            self.data[act]['predecessors'] = old_preds
            for (p, a) in old_edges:
                self.graph.add_edge(p, a)
            return

        self.update_table()

    def calculate_cp(self):
        """
        Рассчитывает критический путь на основании текущих данных self.data (использует нормальные длительности).
        Выводит результат в self.result_text и устанавливает target_entry равной длительности проекта.
        """
        if not self.activities:
            messagebox.showinfo("Инфо", "Нет работ для расчёта")
            return

        # times: используем текущие нормальные длительности
        times = {a: self.data[a]['duration'] for a in self.activities}

        project_duration, critical, es, ef, ls, lf = self.calculate_critical_path(times)

        # Резервы
        total_float = {}
        free_float = {}

        for act in self.activities:
            total_float[act] = ls[act] - es[act]
            # свободный резерв: min ES следующего - EF этого
            succs = list(self.graph.successors(act))
            succ_es = min([es[s] for s in succs], default=project_duration)
            free_float[act] = succ_es - ef[act]

        # Вывод
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "РАСЧЁТ КРИТИЧЕСКОГО ПУТИ\n")
        self.result_text.insert(tk.END, f"{'='*60}\n")
        self.result_text.insert(tk.END, f"Длительность проекта: {project_duration:.2f} дней\n")
        self.result_text.insert(tk.END, f"Критический путь ({len(critical)} работ): {' → '.join(critical)}\n\n")

        self.result_text.insert(tk.END, f"{'Работа':<12} {'ES':>6} {'EF':>6} {'LS':>6} {'LF':>6} {'Общ.рез.':>10} {'Своб.рез.':>10}\n")
        self.result_text.insert(tk.END, "-"*80 + "\n")
        for act in self.activities:
            star = " ← КРИТИЧ." if act in critical else ""
            self.result_text.insert(tk.END,
                                    f"{act:<12} {es[act]:>6.2f} {ef[act]:>6.2f} {ls[act]:>6.2f} {lf[act]:>6.2f} "
                                    f"{total_float[act]:>10.2f} {free_float[act]:>10.2f}{star}\n")

        # Автоматически подставляем текущую длительность
        self.target_entry.delete(0, tk.END)
        self.target_entry.insert(0, f"{project_duration:.2f}")

        # Для внешнего использования возвращаем данные
        return project_duration, critical, es, ef, ls, lf

    def calculate_critical_path(self, times):
        """
        Универсальный расчёт КП для данного словаря times: {act: duration}.
        Возвращает: project_duration, critical_list (по порядку топологической сортировки), ES, EF, LS, LF
        """
        # Прямой проход (ES, EF)
        es = {}
        ef = {}
        for act in topological_sort(self.graph):
            preds = self.data[act]['predecessors']
            if not preds:
                es[act] = 0.0
            else:
                es[act] = max([ef.get(p, 0.0) for p in preds])
            dur = float(times.get(act, self.data[act]['duration']))
            ef[act] = es[act] + dur

        project_duration = max(ef.values()) if ef else 0.0

        # Обратный проход (LS, LF)
        lf = {}
        ls = {}
        for act in reversed(list(topological_sort(self.graph))):
            succs = list(self.graph.successors(act))
            if not succs:
                lf[act] = project_duration
            else:
                lf[act] = min([ls.get(s, project_duration) for s in succs])
            dur = float(times.get(act, self.data[act]['duration']))
            ls[act] = lf[act] - dur

        # Критичность: EF == LF (с погрешностью)
        critical = [act for act in self.activities if abs(ef[act] - lf[act]) < 1e-6]

        return project_duration, critical, es, ef, ls, lf

    def optimize_cost(self):
        """
        Итеративный crashing: на каждом шаге определяем текущий критический путь (по текущим durations),
        среди его работ выбираем ту, у которой минимальный slope и есть запас для ускорения, ускоряем её на 1 день
        (или на оставшуюся разницу до target если меньше 1), повторяем, пока не достигнем целевой длительности
        или не исчерпаем возможности ускорения.
        """
        if not self.activities:
            messagebox.showinfo("Инфо", "Нет работ для оптимизации")
            return

        try:
            target = float(self.target_entry.get())
        except Exception:
            messagebox.showerror("Ошибка", "Введите корректную целевую длительность")
            return

        # Начальные durations — копия нормальных длительностей
        current_duration = {a: float(self.data[a]['duration']) for a in self.activities}

        # Исходная длительность проекта:
        initial_proj_duration, _, _, _, _, _ = self.calculate_critical_path(current_duration)
        initial_cost = sum(self.data[a]['cost_normal'] for a in self.activities)

        if target >= initial_proj_duration - 1e-9:
            messagebox.showinfo("Инфо", "Цель уже достигнута или больше текущей длительности")
            return

        total_cost = initial_cost
        steps = []

        # Будем ускорять шагами по 1 дню (с учётом возможной дробности на последнем шаге)
        max_iterations = 10000  # предохранитель от бесконечного цикла
        it = 0
        current_project_duration = initial_proj_duration

        while current_project_duration > target + 1e-9 and it < max_iterations:
            it += 1
            # ← ВОТ ЭТА СТРОКА САМАЯ ВАЖНАЯ:
            current_project_duration, cp, es, ef, ls, lf = self.calculate_critical_path(current_duration)
            if not cp:
                break

            # Найти на критическом пути работу с минимальным slope и с запасом для уменьшения
            best_act = None
            best_slope = float('inf')
            for act in cp:
                max_reduce = current_duration[act] - self.data[act]['crash_duration']
                if max_reduce > 1e-9:
                    slope = self.data[act]['slope']
                    # Дополнительная проверка: slope может быть inf (нельзя ускорять экономически)
                    if slope < best_slope:
                        best_slope = slope
                        best_act = act

            if best_act is None:
                # Невозможно дальше ускорять
                break

            # Сколько нужно сократить до target
            need = current_project_duration - target
            # Сколько можно сократить у выбранной работы
            possible_reduce = current_duration[best_act] - self.data[best_act]['crash_duration']
            # Сделаем шаг: 1.0 день или остаток need или possible_reduce — что меньше
            step = min(1.0, possible_reduce, need)
            # Для случаев, когда need < 1 и possible_reduce >= need, сократим на need (дробный шаг)
            # иначе сокращаем на 1 день
            if step <= 0:
                break

            current_duration[best_act] -= step
            cost_increase = step * best_slope
            total_cost += cost_increase
            current_project_duration -= step
            steps.append(f"Ускорить {best_act} на {step:.2f} дн. (цена {best_slope:.2f}/день, +{cost_increase:.2f} у.е.)")

        # Вывод результата
        self.result_text.insert(tk.END, "\n\nОПТИМИЗАЦИЯ ПО СТОИМОСТИ (crashing)\n")
        self.result_text.insert(tk.END, "="*60 + "\n")
        if current_project_duration > target + 1e-6:
            self.result_text.insert(tk.END, f"Невозможно достичь цели {target:.2f} дней.\n")
            self.result_text.insert(tk.END, f"Минимально возможная длительность: {current_project_duration:.2f} дней\n")
        else:
            self.result_text.insert(tk.END, f"Цель {target:.2f} дней достигнута!\n")

        self.result_text.insert(tk.END, f"Исходная общая стоимость: {initial_cost:.2f} у.е.\n")
        self.result_text.insert(tk.END, f"Общая стоимость после оптимизации: {total_cost:.2f} у.е.\n")
        self.result_text.insert(tk.END, f"Дополнительные затраты: {total_cost - initial_cost:.2f} у.е.\n\n")
        if steps:
            self.result_text.insert(tk.END, "Шаги оптимизации:\n" + "\n".join(steps) + "\n")
        else:
            self.result_text.insert(tk.END, "Шаги оптимизации отсутствуют — ускорение невозможно.\n")

        # Финальный критический путь по обновлённым durations
        final_proj_duration, final_cp, _, _, _, _ = self.calculate_critical_path(current_duration)
        self.result_text.insert(tk.END, f"\nФинальный критический путь: {' → '.join(final_cp)} = {final_proj_duration:.2f} дней\n")

    def load_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                d = json.load(f)

            # Проверяем структуру
            activities = d.get('activities') if isinstance(d, dict) else None
            data = d.get('data') if isinstance(d, dict) else None
            if not isinstance(activities, list) or not isinstance(data, dict):
                raise ValueError("Некорректный формат JSON. Требуются ключи 'activities' (list) и 'data' (dict).")

            # Очистка текущих данных
            self.activities = []
            self.data = {}
            self.graph.clear()

            a_set = set(activities)
            # Сначала добавим все узлы
            for act in activities:
                self.activities.append(act)
                info = data.get(act)
                if not info:
                    raise ValueError(f"Нет данных для работы {act} в 'data'.")
                # Приведение типов и валидация
                preds = info.get('predecessors', [])
                dur = float(info.get('duration'))
                crash_dur = float(info.get('crash_duration'))
                cost_n = float(info.get('cost_normal'))
                cost_c = float(info.get('cost_crash'))
                if crash_dur >= dur:
                    raise ValueError(f"Для работы {act}: crash_duration должен быть меньше duration.")
                crash_days = dur - crash_dur
                slope = (cost_c - cost_n) / crash_days if crash_days > 0 else float('inf')
                self.data[act] = {
                    'predecessors': [p for p in preds if p in a_set],
                    'duration': dur,
                    'crash_duration': crash_dur,
                    'cost_normal': cost_n,
                    'cost_crash': cost_c,
                    'max_crash_days': crash_days,
                    'slope': slope
                }
                self.graph.add_node(act)

            # Добавим рёбра
            for act, info in self.data.items():
                for p in info['predecessors']:
                    if p in a_set:
                        self.graph.add_edge(p, act)

            if not nx.is_directed_acyclic_graph(self.graph):
                raise ValueError("Загруженный граф содержит цикл.")

            self.update_table()
            messagebox.showinfo("OK", "Загружено")
        except Exception as e:
            messagebox.showerror("Ошибка при загрузке JSON", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = NetworkAnalyzer(root)
    root.mainloop()
