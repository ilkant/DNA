''' Haplogroup and haplotype and their methods '''
class Haplo:
    ''' Haplogroup and haplotype '''
    haplogroup: str
    haplotype: str

    def __init__(self, group_p: str=None, type_p: str=None):
        ''' Konstruktori '''
        self.haplogroup = group_p
        self.haplotype = type_p

    def get(self):
        ''' Get haplogroup and haplotype'''
        return (self.haplogroup, self.haplotype)

    def show(self):
        ''' Show haplogroup and haplotype'''
        print(f"Haplo({self.haplogroup} {self.haplotype})")
