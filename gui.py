
"""
Graafinen klusterointityökalun pääohjelma.
Ilpo Kantonen ilpo@iki.fi. Started spring 2018. AI assisted autumn 2025
"""

from mtsettings import (
    KITSFILE, HAPLOGROUP, OUTPUTDIR, DATATYPE, DLDIR, SHOW_NAMES,
    CLUSTER_NODE_COLOR, CLUSTER_NODE_BORDER_COLOR,
    MEMBER_NODE_COLOR,  MEMBER_NODE_BORDER_COLOR,
    EDGE_COLOR, MEMBER_EDGE_COLOR,
    CLUSTER_LABEL_COLOR, MEMBER_LABEL_COLOR,
    BACKGROUND_COLOR,
    FONT_FAMILY, CLUSTER_FONT_SIZE, MEMBER_FONT_SIZE,
    CLUSTER_FONT_BOLD, MEMBER_FONT_BOLD,
)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QTextEdit, QLabel,
    QMenuBar, QDialog, QFormLayout, QLineEdit,
    QRadioButton, QButtonGroup, QDialogButtonBox,
    QGroupBox, QHBoxLayout, QColorDialog, QTabWidget,
    QSpinBox, QCheckBox, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import QThread, pyqtSignal, QObject, Qt
from PyQt6.QtGui import QAction, QColor

import sys, csv, os, json
import mtsettings
import networkx as nx
import matplotlib.pyplot as plt

from kit import Kit
from netclusters import NetClusters
from mtsettings import KITSFILE, HAPLOGROUP, OUTPUTDIR, DATATYPE, DLDIR, SHOW_NAMES
from build_network import build_network, save_network

DEFAULT_ENCODING = 'utf-8'              # Oletusmerkistö JSON-tallennukseen


