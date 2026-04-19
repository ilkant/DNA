"""
Muuntaa U8a1a1b1.csv -> U8a1a1b1.json
JSON-rakenne yhteensopiva gui.py:n "Lataa klusteriverkosto" -painikkeeseen.

Klusteri tunnistetaan: sarakkeessa 0 on nimi (ei tyhjä), sarakkeet 3-11 tyhjiä.
Jäsenet tunnistetaan: sarakkeessa 3 on Full Name.
YF-rivit (Full Name == "YF"): tallennetaan MDKA + YFull Account -tiedoilla.
"""

import csv
import json
import re

INPUT_FILE  = "i.csv"
OUTPUT_FILE = "J1c2n1.json"

def is_cluster_row(row: list) -> bool:
    """Rivi on klusteririvi, jos sarakkeessa 0 on tekstiä ja sarakkeessa 3 ei ole."""
    col0 = row[0].strip() if len(row) > 0 else ""
    col3 = row[3].strip() if len(row) > 3 else ""
    # Jätetään pois täysin tyhjät rivit
    if not col0:
        return False
    # "Ungrouped" on myös klusteririvi
    return col3 == ""

def parse_cluster_name(row: list) -> tuple[str, str, str]:
    """
    Palauttaa (cluster_name, mutation, my_label).
    col0 = haplogroup / klusterinimi
    col1 = mutaatio
    col2 = oma nimi (esim. Mb, M4, M5 ...)
    """
    col0 = row[0].strip() if len(row) > 0 else ""
    col1 = row[1].strip() if len(row) > 1 else ""
    col2 = row[2].strip() if len(row) > 2 else ""

    # Klusterin nimi: haplogroup + mahdollinen oma nimi välilyönnillä
    # Jos col2 == col0, ei toisteta nimeä
    full_name = col0
    if col2 and col2 != col0:
        full_name = f"{col0} {col2}"

    return full_name, col1, col2

def parse_member_row(row: list) -> dict | None:
    """Muuntaa jäsenrivin dict:ksi. Palauttaa None jos rivi on tyhjä."""
    # Kenttien indeksit CSV:ssä (otsikkorivi):
    # 0=Group, 1=Mutation, 2=Cluster, 3=Full name, 4=Forname, 5=(tyhjä), 6=Surname,
    # 7=Email, 8=MDKA, 9=Haplogroup, 10=Date, 11=Yfull account

    full_name = row[3].strip() if len(row) > 3 else ""
    if not full_name:
        return None

    firstname  = row[4].strip() if len(row) > 4 else ""
    middlename = row[5].strip() if len(row) > 5 else ""
    surname    = row[6].strip() if len(row) > 6 else ""
    email      = row[7].strip() if len(row) > 7 else ""
    mdka       = row[8].strip() if len(row) > 8 else ""
    haplogroup = row[9].strip() if len(row) > 9 else ""
    date       = row[10].strip() if len(row) > 10 else ""
    yfull      = row[11].strip() if len(row) > 11 else ""

    member: dict = {
        "Full Name": full_name,
    }

    if firstname:
        member["First Name"] = firstname
    if middlename:
        member["Middle Name"] = middlename
    if surname:
        member["Surname"] = surname
    if email:
        member["Email"] = email
    if mdka:
        member["MDKA"] = mdka
    if haplogroup:
        member["Haplogroup"] = haplogroup
    if date:
        member["Date"] = date
    if yfull:
        member["YFull Account"] = yfull

    return member


def convert(input_file: str, output_file: str):
    nclusters = []
    current_cluster: dict | None = None

    with open(input_file, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Ohitetaan otsikkorivi (rivi 0)
    for row in rows[1:]:
        # Täydennetään rivit vähintään 12 sarakkeeseen
        while len(row) < 12:
            row.append("")

        col0 = row[0].strip()
        col3 = row[3].strip()

        # Täysin tyhjä rivi -> skipataan
        if not any(c.strip() for c in row):
            continue

        if is_cluster_row(row):
            # Tallenna edellinen klusteri listaan
            if current_cluster is not None:
                nclusters.append(current_cluster)
            # Aloita uusi klusteri
            full_name, mutation, my_label = parse_cluster_name(row)
            current_cluster = {
                "name": full_name,
                "mutation": mutation,
                "my_label": my_label,
                "members": []
            }
        elif col3:  # Jäsenrivi (Full Name sarakkeessa 3)
            member = parse_member_row(row)
            if member and current_cluster is not None:
                current_cluster["members"].append(member)
            elif member and current_cluster is None:
                # Jäsen ilman klusteria -> lisätään "Ungrouped"
                current_cluster = {
                    "name": "Ungrouped",
                    "mutation": "",
                    "my_label": "",
                    "members": [member]
                }

    # Lisää viimeinen klusteri
    if current_cluster is not None:
        nclusters.append(current_cluster)

    output = {"nclusters": nclusters}

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Valmis! Kirjoitettu {output_file}")
    print(f"Klustereita yhteensä: {len(nclusters)}")
    for c in nclusters:
        print(f"  [{c['name']}] mutaatio={c['mutation'] or '-'}, "
              f"my_label={c['my_label'] or '-'}, "
              f"jäseniä={len(c['members'])}")


if __name__ == "__main__":
    convert(INPUT_FILE, OUTPUT_FILE)
