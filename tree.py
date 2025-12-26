import json
import networkx as nx
import matplotlib.pyplot as plt

# Функция для загрузки данных из JSON
def load_data():
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            print("Данные успешно загружены из файла 'data.json'.")
            return data
    except FileNotFoundError:
        print("Файл 'data.json' не найден. Использую встроенные (hardcoded) данные.")
        # Hardcoded JSON как fallback
        data_json = '''
        {
          "projects": ["X", "Y", "Z"],
          "wins_favorable": [460000, 450000, 350000],
          "wins_unfavorable": [250000, -85000, -80000],
          "probs_favorable_base": [0.51, 0.67, 0.98],
          "research_cost": 50000,
          "p_forecast_favorable": 0.52,
          "p_fav_given_forecast_fav": 0.71,
          "p_fav_given_forecast_unfav": 0.31
        }
        '''
        return json.loads(data_json)
    except json.JSONDecodeError:
        print("Ошибка в формате JSON в файле 'data.json'. Использую встроенные данные.")
        return json.loads(data_json)  # fallback

# Загружаем данные
data = load_data()

# Извлекаем параметры
projects = data["projects"]
wins_fav = data["wins_favorable"]
wins_unfav = data["wins_unfavorable"]
probs_fav_base = data["probs_favorable_base"]
cost = data["research_cost"]
p_forecast_fav = data["p_forecast_favorable"]
p_fav_given_fav = data["p_fav_given_forecast_fav"]
p_fav_given_unfav = data["p_fav_given_forecast_unfav"]
p_forecast_unfav = 1 - p_forecast_fav
p_unfav_given_fav = 1 - p_fav_given_fav
p_unfav_given_unfav = 1 - p_fav_given_unfav

# Функция для расчёта ОДО
def calculate_odo(w_fav, w_unfav, p_fav):
    return p_fav * w_fav + (1 - p_fav) * w_unfav

# Базовые ОДО без исследования
odos_base = [calculate_odo(wins_fav[i], wins_unfav[i], probs_fav_base[i]) for i in range(3)]
best_base_idx = odos_base.index(max(odos_base))
best_base_odo = odos_base[best_base_idx]
best_base_project = projects[best_base_idx]

# ОДО при благоприятном прогнозе
odos_fav_forecast = [calculate_odo(wins_fav[i], wins_unfav[i], p_fav_given_fav) for i in range(3)]
max_fav_idx = odos_fav_forecast.index(max(odos_fav_forecast))
max_fav_odo = odos_fav_forecast[max_fav_idx]
max_fav_project = projects[max_fav_idx]

# ОДО при неблагоприятном прогнозе
odos_unfav_forecast = [calculate_odo(wins_fav[i], wins_unfav[i], p_fav_given_unfav) for i in range(3)]
max_unfav_idx = odos_unfav_forecast.index(max(odos_unfav_forecast))
max_unfav_odo = odos_unfav_forecast[max_unfav_idx]
max_unfav_project = projects[max_unfav_idx]

# Общая ОДО с исследованием
odo_with_research = p_forecast_fav * max_fav_odo + p_forecast_unfav * max_unfav_odo
odo_net = odo_with_research - cost

# Определяем, выгоднее ли исследование
if odo_net > best_base_odo:
    best_option = "Проводить исследование"
    best_value = odo_net
else:
    best_option = "Не проводить исследование"
    best_value = best_base_odo

# Вывод расчётов (для обоснования)
print("Базовые ОДО:")
for i, proj in enumerate(projects):
    print(f"{proj}: {odos_base[i]}")
print(f"Лучший без исследования: {best_base_project} с {best_base_odo}\n")

print("ОДО при благоприятном прогнозе:")
for i, proj in enumerate(projects):
    print(f"{proj}: {odos_fav_forecast[i]}")
print(f"Max: {max_fav_odo} ({max_fav_project})\n")

print("ОДО при неблагоприятном прогнозе:")
for i, proj in enumerate(projects):
    print(f"{proj}: {odos_unfav_forecast[i]}")
print(f"Max: {max_unfav_odo} ({max_unfav_project})\n")