class Worker(QObject):
    """Taustasäie, joka suorittaa aikaa vievän datan käsittelyn."""
    # Signaalit (luokka-attribuuttina)
    finished = pyqtSignal()
    progress = pyqtSignal(str)
    plot_data_ready = pyqtSignal(object, object, object, object, object, object, object, object, object, str, object)

    def __init__(self, n_clusters_instance: NetClusters = None):
        super().__init__()
        # n on NetClusters-instanssi (verkko + klusterit)
        self.n = n_clusters_instance if n_clusters_instance is not None else NetClusters()
        self.kits = []
        self.alreadynet = False

    def load_kitlist(self):
        """Lataa kitit levyltä ja lukee niiden osumatiedostot."""
        self.kits.clear()

        try:
            with open(KITSFILE, newline='') as f:
                reader = csv.reader(f)
                data = [tuple(row) for row in reader]
        except FileNotFoundError:
            self.progress.emit(f"Virhe: {KITSFILE} ei löytynyt.")
            self.finished.emit()
            return

        found, notfound = [], []

        for row in data:
            # oletetaan, että rivillä on vähintään 3 saraketta (id, nimi, tiedosto)
            k = Kit(*row[:3])
            self.kits.append(k)
            if os.path.isfile(k.file):
                found.append(k.id)
                try:
                    k.read_matches()
                except Exception as e:
                    self.progress.emit(f"Varoitus: virhe luettaessa {k.file}: {e}")
            else:
                notfound.append(k.id)

        # Muodosta viesti käyttöliittymään
        if not found and not notfound:
            msg = "Yhtään kittiä ei löytynyt."
        elif notfound and not found:
            msg = f"Kittien {', '.join(notfound)} osumalistoja ei löytynyt."
        elif found and not notfound:
            msg = f"Luettiin {len(found)} kitin osumalistat: {', '.join(found)}"
        else:
            msg = (
                f"Luettiin {len(found)} kitin osumalistat ({', '.join(found)}). "
                f"{len(notfound)} kitin osumalistoja ei löytynyt ({', '.join(notfound)})."
            )

        self.progress.emit(msg)
        self.finished.emit()

    def load_from_json(self, filename: str):
        """Lataa verkko- / klusteritiedot JSON-tiedostosta."""
        try:
            with open(filename, "r", encoding=DEFAULT_ENCODING) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.progress.emit(f"Virhe JSON-latauksessa: {e}")
            self.finished.emit()
            return

        if isinstance(data, dict) and "nodes" in data and "links" in data and "edges" not in data:
            # testiverkko.json -muoto: nodes[{id, neighbors}] + links[{source, target}]
            network = self._links_to_network(data)
            self.n.network = network
            n_nodes = len(network["nodes"])
            n_edges = len(network["edges"])
            self.progress.emit(f"Ladattiin haploryhmä (nodes+links): {n_nodes} nodea, {n_edges} edgeä tiedostosta {filename}.")
        elif isinstance(data, dict) and "nodes" in data and "edges" in data:
            # Yhtenäinen tallennettu muoto (haplogroup + nodes + edges, koordinaatit mukana)
            self.n.network = data
            n_nodes = len(data.get("nodes", []))
            n_edges = len(data.get("edges", []))
            coords  = sum(1 for nd in data.get("nodes", []) if 'x' in nd)
            self.progress.emit(
                f"Ladattiin haploryhmä: {n_nodes} nodea, {n_edges} edgeä"
                + (f", {coords} tallennettu koordinaatit" if coords else " (ei koordinaatteja)")
                + f" tiedostosta {filename}.")
        elif isinstance(data, dict) and "nclusters" in data:
            # Vanha muoto: {"nclusters": [...]}
            nclusters = data["nclusters"]
            self.n.nclusters = nclusters
            self.n.network = self._nclusters_to_network(nclusters)
            n_nodes = len(self.n.network.get("nodes", []))
            self.progress.emit(f"Ladattiin {len(nclusters)} klusteria (nclusters-muoto), muunnettu {n_nodes} nodeksi.")
        elif isinstance(data, list):
            # Vanha nclusters-lista
            self.n.nclusters = data
            self.n.network = self._nclusters_to_network(data)
            self.progress.emit(f"Ladattiin {len(data)} klusteria (vanha muoto) tiedostosta {filename}.")
        else:
            self.progress.emit(f"Tuntematon JSON-rakenne tiedostossa {filename}: {type(data)}")

        self.finished.emit()

    def _links_to_network(self, data: dict) -> dict:
        """Muuntaa nodes+links -formaatin (testiverkko.json) sisäiseen nodes/edges-muotoon."""
        nodes_out = []
        for i, node in enumerate(data.get("nodes", [])):
            nid = node.get("id", str(i))
            nodes_out.append({
                "id":       nid,
                "label":    nid,
                "mutation": "",
                "members":  [],
                "kit_ids":  [],
            })
        edges_out = []
        seen = set()
        for link in data.get("links", []):
            src = link.get("source", "")
            tgt = link.get("target", "")
            key = tuple(sorted([src, tgt]))
            if key not in seen:
                seen.add(key)
                edges_out.append({"from": src, "to": tgt, "gd": 1})
        return {
            "haplogroup": "",
            "nodes":      nodes_out,
            "edges":      edges_out,
            "conflicts":  [],
        }

    def load_csv_structure(self, filename: str):
        """Lukee verkon rungon CSV-tiedostosta (testiverkko.csv -muoto).
        Formaatti: Nodes, Ma, Mb, ...
                   Links, Ma - Mb, Ma - M15, ...
        """
        try:
            nodes = []
            links = []
            with open(filename, newline='', encoding='utf-8') as f:
                import csv as _csv
                for row in _csv.reader(f):
                    if not row:
                        continue
                    tag = row[0].strip().lower()
                    if tag == 'nodes':
                        nodes = [x.strip() for x in row[1:] if x.strip()]
                    elif tag == 'links':
                        for item in row[1:]:
                            parts = [p.strip() for p in item.split('-')]
                            if len(parts) == 2 and parts[0] and parts[1]:
                                links.append({'source': parts[0], 'target': parts[1]})

            # Rakennetaan sisäinen network-rakenne (ilman jäseniä vielä)
            network = {
                'haplogroup': '',
                'nodes': [{'id': nid, 'label': nid, 'mutation': '',
                           'members': [], 'kit_ids': []} for nid in nodes],
                'edges': [{'from': lnk['source'], 'to': lnk['target'], 'gd': 1}
                          for lnk in links],
                'conflicts': [],
            }
            self.n.network = network
            self.progress.emit(
                f"Ladattiin haploryhmän verkkorakenne: {len(nodes)} nodea, {len(links)} linkkiä tiedostosta {filename}.")
        except Exception as e:
            self.progress.emit(f"Virhe CSV-latauksessa: {e}")
        self.finished.emit()

    def load_member_data(self, filename: str):
        """Lataa jäsendata JSON:sta ja yhdistää ne verkon nodeihin my_label/name-avaimella.
        Tunnistaa myös tallennetun muodon (nodes+edges) ja lataa sen suoraan.
        """
        try:
            import json as _json
            with open(filename, 'r', encoding='utf-8') as f:
                data = _json.load(f)
        except Exception as e:
            self.progress.emit(f"Virhe JSON-latauksessa: {e}")
            self.finished.emit()
            return

        # Tallennettu muoto (nodes + edges) — lataa suoraan ilman yhdistämistä
        if isinstance(data, dict) and 'nodes' in data and 'edges' in data:
            self.n.network = data
            n_nodes = len(data.get('nodes', []))
            n_edges = len(data.get('edges', []))
            coords  = sum(1 for nd in data.get('nodes', []) if 'x' in nd)
            self.progress.emit(
                f"Ladattiin tallennettu haploryhmä: {n_nodes} nodea, {n_edges} edgeä"
                + (f", koordinaatit tallennettu {coords} nodelle" if coords else "")
                + f" — tiedostosta {filename}.")
            self.finished.emit()
            return

        # Hae nclusters-lista (alkuperäinen muoto)
        if isinstance(data, dict) and 'nclusters' in data:
            nclusters = data['nclusters']
        elif isinstance(data, list):
            nclusters = data
        else:
            self.progress.emit(f"Tuntematon jäsendatan rakenne. Avaimet: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            self.finished.emit()
            return

        # Varmista että verkkorunko on ladattu
        network = getattr(self.n, 'network', None)
        if not network or not network.get('nodes'):
            self.progress.emit("Lataa ensin haploryhmän verkkorakenne (CSV)!")
            self.finished.emit()
            return

        # Rakenna hakemisto: node_id -> node-dict
        node_map = {node['id']: node for node in network['nodes']}

        matched, unmatched = 0, 0
        for clu in nclusters:
            if not isinstance(clu, dict):
                continue
            # Selvitä mihin nodeen tämä klusteri kuuluu
            my_label = clu.get('my_label', '').strip()
            name     = clu.get('name', '').strip()

            # Kokeile my_label ensin, sitten name, sitten name:n viimeinen sana
            node_id = None
            if my_label and my_label in node_map:
                node_id = my_label
            elif name in node_map:
                node_id = name
            else:
                # name voi olla "U8a1a1b1a M4" -> viimeinen sana on node id
                last_word = name.split()[-1] if name.split() else ''
                if last_word in node_map:
                    node_id = last_word

            if node_id is None:
                unmatched += 1
                continue

            # Lisää jäsenet nodeen
            members_raw = clu.get('members', [])
            members = []
            for m in members_raw:
                if isinstance(m, dict):
                    mname = m.get('Full Name', '').strip()
                    if mname:
                        members.append({
                            'name':       mname,
                            'meka':       m.get('MDKA', '').strip(),
                            'haplogroup': m.get('Haplogroup', '').strip(),
                            'date':       m.get('Date', '').strip(),
                            'yfull':      m.get('YFull Account', '').strip(),
                            'email':      m.get('Email', '').strip(),
                            'kit_id':     None,
                            'is_own_kit': False,
                        })
            node_map[node_id]['members'].extend(members)
            node_map[node_id]['mutation'] = clu.get('mutation', '')
            matched += 1

        self.progress.emit(
            f"Yhdistetty: {matched} klusteria kohdistettiin, {unmatched} ei löytänyt nodea.")
        self.finished.emit()

    def _nclusters_to_network(self, nclusters: list) -> dict:
        """Muuntaa nclusters-listan nodes/edges-verkoksi show_network:ia varten.
        Nclusters-muodossa ei ole valmiita GD-edgejä, joten niitä ei lisätä.
        """
        nodes = []
        for i, clu in enumerate(nclusters):
            if not isinstance(clu, dict):
                continue
            members_raw = clu.get("members", [])
            members = []
            for m in members_raw:
                if isinstance(m, dict):
                    name = m.get("Full Name", "").strip()
                    meka = m.get("MDKA", "").strip()
                    if name:
                        members.append({
                            "name":       name,
                            "meka":       meka,
                            "haplogroup": m.get("Haplogroup", "").strip(),
                            "date":       m.get("Date", "").strip(),
                            "yfull":      m.get("YFull Account", "").strip(),
                            "email":      m.get("Email", "").strip(),
                            "kit_id":     None,
                            "is_own_kit": False,
                        })
                elif isinstance(m, str) and m.strip():
                    members.append({
                        "name": m.strip(), "meka": "", "haplogroup": "",
                        "date": "", "yfull": "", "email": "",
                        "kit_id": None, "is_own_kit": False,
                    })
            nodes.append({
                "id":       i,
                "label":    clu.get("my_label", "") or clu.get("name", ""),
                "mutation": clu.get("mutation", ""),
                "members":  members,
                "kit_ids":  []
            })
        return {
            "haplogroup": "",
            "nodes":      nodes,
            "edges":      [],       # nclusters ei sisällä GD-edgejä
            "conflicts":  []
        }

    def show_network(self):
        """Piirtää verkon networkx+matplotlib avulla."""
        network = getattr(self.n, 'network', None)

        # Debug: tulosta mitä network sisältää
        if network is None:
            self.progress.emit("DEBUG: self.n.network on None — haploryhmää ei ole ladattu.")
        elif not isinstance(network, dict):
            self.progress.emit(f"DEBUG: self.n.network on tyyppiä {type(network)}, ei dict.")
        elif 'nodes' not in network:
            self.progress.emit(f"DEBUG: self.n.network on dict, mutta ei 'nodes'-avainta. Avaimet: {list(network.keys())}")
        else:
            self.progress.emit(f"DEBUG: Verkossa {len(network['nodes'])} nodea, {len(network.get('edges',[]))} edgeä.")

        if not network or not network.get('nodes'):
            self.progress.emit("Haploryhmä / verkko on tyhjä — rakenna verkko ensin.")
            self.finished.emit()
            return

        G = nx.Graph()                                      # Luodaan verkko

        for node in network['nodes']:                       # --- Lisätään isojen pallojen nodet ---
            nid = node['id']
            label = node.get('label', '')
            mutation = node.get('mutation', '')
            n_members = len(node.get('members', []))
            G.add_node(f"N{nid}",
                       kind='cluster',
                       node_id=nid,
                       label=label,
                       mutation=mutation,
                       n_members=n_members,
                       members=node.get('members', []))

        for edge in network.get('edges', []):               # Lisätään edget isojen pallojen välille
            G.add_edge(f"N{edge['from']}", f"N{edge['to']}", gd=edge['gd'])

        for node in network['nodes']:                       # Lisätään jäsenet (pienet pallot) isojen pallojen ympärille
            nid = node['id']
            for member in node.get('members', []):
                if isinstance(member, dict):
                    mname = member.get('name', '')
                    G.add_node(f"M_{nid}_{mname}",
                               kind='member',
                               name=mname,
                               meka=member.get('meka', ''),
                               haplogroup=member.get('haplogroup', ''),
                               date=member.get('date', ''),
                               yfull=member.get('yfull', ''),
                               email=member.get('email', ''))
                else:
                    mname = str(member)
                    G.add_node(f"M_{nid}_{mname}", kind='member', name=mname,
                               meka='', haplogroup='', date='', yfull='', email='')
                G.add_edge(f"N{nid}", f"M_{nid}_{mname}", gd=0)

        # --- Layout ---
        cluster_nodes = [n for n, d in G.nodes(data=True) if d.get('kind') == 'cluster']
        member_nodes  = [n for n, d in G.nodes(data=True) if d.get('kind') == 'member']

        # Käytä tallennettuja koordinaatteja jos löytyvät, muuten spring_layout
        pos = {}
        for node in network['nodes']:
            nid  = node['id']
            gkey = f"N{nid}"
            if 'x' in node and 'y' in node:
                pos[gkey] = (float(node['x']), float(node['y']))
            for member in node.get('members', []):
                if isinstance(member, dict):
                    mname = member.get('name', '')
                    mkey  = f"M_{nid}_{mname}"
                    if 'x' in member and 'y' in member:
                        pos[mkey] = (float(member['x']), float(member['y']))

        # Jos koordinaatteja puuttuu, laske spring_layout puuttuville
        missing = [n for n in G.nodes() if n not in pos]
        if missing:
            if len(pos) == 0:
                # Ei yhtään tallennettua — laske kaikille
                pos = nx.spring_layout(G, seed=42, k=2.0, iterations=100, weight=None)
            else:
                # Laske vain puuttuville, kiinnitä loput
                fixed_pos = {n: pos[n] for n in pos}
                pos = nx.spring_layout(
                    G, seed=42, k=2.0, iterations=100, weight=None,
                    pos=fixed_pos, fixed=list(fixed_pos.keys())
                )

        # --- Värit ja koot ---
        cluster_colors = [CLUSTER_NODE_COLOR] * len(cluster_nodes)              # '#4A90D9'
        member_colors  = [MEMBER_NODE_COLOR] * len(member_nodes)                # '#B8D4F0'

        cluster_sizes = [800 + 100 * G.nodes[n]['n_members'] for n in cluster_nodes]
        member_sizes  = [120] * len(member_nodes)

        # Edge-tyypit: klusterien väliset vs jäsen-edget
        cluster_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('gd', 0) > 0]
        member_edges  = [(u, v) for u, v, d in G.edges(data=True) if d.get('gd', 0) == 0]

        # Edge-paksuus GD:n mukaan — järjestys vastaa cluster_edges-listaa
        edge_widths = [
            max(0.5, 3.0 - (G.edges[u, v].get('gd', 1) - 1) * 0.8)
            for u, v in cluster_edges
        ]

        # --- Labelit isoille palloille ---
        cluster_labels = {}
        for n in cluster_nodes:
            d = G.nodes[n]
            nid = d['node_id']
            label = d.get('label', '')
            mutation = d.get('mutation', '')
            n_members = d.get('n_members', 0)
            if n_members == 0:
                # Pelkkä nimi (testiverkko tai ei jäseniä)
                cluster_labels[n] = label if label else str(nid)
            else:
                parts = []
                if label and label != str(nid):
                    parts.append(label)
                else:
                    parts.append(f"#{nid}")
                if mutation:
                    parts.append(mutation)
                parts.append(f"({n_members})")
                cluster_labels[n] = "\n".join(parts)

        # Jäsenten labelit: MDKA lyhennettynä (jos on), muuten sukunimi
        member_labels = {}
        for n in member_nodes:
            d = G.nodes[n]
            meka = d.get('meka', '')
            if meka and meka.lower() not in ('unknown', ''):
                # Näytetään MDKA:n ensimmäinen osa (max 18 merkkiä)
                label = meka.split(',')[0].strip()
                if len(label) > 18:
                    label = label[:17] + '…'
            else:
                label = 'Unknown'
            member_labels[n] = label

        # --- Piirto ---
        colors = cluster_colors + member_colors
        sizes  = cluster_sizes  + member_sizes
        all_nodes = cluster_nodes + member_nodes

        title = f"Haploryhmä {HAPLOGROUP} — {len(cluster_nodes)} nodea"

        self.plot_data_ready.emit(G, pos, cluster_nodes, member_nodes,
                                  cluster_labels, member_labels,
                                  cluster_edges, member_edges,
                                  edge_widths, title, network)
        self.progress.emit("Verkon piirtodata valmis.")
        self.finished.emit()

    def show_mdkas(self):
        """Koostaa MDKA-raportin network-rakenteesta ja lähettää sen progress-signaalina."""
        network = getattr(self.n, 'network', None)
        report_lines = []
        TAB = "    "

        if not network or not network.get('nodes'):
            self.progress.emit("Haploryhmä / verkko on tyhjä — lataa ensin verkkorakenne ja tiedot.")
            self.finished.emit()
            return

        known_mdkas = 0
        unknown_mdkas = 0

        for node in network['nodes']:
            node_id = node.get('label') or node.get('id', '?')
            members = node.get('members', [])
            if not members:
                continue
            report_lines.append(f"Node {node_id}  ({len(members)} jäsentä)")
            for m in members:
                if isinstance(m, dict):
                    name = m.get('name', '').strip()
                    meka = m.get('meka', '').strip()
                else:
                    name = str(m).strip()
                    meka = ''
                if meka and meka.lower() != 'unknown':
                    report_lines.append(f"{TAB}{name}  —  {meka}")
                    known_mdkas += 1
                else:
                    report_lines.append(f"{TAB}{name}  —  <tuntematon MDKA>")
                    unknown_mdkas += 1

        total = known_mdkas + unknown_mdkas
        report_lines.append("")
        report_lines.append(
            f"Yhteensä {total} testattua: {known_mdkas} tunnettua MDKA:ta, "
            f"{unknown_mdkas} tuntematonta.")

        self.progress.emit("\n".join(report_lines))
        self.finished.emit()

    def run(self):
        """Esimerkkiajo: Lataa klusteriverkoston jos löytyy."""
        fname = f"{HAPLOGROUP}.json"
        if os.path.isfile(fname):
            self.alreadynet = True
            self.load_from_json(fname)
            self.progress.emit(f"Haploryhmän {HAPLOGROUP} valmis klusteriverkosto ladattu.")
        else:
            self.progress.emit(f"Haploryhmän {HAPLOGROUP} klusteriverkostoa ei löytynyt.")

        self.finished.emit()

    def make_cluster_network(self):
        """Rakentaa verkon kittien GD-osumalistoista build_network-algoritmilla."""
        if not self.kits:
            self.progress.emit("Virhe: ei kittejä ladattuna. Lataa ensin kitit.")
            self.finished.emit()
            return

        # Tarkistetaan että ainakin yhdellä kitillä on osumia
        kits_with_data = [k for k in self.kits if any(k.gds[gd] for gd in range(4))]
        if not kits_with_data:
            self.progress.emit("Virhe: kiteillä ei ole osumadataa. Lataa kitit ensin.")
            self.finished.emit()
            return

        self.progress.emit(f"Rakennetaan haploryhmän verkko {len(kits_with_data)} kitin datasta...")

        try:
            network = build_network(kits_with_data)
        except Exception as e:
            self.progress.emit(f"Virhe verkon rakennuksessa: {e}")
            self.finished.emit()
            return

        # Tallennetaan verkko tiedostoon
        try:
            import os
            os.makedirs(OUTPUTDIR, exist_ok=True)
            filename = os.path.join(OUTPUTDIR, f"{HAPLOGROUP}.json")
            save_network(network, filename)
            self.progress.emit(f"Haploryhmä tallennettu: {filename}")
        except Exception as e:
            self.progress.emit(f"Varoitus: verkon tallennus epäonnistui: {e}")

        # Tallennetaan haploryhmä myös NetClusters-instanssiin
        self.n.network = network

        # Raportti
        n_nodes = len(network['nodes'])
        n_edges = len(network['edges'])
        n_conflicts = len(network.get('conflicts', []))
        self.progress.emit(f"Valmis! Nodeja: {n_nodes}, edgejä: {n_edges}.")
        if n_conflicts:
            self.progress.emit(f"HUOMIO: {n_conflicts} ristiriitaa löytyi — tarkista data!")
            for c in network['conflicts']:
                self.progress.emit(
                    f"  Nodet {c['nodes']}: GD={c['gd_existing']} vs GD={c['gd_new']} (kitti {c['kit_id']})"
                )
        else:
            self.progress.emit("Ristiriitoja ei löytynyt — kaikki täsmäsi!")

        self.finished.emit()

    def write(self, fname_p=None):
        """Tallenna JSON-muotoon. Jos ei parametria, tallenna oletuspolkuun OUTPUTDIR/HAPLOGROUP.json"""
        if fname_p is None:
            fname_p = os.path.join(OUTPUTDIR, f"{HAPLOGROUP}.json")
        try:
            with open(fname_p, 'w', encoding=DEFAULT_ENCODING) as f:
                # Pyydetään että NetClusters tarjoaa seralisoitavan rakenteen self.n.nclusters
                json.dump(getattr(self.n, "nclusters", {}), f, indent=2, ensure_ascii=False)
            self.progress.emit(f"Tallennettu {fname_p}")
        except Exception as e:
            self.progress.emit(f"Virhe tallennuksessa: {e}")

    def autosave(self):
        """Tallentaa verkon automaattisesti JSON-tiedostoon."""
        try:
            os.makedirs(OUTPUTDIR, exist_ok=True)
            filename = os.path.join(OUTPUTDIR, f"{HAPLOGROUP}.json")
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(getattr(self.n, "nclusters", {}), f, indent=2, ensure_ascii=False)
            self.progress.emit(f"Automaattinen tallennus suoritettu: {filename}")
        except Exception as e:
            self.progress.emit(f"Automaattinen tallennus epäonnistui: {e}")


