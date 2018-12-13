# get rid of numpy deprecation warnings
import warnings
import numpy as np
warning = "using a non-integer number instead of an integer will result in an error " + \
          "in the future"
warnings.filterwarnings("ignore", category=np.VisibleDeprecationWarning, message=warning)
