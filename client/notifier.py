# -*- coding: utf-8-*-
import Queue
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
import logging
import jasperpath
import pkgutil


class Notifier(object):

    def __init__(self, profile):
        self._logger = logging.getLogger(__name__)
        self.q = Queue.Queue()
        self.profile = profile
        self.notifiers = self.get_modules()
        sched = BackgroundScheduler(timezone="UTC", daemon=True)
        sched.start()
        sched.add_job(self.gather, 'interval', seconds=30)
        atexit.register(lambda: sched.shutdown(wait=False))

    @classmethod
    def get_modules(cls):
        logger = logging.getLogger(__name__)
        locations = [jasperpath.PLUGIN_PATH]
        logger.debug("Looking for modules in: %s",
                     ', '.join(["'%s'" % location for location in locations]))
        modules = []
        for finder, name, ispkg in pkgutil.walk_packages(locations):
            try:
                loader = finder.find_module(name)
                mod = loader.load_module(name)
            except:
                logger.warning("Skipped module '%s' due to an error.", name,
                               exc_info=True)
            else:
                if hasattr(mod, 'NOTIFIER'):
                    logger.debug("Found module '%s' with NOTIFIER: %r", name,
                                 mod.NOTIFIER)
                    modules.append(mod)
                else:
                    logger.warning("Skipped module '%s' because it misses " +
                                   "the NOTIFIER constant.", name)
        modules.sort(key=lambda mod: mod.PRIORITY if hasattr(mod, 'PRIORITY')
        else 0, reverse=True)

        return modules

    def gather(self):
        for client in self.notifiers:
            for notification in client.getNotifications():
                self.q.put(notification)

    def getNotification(self):
        """Returns a notification. Note that this function is consuming."""
        try:
            notif = self.q.get(block=False)
            return notif
        except Queue.Empty:
            return None

    def getAllNotifications(self):
        """
            Return a list of notifications in chronological order.
            Note that this function is consuming, so consecutive calls
            will yield different results.
        """
        notifs = []

        notif = self.getNotification()
        while notif:
            notifs.append(notif)
            notif = self.getNotification()

        return notifs

class Notification(object):

    def __init__(self, message, handleNotification):
        self.handleNotification = handleNotification
        self.message = message

    def handle(self, mic):
        self.handleNotification(self, mic)
