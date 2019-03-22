# bring important mkidplotter functions and classes to the top level
from mkidplotter.gui.results import Results
from mkidplotter.gui.inputs import NoiseInput, BooleanListInput
from mkidplotter.gui.windows import SweepGUI, PulseGUI
from mkidplotter.gui.parameters import (DirectoryParameter, FileParameter,
                                        TextEditParameter)
from mkidplotter.gui.indicators import IntegerIndicator, FloatIndicator, BooleanIndicator
from mkidplotter.gui.widgets import (SweepPlotWidget, TransmissionPlotWidget,
                                     NoisePlotWidget, PulsePlotWidget, TimePlotWidget)
from mkidplotter.gui.procedures import (SweepGUIProcedure, SweepGUIProcedure2,
                                        SweepBaseProcedure, MKIDProcedure)
from mkidplotter.icons.manage_icons import get_image_icon
# bring important pymeasure classes and functions to the top level
from pymeasure.experiment import IntegerParameter, FloatParameter, VectorParameter

# TODO: suppress problematic warnings locally using with statement
# get rid of numpy deprecation warnings
import warnings
import numpy as np
warning = "using a non-integer number instead of an integer will result in an error " + \
          "in the future"
warnings.filterwarnings("ignore", category=np.VisibleDeprecationWarning, message=warning)
warnings.filterwarnings("ignore", message="All-NaN slice encountered",
                        category=RuntimeWarning, module="numpy")
warnings.filterwarnings("ignore", message="All-NaN axis encountered",
                        category=RuntimeWarning, module="numpy")
warnings.filterwarnings("ignore", message="All-NaN slice encountered",
                        category=RuntimeWarning, module="pyqtgraph")
warnings.filterwarnings("ignore", message="invalid value encountered in",
                        category=RuntimeWarning, module="pyqtgraph")
