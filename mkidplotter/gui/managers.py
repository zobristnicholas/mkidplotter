import logging
from mkidplotter.gui.workers import Worker
import pymeasure.display.manager as manager
from pymeasure.display.listeners import Monitor

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Manager(manager.Manager):
    """Extension of the pymeasure Manager class to allow for multiple plots."""
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

    def next(self):
        """
        Initiates the start of the next experiment in the queue as long
        as no other experiments are currently running and there is a procedure
        in the queue. Uses the Worker class from mkidplotter instead of pymeasure.
        """
        if self.is_running():
            raise Exception("Another procedure is already running")
        else:
            if self.experiments.has_next():
                log.debug("Manager is initiating the next experiment")
                experiment = self.experiments.next()
                self._running_experiment = experiment

                self._worker = Worker(experiment.results, port=self.port,
                                      log_level=self.log_level)

                self._monitor = Monitor(self._worker.monitor_queue)
                self._monitor.worker_running.connect(self._running)
                self._monitor.worker_failed.connect(self._failed)
                self._monitor.worker_abort_returned.connect(self._abort_returned)
                self._monitor.worker_finished.connect(self._finish)
                self._monitor.progress.connect(self._update_progress)
                self._monitor.status.connect(self._update_status)
                self._monitor.log.connect(self._update_log)

                self._monitor.start()
                self._worker.start()

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
