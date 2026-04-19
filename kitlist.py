"""
Clusters of one Kit (tested person) and Net clusters and M clusters
"""
import os
import csv
from gds import Gds
from link import Link
from mtsettings import GDMAX, KITSFILE
from match import Match, Name
from cluster import Cluster
from kit import Kit

class KitList(Cluster):
    ''' Kittiklusteri '''
    kits: list
    def __init__(self):
        ''' Kittiklusteri konstuktori '''

        super().__init__("Kits")                # Name of subroup. A cluster of haplogroup.
        self.kits = []

    def show(self, debug2_p=False, debug3_p=False):
        ''' Näytä osuman klusteri '''
        i = 0
        for y in self.gds:
            if debug2_p:
                print(f"GD {i} cluster {len(y)} matches.")
            if debug3_p:
                for z in y:
                    z.show()
            i += 1
        print('')

    def get_cluster(self, level: int=0) -> list:
        ''' Returns a match cluster
        :return: list: list List of matches in one cluster
        '''
        if 0 <= level < GDMAX-1:
            if self.gds[level] is not None:
                return self.gds[level]
        else:
            print('Wrong GD-level', level)

    def load_kits(self):
        data = None
        print("Ollaan load_kits")
        with open(KITSFILE, newline='') as f:
            reader = csv.reader(f)
            data = [tuple(row) for row in reader]

        print("Ollaan load_kits")
        found, notfound = "", ""
        for i, row in enumerate(data):
            k = Kit(data[i][0], data[i][1], data[i][2])
            self.kits.append(k)
            if os.path.isfile(k.file):  # Löytyykö kitin osumalistatiedosto?
                found += f' {k.id}'
                k.read_matches()  # Käydään kitin osumat läpi ja lisätään 4-tasoiseen osumalistaan.
            else:
                notfound += f' {k.id}'

        found, notfound = found.strip(), notfound.strip()

        match len(found.split()):
            case 0:
                match len(notfound.split()):
                    case 0:
                        self.progress.emit("#Yhtään kittiä ei löytynyt.")
                    case 1:
                        self.progress.emit(f"Kitin {notfound} osumalistaa ei löytynyt.")
                    case _:
                        self.progress.emit(f"Kittien {notfound} osumalistoja ei löytynyt.")
            case 1:
                match len(notfound.split()):
                    case 0:
                        self.progress.emit(f"Luettiin kitin {found} osumalistat.")
                    case 1:
                        self.progress.emit(
                            f"Luettiin kitin {found} osumalistat. Kitin {notfound} osumalistoja ei löytynyt.")
                    case _:
                        self.progress.emit(
                            f"Luettiin kitin {found} osumalistat. Kittien {notfound} osumalistoja ei löytynyt.")
            case _:
                self.progress.emit(
                    f"Luettiin kittien {found} osumalistat. Kittien {notfound} osumalistoja ei löytynyt.")
