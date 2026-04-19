# mt_network

This program is not a ready project. It's on the way to finish. It is programmed with pyCharm.

Cluster network program. It makes nodes.csv and links.csv to Gephi. Gephi can display a network of mt-dna matches
in one haplogroup. The match clusters can be subgroups to that haplogroup. Grouping depends on GD values between
matches. 

This is the main purpose to this program. You can do other things with this program too. Be free to modify code.
If you think you know better methods to do something, feel free to contact and tell to Ilpo at ilpo@iki.fi.

Input to this program are downloaded mt-dna match lists from FTDNA. Output are nodes.csv and links.csv. With Gephi
you can do beautiful graphs of GD network. You can also print MDKA:s as txt and xml file and a spreadsheet.

TODO:

- Split the cluster, if it contains matches which have other matches than common matches in that cluster.
- Add GUI to main.
- Fork to working with y-dna
