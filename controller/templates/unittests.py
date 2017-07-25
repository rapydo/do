# -*- coding: utf-8 -*-

"""
Run unittests inside the RAPyDo framework
"""

import json
from tests import RestTestsAuthenticatedBase
from utilities.logs import get_logger

log = get_logger(__name__)


class Test{{ endpoint_name.capitalize() }}(RestTestsAuthenticatedBase):

    """ Quickstart:
    - setUp and tearDown methods before and after each test
    - one method inside this class for each functionality to test
    - decide the order with the name: test_NUMBER_METHOD_FUNCTIONALITY
    """

    _main_endpoint = '/{{ endpoint_name }}'

    # def tearDown(self):
    #     """ override original teardown if you create custom data """

    #     log.debug('### Cleaning custom data ###\n')
    #     super().tearDown()

    def test_01_GET_public_PID(self):
        """ Test directory creation: POST """

        endpoint = (self._api_uri + self._main_endpoint)
        log.info('*** Testing GET call on %s' % endpoint)

        # If NO authorization required
        r = self.app.get(endpoint, headers=self.__class__.auth_header)
        # If authorization required
        # r = self.app.get(endpoint, headers=self.__class__.auth_header)

        # Assert what is right or wrong
        self.assertEqual(r.status_code, self._hcodes.HTTP_OK_BASIC)
        data = json.loads(r.get_data(as_text=True))
        # pretty print data obtained from API to check the content
        # log.pp(data)
        self.assertEqual(data['Response']['data'], 'Hello world!')
