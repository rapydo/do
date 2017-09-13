# -*- coding: utf-8 -*-

"""
Endpoint example for the RAPyDo framework
"""

#################
# IMPORTS
from restapi.rest.definition import EndpointResource
# from restapi.services.detect import detector
from utilities.logs import get_logger

#################
# INIT VARIABLES
log = get_logger(__name__)
service_name = "{{ service_name }}"
# NOTE: if you need to operate based on service availability
# SERVICE_AVAILABLE = detector.check_availability(service_name)


#################
# REST CLASS
class {{ class_name }}(EndpointResource):

    def get(self):
        # Write server logs, on different levels:
        # very_verbose, verbose, debug, info, warning, error, critical, exit
        log.info("Received a test HTTP request")

        # Parse input parameters:
        # NOTE: they can be caught only if indicated in swagger files
        self.get_input()
        # pretty print arguments obtained from the _args private attribute
        log.pp(self._args, prefix_line='Parsed args')

        # Activate a service handle
        service_handle = self.get_service_instance(service_name)
        log.debug("Connected to %s:\n%s", service_name, service_handle)

        # Handle errors
        if service_handle is None:
            log.error('Service %s unavailable', service_name)
            return self.send_errors(
                message='Server internal error. Please contact adminers.',
                # code=hcodes.HTTP_BAD_NOTFOUND
            )

        # Output any python structure (int, string, list, dictionary, etc.)
        response = 'Hello world!'
        return self.force_response(response)