class ColorButton(QPushButton):
    """Painike joka näyttää värin ja avaa QColorDialog klikkaamalla."""
    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 24)
        self.set_color(color)
        self.clicked.connect(self._pick_color)

    def set_color(self, color: str):
        self._color = color
        self.setStyleSheet(
            f"background-color: {color}; border: 1px solid #888; border-radius: 3px;"
        )
        self.setText(color)

    def color(self) -> str:
        return self._color

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self, "Valitse väri")
        if c.isValid():
            self.set_color(c.name())


class SettingsDialog(QDialog):
    """Asetusikkuna — välilehdet: Yleiset, Värit, Fontit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Asetukset")
        self.setMinimumWidth(560)
        self.setMinimumHeight(480)

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # ── Välilehti 1: Yleiset ──────────────────────────────
        gen_widget = QWidget()
        gen_layout = QVBoxLayout(gen_widget)
        gen_form   = QFormLayout()

        self.kitsfile_edit   = QLineEdit(KITSFILE)
        self.dldir_edit      = QLineEdit(DLDIR)
        self.outputdir_edit  = QLineEdit(OUTPUTDIR)
        self.haplogroup_edit = QLineEdit(HAPLOGROUP)

        gen_form.addRow("Kitti-tiedosto (KITSFILE):",   self.kitsfile_edit)
        gen_form.addRow("Lataushakemisto (DLDIR):",      self.dldir_edit)
        gen_form.addRow("Tulostehakemisto (OUTPUTDIR):", self.outputdir_edit)
        gen_form.addRow("Haploryhmä (HAPLOGROUP):",      self.haplogroup_edit)
        gen_layout.addLayout(gen_form)

        privacy_group  = QGroupBox("Näkyvyys")
        privacy_layout = QHBoxLayout(privacy_group)
        self.radio_private = QRadioButton("Yksityinen")
        self.radio_public  = QRadioButton("Julkinen")
        self.radio_private.setChecked(not SHOW_NAMES)
        self.radio_public.setChecked(SHOW_NAMES)
        privacy_layout.addWidget(self.radio_private)
        privacy_layout.addWidget(self.radio_public)
        gen_layout.addWidget(privacy_group)
        gen_layout.addStretch()
        tabs.addTab(gen_widget, "Yleiset")

        # ── Välilehti 2: Värit ────────────────────────────────
        color_scroll = QScrollArea()
        color_scroll.setWidgetResizable(True)
        color_inner  = QWidget()
        color_form   = QFormLayout(color_inner)
        color_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def _cb(val):
            btn = ColorButton(val)
            return btn

        self.cb_cluster_node        = _cb(CLUSTER_NODE_COLOR)
        self.cb_cluster_node_border = _cb(CLUSTER_NODE_BORDER_COLOR)
        self.cb_member_node         = _cb(MEMBER_NODE_COLOR)
        self.cb_member_node_border  = _cb(MEMBER_NODE_BORDER_COLOR)
        self.cb_edge                = _cb(EDGE_COLOR)
        self.cb_member_edge         = _cb(MEMBER_EDGE_COLOR)
        self.cb_cluster_label       = _cb(CLUSTER_LABEL_COLOR)
        self.cb_member_label        = _cb(MEMBER_LABEL_COLOR)
        self.cb_background          = _cb(BACKGROUND_COLOR)

        color_form.addRow("Klusterinode (täyttö):",        self.cb_cluster_node)
        color_form.addRow("Klusterinode (reunus):",        self.cb_cluster_node_border)
        color_form.addRow("Jäsennode (täyttö):",           self.cb_member_node)
        color_form.addRow("Jäsennode (reunus):",           self.cb_member_node_border)
        color_form.addRow("Klustereiden välinen edge:",    self.cb_edge)
        color_form.addRow("Jäsen-edge:",                   self.cb_member_edge)
        color_form.addRow("Klusterilabelin väri:",         self.cb_cluster_label)
        color_form.addRow("Jäsenlabelin väri:",            self.cb_member_label)
        color_form.addRow("Tausta:",                       self.cb_background)

        color_scroll.setWidget(color_inner)
        tabs.addTab(color_scroll, "Värit")

        # ── Välilehti 3: Fontit ───────────────────────────────
        font_widget = QWidget()
        font_form   = QFormLayout(font_widget)
        font_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.font_family_edit = QLineEdit(FONT_FAMILY)

        self.cluster_font_size = QSpinBox()
        self.cluster_font_size.setRange(6, 32)
        self.cluster_font_size.setValue(CLUSTER_FONT_SIZE)

        self.member_font_size = QSpinBox()
        self.member_font_size.setRange(4, 24)
        self.member_font_size.setValue(MEMBER_FONT_SIZE)

        self.cluster_font_bold = QCheckBox("Lihavoitu")
        self.cluster_font_bold.setChecked(CLUSTER_FONT_BOLD)

        self.member_font_bold = QCheckBox("Lihavoitu")
        self.member_font_bold.setChecked(MEMBER_FONT_BOLD)

        font_form.addRow("Fontti (font_family):",          self.font_family_edit)
        font_form.addRow("Klusterilabelin koko (pt):",     self.cluster_font_size)
        font_form.addRow("Klusterilabelin tyyli:",         self.cluster_font_bold)
        font_form.addRow("Jäsenlabelin koko (pt):",        self.member_font_size)
        font_form.addRow("Jäsenlabelin tyyli:",            self.member_font_bold)
        tabs.addTab(font_widget, "Fontit")

        # ── OK / Peruuta ──────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.apply_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def apply_settings(self):
        """Kirjoittaa muutokset globaaleihin muuttujiin ja mtdna.ini-tiedostoon."""
        import mtsettings

        # Yleiset
        mtsettings.KITSFILE   = self.kitsfile_edit.text().strip()
        mtsettings.DLDIR      = self.dldir_edit.text().strip()
        mtsettings.OUTPUTDIR  = self.outputdir_edit.text().strip()
        mtsettings.HAPLOGROUP = self.haplogroup_edit.text().strip()
        mtsettings.SHOW_NAMES = self.radio_public.isChecked()

        # Värit
        mtsettings.CLUSTER_NODE_COLOR        = self.cb_cluster_node.color()
        mtsettings.CLUSTER_NODE_BORDER_COLOR = self.cb_cluster_node_border.color()
        mtsettings.MEMBER_NODE_COLOR         = self.cb_member_node.color()
        mtsettings.MEMBER_NODE_BORDER_COLOR  = self.cb_member_node_border.color()
        mtsettings.EDGE_COLOR                = self.cb_edge.color()
        mtsettings.MEMBER_EDGE_COLOR         = self.cb_member_edge.color()
        mtsettings.CLUSTER_LABEL_COLOR       = self.cb_cluster_label.color()
        mtsettings.MEMBER_LABEL_COLOR        = self.cb_member_label.color()
        mtsettings.BACKGROUND_COLOR          = self.cb_background.color()

        # Fontit
        mtsettings.FONT_FAMILY       = self.font_family_edit.text().strip()
        mtsettings.CLUSTER_FONT_SIZE = self.cluster_font_size.value()
        mtsettings.MEMBER_FONT_SIZE  = self.member_font_size.value()
        mtsettings.CLUSTER_FONT_BOLD = self.cluster_font_bold.isChecked()
        mtsettings.MEMBER_FONT_BOLD  = self.member_font_bold.isChecked()

        # Päivitä tämän moduulin globaalit
        global KITSFILE, DLDIR, OUTPUTDIR, HAPLOGROUP, SHOW_NAMES
        global CLUSTER_NODE_COLOR, CLUSTER_NODE_BORDER_COLOR
        global MEMBER_NODE_COLOR, MEMBER_NODE_BORDER_COLOR
        global EDGE_COLOR, MEMBER_EDGE_COLOR
        global CLUSTER_LABEL_COLOR, MEMBER_LABEL_COLOR, BACKGROUND_COLOR
        global FONT_FAMILY, CLUSTER_FONT_SIZE, MEMBER_FONT_SIZE
        global CLUSTER_FONT_BOLD, MEMBER_FONT_BOLD

        KITSFILE   = mtsettings.KITSFILE
        DLDIR      = mtsettings.DLDIR
        OUTPUTDIR  = mtsettings.OUTPUTDIR
        HAPLOGROUP = mtsettings.HAPLOGROUP
        SHOW_NAMES = mtsettings.SHOW_NAMES

        CLUSTER_NODE_COLOR        = mtsettings.CLUSTER_NODE_COLOR
        CLUSTER_NODE_BORDER_COLOR = mtsettings.CLUSTER_NODE_BORDER_COLOR
        MEMBER_NODE_COLOR         = mtsettings.MEMBER_NODE_COLOR
        MEMBER_NODE_BORDER_COLOR  = mtsettings.MEMBER_NODE_BORDER_COLOR
        EDGE_COLOR                = mtsettings.EDGE_COLOR
        MEMBER_EDGE_COLOR         = mtsettings.MEMBER_EDGE_COLOR
        CLUSTER_LABEL_COLOR       = mtsettings.CLUSTER_LABEL_COLOR
        MEMBER_LABEL_COLOR        = mtsettings.MEMBER_LABEL_COLOR
        BACKGROUND_COLOR          = mtsettings.BACKGROUND_COLOR

        FONT_FAMILY       = mtsettings.FONT_FAMILY
        CLUSTER_FONT_SIZE = mtsettings.CLUSTER_FONT_SIZE
        MEMBER_FONT_SIZE  = mtsettings.MEMBER_FONT_SIZE
        CLUSTER_FONT_BOLD = mtsettings.CLUSTER_FONT_BOLD
        MEMBER_FONT_BOLD  = mtsettings.MEMBER_FONT_BOLD

        # Tallenna mtdna.ini-tiedostoon
        mtsettings.save_to_ini()

        self.accept()


class MainWindow(QMainWindow):
    """Graafisen käyttöliittymän pääikkuna."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("mtDNA Klusterianalyysi")
        self.setGeometry(100, 100, 800, 600)

        # Alusta NetClusters-objekti
        self.n = NetClusters()
        self.thread = None
        self.worker = None

        # Keskuswidget + loki
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)

        self.title_label = QLabel(f"Haploryhmä {HAPLOGROUP}")
        font = self.title_label.font()
        font.setPointSize(14)
        font.setBold(True)
        self.title_label.setFont(font)
        main_layout.addWidget(self.title_label)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        main_layout.addWidget(self.log_output)

        # Valikkorivi
        self._build_menu()

    def _build_menu(self):
        """Rakentaa valikkopalkin."""
        menubar = self.menuBar()

        # ── Tiedosto ──────────────────────────────────────────
        file_menu = menubar.addMenu("Tiedosto")

        act_load_json = QAction("Lataa haploryhmä (JSON)…", self)
        act_load_json.setShortcut("Ctrl+O")
        act_load_json.triggered.connect(self.start_load_members)
        file_menu.addAction(act_load_json)

        file_menu.addSeparator()

        act_save = QAction("Talleta haploryhmä", self)
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self.save_network_as)
        file_menu.addAction(act_save)

        file_menu.addSeparator()

        act_quit = QAction("Poistu", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.save_and_exit)
        file_menu.addAction(act_quit)

        # ── Näytä ─────────────────────────────────────────────
        view_menu = menubar.addMenu("Näytä")

        act_show_net = QAction("Näytä haploryhmä", self)
        act_show_net.setShortcut("Ctrl+N")
        act_show_net.triggered.connect(self.start_show_network)
        view_menu.addAction(act_show_net)

        act_show_mdka = QAction("Listaa MDKAt", self)
        act_show_mdka.setShortcut("Ctrl+M")
        act_show_mdka.triggered.connect(self.start_show_mdkas)
        view_menu.addAction(act_show_mdka)

        # ── Asetukset ─────────────────────────────────────────
        settings_menu = menubar.addMenu("Asetukset")

        act_settings = QAction("Asetukset…", self)
        act_settings.setShortcut("Ctrl+,")
        act_settings.triggered.connect(self.open_settings)
        settings_menu.addAction(act_settings)

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # Päivitä otsikko jos haplogroup muuttui
            self.title_label.setText(f"Haploryhmä {HAPLOGROUP}")
            self.log_message("Asetukset päivitetty.")

    def save_network_as(self):
        """Tallentaa verkon JSON-tiedostoon koordinaatteineen."""
        from PyQt6.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getSaveFileName(
            self, "Talleta haploryhmä", f"{HAPLOGROUP}.json",
            "JSON-tiedostot (*.json);;Kaikki tiedostot (*)"
        )
        if not filename:
            return
        try:
            network = getattr(self.n, 'network', None)
            if not network:
                self.log_message("Ei haploryhmää / verkkoa ladattuna — ei tallennettavaa.")
                return
            # Tallennetaan yhtenäiseen muotoon: haplogroup + nodes + edges
            data = {
                "haplogroup": HAPLOGROUP,
                "nodes":      network.get("nodes", []),
                "edges":      network.get("edges", []),
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            n_nodes = len(data["nodes"])
            n_edges = len(data["edges"])
            # Laske koordinaattien määrä
            coords = sum(1 for nd in data["nodes"] if 'x' in nd)
            self.log_message(
                f"Haploryhmä tallennettu: {filename}  "
                f"({n_nodes} nodea, {n_edges} edgeä, {coords} koordinaattiä)")
        except Exception as e:
            self.log_message(f"Virhe tallennuksessa: {e}")

    # -------------------------
    # Taustasäikeen käynnistykset
    # -------------------------
    def start_load_members(self):
        """Avaa JSON-tiedostodialogi ja yhdistää jäsendata verkkoon."""
        from PyQt6.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getOpenFileName(
            self, "Avaa jäsendata (JSON)", "", "JSON-tiedostot (*.json);;Kaikki tiedostot (*)"
        )
        if not filename:
            self.log_message("Lataus peruutettu.")
            return
        thread = QThread()
        worker = Worker(self.n)
        worker.moveToThread(thread)
        thread.started.connect(lambda: worker.load_member_data(filename))
        worker.progress.connect(self.log_message)
        worker.plot_data_ready.connect(self.update_plot)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self.thread = thread
        self.worker = worker
        thread.start()
        self.log_message(f"Ladataan jäsendata: {filename}")

    def start_load_network(self):
        """Avaa tiedostodialogi ja lataa valittu JSON-verkko."""
        from PyQt6.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getOpenFileName(
            self, "Avaa haploryhmän JSON", "", "JSON-tiedostot (*.json);;Kaikki tiedostot (*)"
        )
        if not filename:
            self.log_message("Lataus peruutettu.")
            return
        self._load_network_file(filename)

    def _load_network_file(self, filename: str):
        """Lataa verkkotiedosto taustasäikeessä."""
        thread = QThread()
        worker = Worker(self.n)
        worker.moveToThread(thread)
        thread.started.connect(lambda: worker.load_from_json(filename))
        worker.progress.connect(self.log_message)
        worker.plot_data_ready.connect(self.update_plot)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self.thread = thread
        self.worker = worker
        thread.start()
        self.log_message(f"Ladataan haploryhmä: {filename}")

    def start_build_network(self):
        self.start_worker(mode="buildnetwork")

    def start_show_network(self):
        self.start_worker(mode="shownetwork")

    def start_show_mdkas(self):
        self.start_worker(mode="showmdkas")

    def start_load_kits(self):
        self.start_worker(mode="kits")

    def start_worker(self, mode="network"):
        """Yhteinen metodi säikeen käynnistämiseen."""
        # Luo uusi säie + worker tähän tehtävään
        thread = QThread()
        worker = Worker(self.n)

        worker.moveToThread(thread)

        # Liitetään oikea metodi thread.started:iin
        if mode == "network":
            thread.started.connect(worker.run)
        elif mode == "kits":
            thread.started.connect(worker.load_kitlist)
        elif mode == "buildnetwork":
            thread.started.connect(worker.make_cluster_network)
        elif mode == "shownetwork":
            thread.started.connect(worker.show_network)
        elif mode == "showmdkas":
            thread.started.connect(worker.show_mdkas)
        else:
            thread.started.connect(worker.run)

        # Signaalit
        worker.progress.connect(self.log_message)
        worker.plot_data_ready.connect(self.update_plot)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        # Käytetään paikallisia viitteitä estääksemme tuhoutumisen ennen aikojaan
        self.thread = thread
        self.worker = worker

        thread.start()
        self.log_message(f"Aloitetaan {'kittien' if mode=='kits' else 'verkoston'} lataus...")

    def update_plot(self, G, pos, cluster_nodes, member_nodes,
                    cluster_labels, member_labels,
                    cluster_edges, member_edges,
                    edge_widths, title, network=None):
        """Piirtää verkon matplotlib-ikkunaan drag-tuella ja tooltipseillä."""
        import math as _math

        fig, ax = plt.subplots(figsize=(14, 10))
        fig.patch.set_facecolor(BACKGROUND_COLOR)
        ax.set_facecolor(BACKGROUND_COLOR)
        ax.set_title(title, fontsize=13)
        ax.axis("off")

        # --- Tooltip-data ---
        tooltip_data = {}
        for n in cluster_nodes:
            d = G.nodes[n]
            members = d.get("members", [])
            names = [m.get("name","") if isinstance(m,dict) else str(m) for m in members]
            header = str(d.get("label","") or d.get("node_id",""))
            if d.get("mutation"): header += "  " + d["mutation"]
            body = "\n".join("  " + nm for nm in names[:20])
            if len(names) > 20: body += "\n  ..."
            tooltip_data[n] = header + "\n" + str(len(names)) + " jäsentä:\n" + body
        for n in member_nodes:
            d = G.nodes[n]
            lines = [d.get("name", str(n))]
            if d.get("meka"):   lines.append(f"MDKA: {d['meka']}")
            if d.get("haplogroup"): lines.append(f"Haplo: {d['haplogroup']}")
            if d.get("yfull"):  lines.append(f"YFull: {d['yfull']}")
            if d.get("date"):   lines.append(f"Pvm: {d['date']}")
            tooltip_data[n] = "\n".join(lines)

        # --- Piirtofunktio (kutsutaan myös drag-päivityksen jälkeen) ---
        cluster_sizes = [800 + 100 * G.nodes[n]["n_members"] for n in cluster_nodes]

        def redraw():
            ax.clear()
            ax.set_facecolor(BACKGROUND_COLOR)
            ax.set_title(title, fontsize=13)
            ax.axis("off")
            # Edget
            if cluster_edges:
                nx.draw_networkx_edges(G, pos, edgelist=cluster_edges,
                                       width=edge_widths, edge_color=EDGE_COLOR, ax=ax)
            if member_edges:
                nx.draw_networkx_edges(G, pos, edgelist=member_edges,
                                       width=0.5, edge_color=MEMBER_EDGE_COLOR,
                                       style="dashed", ax=ax)
            # Nodet
            nx.draw_networkx_nodes(G, pos, nodelist=cluster_nodes,
                                   node_size=cluster_sizes, node_color=CLUSTER_NODE_COLOR, ax=ax)
            nx.draw_networkx_nodes(G, pos, nodelist=member_nodes,
                                   node_size=120, node_color=MEMBER_NODE_COLOR, ax=ax)
            # Labelit
            nx.draw_networkx_labels(G, pos, labels=cluster_labels,
                                    font_size=CLUSTER_FONT_SIZE,
                                    font_color=CLUSTER_LABEL_COLOR,
                                    font_weight="bold" if CLUSTER_FONT_BOLD else "normal",
                                    font_family=FONT_FAMILY, ax=ax)
            if member_labels:
                nx.draw_networkx_labels(G, pos, labels=member_labels,
                                        font_size=MEMBER_FONT_SIZE,
                                        font_color=MEMBER_LABEL_COLOR,
                                        font_weight="bold" if MEMBER_FONT_BOLD else "normal",
                                        font_family=FONT_FAMILY, ax=ax)
            fig.canvas.draw_idle()

        redraw()
        fig.tight_layout()

        # --- Tooltip-annotaatio ---
        annot = ax.annotate("", xy=(0,0), xytext=(15,15),
                            textcoords="offset points",
                            bbox=dict(boxstyle="round,pad=0.4", fc="#FFFFCC", alpha=0.9),
                            fontsize=8, zorder=10)
        annot.set_visible(False)

        # --- Drag-tila ---
        drag_state = {"node": None, "dragging": False}
        DRAG_THRESHOLD = 0.01   # min siirto jotta lasketaan dragiksi eikä klikkaukseksi

        def nearest_node(x, y, only_clusters=False):
            """Palauttaa lähimmän noden ja etäisyyden."""
            best_n, best_d = None, float("inf")
            candidates = cluster_nodes if only_clusters else list(pos.keys())
            for n in candidates:
                nx_, ny_ = pos[n]
                d = (nx_ - x)**2 + (ny_ - y)**2
                if d < best_d:
                    best_d, best_n = d, n
            return best_n, best_d

        def on_press(event):
            if event.inaxes != ax or event.xdata is None:
                return
            n, d = nearest_node(event.xdata, event.ydata)
            # Nappaa node jos hiiri on riittävän lähellä
            # Isompi threshold klusterinodeille (isompi pallo)
            threshold = 0.04 if n in cluster_nodes else 0.005
            if d < threshold:
                drag_state["node"] = n
                drag_state["dragging"] = False
                annot.set_visible(False)

        def on_motion(event):
            if event.inaxes != ax or event.xdata is None:
                return
            x, y = event.xdata, event.ydata

            # Drag-logiikka
            if drag_state["node"] is not None:
                drag_state["dragging"] = True
                node = drag_state["node"]
                old_x, old_y = pos[node]
                dx, dy = x - old_x, y - old_y
                # Siirrä tämä node
                pos[node] = (x, y)
                # Jos jäsennode: siirrä vain se
                # Jos klusterinode: siirrä myös sen jäsenet samalla deltalla
                if node in cluster_nodes:
                    for mn in member_nodes:
                        # Tarkista onko tämä jäsen tämän klusterin lapsi
                        if G.has_edge(node, mn):
                            mx, my = pos[mn]
                            pos[mn] = (mx + dx, my + dy)
                redraw()
                return

            # Tooltip-logiikka (vain jos ei dragata)
            n, d = nearest_node(x, y)
            threshold = 0.04 if n in cluster_nodes else 0.008
            if n and d < threshold and n in tooltip_data:
                annot.xy = pos[n]
                annot.set_text(tooltip_data[n])
                annot.set_visible(True)
            else:
                annot.set_visible(False)
            fig.canvas.draw_idle()

        def on_release(event):
            if drag_state["dragging"] and network is not None:
                # Tallenna uudet koordinaatit network-rakenteeseen
                node_map = {node['id']: node for node in network.get('nodes', [])}
                for nd in cluster_nodes:
                    nid = G.nodes[nd].get('node_id')
                    if nid is not None and str(nid) in node_map:
                        x, y = pos[nd]
                        node_map[str(nid)]['x'] = round(x, 6)
                        node_map[str(nid)]['y'] = round(y, 6)
                for mn in member_nodes:
                    nd_data = G.nodes[mn]
                    # member key: M_{nid}_{mname}
                    parts = mn.split('_', 2)
                    if len(parts) == 3:
                        nid, mname = parts[1], parts[2]
                        if nid in node_map:
                            for m in node_map[nid].get('members', []):
                                if isinstance(m, dict) and m.get('name','') == mname:
                                    x, y = pos[mn]
                                    m['x'] = round(x, 6)
                                    m['y'] = round(y, 6)
                                    break
            drag_state["node"] = None
            drag_state["dragging"] = False

        fig.canvas.mpl_connect("button_press_event",   on_press)
        fig.canvas.mpl_connect("motion_notify_event",  on_motion)
        fig.canvas.mpl_connect("button_release_event", on_release)

        plt.show()


    def on_progress(self, msg):
        print(msg)

    def on_finished(self):
        print("Työ valmis.")

    # -------------------------
    # GUI:n toiminnot
    # -------------------------
    def log_message(self, message):
        """Tulostaa viestin loki-ikkunaan."""
        # message voi olla myös lista tai muu; muotoillaan str:ksi
        if isinstance(message, (list, tuple)):
            message = "\n".join(map(str, message))
        self.log_output.append(str(message))
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())

    def save_and_exit(self):
        """Talleta XML, JSON tai TOON muotoon ja poistu."""
        try:
            filename = os.path.join(OUTPUTDIR, f"{HAPLOGROUP}.{DATATYPE}")
            # Käytetään self.worker:n writeä jos se on olemassa, muuten self.n:ää
            if self.worker is not None:
                try:
                    # Worker.write tallentaa self.n.nclusters
                    self.worker.write(filename)         # Workeriin myös XML, JSON ja TOON muodot
                except Exception:
                    # fallback: yritä kutsua NetClusters:n write-menetelmää
                    if hasattr(self.n, 'write'):
                        self.n.write(filename)
                    else:
                        # kirjoitetaan nclusters suoraan
                        with open(filename, 'w', encoding=DEFAULT_ENCODING) as f:
                            match DATATYPE:
                                case "xml":  print("Not implemented yet.")
                                case "json": json.dump(getattr(self.n, "nclusters", {}), f, indent=2, ensure_ascii=False)
                                case "toon": print("Not implemented yet.")
                                case _:      print("Not implemented yet.")
            else:
                with open(filename, 'w', encoding=DEFAULT_ENCODING) as f:
                    json.dump(getattr(self.n, "nclusters", {}), f, indent=2, ensure_ascii=False)
                    match DATATYPE:
                        case "xml":
                            print("Not implemented yet.")
                        case "json":
                            json.dump(getattr(self.n, "nclusters", {}), f, indent=2, ensure_ascii=False)
                        case "toon":
                            print("Not implemented yet.")
                        case _:
                            print("Not implemented yet.")

            self.log_message(f"Tiedot tallennettu tiedostoon {filename}.")
        except Exception as e:
            self.log_message(f"Virhe tallennuksessa: {e}")
        self.log_message("Suljetaan ohjelma...")
        QApplication.instance().quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    try:
        app.setStyle('Fusion')
    except Exception:
        # Jos tyyliä ei löydy, ei kaadu
        pass

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


