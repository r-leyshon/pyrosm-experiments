import re
import os

from shiny import ui, render, App, reactive
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import shinyswatch

# set working directory to that expected by deployment
os.chdir(os.path.dirname(os.path.realpath(__file__)))
# get the available city values
found_fs = os.listdir("data/")
cities = [f.split("-")[0] for f in found_fs]
cities = list(set(cities))


app_ui = ui.page_fixed(
    ui.tags.header(ui.tags.html(lang="en"), ui.tags.title("Pyrosm Cities App")),
    shinyswatch.theme.sketchy(),
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
            ui.input_action_button(id="show_mod", label="Notes"),
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
    def return_plt_txt():
        # get the OSM ingest date:
        pat = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
        vint = pat.search(return_data()[1]).group(0)
        plot_text = reactive.Value("Make a Selection & Click Go")
        plot_text.set(
            f"{input.featureSelector()} in {input.citySelector()}".title()
            + f" OSM: {vint}"
        )
        return plot_text()

    @reactive.event(input.runButton)
    def selected_feature():
        # Selecting column to colour plot depends on selected feature
        colour_col = reactive.Value(None)
        if input.featureSelector() == "net-driving":
            colour_col.set(None)
        elif input.featureSelector() == "natural":
            colour_col.set("reclassified_natural")
        else:
            colour_col.set("reclassified_landuse")
        return colour_col()

    @output
    @render.plot
    @reactive.event(input.runButton)
    def viz_feature():
        with ui.Progress(min=1, max=100) as p:
            p.set(message="Working", detail="Sit tight...")

            ax = return_data()[0].plot(
                column=selected_feature(),
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
            return pd.DataFrame.from_dict(tab_dict, orient="columns")
        else:
            dat["area_km"] = dat.area / 1000000
            # marseilles has a nat feature that results in a negative area, remove
            dat = dat[dat["area_km"] > 0]
            tot_area = sum(dat["area_km"])
            summ_tab = (
                dat.groupby(selected_feature())
                .sum("area_km")
                .round(3)
                .sort_values(by="area_km", ascending=False)
                .reset_index()
            )
            summ_tab["perc_total"] = round(summ_tab["area_km"] / tot_area * 100, 3)
            return summ_tab

    @reactive.Effect
    @reactive.event(input.runButton)
    def _():
        if input.crsSelector() == "wgs84":
            ui.notification_show(
                "CRS is geographic. Results from 'area' are likely incorrect.",
                type="warning",
            )

    @reactive.Effect
    @reactive.event(input.show_mod)
    def _():
        t_txt = reactive.Value("")
        p_txt = reactive.Value("")
        if input.featureSelector() == "net-driving":
            t_txt.set("OSM Driving Network")
            p_txt.set(
                "This transport mode includes private car but not public"
                " service vehicles."
                " Click outside of this window to return to the app."
            )
        else:
            t_txt.set("OSM Landuse / Natural Features")
            p_txt.set(
                "Accurate area calculation requires an appropriate CRS to be"
                " selected. Categories have been grouped to improve plotting."
                " Click outside of this window to return to the app."
            )

        m = ui.modal(
            p_txt(),
            title=t_txt(),
            easy_close=True,
            footer=None,
        )
        ui.modal_show(m)


app = App(app_ui, server)
