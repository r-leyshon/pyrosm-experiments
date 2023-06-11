import re
import toml
import os

from shiny import ui, render, App, reactive
import geopandas as gpd

# set working directory to that expected by deployment
os.chdir(os.path.dirname(os.path.realpath(__file__)))
# get the available city values
CONFIG = toml.load("config/01-update-db.toml")

cities = CONFIG["cities"]["aoi"]


app_ui = ui.page_fixed(
    ui.tags.header(ui.tags.html(lang="en"), ui.tags.title("Some Title")),
    ui.h1("City Road Network"),
    ui.markdown(
        """
        This app uses [pyrosm][0] to summarise city spatial feature data available in
        [Open Street Map (OSM)][1]. Please note that OSM is crowd-sourced data
        maintained by community contribution. OSM accuracy and consistency vary by
        area.

        [0]: https://pyrosm.readthedocs.io/en/latest/index.html
        [1]: https://www.openstreetmap.org/
    """
    ),
    ui.layout_sidebar(
        ui.panel_sidebar(
            ui.input_selectize(
                id="citySelector",
                label="Select a city:",
                choices=cities,
                selected=cities[-1],
            ),
            ui.input_select(
                id="featureSelector",
                label="Select a feature:",
                choices=["net-driving", "landuse", "natural"],
                selected="landuse",
            ),
            ui.input_action_button(
                id="runButton", label="Go", class_="btn-primary w-100"
            ),
        ),
        ui.panel_main(ui.output_plot("viz_feature")),
    ),
)


def server(input, output, session):
    @output
    @render.plot
    @reactive.event(input.runButton)
    def viz_feature():
        search_pat = re.compile(f"{input.citySelector()}-{input.featureSelector()}.*")
        dat_pth = "data/"
        all_files = os.listdir(dat_pth)
        found = [
            os.path.join(dat_pth, fn) for fn in all_files if bool(search_pat.search(fn))
        ]
        dat = gpd.read_feather(found[0])
        dat.plot()

        # fp = pyrosm.get_data(input.citySelector())  # downloads to tmp
        # osm = pyrosm.OSM(fp)
        # net = osm.get_network(network_type="driving")
        # net_len = int(round(sum(net["length"]) / 1000, 0))
        # return f"Estimated road length is {net_len:,} kilometers (nearest km)."


app = App(app_ui, server)
