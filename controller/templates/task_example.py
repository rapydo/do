from restapi.connectors.celery import CeleryExt
import time

from restapi.utilities.logs import log

celery_app = CeleryExt.celery_app


@celery_app.task(bind=True)
def testme(self):
    with celery_app.app.app_context():

        # self.db = celery_app.get_service('sqlalchemy')

        log.info("Task started!")

        self.update_state(state="STARTING", meta={'current': 1, 'total': 3})
        time.sleep(1)

        self.update_state(state="COMPUTING", meta={'current': 2, 'total': 3})
        time.sleep(1)

        self.update_state(state="FINAL", meta={'current': 3, 'total': 3})
        time.sleep(1)

        log.info("Task executed!")
        return "Task executed!"
