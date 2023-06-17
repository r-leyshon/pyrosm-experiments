import re
import toml
import os

from shiny import ui, render, App, reactive
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

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
            ui.input_select(
                id="crsSelector",
                label="Project to CRS:",
                choices=["wgs84", "27700", "2154"],
                selected="wgs84",
            ),
            ui.input_action_button(
                id="runButton", label="Go", class_="btn-primary w-100"
            ),
        ),
        ui.panel_main(
            ui.output_text("debug_txt"),
            ui.h2(ui.output_text("return_plt_txt")),
            ui.output_plot("viz_feature"),
            ui.output_table("summ_table"),
        ),
    ),
)


def server(input, output, session):
    @reactive.event(input.runButton)
    def return_data():
        # return the required geodataframe
        search_pat = re.compile(f"{input.citySelector()}-{input.featureSelector()}.*")
        dat_pth = "data/"
        all_files = os.listdir(dat_pth)
        found = [
            os.path.join(dat_pth, fn) for fn in all_files if bool(search_pat.search(fn))
        ]
        pth = found[0]
        dat = gpd.read_feather(pth)
        dat = dat.to_crs(input.crsSelector())
        return (dat, pth)

    @output
    @render.text
    @reactive.event(input.runButton)
    def return_plt_txt():
        # get the OSM ingest date:
        pat = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
        vint = pat.search(return_data()[1]).group(0)
        plot_text = reactive.Value(
            f"{input.featureSelector()} in {input.citySelector()}".title()
            + f" OSM: {vint}"
        )
        return plot_text()

    @output
    @render.plot
    @reactive.event(input.runButton)
    def viz_feature():
        with ui.Progress(min=1, max=100) as p:
            p.set(message="Working", detail="Sit tight...")
            # Selecting column to colour plot depends on selected feature
            colour_col = reactive.Value(None)
            if input.featureSelector() == "net-driving":
                colour_col.set(None)
            elif input.featureSelector() == "natural":
                colour_col.set("reclassified_natural")
            else:
                colour_col.set("reclassified_landuse")

            ax = return_data()[0].plot(
                column=colour_col(),
                legend=True,
                figsize=(16, 16),
                legend_kwds=dict(loc="upper left", ncol=1, bbox_to_anchor=(1, 1)),
            )
            # style
            ax.set_facecolor("black")
            ax.set(yticklabels=[])
            ax.set(xticklabels=[])
            plt.tick_params(axis="both", which="both", bottom=False, left=False)

        @output
        @render.table
        @reactive.event(input.runButton)
        def summ_table():
            tab_dict = dict()
            dat = return_data()[0]
            if input.featureSelector() == "net-driving":
                tab_dict["Total length (km)"] = [int(sum(dat["length"]) / 1000)]
            else:
                areas = dat.area
                # marseilles has a nat feature that results in a negative area, remove
                areas = [a for a in areas if a > 0]
                tab_dict[f"Total {input.featureSelector()} area (km2)"] = [
                    sum(areas) / 1000000
                ]
            return pd.DataFrame.from_dict(tab_dict, orient="columns")

        @output
        @render.text
        def debug_txt():
            dat = return_data()[0]
            areas = dat.area
            return sum(areas)


app = App(app_ui, server)
