"""Render the public GitHub activity dashboard for the profile README."""

import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

USER = "MitoCoder"
ASSETS = Path(__file__).resolve().parents[1] / "assets"
COLORS = ("#1a2942", "#263e75", "#484aaa", "#795bea", "#b49aff")


def fetch(url):
    request = Request(url, headers={"User-Agent": f"{USER}-profile-dashboard"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


class Calendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.counts = {}
        self.tooltip = None

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "td" and "data-date" in attrs and "data-level" in attrs:
            cell_id = attrs["id"]
            row, column = map(int, cell_id.rsplit("-", 2)[1:])
            self.cells[cell_id] = (row, column, int(attrs["data-level"]))
        if tag == "tool-tip" and attrs.get("for") in self.cells:
            self.tooltip = attrs["for"]

    def handle_endtag(self, tag):
        if tag == "tool-tip":
            self.tooltip = None

    def handle_data(self, text):
        if self.tooltip:
            match = re.match(r"(No|[\d,]+) contributions? on ", text.strip())
            if match:
                count = match.group(1).replace(",", "")
                self.counts[self.tooltip] = 0 if count == "No" else int(count)


def svg_text(x, y, value, size, fill="#eaf1ff", weight=400):
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" '
        f'font-weight="{weight}">{html.escape(str(value))}</text>'
    )


def write_svg(filename, description, height, elements):
    markup = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1040 {height}" '
        f'width="1040" height="{height}" role="img" aria-labelledby="title" '
        'font-family="Segoe UI, Arial, sans-serif">',
        f'<title id="title">{html.escape(description)}</title>',
        f'<rect x="1" y="1" width="1038" height="{height - 2}" rx="22" '
        'fill="#0b1326" stroke="#344368" stroke-width="2"/>',
        *elements,
        "</svg>",
    ]
    (ASSETS / filename).write_text("\n".join(markup) + "\n", encoding="utf-8")


def render_metrics(calendar, commits, pushes):
    contributions = sum(calendar.counts.values())
    active_days = sum(count > 0 for count in calendar.counts.values())
    metrics = [
        (contributions, "Contribuições", "últimos 12 meses"),
        (commits, "Commits públicos", "indexados pelo GitHub"),
        (pushes, "Pushes públicos", "eventos recentes"),
        (active_days, "Dias ativos", "últimos 12 meses"),
    ]
    elements = []
    for index, (value, label, period) in enumerate(metrics):
        x = 34 + index * 252
        if index:
            elements.append(f'<path d="M{x - 17} 24v110" stroke="#344368"/>')
        elements.extend([
            svg_text(x, 66, value, 50, "#b49aff", 700),
            svg_text(x, 102, label, 22, weight=700),
            svg_text(x, 127, period, 17, "#bac8e4"),
        ])
    description = " · ".join(f"{value} {label.lower()} ({period})"
                             for value, label, period in metrics)
    write_svg("atividade.svg", description, 158, elements)


def render_snake(calendar):
    grid = {(row, column): level for row, column, level in calendar.cells.values()}
    columns = max(column for _, column in grid) + 1
    tiles = [
        (row, column)
        for column in range(columns)
        for row in (range(7) if column % 2 == 0 else range(6, -1, -1))
        if (row, column) in grid
    ]
    step = min(18, 954 // columns)
    left = (1040 - columns * step) // 2
    top = 66
    tile = step - 4
    duration = len(tiles) + 10
    elements = [
        '<style>@media (prefers-reduced-motion: reduce) { .motion { display: none; } }</style>',
        svg_text(left, 41, "MITOCODER ARCADE", 23, "#b49aff", 700),
        svg_text(left + 300, 41, "COBRINHA DE CONTRIBUIÇÕES", 17, "#bac8e4", 700),
    ]
    positions = []
    for row, column in tiles:
        x, y = left + column * step, top + row * step
        positions.append((x, y))
        shape = f'<rect x="{x}" y="{y}" width="{tile}" height="{tile}" rx="3"'
        elements.append(f'{shape} fill="{COLORS[grid[row, column]]}"/>')

    for index, (row, column) in enumerate(tiles):
        if grid[row, column]:
            x, y = positions[index]
            key = f"{(index + 4) / duration:.6f}"
            elements.append(
                f'<rect class="motion" x="{x}" y="{y}" width="{tile}" height="{tile}" '
                f'rx="3" fill="{COLORS[0]}" opacity="0">'
                f'<animate attributeName="opacity" values="0;1;0" keyTimes="0;{key};1" '
                f'calcMode="discrete" dur="28s" repeatCount="indefinite"/></rect>'
            )

    offscreen = [(-40, -40)]
    for index, color in enumerate(("#2e9b9d", "#4fc8b8", "#8ff5d7", "#dcfff3")):
        path = offscreen * (7 - index) + positions + offscreen * (3 + index)
        coordinates = ";".join(f"{x} {y}" for x, y in path)
        elements.append(
            f'<rect class="motion" x="0" y="0" width="{tile}" height="{tile}" '
            f'rx="4" fill="{color}" transform="translate(-40 -40)">'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="{coordinates}" calcMode="discrete" dur="28s" '
            'repeatCount="indefinite"/></rect>'
        )

    elements.append(svg_text(left, top + 7 * step + 20,
                             "Cada quadrado representa um dia no GitHub.", 17, "#bac8e4"))
    write_svg("cobrinha.svg", "Cobrinha animada no calendário de contribuições de MitoCoder",
              top + 7 * step + 39, elements)


def main():
    calendar = Calendar()
    calendar.feed(fetch(f"https://github.com/users/{USER}/contributions"))
    if not 350 <= len(calendar.cells) <= 380 or calendar.cells.keys() != calendar.counts.keys():
        raise ValueError("Não foi possível ler o calendário completo do perfil.")

    api = "https://api.github.com"
    search = json.loads(fetch(f"{api}/search/commits?q=author%3A{USER}&per_page=1"))
    if search["incomplete_results"]:
        raise ValueError("A busca de commits retornou resultados incompletos.")

    pushes = 0
    for page in range(1, 4):
        events = json.loads(fetch(f"{api}/users/{USER}/events/public?per_page=100&page={page}"))
        pushes += sum(event["type"] == "PushEvent" for event in events)
        if len(events) < 100:
            break

    render_metrics(calendar, search["total_count"], pushes)
    render_snake(calendar)


if __name__ == "__main__":
    main()
