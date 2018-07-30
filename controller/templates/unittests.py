# -*- coding: utf-8 -*-

"""
Run unittests inside the RAPyDo framework
"""

from restapi.tests import BaseTests, API_URI, AUTH_URI
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger

log = get_logger(__name__)


class Test{{ class_name }}(BaseTests):

    """ Quickstart:
    - setUp and tearDown methods before and after each test
    - one method inside this class for each functionality to test
    - decide the order with the name: test_NUMBER_METHOD_FUNCTIONALITY
    """

    _main_endpoint = '/{{ endpoint_name }}'

    def test_01_GET_giveityourname(self, client):
        """
        testing a feature on your endpoint class
        """

        endpoint = API_URI + self._main_endpoint
        log.info('*** Testing GET call on %s' % endpoint)

        r = client.get(endpoint)  # If NO authorization required
        # headers, _ = self.do_login(client, None, None)
        # r = client.get(
        #     endpoint,
        #     headers=headers  # If authorization required
        # )

        # Assert what is right or wrong
        assert r.status_code == hcodes.HTTP_OK_BASIC
        output = self.get_content(r)

        # pretty print data obtained from API to check the content
        # log.pp(output)
        assert output == 'Hello world!'
