# -*- coding: utf-8 -*-

from utilities import template
from utilities import path
from utilities import PROJECT_DIR, BACKEND_DIR, SWAGGER_DIR

TEMPLATE_DIR = 'templates'


def justatest(file='test.py'):
    data = {
        'name': "PEPPE!",
        # "items": ["oranges", "bananas", "steak", "milk"]
    }
    templated = template.render(file, TEMPLATE_DIR, **data)

    # to save the results
    with open("my_new_file.html", "wb") as fh:
        fh.write(templated)

    return True


class NewEndpointScaffold(object):
    """
    Scaffold necessary directories and file to create
    a new endpoint within the RAPyDo framework
    """

    def __init__(self, project, endpoint_name='foo'):
        super(NewEndpointScaffold, self).__init__()
        self.custom_project = project
        self.original_name = endpoint_name
        self.endpoint_name = endpoint_name.lower()
        self._run()

    def swagger_dir(self):
        swagger_endpoint_path = [
            PROJECT_DIR,
            self.custom_project,
            BACKEND_DIR,
            SWAGGER_DIR,
            self.endpoint_name
        ]
        p = path.build(swagger_endpoint_path)
        path.create(p, directory=True, force=True)

    def swagger_specs(self):
        pass

    def swagger_first_operation(self):
        pass

    def swagger(self):

        self.swagger_dir()
        self.swagger_specs()
        self.swagger_first_operation()

    def rest_class(self):
        pass

    def test_class(self):
        pass

    def _run(self):
        self.swagger_dir()

        # # YET TODO
        print("specs")
        self.swagger_specs()
        print("file")
        self.swagger_first_operation()
        print("completed")
