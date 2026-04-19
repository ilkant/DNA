"""
Base clusters of one kit (tested person) and net clusters and match clusters
Ilpo Kantonen 2025-10-23
"""
from mtsettings import GDMAX
from match import Match, Name

class Cluster:
    ''' Base cluster to kit clusters and network clusters and match clusters. '''
    matches: list                   # list of matches
    name: str

    def __init__(self, name_p:str="Cluster"):
        self.name = name_p          # Name of cluster. A cluster of haplogroup or of subgroup.
        self.matches = []

    def __getitem__(self, i: int) -> Match:
        """
        Returns a match of index i from Cluster
        :param i:
        :return: Match
        """
        if 0 <= i <= len(self.matches) -1:
            return self.matches[i]
        else:
            print('Cluster error: index out of matches.')

    def add_kit_matches(self, ml_p:list):
        ''' Lisää osuma klusteriin '''
        self.matches.append(ml_p)

    def remove_match(self, name_p: str) -> bool:
        ''' Poista osuma klusterista '''
        for i in range(len(self.matches)):
            if self.matches[i].Fullname == name_p:
                self.matches.pop(i)
                return True
        return False

    def get_name(self):
        return self.name

    def show(self, debug2_p=False, debug3_p=False):
        ''' Näytä osuma klusterissa '''
        i = 0
        print(f"Cluster {self.name} has len({self.matches}) matches")
        for y in self.matches:
            if debug2_p:
                print(f"GD {i} cluster {len(y)} matches.")
            if debug3_p:
                for z in y:
                    z.show()
            i += 1
        print('')
