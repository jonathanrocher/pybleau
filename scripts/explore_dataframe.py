
from pandas import DataFrame
from numpy import array, nan, random

from app_common.std_lib.logging_utils import initialize_logging

from pybleau.app.api import DataFrameAnalyzer, DataFrameAnalyzerView

LEN = 16

initialize_logging(logging_level="DEBUG")

TEST_DF = DataFrame({"axial disp": [1, 2, 3, 4]*(LEN//4),
                     "break point": [1, 2, 3, 4]*(LEN//4),
                     # As above but no nan inserted below:
                     "break point2": sorted([1, 2, 3, 4]*(LEN//4)),
                     "correlation": range(1, LEN+1),
                     "disposed batch": random.choice(list("abc"), size=LEN),
                     "efficiency": random.randn(LEN),
                     "final yield": random.randn(LEN),
                     "gain": random.randn(LEN),
                     # Highly repetitive column to split the entire data into 2
                     "handled": array([0, 1]*(LEN//2), dtype=bool),
                     # Same as above but as a string:
                     "intercepted": array(["F", "T"]*(LEN//2)),
                     "jump": sorted(list("abcdefgh")*2),
                     "kill": sorted(list("abcd")*4),
                     "run_name": list("abcdefghijklmnop"),
})

TEST_DF.iloc[-1, 1] = nan

print(TEST_DF["disposed batch"])

analyzer = DataFrameAnalyzer(source_df=TEST_DF)
view = DataFrameAnalyzerView(
    model=analyzer, include_plotter=True, plotter_layout="HSplit",
    plotter_kw={"container_layout_type": "horizontal",
                "num_container_managers": 5, "multi_container_mode": 2}
)
view.configure_traits()
