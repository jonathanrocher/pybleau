""" See base class module for general documentation on factories.
"""

from __future__ import print_function, division

import pandas as pd
import logging

from traits.api import Constant, Tuple
from chaco.api import ArrayPlotData, ColorBar, ColormappedSelectionOverlay, \
    HPlotContainer, LinearMapper, ScatterInspectorOverlay
from chaco.default_colormaps import color_map_name_dict
from chaco.tools.api import RangeSelection, RangeSelectionOverlay

from app_common.chaco.scatter_position_tool import add_scatter_inspectors, \
    DataframeScatterInspector

from .plot_config import SCATTER_PLOT_TYPE
from .base_factories import StdXYPlotFactory

SELECTION_COLOR = "red"

DISCONNECTED_SELECTION_COLOR = "grey"

SELECTION_METADATA_NAME = 'selections'

logger = logging.getLogger(__name__)


class ScatterPlotFactory(StdXYPlotFactory):
    """ Factory to build a scatter plot.

    This plot currently supports displaying many dimensions at once since it
    supports a legend tool to select parts of the data and a hover tool to
    display any number of additional columns.
    """
    #: Plot type as used by Plot.plot
    plot_type_name = Constant("scatter")

    #: Plot type as selected by user
    plot_type = Constant(SCATTER_PLOT_TYPE)

    #: Inspector tool and overlay to query/listen to for events
    inspector = Tuple

    def _plot_tools_default(self):
        return {"zoom", "pan", "click_selector", "legend", "hover"}

    def generate_plot(self):
        plot, desc = super(ScatterPlotFactory, self).generate_plot()
        if "click_selector" in self.plot_tools:
            self.add_click_selector_tool(plot)

        if "hover" in self.plot_tools:
            self.add_hover_display_tool(plot)

        return plot, desc

    def add_click_selector_tool(self, plot):
        for renderer_name in plot.plots:
            renderer = plot.plots[renderer_name][0]
            marker_size = self.plot_style["marker_size"]
            marker = self.plot_style["marker"]
            inspector_tool = DataframeScatterInspector(
                renderer, selection_metadata_name=SELECTION_METADATA_NAME,
                selection_mode="toggle", persistent_hover=False
            )
            renderer.tools.append(inspector_tool)
            inspector_overlay = ScatterInspectorOverlay(
                renderer,
                selection_marker=marker,
                selection_marker_size=marker_size,
                selection_color=self.inspector_selection_color
            )

            renderer.overlays.append(inspector_overlay)
            # FIXME: This overwrite itself when multiple renderers are drawn...
            self.inspector = (inspector_tool, inspector_overlay)

    def add_hover_display_tool(self, plot):
        """ Add mouse hover tool to display column values on hover.
        """
        if not self.hover_col_names:
            return

        if not self.z_col_name:
            renderer_data = pd.DataFrame({col: plot.data.arrays[col]
                                          for col in self.hover_col_names})
        else:
            renderer_data = []
            for hue_name in self._hue_values:
                data = {}
                for col in self.hover_col_names:
                    key = self._plotdata_array_key(col, hue_name)
                    data[col] = plot.data.get_data(key)

                renderer_data.append(pd.DataFrame(data))

        add_scatter_inspectors(plot, datasets=renderer_data,
                               include_overlay=True, align="ul")


class CmapScatterPlotFactory(ScatterPlotFactory):
    """ Factory to build a single scatter plot colormapped by a z array.

    See Also
    --------
    ScatterPlotFactory:
        Use the ScatterPlotFactory to create a scatter Plot with 1 or more
        scatter renderers, for example when colorizing using a column of
        discrete values.
    """
    #: Plot type as used by Plot.plot
    plot_type_name = Constant("cmap_scatter")

    def _plot_tools_default(self):
        # No need for a legend
        return {"zoom", "pan", "click_selector", "colorbar_selector", "hover"}

    def adjust_plot_style(self):
        """ Translate general plotting style info into cmap_scatter params.
        """
        self.plot_style.pop("color")
        self.plot_style["fill_alpha"] = self.plot_style.pop("alpha")
        palette_name = self.plot_style["color_palette"]
        self.plot_style["color_mapper"] = color_map_name_dict[palette_name]

    def generate_plot(self):
        # FIXME: move the plot title to the container level.

        plot, desc = super(CmapScatterPlotFactory, self).generate_plot()
        cmap_renderer = plot.plots["cmap_scatter"][0]
        select_tool = "colorbar_selector" in self.plot_tools
        if select_tool:
            selection = ColormappedSelectionOverlay(cmap_renderer,
                                                    fade_alpha=0.35,
                                                    selection_type="mask")
            cmap_renderer.overlays.append(selection)

        # Add a colorbar:
        colorbar = create_cmap_scatter_colorbar(plot.color_mapper,
                                                select_tool=select_tool)
        colorbar.plot = cmap_renderer
        colorbar.title = self.z_axis_title
        colorbar.padding_top = plot.padding_top
        colorbar.padding_bottom = plot.padding_bottom

        # Create a container to position the plot and the colorbar side-by-side
        container = HPlotContainer(use_backbuffer=True)
        container.add(plot)
        container.add(colorbar)
        container.bgcolor = "lightgray"
        return container, desc

    def add_renderers(self, plot):
        for desc in self.renderer_desc:
            plot.plot((desc["x"], desc["y"], desc["z"]), type="cmap_scatter",
                      name=desc["name"], **self.plot_style)

    def initialize_plot_data(self, x_arr=None, y_arr=None, z_arr=None,
                             **adtl_arrays):
        """ Set the plot_data and the list of renderer descriptions.
        """
        if x_arr is None or y_arr is None or z_arr is None:
            msg = "2D cmap scatters require a valid plot_data or an array for"\
                  " x, y and z."
            logger.exception(msg)
            raise ValueError(msg)

        data_map = {self.x_col_name: x_arr, self.y_col_name: y_arr,
                    self.z_col_name: z_arr}
        data_map.update(adtl_arrays)
        renderer_data = {"x": self.x_col_name, "y": self.y_col_name,
                         "z": self.z_col_name, "name": "cmap_scatter"}
        self.renderer_desc.append(renderer_data)
        self.plot_data = ArrayPlotData(**data_map)
        return data_map

    def add_hover_display_tool(self, plot):
        """ Add mouse hover tool to display column values on hover.
        """
        if not self.hover_col_names:
            return

        renderer_data = pd.DataFrame({col: plot.data.arrays[col]
                                      for col in self.hover_col_names})
        add_scatter_inspectors(plot, datasets=renderer_data,
                               include_overlay=True, align="ul")


def create_cmap_scatter_colorbar(colormap, select_tool=False):
    """ Create a fancy colorbar for a CMAP scatter plot, with a selection tool.
    """
    colorbar = ColorBar(index_mapper=LinearMapper(range=colormap.range),
                        color_mapper=colormap,
                        orientation='v',
                        resizable='v',
                        width=30,
                        padding=20)
    if select_tool:
        colorbar.tools.append(RangeSelection(component=colorbar))
        colorbar.overlays.append(RangeSelectionOverlay(component=colorbar,
                                                       border_color="white",
                                                       alpha=0.8,
                                                       fill_color="lightgray"))
    return colorbar