print(f"ОДО с исследованием: {odo_with_research}")
print(f"Net ОДО: {odo_net}")
print(f"Наиболее выгодный вариант: {best_option} с значением {best_value}")

# Теперь строим дерево с вычисленными значениями
G = nx.DiGraph()

# Узлы с метками (динамические значения)
nodes = {
    "Start": "Начало\n(Выбор: исследование?)",
    "Research": f"Проводить исследование\n(-{cost})",
    "NoResearch": "Не проводить\nисследование",
    "ForecastFav": f"Прогноз благоприятный\n{p_forecast_fav}",
    "ForecastUnfav": f"Прогноз неблагоприятный\n{p_forecast_unfav}",
    "MaxFav": f"max = {max_fav_odo}\n(Выбрать {max_fav_project})",
    "MaxUnfav": f"max = {max_unfav_odo}\n(Выбрать {max_unfav_project})",
    "Total": f"ОДО = {odo_with_research}\nNet = {odo_net}",
    "BestNoRes": f"max = {best_base_odo}\n(Выбрать {best_base_project})",
}

# Добавляем узлы проектов
for i, proj in enumerate(projects):
    nodes[f"Fav{proj}"] = f"{proj}\n{odos_fav_forecast[i]}{' *' if i == max_fav_idx else ''}"
    nodes[f"Unfav{proj}"] = f"{proj}\n{odos_unfav_forecast[i]}{' *' if i == max_unfav_idx else ''}"
    nodes[f"No{proj}"] = f"{proj}\n{odos_base[i]}{' *' if i == best_base_idx else ''}"

for node, label in nodes.items():
    G.add_node(node, label=label)

# Ребра (динамические цвета: красный для оптимального пути)
research_color = "red" if odo_net > best_base_odo else "black"
no_research_color = "red" if odo_net <= best_base_odo else "black"

forecast_fav_color = "red" if odo_net > best_base_odo else "black"
forecast_unfav_color = "black"  # Обычно не оптимальный, но если нужно, можно скорректировать

