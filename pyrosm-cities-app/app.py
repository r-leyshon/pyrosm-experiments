from shiny import ui, render, App, reactive
import pyrosm
from pyrosm.data import sources

# get the available city values with pyrosm
cities = sources.cities.available


app_ui = ui.page_fixed(
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
                selected="Birmingham",
            ),
            ui.input_action_button(
                id="runButton", label="Go", class_="btn-primary w-100"
            ),
        ),
        ui.panel_main(ui.output_text("measure_net")),
    ),
)


def server(input, output, session):
    @output
    @render.text
    @reactive.event(input.runButton)
    def measure_net():
        fp = pyrosm.get_data(input.citySelector())  # downloads to tmp
        osm = pyrosm.OSM(fp)
        net = osm.get_network(network_type="driving")
        net_len = int(round(sum(net["length"]) / 1000, 0))
        return f"Estimated road length is {net_len:,} kilometers (nearest km)."


app = App(app_ui, server)
