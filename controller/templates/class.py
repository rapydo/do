# -*- coding: utf-8 -*-

"""
Endpoint example for the RAPyDo framework
"""

#################
# IMPORTS
from restapi.rest.definition import EndpointResource
# from restapi.services.detect import detector
from utilities.logs import get_logger

#################
# INIT VARIABLES
log = get_logger(__name__)
service_name = "{{ service_name }}"
# NOTE: if you need to operate based on service availability
# SERVICE_AVAILABLE = detector.check_availability(service_name)


#################
# REST CLASS
class {{ class_name }}(EndpointResource):

    def get(self):
        log.info("Received a test HTTP request")
        response = 'Hello world!'

        service_handle = self.get_service_instance(service_name)
        log.debug("Connected to %s:\n%s" % (service_name, service_handle))

        return self.force_response(response)
