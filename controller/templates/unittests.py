# -*- coding: utf-8 -*-

"""
Run unittests inside the RAPyDo framework
"""

from restapi.tests import BaseTests, API_URI, AUTH_URI
from restapi.utilities.htmlcodes import hcodes

from controller import log


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
        log.info('*** Testing GET call on {}', endpoint)

        r = client.get(endpoint)  # If NO authorization required
        # headers, _ = self.do_login(client, None, None)
        # r = client.get(
        #     endpoint,
        #     headers=headers  # If authorization required
        # )

        # Assert what is right or wrong
        assert r.status_code == hcodes.HTTP_OK_BASIC
        output = self.get_content(r)

        assert output == 'Hello world!'
