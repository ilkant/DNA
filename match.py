''' Matches '''
from haplo import Haplo

#pylint: disable=too-many-arguments
#pylint: disable=too-many-positional-arguments

class Name:
    ''' Person name as fullname which contains first name, middle name and last name. '''
    fullname: str       # Full name
    firstname: str      # First name
    middlename: str     # Middle name
    lastname: str       # Last name

    def __init__(self, fun_p, fin_p="", min_p="", lan_p=""):
        self.fullname, self.firstname = fun_p, fin_p
        self.middlename, self.lastname =  min_p, lan_p

    def get_name(self):
        ''' Returns name of person as a tuple.'''
        return (self.fullname, self.firstname, self.middlename, self.lastname)

    def show_name(self):
        ''' Show name '''
        print(f"{self.fullname}")

class Match:
    ''' Osuma '''
    name: Name
    gd: int
    # haplo: Haplo
    mdka: str

    def __init__(self, name_p: Name, gd_p: int = 0, mdka_p: str = None):
        """ Match constructor has name, gd and mndka """
        self.name = name_p
        self.gd = gd_p
        self.mdka = mdka_p

    def __getitem__(self, i: int) -> str:
        """ Returns item of match indexed by i. """
        return self[i]

    def show(self):
        ''' Shows match name, gd and mdka '''
        print(f"Match: {self.name} {self.gd} {self.mdka}")

class FileMatch(Match):
    ''' Match in the marchlist file '''
    kit: str
    matchdate: str
    haplo: Haplo

    def __init__(self, name_p: Name=None, kit_p: str=None, haplo_p: Haplo=None,
                 mdate_p: str=None, gd_p: int=0, mdka_p: str=None):
        """ Constuctor which passes base match arguments to base class """
        super().__init__(name_p, gd_p, mdka_p)
        self.matchdate = mdate_p
        self.kit = kit_p
        self.haplo = haplo_p

    def show(self):
        print(f"FileMatch KIT {self.kit} NAME {self.name.get_name()} GD {self.gd} MDKA {self.mdka}")

class Clumatch(Match):
    ''' Cluster match '''
    def __init__(self, kit_p, gd_p, name_p, email_p, mdka_p):
        self.kit = kit_p
        super().__init__(kit_p, gd_p, name_p, email_p, mdka_p)

    def show(self):
        print(f"{self.name.fullname} {self.mdka}")
