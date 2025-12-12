# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import networkx as nx
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

class DecisionTreeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Дерево решений — EMV")
        self.root.geometry("1200x800")

        self.G = nx.DiGraph()
        self.node_counter = 0

        self.setup_ui()
        self.draw_tree()

    def setup_ui(self):
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=8, pady=8)

        ttk.Button(top, text="Новое дерево", command=self.new_tree).pack(side="left", padx=4)
        ttk.Button(top, text="Добавить решение", command=self.add_decision_node).pack(side="left", padx=4)
        ttk.Button(top, text="Добавить событие", command=self.add_chance_node).pack(side="left", padx=4)
        ttk.Button(top, text="Добавить ребро", command=self.add_edge_dialog).pack(side="left", padx=4)
        ttk.Button(top, text="Удалить узел", command=self.delete_selected_node).pack(side="left", padx=4)
        ttk.Button(top, text="Рассчитать EMV", command=self.calculate_emv).pack(side="left", padx=10)
        ttk.Button(top, text="Сохранить JSON", command=self.save_json).pack(side="right", padx=4)
        ttk.Button(top, text="Загрузить JSON", command=self.load_json).pack(side="right", padx=4)

        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True, padx=8, pady=8)

        left = ttk.LabelFrame(main, text="Узлы (select для ред.)")
        left.pack(side="left", fill="y", padx=6, pady=6)

        self.node_listbox = tk.Listbox(left, width=36, height=24)
        self.node_listbox.pack(side="top", fill="y", padx=4, pady=4)
        self.node_listbox.bind("<<ListboxSelect>>", self.on_node_select)

        edit = ttk.LabelFrame(main, text="Редактирование узла")
        edit.pack(side="left", fill="y", padx=6, pady=6)

        ttk.Label(edit, text="ID (readonly):").pack(anchor="w", padx=6, pady=(6,2))
        self.id_label = ttk.Label(edit, text="")
        self.id_label.pack(anchor="w", padx=6)

        ttk.Label(edit, text="Название:").pack(anchor="w", padx=6, pady=(6,2))
        self.name_entry = ttk.Entry(edit, width=30)
        self.name_entry.pack(padx=6, pady=2)

        ttk.Label(edit, text="Тип узла:").pack(anchor="w", padx=6, pady=(6,2))
        self.type_var = tk.StringVar(value="decision")
        ttk.Radiobutton(edit, text="Решение", variable=self.type_var, value="decision").pack(anchor="w", padx=12)
        ttk.Radiobutton(edit, text="Событие", variable=self.type_var, value="chance").pack(anchor="w", padx=12)

        ttk.Label(edit, text="Значение (число):").pack(anchor="w", padx=6, pady=(6,2))
        self.value_entry = ttk.Entry(edit, width=30)
        self.value_entry.pack(padx=6, pady=2)

        ttk.Button(edit, text="Сохранить изменения", command=self.update_selected_node).pack(pady=10, padx=6)

        right = ttk.Frame(main)
        right.pack(side="left", fill="both", expand=True, padx=6, pady=6)

        self.fig = Figure(figsize=(7,6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    # ---------- CRUD ----------
    def new_tree(self):
        if messagebox.askyesno("Подтвердите", "Очистить текущее дерево?"):
            self.G.clear()
            self.node_counter = 0
            self.refresh_node_list()
            self.draw_tree()

    def add_decision_node(self):
        nid = f"D_{self.node_counter}"
        self.node_counter += 1
        label = f"Decision {nid}"
        self.G.add_node(nid, label=label, type="decision", value=0.0)
        self.refresh_node_list()
        self.draw_tree()

    def add_chance_node(self):
        nid = f"C_{self.node_counter}"
        self.node_counter += 1
        label = f"Chance {nid}"
        self.G.add_node(nid, label=label, type="chance", value=0.0)
        self.refresh_node_list()
        self.draw_tree()

    def delete_selected_node(self):
        nid = self.get_selected_node_id()
        if not nid: return
        if messagebox.askyesno("Подтвердите", f"Удалить узел {nid}?"):
            self.G.remove_node(nid)
            self.refresh_node_list()
            self.draw_tree()

    def add_edge_dialog(self):
        parent = self.get_selected_node_id()
        if not parent:
            messagebox.showinfo("Добавить ребро", "Сначала выберите узел-родитель")
            return
        target = simpledialog.askstring("Добавить ребро", "Введите ID дочернего узла:", parent=self.root)
        if not target or target not in self.G.nodes:
            messagebox.showerror("Ошибка", "Такого узла нет")
            return
        prob = None
        if self.G.nodes[parent].get('type') == 'chance':
            prob = simpledialog.askfloat("Вероятность", "Введите вероятность для ребра (0..1):", parent=self.root, minvalue=0.0, maxvalue=1.0)
            if prob is None: return
        self.G.add_edge(parent, target, prob=prob)
        self.draw_tree()

    def refresh_node_list(self):
        self.node_listbox.delete(0, tk.END)
        for nid in self.G.nodes:
            n = self.G.nodes[nid]
            label = n.get('label', '')
            t = n.get('type', '')
            self.node_listbox.insert(tk.END, f"{nid} — {label} ({t})")

    def get_selected_node_id(self):
        sel = self.node_listbox.curselection()
        if not sel: return None
        text = self.node_listbox.get(sel[0])
        return text.split(" — ")[0].strip() if " — " in text else text.strip()

    def on_node_select(self, event):
        nid = self.get_selected_node_id()
        if not nid or nid not in self.G.nodes: return
        data = self.G.nodes[nid]
        self.id_label.config(text=nid)
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, data.get('label', ''))
        self.type_var.set(data.get('type', 'decision'))
        self.value_entry.delete(0, tk.END)
        self.value_entry.insert(0, str(data.get('value', 0.0)))

    def update_selected_node(self):
        nid = self.get_selected_node_id()
        if not nid: return
        try:
            label = self.name_entry.get().strip() or nid
            ntype = self.type_var.get()
            val = float(self.value_entry.get())
            self.G.nodes[nid].update({'label': label, 'type': ntype, 'value': val})
            self.refresh_node_list()
            self.draw_tree()
        except:
            messagebox.showerror("Ошибка", "Неверное значение")

    # ---------- EMV ----------
    def calculate_emv(self):
        if not self.G.nodes:
            messagebox.showinfo("EMV", "Дерево пусто")
            return
        try:
            topo = list(nx.topological_sort(self.G))
        except nx.NetworkXUnfeasible:
            messagebox.showerror("Ошибка", "Граф содержит циклы")
            return

        emv = {}
        best_child = {}
        for node in reversed(topo):
            ntype = self.G.nodes[node].get('type')
            children = list(self.G.successors(node))
            if not children:
                emv[node] = self.G.nodes[node].get('value', 0.0)
                continue
            if ntype == 'chance':
                total = 0.0
                for child in children:
                    prob = self.G.edges[node, child].get('prob', 0.0)
                    total += prob * emv.get(child, self.G.nodes[child].get('value',0.0))
                emv[node] = total
            else:  # decision
                child_emvs = [emv.get(c, self.G.nodes[c].get('value',0.0)) for c in children]
                best_idx = int(max(range(len(child_emvs)), key=lambda i: child_emvs[i]))
                best_child[node] = children[best_idx]
                emv[node] = child_emvs[best_idx]

        roots = [n for n in topo if self.G.in_degree(n)==0]
        text = "\n".join([f"{r}: EMV={emv.get(r,0.0):.2f}" for r in roots])
        messagebox.showinfo("EMV результат", text)
        self.draw_tree(highlight_edges=[(u,v) for u,v in best_child.items()])

    # ---------- Draw ----------
    def draw_tree(self, highlight_edges=None):
        highlight_edges = highlight_edges or []
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.clear()
        ax.set_axis_off()
        if not self.G.nodes:
            self.canvas.draw()
            return
        pos = nx.spring_layout(self.G, seed=42, k=1.5, iterations=50)
        decision_nodes = [n for n in self.G.nodes if self.G.nodes[n].get('type')=='decision']
        chance_nodes = [n for n in self.G.nodes if self.G.nodes[n].get('type')=='chance']

        nx.draw_networkx_nodes(self.G, pos, nodelist=decision_nodes, node_color='lightblue', node_shape='s', node_size=1600, edgecolors='black')
        nx.draw_networkx_nodes(self.G, pos, nodelist=chance_nodes, node_color='lightgreen', node_shape='o', node_size=1400, edgecolors='black')

        nx.draw_networkx_edges(self.G, pos, alpha=0.4, arrows=True, arrowsize=12, width=1.2)
        if highlight_edges:
            nx.draw_networkx_edges(self.G, pos, edgelist=highlight_edges, edge_color='red', width=3, arrowsize=14)

        labels = {n: self.G.nodes[n].get('label', n) for n in self.G.nodes}
        nx.draw_networkx_labels(self.G, pos, labels, font_size=9)

        edge_labels = {}
        for u,v in self.G.edges:
            p = self.G.edges[u,v].get('prob')
            if p is not None: edge_labels[(u,v)] = f"p={p:.2f}"
        if edge_labels:
            nx.draw_networkx_edge_labels(self.G, pos, edge_labels=edge_labels, font_color='darkgreen', font_size=8)

        self.canvas.draw()

    # ---------- Save/Load ----------
    def save_json(self):
        if not self.G.nodes:
            messagebox.showinfo("Сохранение", "Дерево пустое")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
        if not path: return
        data = nx.node_link_data(self.G)
        with open(path,'w',encoding='utf-8') as f:
            json.dump(data,f,ensure_ascii=False, indent=2)
        messagebox.showinfo("Сохранено", f"Сохранено в {path}")

    def load_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Если есть ключ edges вместо links
            if 'links' not in data and 'edges' in data:
                data['links'] = data.pop('edges')

            # Нормализация: from/to → source/target
            if 'links' in data:
                normalized = []
                for link in data['links']:
                    l = dict(link)
                    if 'from' in l and 'to' in l:
                        l['source'] = l.pop('from')
                        l['target'] = l.pop('to')
                    normalized.append(l)
                data['links'] = normalized

            # NetworkX node_link_graph требует хотя бы пустой список links
            if 'links' not in data:
                data['links'] = []

            # Загружаем граф
            self.G = nx.node_link_graph(data)

            # Переносим вероятности из узлов в рёбра, если родитель chance
            for u, v in list(self.G.edges()):
                if 'prob' not in self.G.edges[u, v]:
                    child_prob = self.G.nodes[v].get('prob')
                    if child_prob is not None and self.G.nodes[u].get('type') == 'chance':
                        self.G.edges[u, v]['prob'] = child_prob

            # Обновляем счетчик узлов
            nums = []
            for n in self.G.nodes:
                try:
                    part = str(n).split('_')[-1]
                    nums.append(int(part))
                except Exception:
                    pass
            self.node_counter = max(nums, default=-1) + 1

            self.refresh_node_list()
            self.draw_tree()
            messagebox.showinfo("Загружено", f"Дерево загружено из {path}")

        except Exception as e:
            messagebox.showerror("Ошибка загрузки", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = DecisionTreeApp(root)
    root.mainloop()
