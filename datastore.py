"""
Tiedostojen luku ja kirjoitus: JSON, kitit (CSV).
Ilpo Kantonen 2025
"""

import csv
import json
import os

from kit import Kit
from mtsettings import KITSFILE, HAPLOGROUP, OUTPUTDIR, FENCODING

DEFAULT_ENCODING = FENCODING


def load_kits(progress_cb=None) -> tuple[list, list, list]:
    """
    Lukee kits.csv-tiedoston ja lataa jokaisen kitin osumalistan.

    :param progress_cb: valinnainen callable(str) viestien välittämiseen
    :return: (kits, found_ids, notfound_ids)
    """
    def log(msg):
        if progress_cb:
            progress_cb(msg)

    kits = []
    found, notfound = [], []

    try:
        with open(KITSFILE, newline='', encoding=DEFAULT_ENCODING) as f:
            reader = csv.reader(f)
            rows = [tuple(row) for row in reader]
    except FileNotFoundError:
        log(f"Virhe: {KITSFILE} ei löytynyt.")
        return kits, found, notfound

    for row in rows:
        if len(row) < 3:
            log(f"Varoitus: ohitetaan vajaa rivi {row}")
            continue
        k = Kit(*row[:3])
        kits.append(k)
        if os.path.isfile(k.file):
            found.append(k.id)
            try:
                k.read_matches()
            except Exception as e:
                log(f"Varoitus: virhe luettaessa {k.file}: {e}")
        else:
            notfound.append(k.id)

    # Muodosta yhteenviesti
    if not found and not notfound:
        msg = "Yhtään kittiä ei löytynyt."
    elif found and not notfound:
        msg = f"Luettiin {len(found)} kitin osumalistat: {', '.join(found)}"
    elif notfound and not found:
        msg = f"Kittien {', '.join(notfound)} osumalistoja ei löytynyt."
    else:
        msg = (
            f"Luettiin {len(found)} kitin osumalistat ({', '.join(found)}). "
            f"{len(notfound)} kitin osumalistoja ei löytynyt ({', '.join(notfound)})."
        )
    log(msg)
    return kits, found, notfound


def load_json(filename: str, progress_cb=None) -> list | None:
    """
    Lataa klusteriverkkodata JSON-tiedostosta.

    :param filename: tiedostopolku
    :param progress_cb: valinnainen callable(str)
    :return: nclusters-lista tai None virhetilanteessa
    """
    def log(msg):
        if progress_cb:
            progress_cb(msg)

    try:
        with open(filename, "r", encoding=DEFAULT_ENCODING) as f:
            data = json.load(f)
    except FileNotFoundError:
        log(f"Virhe: tiedostoa ei löydy: {filename}")
        return None
    except json.JSONDecodeError as e:
        log(f"Virhe JSON-jäsennyksessä ({filename}): {e}")
        return None

    # Tuetaan sekä vanhaa listamuotoa että uudempaa {nclusters: [...]} -rakennetta
    if isinstance(data, dict) and "nclusters" in data:
        log(f"Ladattiin klusteriverkosto (dict-muoto) tiedostosta {filename}.")
        return data["nclusters"]
    elif isinstance(data, list):
        log(f"Ladattiin klusteriverkosto (lista-muoto) tiedostosta {filename}.")
        return data
    else:
        log(f"Varoitus: tuntematon JSON-rakenne tiedostossa {filename}.")
        return data


def save_json(nclusters, filename: str = None, progress_cb=None) -> bool:
    """
    Tallentaa klusteriverkon JSON-tiedostoon.

    :param nclusters: tallennettava data (lista tai dict)
    :param filename: tiedostopolku; oletuksena OUTPUTDIR/HAPLOGROUP.json
    :param progress_cb: valinnainen callable(str)
    :return: True jos onnistui
    """
    def log(msg):
        if progress_cb:
            progress_cb(msg)

    if filename is None:
        filename = os.path.join(OUTPUTDIR, f"{HAPLOGROUP}.json")

    try:
        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
        with open(filename, "w", encoding=DEFAULT_ENCODING) as f:
            json.dump(nclusters, f, indent=2, ensure_ascii=False)
        log(f"Tallennettu: {filename}")
        return True
    except Exception as e:
        log(f"Virhe tallennuksessa ({filename}): {e}")
        return False
