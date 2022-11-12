import pyrosm
import os
from pyprojroot import here
from shapely.geometry.multipolygon import MultiPolygon
from shapely.geometry.polygon import Polygon
import geopandas as gpd
import re
import numpy as np
import pygeos


def ingest_osm(osm_pth, bbox=None):
    """
    Read in OSM data. Find the available boundary names.

    Args:
        osm_pth (str): Path to the osm.pbf file.

        bbox (shapely.geometry.Geometry, optional): A geometry to filter
        the pyrosm.OSM object. Can be Polygon or Multipolygon.

    Returns:
        pyrosm.OSM object, array of available boundaries within the osm.pbf
    """
    pth = os.path.normpath(osm_pth)

    if not osm_pth.endswith(".osm.pbf"):
        raise ValueError("Incorrect suffix. Check the `osm_pth` filename.")
    elif not os.path.exists(pth):
        raise FileNotFoundError("`osm_pth` not found.")
    elif bbox:
        if isinstance(bbox, MultiPolygon) | isinstance(bbox, Polygon):
            osm_dat = pyrosm.OSM(osm_pth, bounding_box=bbox)
            return osm_dat
        else:
            raise TypeError("`bbox` must be a shapely polygon or multipolygon.")

    else:
        osm_dat = pyrosm.OSM(osm_pth)
        bounds = osm_dat.get_boundaries().name.values
        print(f"OSM data ingested. {len(bounds)} boundaries available.")
        return (osm_dat, bounds)


x, y = ingest_osm(
    os.path.join(here(), "data", "external", "cropped_north_line.osm.pbf")
)
aoi = y[3]


def filter_buildings(osm_obj, osm_pth, aoi_pat):
    """
    Filter osm.pbf to a specific area and return the buildings.

    Finds the matching bounding box geometry to `aoi_pat` if available
    within the `osm_obj`. If found, refilters the osm.pbf file on disk to
    the area of interest extent. Extract the buildings.

    Args:
        osm_obj (pyrosm.pyrosm.OSM): Pyrosm object extracted from the
        osm.pbf file. The output of `ingest_osm()` when you do not provide
        a value to the bbox argument.
        osm_pth (str): Path to the osm.pbf file.
        aoi_pat (str): The pattern to search for bounding box geometry.

    Returns:
        Geopandas DF with buildings for the area of interest.
    """
    if not isinstance(osm_obj, pyrosm.pyrosm.OSM):
        raise TypeError("`osm_obj` must be of type pyrosm.OSM.")
    elif not isinstance(aoi_pat, str):
        raise TypeError("`aoi_pat` must be of type str.")

    bbox_gdf = osm_obj.get_boundaries(name=aoi_pat)
    bbox_geom = bbox_gdf.geometry.values[0]

    aoi_osm = ingest_osm(osm_pth, bbox=bbox_geom)
    aoi_buildings = aoi_osm.get_buildings()
    aoi_buildings = aoi_buildings.assign(aoinm=aoi_pat)

    return aoi_buildings


# aoi = y[46] # works for a polygon bbox
aoi = y[3]  # works for a multipoly bbox
# aoi = y[4]

aoi_x = filter_buildings(
    x,
    osm_pth=os.path.join(here(), "data", "external", "cropped_north_line.osm.pbf"),
    aoi_pat=aoi,
)


def clean_aoi(aoinms, rem_pats="(?i)alba|england|united kingdom|north east"):
    """_summary_

    Args:
        aoinms (_type_): _description_
        rem_pats (_type_): _description_
        'Alba / Scotland', 'England', 'United Kingdom'
    """
    pat = re.compile(rem_pats)
    # working with numpy ndarray, so need to vectorise the match
    vmatch = np.vectorize(lambda x: bool(pat.match(x)))
    sel = vmatch(aoinms)
    # returns a boolean array, invert to filter out patterns
    return aoinms[~sel]


y = clean_aoi(y)


probs = list()
area_buildings = gpd.GeoDataFrame()

for area in y:
    try:
        aoi_builds = filter_buildings(
            osm_obj=x,
            osm_pth=os.path.join(
                here(), "data", "external", "cropped_north_line.osm.pbf"
            ),
            aoi_pat=area,
        )
        area_buildings = area_buildings.concat(aoi_builds)
    except pygeos.GEOSException:
        print(f"{area} triggered exception")
        probs = probs.append(area)
