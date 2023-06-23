from pathlib import Path
import os
import toml
from datetime import datetime
import re
import subprocess

import pyrosm
from pyrosm.data import sources
from pyrosm_proto import DecodeError
from pyprojroot import here
from django.utils.text import slugify
import numpy as np

"""This script is used to generate or overwrite a database of
pyrosm-derived features for use with the pyrosm-cities-app. This is to
avoid the demanding processing load that causes out of memory error on
shinyapps.io.
"""
# configure script
CONF = toml.load(here("pyrosm-cities-app/config/01-update-db.toml"))
AOI = CONF["cities"]["aoi"]
MODES = CONF["network"]["modes"]
BBOXES = CONF["osm"]["bbox"]
REGIONS = CONF["osm"]["region"]
# find osm available cities & compare with AOI
cities = [x.lower() for x in sources.cities.available]
# extract the available networks & write to disk
out_pth = here("pyrosm-cities-app/data/")
try:
    Path.mkdir(out_pth)  # handles missing parent dirs
except FileExistsError:
    pass
# date for vintages
vint = datetime.strftime(datetime.now(), "%Y-%m-%d")

# ingest the data to tmp - don't store as too large, create osm objects
transp = "|".join(["aero", "railway", "highway", "motorway", "road", "runway"]).lower()

agri = "|".join(
    [
        "Allotments",
        "Animal",
        "Farm",
        "Field",
        "Flowerbed",
        "Forest",
        "Grass",
        "Green",
        "Horticulture",
        "Meadow",
        "Orchard",
        "plant_nursery",
        "Scrub",
        "Shrubs",
        "Vineyard",
        "Apiary",
        "Aquaculture",
        "Arboretum",
        "Growing",
        "Pasture",
    ]
).lower()

rec = "|".join(
    [
        "Contains recreation",
        "Park",
        "Leisure",
        "Sport",
        "Recreation",
        "Tourism",
        "Playing ",
    ]
)

commerce = "|".join(
    [
        "Commercial",
        "Depot",
        "Retail",
        "Storage",
        "Warehouse",
        "Hospitality",
        "Logistics",
    ]
)

indus = "|".join(["Industrial", "Factory", "Industr", "Quarry"])

amen = "|".join(
    [
        "Landfill",
        "Cemetery",
        "Military",
        "Parking",
        "Religious",
        "Health",
        "car_park",
        "Church",
        "Education",
        "Government",
        "^hospital$",
        "Sewage",
    ]
)

develop = "|".join(["proposed_construction", "Construction", "proposed_station"])

trans_pat = re.compile(transp, re.IGNORECASE)
agri_pat = re.compile(agri, re.IGNORECASE)
rec_pat = re.compile(rec, re.IGNORECASE)
comm_pat = re.compile(commerce, re.IGNORECASE)
indus_pat = re.compile(indus, re.IGNORECASE)
amen_pat = re.compile(amen, re.IGNORECASE)
dev_pat = re.compile(develop, re.IGNORECASE)

rock_pat = re.compile(
    r"rock|cliff|shingle|sand|stone|scree|gorge|ridge|landslide|mountain", re.IGNORECASE
)
water_pat = re.compile(
    r"bay|beach|coast|spring|water|wet|shoal|river|flood|reed", re.IGNORECASE
)
green_pat = re.compile(
    r"grass|mud|heath|tree|shrub|scrub|scub|wood|forest|field|earth|meadow|lawn|fell",
    re.IGNORECASE,
)

osm_cities = dict()
for city in AOI:
    if city in cities:
        # logic to ingest city data from pyrosm
        fp = pyrosm.get_data(city)
        osm_cities[city] = pyrosm.OSM(fp)
    else:
        # logic to ingest region data with pyrosm, then use osmium to filter to bbox
        # get the OSM for the region
        region = REGIONS[city]
        bbox = BBOXES[city]
        bbox_str = ",".join([str(x) for x in bbox])
        print(f"City not available in pyrosm sources. Ingesting from {region} region.")
        fp = pyrosm.get_data(region)
        tmp = os.path.dirname(fp)
        out_tmp = os.path.join(tmp, f"{slugify(city)}-osm.pbf")
        subprocess.run(
            [
                "osmium",
                "extract",
                "--strategy",
                "complete_ways",
                "--bbox",
                bbox_str,
                fp,
                "-o",
                out_tmp,
            ]
        )
        osm_cities[city] = pyrosm.OSM(out_tmp)

