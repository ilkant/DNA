"""
Lukee verkkograafin CSV-tiedostosta.

CSV-formaatti — kaksi rivityyppiä:
  - Nodes-rivi: pilkulla eroteltu lista solmujen nimistä
      Ma, Mb, Mc, M4, M5, ...
  - Links-rivi: pilkulla eroteltu lista yhteyksistä muodossa "A - B"
      Ma - Mb, Ma - M10, Mb - Mc, ...

Rivityyppi tunnistetaan automaattisesti: jos arvo sisältää " - ", se on linkki.
"""

import csv
import json


def read_graph_csv(filepath: str) -> tuple[list[str], list[tuple[str, str]]]:
    """
    Lukee verkkograafin CSV-tiedostosta.

    Returns:
        nodes: lista solmujen nimistä
        links: lista (alku, loppu) -tupleista
    """
    nodes: list[str] = []
    links: list[tuple[str, str]] = []

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            values = [v.strip() for v in row if v.strip()]
            if not values:
                continue

            # Ohitetaan avainsanat "Nodes" ja "Links" rivin alussa
            if values[0] in ("Nodes", "Links"):
                values = values[1:]
            if not values:
                continue

            # Tunnista rivityyppi: jos ensimmäinen arvo sisältää " - ", kaikki ovat linkkejä
            if " - " in values[0]:
                for item in values:
                    parts = [p.strip() for p in item.split(" - ")]
                    if len(parts) == 2:
                        links.append((parts[0], parts[1]))
                    else:
                        print(f"Varoitus: tuntematon linkkimuoto '{item}'")
            else:
                nodes.extend(values)

    return nodes, links


def build_network(nodes: list[str], links: list[tuple[str, str]]) -> dict:
    """
    Muodostaa verkon solmuista ja yhteyksistä.

    Rakenne:
    {
        "nodes": [
            { "id": "Ma", "neighbors": ["Mb", "M10", "M11"] },
            ...
        ],
        "links": [
            { "source": "Ma", "target": "Mb" },
            ...
        ]
    }
    """
    # Rakennetaan naapurilista jokaiselle solmulle
    neighbor_map: dict[str, list[str]] = {node: [] for node in nodes}

    for source, target in links:
        if source in neighbor_map:
            neighbor_map[source].append(target)
        else:
            print(f"Varoitus: linkissä tuntematon solmu '{source}'")
        if target in neighbor_map:
            neighbor_map[target].append(source)  # suuntaamaton verkko
        else:
            print(f"Varoitus: linkissä tuntematon solmu '{target}'")

    network = {
        "nodes": [
            {"id": node, "neighbors": neighbor_map[node]}
            for node in nodes
        ],
        "links": [
            {"source": source, "target": target}
            for source, target in links
        ]
    }
    return network


def main():
    input_file  = "J1c2n1.csv"   # Vaihda tiedostopolku tarvittaessa
    output_file = "J1c2n1-1.json"

    nodes, links = read_graph_csv(input_file)

    print("=== Solmut (Nodes) ===")
    print(", ".join(nodes))
    print(f"Yhteensä {len(nodes)} solmua.\n")

    print("=== Yhteydet (Links) ===")
    for source, target in links:
        print(f"  {source} --> {target}")
    print(f"Yhteensä {len(links)} yhteyttä.\n")

    # Muodostetaan verkko ja tallennetaan JSON:iin
    network = build_network(nodes, links)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(network, f, indent=2, ensure_ascii=False)

    print(f"Verkko tallennettu tiedostoon: {output_file}")


if __name__ == "__main__":
    main()
