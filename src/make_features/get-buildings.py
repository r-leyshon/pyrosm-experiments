import pyrosm
import os
from pyprojroot import here

"""
1. get Data


2. filter to aoi

3. get buildings

4. summarise classification
"""


def ingest_osm(osm_pth):
    """
    Read in OSM data. Find the available boundary names.

    Args:
        osm_pth (str): Path to the osm.pbf file.
    """
    pth = os.path.normpath(osm_pth)

    if not osm_pth.endswith(".osm.pbf"):
        raise ValueError("Incorrect suffix. Check the `osm_pth` filename.")
    elif not os.path.exists(pth):
        raise FileNotFoundError("`osm_pth` not found.")
    else:
        osm_dat = pyrosm.OSM(osm_pth)
        bounds = osm_dat.get_boundaries().name.values
        print(f"OSM data ingested. {len(bounds)} boundaries available.")
        return (osm_dat, bounds)


x, y = ingest_osm(
    os.path.join(here(), "data", "external", "cropped_north_line.osm.pbf")
)