n_cities = len(osm_cities)
n_nets = n_cities * len(MODES)
n = 1
probs = []
# road network
for city, osm in osm_cities.items():
    for mod in MODES:
        print(f"Extracting network {n} of {n_nets}")
        try:
            net = osm.get_network(network_type=mod)
            # slugify standardises filenames
            slug = slugify(f"{city}-net-{mod}-{vint}")
            fname = os.path.join(out_pth, f"{slug}.arrow")
            # retain only columns of interest
            net = net.loc[:, ["geometry", "length", "maxspeed"]]
            print(f"Writing net to {fname}")
            net.to_feather(fname)
        except (DecodeError, ValueError):
            print(f"OSM encoding problem encountered with {city}. Skipping.")
            probs.append(city)
            pass
        n += 1

# remove any city that threw a decode error
for prob in probs:
    del osm_cities[prob]
    n_cities -= 1

# extract land use features & write to disk
n = 1
for city, osm in osm_cities.items():
    print(f"Extracting landuse features {n} of {n_cities}")
    landuse = osm.get_landuse()
    slug = slugify(f"{city}-landuse-{vint}")
    fname = os.path.join(out_pth, f"{slug}.arrow")
    # filter out point data
    landuse = landuse[np.array(landuse.geom_type != "Point", dtype=bool)]
    # keep only features of interest
    landuse = landuse.loc[:, ["landuse", "geometry"]]
    # reclassify
    landuse["reclassified_landuse"] = landuse.landuse
    landuse.reclassified_landuse = [
        "transport" if bool(trans_pat.search(land_class)) else land_class
        for land_class in landuse.reclassified_landuse
    ]
    landuse.reclassified_landuse = [
        "agriculture" if bool(agri_pat.search(land_class)) else land_class
        for land_class in landuse.reclassified_landuse
    ]
    landuse.reclassified_landuse = [
        "recreation" if bool(rec_pat.search(land_class)) else land_class
        for land_class in landuse.reclassified_landuse
    ]
    landuse.reclassified_landuse = [
        "commerce" if bool(comm_pat.search(land_class)) else land_class
        for land_class in landuse.reclassified_landuse
    ]
    landuse.reclassified_landuse = [
        "industry" if bool(indus_pat.search(land_class)) else land_class
        for land_class in landuse.reclassified_landuse
    ]
    landuse.reclassified_landuse = [
        "amenities" if bool(amen_pat.search(land_class)) else land_class
        for land_class in landuse.reclassified_landuse
    ]
    landuse.reclassified_landuse = [
        "development" if bool(dev_pat.search(land_class)) else land_class
        for land_class in landuse.reclassified_landuse
    ]
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
    # filter out point data
    nat = nat[np.array(nat.geom_type != "Point", dtype=bool)]
    # keep only features of interest
    nat = nat.loc[:, ["natural", "geometry"]]
    # reclassify the natural columns
    # reclassify
    nat["reclassified_natural"] = nat.natural

    nat.reclassified_natural = [
        "rock" if bool(rock_pat.search(nat_class)) else nat_class
        for nat_class in nat.reclassified_natural
    ]
    nat.reclassified_natural = [
        "water" if bool(water_pat.search(nat_class)) else nat_class
        for nat_class in nat.reclassified_natural
    ]
    nat.reclassified_natural = [
        "green" if bool(green_pat.search(nat_class)) else nat_class
        for nat_class in nat.reclassified_natural
    ]
    print(f"Writing natural features to {fname}")
    nat.to_feather(fname)
    n += 1
