# -*- coding: utf-8 -*-

"""
Run unittests inside the RAPyDo framework
"""

from tests import RestTestsAuthenticatedBase
from utilities.logs import get_logger

log = get_logger(__name__)


class Test{{ class_name }}(RestTestsAuthenticatedBase):

    """ Quickstart:
    - setUp and tearDown methods before and after each test
    - one method inside this class for each functionality to test
    - decide the order with the name: test_NUMBER_METHOD_FUNCTIONALITY
    """

    _main_endpoint = '/{{ endpoint_name }}'

    # def setUp(self):
    #     """ override original setup to create custom data at each request """

    #     super().setUp()  # Call father's method
    #     log.debug('### Create some custom data ###\n')

    def test_01_GET_giveityourname(self):
        """
        testing a feature on your endpoint class
        """

        endpoint = (self._api_uri + self._main_endpoint)
        log.info('*** Testing GET call on %s' % endpoint)

        r = self.app.get(endpoint)  # If NO authorization required
        # r = self.app.get(
        #     endpoint,
        #     headers=self.__class__.auth_header  # If authorization required
        # )

        # Assert what is right or wrong
        self.assertEqual(r.status_code, self._hcodes.HTTP_OK_BASIC)
        output = self.get_content(r)

        # pretty print data obtained from API to check the content
        # log.pp(output)
        self.assertEqual(output, 'Hello world!')

    # def tearDown(self):
    #     """ override teardown: remove custom data at each request """

    #     log.debug('### Cleaning custom data ###\n')
    #     super().tearDown()
