import logging
from pymeasure.display.manager import Manager, Experiment

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MKIDManager(Manager):
    """Extension of the pymeasure Manager class to allow for multiple plots
    """
    def load(self, experiment):
        """ Load a previously executed Experiment
        """
        for index, plot in enumerate(self.plot):
            for curve in experiment.curve[index]:
                plot.addItem(curve)
        self.browser.add(experiment)
        self.experiments.append(experiment)

    def remove(self, experiment):
        """ Removes an Experiment
        """
        self.experiments.remove(experiment)
        self.browser.takeTopLevelItem(
            self.browser.indexOfTopLevelItem(experiment.browser_item))
        for index, plot in enumerate(self.plot):
            for curve in experiment.curve[index]:
                plot.removeItem(curve)

    def _finish(self):
        log.debug("Manager's running experiment has finished")
        experiment = self._running_experiment
        self._clean_up()
        experiment.browser_item.setProgress(100.)
        for index, _ in enumerate(self.plot):
            for curve in experiment.curve[index]:
                curve.update()
        self.finished.emit(experiment)
        if self._is_continuous:  # Continue running procedures
            self.next()
