"""
build_network.py
Rakentaa haploryhmän mutaatioverkon kittien GD-osumalistoista.

Debug-tasot (asetetaan mtsettings.DEBUG):
  0 = ei viestejä
  1 = yhteenveto (kittien määrä, lopputulos)
  2 = kitti kerrallaan + GD-tasot
  3 = kaikki: nodejen luonti, yhdistely, edget

Ilpo Kantonen 2025
"""

import json
from mtsettings import DEBUG


def _log(progress_cb, level: int, msg: str):
    """Tulostaa viestin jos DEBUG >= level."""
    if progress_cb and DEBUG >= level:
        progress_cb(msg)


def get_members(gd_list: list) -> list:
    """Poimii jäsenet GD-listasta. Palauttaa {name, kit_id, is_own_kit, meka}-dictionaryjä."""
    members = []
    seen = set()
    for match in gd_list:
        name = match.get('Full Name', '').strip()
        if not name or name in seen:
            continue
        seen.add(name)
        meka = match.get('Maternal Earliest Known Ancestor', '').strip()
        members.append({'name': name, 'meka': meka, 'kit_id': None, 'is_own_kit': False})
    return members


def find_node_by_name(nodes: list, name: str) -> int | None:
    """Palauttaa node-indeksin jos nimi löytyy, muuten None. Ohittaa None-alkiot."""
    for i, node in enumerate(nodes):
        if node is not None and name in node['_names']:
            return i
    return None


def find_or_create_node(nodes: list, new_members: list,
                        own_kit_id: str, own_kit_names: set,
                        progress_cb=None) -> int:
    """
    Etsii nodea jossa on yhteisiä nimiä. Jos löytyy, yhdistää.
    Jos ei löydy, luo uuden noden.
    Poistetut nodet merkitään None:ksi — uudelleennumerointi tehdään kerran lopussa.
    """
    new_names = {m['name'] for m in new_members}

    matching_indices = set()
    for name in new_names:
        idx = find_node_by_name(nodes, name)
        if idx is not None:
            matching_indices.add(idx)

    if not matching_indices:
        new_node = {
            'id': len(nodes),
            'label': '',
            'mutation': '',
            'members': [],
            '_names': set(),
            'kit_ids': set()
        }
        nodes.append(new_node)
        target = len(nodes) - 1
        _log(progress_cb, 3, f"    → Uusi node #{target} ({len(new_names)} jäsentä)")
    else:
        target = min(matching_indices)
        extras = sorted(matching_indices - {target}, reverse=True)
        if extras:
            _log(progress_cb, 3,
                 f"    → Yhdistetään nodet {sorted(matching_indices)} → #{target}")
        for idx in extras:
            for m in nodes[idx]['members']:
                if m['name'] not in nodes[target]['_names']:
                    nodes[target]['members'].append(m)
                    nodes[target]['_names'].add(m['name'])
            nodes[target]['kit_ids'] |= nodes[idx]['kit_ids']
            nodes[idx] = None  # merkitään poistetuksi, ei pop() → O(1)

    for m in new_members:
        if m['name'] not in nodes[target]['_names']:
            m['is_own_kit'] = m['name'] in own_kit_names
            nodes[target]['members'].append(m)
            nodes[target]['_names'].add(m['name'])

    nodes[target]['kit_ids'].add(own_kit_id)
    return target


def add_edge(edges: dict, conflicts: list, from_idx: int, to_idx: int,
             gd: int, kit_id: str, progress_cb=None):
    """
    Lisää edgen edges-sanakirjaan.
    Jos sama nodepari löytyy eri GD:llä → kirjaa ristiriita.
    """
    key = tuple(sorted([from_idx, to_idx]))
    if key in edges:
        existing_gd = edges[key]['gd']
        if existing_gd != gd:
            conflicts.append({
                'nodes': list(key),
                'gd_existing': existing_gd,
                'gd_new': gd,
                'kit_id': kit_id
            })
            _log(progress_cb, 2,
                 f"    ⚠ Ristiriita: nodet {key} GD={existing_gd} vs GD={gd} (kitti {kit_id})")
            if gd < existing_gd:
                edges[key]['gd'] = gd
    else:
        edges[key] = {'gd': gd, 'kit_ids': set()}
        _log(progress_cb, 3, f"    → Edge {key[0]}—{key[1]} GD={gd}")
    edges[key]['kit_ids'].add(kit_id)


