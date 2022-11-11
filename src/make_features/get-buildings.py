import pyrosm
import os
from pyprojroot import here
import shapely

"""
1. get Data


2. filter to aoi

3. get buildings

4. summarise classification
"""


def ingest_osm(osm_pth, bbox=None):
    """
    Read in OSM data. Find the available boundary names.

    Args:
        osm_pth (str): Path to the osm.pbf file.

        bbox
    """
    pth = os.path.normpath(osm_pth)

    if not osm_pth.endswith(".osm.pbf"):
        raise ValueError("Incorrect suffix. Check the `osm_pth` filename.")
    elif not os.path.exists(pth):
        raise FileNotFoundError("`osm_pth` not found.")
    elif bbox:
        if isinstance(bbox, shapely.geometry.multipolygon.MultiPolygon):
            osm_dat = pyrosm.OSM(osm_pth, bounding_box=bbox)
            return osm_dat
        else:
            raise TypeError("`bbox` must be a shapely geometry.")

    else:
        osm_dat = pyrosm.OSM(osm_pth)
        bounds = osm_dat.get_boundaries().name.values
        print(f"OSM data ingested. {len(bounds)} boundaries available.")
        return (osm_dat, bounds)


x, y = ingest_osm(
    os.path.join(here(), "data", "external", "cropped_north_line.osm.pbf")
)
aoi = y[3]


def filter_osm(osm_obj, osm_pth, aoi_pat):
    """_summary_

    Args:
        osm_obj (_type_): _description_
        osm_pth
        aoi_pat (_type_): _description_
    """
    if not isinstance(osm_obj, pyrosm.pyrosm.OSM):
        raise TypeError("`osm_obj` must be of type pyrosm.OSM.")
    elif not isinstance(aoi_pat, str):
        raise TypeError("`aoi_pat` must be of type str.")

    bbox_geom = osm_obj.get_boundaries(name=aoi_pat).geometry.values[0]
    aoi_osm = ingest_osm(osm_pth, bbox=bbox_geom)
    return aoi_osm


aoi_x = filter_osm(
    x,
    osm_pth=os.path.join(here(), "data", "external", "cropped_north_line.osm.pbf"),
    aoi_pat=aoi,
)
