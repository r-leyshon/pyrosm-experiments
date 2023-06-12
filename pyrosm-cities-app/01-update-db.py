from pathlib import Path
import os
import toml
from datetime import datetime

import pyrosm
from pyrosm.data import sources
from pyprojroot import here
from django.utils.text import slugify

"""This script is used to generate or overwrite a database of
pyrosm-derived features for use with the pyrosm-cities-app. This is to
avoid the demanding processing load that causes out of memory error on
shinyapps.io.
"""
# configure script
CONF = toml.load(here("pyrosm-cities-app/config/01-update-db.toml"))
AOI = CONF["cities"]["aoi"]
MODES = CONF["network"]["modes"]
# find osm available cities & compare with AOI
cities = [x.lower() for x in sources.cities.available]
missing = set(AOI).difference(cities)
if len(missing) > 0:
    raise ValueError(
        f"Cities being searched for are not in pyrosm.sources:\n{', '.join(missing)}"
    )

# ingest the data to tmp - don't store as too large, create osm objects
osm_cities = dict()
for city in AOI:
    fp = pyrosm.get_data(city)
    osm_cities[city] = pyrosm.OSM(fp)

# extract the available networks & write to disk
out_pth = here("pyrosm-cities-app/data/")
try:
    Path.mkdir(out_pth)  # handles missing parent dirs
except FileExistsError:
    pass
# date for vintages
vint = datetime.strftime(datetime.now(), "%Y-%m-%d")
n_cities = len(osm_cities)
n_nets = n_cities * len(MODES)
n = 1
for city, osm in osm_cities.items():
    for mod in MODES:
        print(f"Extracting network {n} of {n_nets}")
        net = osm.get_network(network_type=mod)
        n += 1
        # slugify standardises filenames
        slug = slugify(f"{city}-net-{mod}-{vint}")
        fname = os.path.join(out_pth, f"{slug}.arrow")
        # retain only columns of interest
        net = net.loc[:, ["geometry", "length", "maxspeed"]]
        print(f"Writing net to {fname}")
        net.to_feather(fname)


# extract land use features & write to disk
n = 1
for city, osm in osm_cities.items():
    print(f"Extracting landuse features {n} of {n_cities}")
    landuse = osm.get_landuse()
    slug = slugify(f"{city}-landuse-{vint}")
    fname = os.path.join(out_pth, f"{slug}.arrow")
    # keep only features of interest
    landuse = landuse.loc[:, ["landuse", "geometry"]]
    print(f"Writing landuse features to {fname}")
    landuse.to_feather(fname)
    n += 1

# finally with green space
n = 1
for city, osm in osm_cities.items():
    print(f"Extracting natural features {n} of {n_cities}")
    nat = osm.get_natural()
    slug = slugify(f"{city}-natural-{vint}")
    fname = os.path.join(out_pth, f"{slug}.arrow")
    # keep only features of interest
    nat = nat.loc[:, ["natural", "geometry"]]
    print(f"Writing natural features to {fname}")
    nat.to_feather(fname)
    n += 1