def build_network(kits: list, progress_cb=None) -> dict:
    """
    Rakentaa verkon kittien GD-osumalistoista.

    :param kits:        lista Kit-olioita joilla on gds[0..3] osumalistat
    :param progress_cb: valinnainen callable(str) edistymisviesteihin
    :return:            dict jossa 'nodes', 'edges', 'conflicts'
    """
    nodes, edges, conflicts = [], {}, []
    own_kit_names = {kit.kit_name.strip() for kit in kits}

    _log(progress_cb, 1, f"▶ Aloitetaan verkon rakentaminen — {len(kits)} kittiä")

    for ki, kit in enumerate(kits):
        _log(progress_cb, 2, f"  [{ki+1}/{len(kits)}] Kitti {kit.id} ({kit.kit_name})")

        # GD=0: kitin oma node
        gd0_members = get_members(kit.gds[0])
        _log(progress_cb, 2, f"    GD=0: {len(gd0_members)} jäsentä omassa nodessa")
        kit_node_idx = find_or_create_node(nodes, gd0_members, kit.id,
                                           own_kit_names, progress_cb)

        # GD=1,2,3: naapurinodet ja edget
        for gd in range(1, 4):
            gd_members = get_members(kit.gds[gd])
            if not gd_members:
                _log(progress_cb, 3, f"    GD={gd}: ei osumia")
                continue
            _log(progress_cb, 2, f"    GD={gd}: {len(gd_members)} jäsentä naapurinodessa")
            neighbor_idx = find_or_create_node(nodes, gd_members, kit.id,
                                               own_kit_names, progress_cb)
            if neighbor_idx != kit_node_idx:
                add_edge(edges, conflicts, kit_node_idx, neighbor_idx,
                         gd, kit.id, progress_cb)

        # Väliyhteenveto taso 2:ssä
        active = sum(1 for n in nodes if n is not None)
        _log(progress_cb, 2, f"    Tilanne: {active} nodea, {len(edges)} edgeä")

    # Siivotaan None-alkiot ja tehdään uudelleennumerointi kerran
    _log(progress_cb, 1, "▶ Siivotaan ja numeroidaan nodet...")
    old_to_new = {}
    clean_nodes = []
    for old_idx, node in enumerate(nodes):
        if node is not None:
            new_idx = len(clean_nodes)
            old_to_new[old_idx] = new_idx
            node['id'] = new_idx
            clean_nodes.append(node)

    _log(progress_cb, 3, f"  Poistettu {len(nodes) - len(clean_nodes)} yhdisteltyä (None) nodea")

    # Päivitetään edge-indeksit
    clean_edges = {}
    for (a, b), data in edges.items():
        na, nb = old_to_new.get(a), old_to_new.get(b)
        if na is None or nb is None:
            continue
        clean_edges[tuple(sorted([na, nb]))] = data

    # Päivitetään conflicts-indeksit
    clean_conflicts = []
    for c in conflicts:
        na = old_to_new.get(c['nodes'][0])
        nb = old_to_new.get(c['nodes'][1])
        if na is not None and nb is not None:
            clean_conflicts.append({**c, 'nodes': [na, nb]})

    _log(progress_cb, 1,
         f"✔ Valmis: {len(clean_nodes)} nodea, {len(clean_edges)} edgeä"
         + (f", {len(clean_conflicts)} ristiriitaa" if clean_conflicts else ", ei ristiriitoja"))

    result = {
        "haplogroup": kits[0].haplogroup if kits else "",
        "nodes": [
            {
                "id":      node['id'],
                "label":   node.get('label', ''),
                "mutation": node.get('mutation', ''),
                "members": node['members'],
                "kit_ids": sorted(node['kit_ids'])
            }
            for node in clean_nodes
        ],
        "edges": [
            {
                "from":    a,
                "to":      b,
                "gd":      data['gd'],
                "kit_ids": sorted(data['kit_ids'])
            }
            for (a, b), data in sorted(clean_edges.items())
        ],
        "conflicts": clean_conflicts
    }

    return result


def save_network(network: dict, filename: str, encoding: str = 'utf-8'):
    """Tallentaa verkon JSON-tiedostoon."""
    with open(filename, 'w', encoding=encoding) as f:
        json.dump(network, f, indent=2, ensure_ascii=False)
    print(f"Verkko tallennettu: {filename}")
    print(f"  Nodeja:    {len(network['nodes'])}")
    print(f"  Edgejä:    {len(network['edges'])}")
    if network['conflicts']:
        print(f"  RISTIRIITOJA: {len(network['conflicts'])}!")
        for c in network['conflicts']:
            print(f"    Nodet {c['nodes']}: GD={c['gd_existing']} vs "
                  f"GD={c['gd_new']} (kitti {c['kit_id']})")
    else:
        print(f"  Ristiriitoja: ei — kaikki täsmäsi!")


def load_network(filename: str, encoding: str = 'utf-8') -> dict:
    """Lataa verkon JSON-tiedostosta."""
    with open(filename, 'r', encoding=encoding) as f:
        return json.load(f)
