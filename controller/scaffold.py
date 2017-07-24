# -*- coding: utf-8 -*-

from utilities.myyaml import YAML_EXT
from utilities import template
from utilities import path
from utilities import PROJECT_DIR, BACKEND_DIR, SWAGGER_DIR
from utilities.logs import get_logger

log = get_logger(__name__)

TEMPLATE_DIR = 'templates'


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
        self.swagger_path = path.build(swagger_endpoint_path)
        path.create(self.swagger_path, directory=True, force=True)

    @staticmethod
    def save_template(filename, content):
        with open(filename, "w") as fh:
            fh.write(content)

    def render(self, filename, data, outdir='custom'):

        mypath = path.join(outdir, filename)
        if path.file_exists_and_nonzero(mypath):
            log.warning("%s already exists" % filename)
            return False

        filepath = str(mypath)

        # FIXME: decide where template dir is
        template_dir = TEMPLATE_DIR
        templated_content = template.render(filename, template_dir, **data)

        self.save_template(filepath, templated_content)
        log.debug("rendered %s" % filepath)
        return True

    # OLD VERSION
    # def render(self, template_file, output_file, data):
    #     templated_content = template.render(
    #         template_file, template_dir, **data)
    #     self.save_template(output_file, templated_content)

    def swagger_specs(self):
        self.render(
            'specs.%s' % YAML_EXT,
            data={'endpoint_name': self.endpoint_name},
            outdir=self.swagger_path
        )

    def swagger_first_operation(self):
        self.render(
            'get.%s' % YAML_EXT,
            data={'endpoint_name': self.endpoint_name},
            outdir=self.swagger_path
        )

    def swagger(self):

        self.swagger_dir()
        self.swagger_specs()
        self.swagger_first_operation()

    def rest_class(self):
        pass

    def test_class(self):
        pass

    def _run(self):
        self.swagger()

        # # YET TODO
        print("todo")
        self.rest_class()
        self.test_class()
        print("completed")