'''
Kutsu autosave() seuraavissa kohdissa

Lisää rivin self.autosave() seuraaviin metodeihin:

1️⃣ load_from_json() loppuun:
        self.progress.emit(f"Ladattiin klusteriverkosto tiedostosta {filename}.")
        self.autosave()  # <-- lisätty

2️⃣ make_cluster_network() loppuun:
        self.progress.emit("Tehdään klusteriverkko (placeholder).")
        self.autosave()  # <-- lisätty
        self.finished.emit()

3️⃣ load_kitlist() loppuun (jos kittejä luettu):
        self.progress.emit(msg)
        self.autosave()  # <-- lisätty
        self.finished.emit()

🧠 Lisävinkki

Jos haluat vielä varmistaa, että automaattitallennus ei käynnisty liian usein (esim. jos klusteriverkkoa rakennetaan vaiheittain), voit lisätä pienen “debounce”-logiikan:

import time

class Worker(QObject):
    ...
    _last_save_time = 0

    def autosave(self):
        """Tallentaa verkon, mutta enintään kerran 10 sekunnissa."""
        now = time.time()
        if now - self._last_save_time < 10:
            return
        self._last_save_time = now
        ...

✅ Lopputulos

Nyt ohjelma tallentaa automaattisesti OUTPUTDIR/HAPLOGROUP.json-tiedoston aina kun:

verkko ladataan,

uusia kittejä luetaan,

tai klusteriverkko rakennetaan uudelleen.

Ja käyttäjä näkee viestin loki-ikkunassa:

Automaattinen tallennus suoritettu: data/mtHaplo.json


HUOM!!! 16.11.2025 lisätty TOON tiedostomuoto JSON:in rinnalle. Se on 30 % tehokkaampi.

from toon_format import encode, decode

data = # your data structure
toon_string = encode(data)
decoded = decode(toon_string)
'''