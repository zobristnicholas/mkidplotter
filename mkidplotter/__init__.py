# get rid of numpy deprecation warnings
import warnings
import numpy as np
# catch known harmless warnings
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
