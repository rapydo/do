# -*- coding: utf-8 -*-

"""
Meta thinking: python objects & introspection

usefull documentation:
http://python-3-patterns-idioms-test.readthedocs.org/en/latest/Metaprogramming.html
"""

import pkgutil
import inspect
from importlib import import_module
# TO FIX: remove
from rapydo.confs import BACKEND_PACKAGE, CUSTOM_PACKAGE
from rapydo.utils.logs import get_logger

log = get_logger(__name__)


################################
# Utilities
class Meta(object):
    """Utilities with meta in mind"""

    _latest_list = {}
    _submodules = []

    def get_latest_classes(self):
        return self._latest_list

    def set_latest_classes(self, classes):
        self._latest_list = classes

    def get_submodules_from_package(self, package):
        self._submodules = []
        for importer, modname, ispkg \
                in pkgutil.iter_modules(package.__path__):
            if not ispkg:
                self._submodules.append(modname)
                log.debug("Found %s submodule inside %s" %
                          (modname, package.__name__))
        return self._submodules

    def get_classes_from_module(self, module):
        """
        Find classes inside a python module file.

        Note: this method returns a dict.
        """

        classes = {}
        try:
            classes = dict(
                [
                    (name, cls)
                    for name, cls in module.__dict__.items()
                    if isinstance(cls, type)
                ]
            )
        except AttributeError:
            log.warning("Could not find any class inside your module")

        self.set_latest_classes(classes)
        return self.get_latest_classes()

    def get_new_classes_from_module(self, module):
        """
        Skip classes not originated inside the module.

        Note: this method returns a list.
        """

        classes = {}
        for key, value in self.get_classes_from_module(module).items():
            if module.__name__ in value.__module__:
                classes[key] = value
        self.set_latest_classes(classes)
        return self.get_latest_classes()

    def get_module_from_string(self, modulestring, prefix_package=False,
                               exit_if_not_found=False, exit_on_fail=False):
        """
        Getting a module import
        when your module is stored as a string in a variable
        """

        module = None
        if prefix_package:
            modulestring = BACKEND_PACKAGE + '.' + modulestring.lstrip('.')

        try:
            # Meta language for dinamically import
            module = import_module(modulestring)
        except ImportError as e:
            if exit_on_fail:
                raise e
            else:
                log.warning("Failed to load module: " + str(e))

        # TOFIX: cannot use the proper exception (available in python 3.6+)
        # because we are stuck on python 3.5 con IMC
        # except ModuleNotFoundError as e:
        except BaseException as e:
            # if True:
            if exit_if_not_found:
                raise e
            else:
                log.warning("Module %s not found " % modulestring)

        return module

    def import_submodules_from_package(self, package_name,
                                       exit_if_not_found=False,
                                       exit_on_fail=False):

        submodules = []
        package = self.get_module_from_string(package_name)

        for module_name in self.get_submodules_from_package(package):
            module_path = package_name + '.' + module_name
            log.debug("Loading module '%s'" % module_path)

            submod = self.get_module_from_string(
                module_path,
                exit_if_not_found=exit_if_not_found,
                exit_on_fail=exit_on_fail)
            submodules.append(submod)
        return submodules

    @staticmethod
    def get_methods_inside_instance(instance, private_methods=False):
        methods = {}
        all_methods = inspect.getmembers(instance, predicate=inspect.ismethod)
        for name, method in all_methods:
            if not private_methods and name[0] == '_':
                continue
            methods[name] = method
        return methods

    @staticmethod
    def get_class_from_string(classname, module):
        """ Get a specific class from a module using a string variable """

        myclass = None
        try:
            # Meta language for dinamically import
            myclass = getattr(module, classname)
        except AttributeError as e:
            log.critical("Failed to load class from module: " + str(e))

        return myclass

    @staticmethod
    def metaclassing(your_class, label=None, attributes={}):
        """
        Creating a class using metas.
        Very usefull for automatic algorithms.
        """

        methods = dict(your_class.__dict__)
        for key, value in attributes.items():
            methods.update({key: value})
        return type(label, (your_class,), methods)

    @staticmethod
    def get_self_reference_from_args(*args):
        """
        Useful in decorators:
        being able to call the internal method by getting
        the 'self' reference from the decorated method
        (when it's there)
        """

        if len(args) > 0:
            candidate_as_self = args[0]
            cls_attribute = getattr(candidate_as_self, '__class__', None)
            if cls_attribute is not None and inspect.isclass(cls_attribute):
                return args[0]
        return None

    def models_module(self, name, package):
        module_name = "%s.%s.%s" % (package, 'models', name)
        return self.get_module_from_string(module_name)

    def obj_from_models(self, obj_name, module_name, package):
        module = self.models_module(module_name, package)
        obj = getattr(module, obj_name, None)
        return obj

    def import_models(self, name, custom=False, exit_on_fail=True):

        models = {}
        if custom:
            package = CUSTOM_PACKAGE
            # exit_on_fail = False
        else:
            package = BACKEND_PACKAGE
        module = self.models_module(name, package)

        if module is not None:
            models = self.get_new_classes_from_module(module)
        elif exit_on_fail:
            log.error("Missing module associated to requested models")
            exit(1)

        return models

    def get_authentication_module(self, auth_service):

        module_name = "%s.%s.%s" % ('services', 'authentication', auth_service)
        log.verbose("Loading auth extension: %s" % module_name)
        module = self.get_module_from_string(
            modulestring=module_name, prefix_package=True, exit_on_fail=True)

        return module

    @staticmethod
    def class_factory(name, parents=object, attributes_and_methods={}):
        if not isinstance(parents, tuple):
            parents = (parents, )
        return type(name, parents, attributes_and_methods)

    def get_celery_tasks_from_module(self, submodule):
        """
            Extract all celery tasks from a module.
            Celery tasks are functions decorated by @celery_app.task(...)
            This decorator transform the function into a class child of
            celery.local.PromiseProxy
        """
        tasks = {}
        functions = inspect.getmembers(submodule)
        for func in functions:

            obj_type = type(func[1])

            if obj_type.__module__ != "celery.local":
                continue

            tasks[func[0]] = func[1]
        return tasks