edges = [
    ("Start", "Research", {"label": f"Проводить (-{cost})", "color": research_color, "fontcolor": research_color}),
    ("Start", "NoResearch", {"label": "Не проводить", "color": no_research_color, "fontcolor": no_research_color}),

    ("Research", "ForecastFav",
     {"label": f"{p_forecast_fav}", "color": forecast_fav_color, "fontcolor": forecast_fav_color}),
    ("Research", "ForecastUnfav", {"label": f"{p_forecast_unfav}", "color": "black"}),

    ("ForecastFav", f"Fav{projects[0]}",
     {"label": f"{p_fav_given_fav} / {p_unfav_given_fav}", "color": "red" if 0 == max_fav_idx else "gray",
      "fontcolor": "red" if 0 == max_fav_idx else "black"}),
    ("ForecastFav", f"Fav{projects[1]}",
     {"label": f"{p_fav_given_fav} / {p_unfav_given_fav}", "color": "red" if 1 == max_fav_idx else "gray",
      "fontcolor": "red" if 1 == max_fav_idx else "black"}),
    ("ForecastFav", f"Fav{projects[2]}",
     {"label": f"{p_fav_given_fav} / {p_unfav_given_fav}", "color": "red" if 2 == max_fav_idx else "gray",
      "fontcolor": "red" if 2 == max_fav_idx else "black"}),

    ("ForecastUnfav", f"Unfav{projects[0]}",
     {"label": f"{p_fav_given_unfav} / {p_unfav_given_unfav}", "color": "red" if 0 == max_unfav_idx else "gray",
      "fontcolor": "red" if 0 == max_unfav_idx else "black"}),
    ("ForecastUnfav", f"Unfav{projects[1]}",
     {"label": f"{p_fav_given_unfav} / {p_unfav_given_unfav}", "color": "red" if 1 == max_unfav_idx else "gray",
      "fontcolor": "red" if 1 == max_unfav_idx else "black"}),
    ("ForecastUnfav", f"Unfav{projects[2]}",
     {"label": f"{p_fav_given_unfav} / {p_unfav_given_unfav}", "color": "red" if 2 == max_unfav_idx else "gray",
      "fontcolor": "red" if 2 == max_unfav_idx else "black"}),

    (f"Fav{projects[0]}", "MaxFav", {"label": "", "color": "red" if 0 == max_fav_idx else "gray"}),
    (f"Fav{projects[1]}", "MaxFav", {"label": "", "color": "red" if 1 == max_fav_idx else "gray"}),
    (f"Fav{projects[2]}", "MaxFav", {"label": "", "color": "red" if 2 == max_fav_idx else "gray"}),

    (f"Unfav{projects[0]}", "MaxUnfav", {"label": "", "color": "red" if 0 == max_unfav_idx else "gray"}),
    (f"Unfav{projects[1]}", "MaxUnfav", {"label": "", "color": "red" if 1 == max_unfav_idx else "gray"}),
    (f"Unfav{projects[2]}", "MaxUnfav", {"label": "", "color": "red" if 2 == max_unfav_idx else "gray"}),

    ("MaxFav", "Total", {"label": "", "color": "red"}),
    ("MaxUnfav", "Total", {"label": "", "color": "black"}),

    ("NoResearch", f"No{projects[0]}",
     {"label": f"{probs_fav_base[0]} / {1 - probs_fav_base[0]}", "color": "red" if 0 == best_base_idx else "gray",
      "fontcolor": "red" if 0 == best_base_idx else "black"}),
    ("NoResearch", f"No{projects[1]}",
     {"label": f"{probs_fav_base[1]} / {1 - probs_fav_base[1]}", "color": "red" if 1 == best_base_idx else "gray",
      "fontcolor": "red" if 1 == best_base_idx else "black"}),
    ("NoResearch", f"No{projects[2]}",
     {"label": f"{probs_fav_base[2]} / {1 - probs_fav_base[2]}", "color": "red" if 2 == best_base_idx else "gray",
      "fontcolor": "red" if 2 == best_base_idx else "black"}),

    (f"No{projects[0]}", "BestNoRes", {"label": "", "color": "red" if 0 == best_base_idx else "gray"}),
    (f"No{projects[1]}", "BestNoRes", {"label": "", "color": "red" if 1 == best_base_idx else "gray"}),
    (f"No{projects[2]}", "BestNoRes", {"label": "", "color": "red" if 2 == best_base_idx else "gray"}),
]

for u, v, d in edges:
    G.add_edge(u, v, **d)

# Позиционирование (адаптировано для 3 проектов)
pos = {
    "Start": (0, 10),
    "Research": (3, 15),
    "NoResearch": (3, 5),
    "ForecastFav": (6, 18),
    "ForecastUnfav": (6, 12),
    "BestNoRes": (6, 5),
    f"Fav{projects[0]}": (9, 20),
    f"Fav{projects[1]}": (9, 18),
    f"Fav{projects[2]}": (9, 16),
    f"Unfav{projects[0]}": (9, 13),
    f"Unfav{projects[1]}": (9, 11),
    f"Unfav{projects[2]}": (9, 9),
    f"No{projects[0]}": (9, 6),
    f"No{projects[1]}": (9, 4),
    f"No{projects[2]}": (9, 2),
    "MaxFav": (12, 18),
    "MaxUnfav": (12, 12),
    "Total": (15, 15),
}

# Рисование
plt.figure(figsize=(18, 12))

nx.draw_networkx_nodes(G, pos, node_shape="s", node_size=4000, node_color="lightblue", edgecolors="black")

labels = nx.get_node_attributes(G, 'label')
nx.draw_networkx_labels(G, pos, labels, font_size=9, font_weight="bold")

edge_colors = [G[u][v]['color'] for u, v in G.edges()]
nx.draw_networkx_edges(G, pos, edge_color=edge_colors, arrows=True, arrowsize=20, width=2)

edge_labels = nx.get_edge_attributes(G, 'label')
filtered_edge_labels = {k: v for k, v in edge_labels.items() if v}
nx.draw_networkx_edge_labels(G, pos, edge_labels=filtered_edge_labels, font_color="black", font_size=8)

plt.title("Дерево решений при дополнительном исследовании рынка", fontsize=16, pad=20)
plt.axis("off")
plt.tight_layout()
plt.show()