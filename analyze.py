import networkx as nx

# Verkon tiheys (0-1, 1=täysin yhteydessä)
print(nx.density(G))

# Keskimääräinen aste (kuinka moneen solmuun kukin on yhteydessä)
print(sum(dict(G.degree()).values()) / G.number_of_nodes())

# Klusterointikerroin (kuinka paljon naapurit ovat yhteydessä toisiinsa)
print(nx.average_clustering(G))