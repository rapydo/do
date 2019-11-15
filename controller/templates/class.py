# -*- coding: utf-8 -*-

"""
Endpoint example for the RAPyDo framework
"""

#################
# IMPORTS
from restapi.rest.definition import EndpointResource
from controller import log

#################
# INIT VARIABLES
service_name = "{{ service_name }}"
# NOTE: if you need to operate based on service availability
# SERVICE_AVAILABLE = detector.check_availability(service_name)


#################
# REST CLASS
class {{ class_name }}(EndpointResource):

    def get(self):
        # Write server logs, on different levels:
        # verbose, debug, info, warning, error, critical, exit
        log.info("Received a test HTTP request")

        # Parse input parameters:
        # NOTE: they can be caught only if indicated in swagger files
        self.get_input()

        # Activate a service handle
        service_handle = self.get_service_instance(service_name)
        log.debug("Connected to {}:\n{}", service_name, service_handle)

        # Handle errors
        if service_handle is None:
            log.error('Service {} unavailable', service_name)
            return self.send_errors(
                message='Server internal error. Please contact adminers.',
                # code=hcodes.HTTP_BAD_NOTFOUND
            )

        # Output any python structure (int, string, list, dictionary, etc.)
        response = 'Hello world!'
        return self.force_response(response)
