import re
import logging
from pymeasure.display import browser

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def natural_sort(text):
    regex = '(\d*\.\d+|\d+)'
    parts = re.split(regex, text)
    return tuple((e if i % 2 == 0 else float(e)) for i, e in enumerate(parts))


class BrowserItem(browser.BrowserItem):      
    def __lt__(self, other):
        column = self.treeWidget().sortColumn()
        text = self.text(column)
        other_text = other.text(column)
        return natural_sort(text) < natural_sort(other_text)
