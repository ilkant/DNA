"""
Links between GD-clusters.
"""

class Link:
    ''' Original and destination linkw'''
    orig: str
    dest: str
    gd: int

    def __init__(self, orig_p: str=None, dest_p: str=None, gd_p: int=0):
        self.orig = orig_p
        self.dest = dest_p
        self.gd = gd_p

    def show(self):
        ''' Show link from original to destination '''
        print(f"Link {self.orig} -> {self.dest}")
