#!/usr/bin/env python3

import sys
import json
import requests
import logging
import re
from pathlib import Path
from updateexts import UpdateExts
from annotate import Annotate
from packaging.requirements import Requirement

logger = logging.getLogger()

__version__ = '0.1.0'
__date__ = '2025-03-16'
__author__ = 'John Dey'


class UpdatePython(UpdateExts, Annotate):
    """
       extend ExtsList class to update package names from PyPI
       Python Issues
        - There are many small inconsistancies with PyPi which make it difficult
       to fully automate building of EasyConfig files.
       - pypi projects names do not always match module names and or file names
         project: liac-arff, module: arff,  file name: liac_arff.zip
    """
    def __init__(self, easyconfig, operation, verbose, eb):
        self.verbose = verbose
        self.pkg_dict = None
        self.dep_types = ['requires_dist']
        self.python_version = None
        self.exts_search_pypi = None
        self.exts_processed_normalized = []
        self.dotGraph = {}
        self.indent = "    "
        self.exts_orig = []
        self.dep_exts = []
        if operation == 'search_pypi':
            self.display_pypi_meta(easyconfig)
        elif operation == 'description':
            # UpdateExts.__init__(self, verbose, eb)
            self.exts_description(eb.exts_list)
        elif operation == 'dep_graph':
            print(f" == Python Descriptions")
            self.pypi_query(eb.exts_list, easyconfig)
        elif operation == 'annotate':
            print(f' == Annotate {eb.easyconfig}')
            UpdateExts.__init__(self, verbose,             eb)
            Annotate.__init__(self, easyconfig, verbose, self.exts_orig, self.dep_exts)
            self.create_markdown()
        elif operation == 'update':
            (nums) = eb.pyver.split('.')
            self.pyshortver = f"{nums[0]}.{nums[1]}"
            self.env = {'python_version': self.pyshortver, 'extra': 'none'}
            logging.debug("Python Version: %s" % self.pyshortver)
            UpdateExts.__init__(self, verbose, eb)
            # Python >3.3 has additional built in modules
            self.depend_exclude = ['argparse', 'asyncio', 'typing', 'sys'
                                   'functools32', 'enum34', 'future', 'configparser']
            self.updateexts()
            eb.print_update(eb.language, self.exts_processed)

    def display_pypi_meta(self, pypi_project_name):
        """ display metadata from PyPi
        --search-pypi <pypi_project_name>
        """
        print(f"Search PyPi for {pypi_project_name}")
        project = self.get_pypi_project({'name': pypi_project_name, 'version': ""})
        if project == 'not found':
            sys.exit(1)
        self.print_meta(project)
        project = self.get_pypi_pkg_data({'name': project['info']['name']}, project['info']['version'])
        if project == 'not found':
            sys.exit(1)
        for url in project['urls']:
            if 'filename' in url:
                print(f"Filename: {url['filename']}")

    def get_pypi_project(self, pkg):
        """ Python PyPi project
        ['info']['classifiers']: 'audience', 'Topic'
        """
        req = f"https://pypi.org/pypi/{pkg['name']}/json"
        resp = requests.get(req)
        logging.debug('get_pypi_project: request: %s responce: %s', req, resp.status_code)
        if 200 <= resp.status_code < 300:
            return resp.json()
        else:
            logging.error('API error: %s GET project %s', resp.status_code, pkg['name'])
            return 'not found'

    def get_pypi_pkg_data(self, pkg, version=None):
        """
        return meta data from PyPi.org)
        """
        req = 'https://pypi.org/pypi/%s/%s/json' % (pkg['name'], version)
        resp = requests.get(req)
        if 200 < resp.status_code or resp.status_code >= 300:
            logging.error("API error: %s GET release %s", resp.status_code, pkg['name'])
            return 'not found'
        project = resp.json()
        # verify that Project name is correct
        # projects names might differ from import names
        # sphinx -> Sphinx
        if pkg['name'] != project['info']['name']:
            logging.debug('Python name mismatch. name %s modulename %s\n', project['info']['name'], 
                          pkg['name'])
            if 'spec' in pkg:
                pkg['spec']['modulename'] = pkg['name']
            else:
                pkg['spec'] = {'modulename': pkg['name']}
            pkg['name'] = project['info']['name']
        print(f"Project: {project['info']['name']} {project}")
        sys.exit(1)
        return project

    def check_package_name(self, pkg_name):
        """
        verify that package name from EasyConfig
        matches package name from PyPi
        """
        pkg = {'name': pkg_name}
        response = self.get_pypi_pkg_data(pkg)
        if response == 'not found':
            return response
        else:
            return response['info']['name']

    def print_meta(self, project):
        """ print 'info' dict from pypi.org

        """
        if 'info' in project:
            info = project['info']
        else:
            return
        print(f"{info['name']}: {info['version']}")
        for key in info:
            if key == 'description':
                print(f"    %s: %s" % (key, info[key][1:60]))
            else:
                print(f"    {key}: {json.dumps(info[key], indent=4)}")
        print('===')

    def pypi_requires_dist(self, name, requires_dist):
        """ process the requires_dist from Pypi. The requires_dist is a list of dependancies
         written in PEP 508 sepification.
           Evaluate each secification from requires_dist to determine if the package is required.
              Evaluate the package with the Marker evaluator from <packaging>.
            If the `Marker` is True, add the package name to the list of dependencies.
        """
        if requires_dist is None:
            return []
        depends_on = []
        for req in requires_dist:
            require = Requirement(req)
            if require.marker:
                evaluated = require.marker.evaluate(self.env)
                if evaluated:
                    depends_on.append(require.name)
                    logging.debug("from: %s add dependency: %s", name, require.name)
            else:
                depends_on.append(require.name)
        return depends_on

    def get_pypi_release(self, pkg, project):
        """if source dist is not available from pypi search
        the release for a wheel file.
        """
        status = 'not found'
        if 'version' in pkg['meta']:
            version = pkg['meta']['version']
        else:
            print(f'no version info! for {pkg['name']}')
        for ver in project['releases'][version]:
            if 'packagetype' in ver and ver['packagetype'] == 'sdist':
                pkg['meta']['url'] = ver['url']
                pkg['meta']['filename'] = ver['filename']
                status = 'ok'
                break
        # one last try to find package release data
        if status != 'ok':
            cplist = ['cp38', 'cp39', 'cp310', 'cp311', 'cp312']
            for rel in project['releases'][version]:
                if any(cver in rel['python_version'] for cver in cplist):
                    if 'manylinux' in rel['filename']:
                        pkg['meta'].update(rel)
                        status = 'ok'
                        break
        return status

    def check_download_filename(self, pkg):
        """ Python project name, module name, and file name do not awlays match
            define 'source_tmpl' to match the file name from pypi
        """
        if 'filename' not in pkg['meta']:
            return
        filename = pkg['meta']['filename']
        template = None
        name = pkg['name']
        version = pkg['version']
        source_targz = f"{name}-{version}.tar.gz"
        if source_targz == filename:
            return   # no need to check further

        if '-' in pkg['name']:
            dash_targz = f"{name.replace('-', '_')}-{version}.tar.gz"
            if dash_targz == filename:
                template = f"{name.replace('-', '_')}-%(version)s.tar.gz"
        if '.' in pkg['name']:
            dot_targz = f"{name.replace('.', '_')}-{version}.tar.gz"
            if dot_targz == filename:
                template = f"{name.replace('.', '_')}-%(version)s.tar.gz"
        if any(map(str.isupper, name)):
            lower_targz = f"{name.lower()}-{version}.tar.gz"
            if lower_targz == filename:
                template = f"{name.lower()}-{version}s.tar.gz"
        if 'zip' in filename and filename == f"{name}-{version}.zip":
            template = "%(name)s-%(version)s.zip"
        if 'tar.bz2' in filename and filename == f"{name}-{version}.tar.bz2":
            template = "%(name)s-%(version)s.tar.bz2"
        if not template:
            print(f"WARNING: {name} filename does not match templates. {filename}")
        if 'spec' not in pkg:
            pkg['spec'] = {'source_tmpl': template}
            print(f"WARNING: {name} filename does not have a spec.")
        else:
            pkg['spec']['source_tmpl'] = template

    def get_package_info(self, pkg):
        """get version information from pypi.  If <pkg_name> is not processed
        seach pypi. pkg_name is now case sensitive and must match
        """
        project = self.get_pypi_project(pkg)
        self.project = project
        logging.debug('get_package_info: version: %s project: %s', pkg['version'], project)

        if self.project == 'not found':
            return 'not found'
        pkg['meta'].update(project['info'])
        # new_version = pkg['meta']['version']
        status = self.get_pypi_release(pkg, project)
        #  self.check_download_filename(pkg, project)
        pkg['meta']['requires'] = []
        if 'requires_dist' in project['info']:
            requires = project['info']['requires_dist']
            dep_list = self.pypi_requires_dist(pkg['name'], requires)
            for dep in dep_list:
                pkg['meta']['requires'].append([dep, 'requires'])
        if 'classiferiers' in project['info']:
            if 'win' in pkg['meta']['classifiers'].lower():
                print(f"WARNING: {pkg['name']} is win32.  Classifiers: {pkg['meta']['classifiers']}")
        if 'summary' in project['info'] or 'Summary' in project['info']:
            pkg['meta']['description'] = project['info']['summary']
        else:
            logging.error("pkg: %s no Pypi info: %s", pkg['name'], project['info'])
        if project['info']['version'] != pkg['version']:
            pkg['orig_version'] = pkg['version']
            pkg['version'] = project['info']['version']
        else:
            pkg['orig_version'] = None
        return 'ok'

    def processed(self, pkg):
        """ Python version - add package to exts_processed list 
        self.exts_procsssed_normalized is a list a flat list of normalized package names
         contains both the package name and the module name
        """
        dup_pkg = dict(pkg)
        if pkg['action'] == 'add':
            self.ext_counter += 1
        self.exts_processed.append(dup_pkg)
        normalized_name = self.normalize_name(dup_pkg['name'])
        if normalized_name != dup_pkg['name']:
            self.exts_processed_normalized.append(normalized_name)
        else:
            self.exts_processed_normalized.append(dup_pkg['name'])
        if 'spec' in pkg and 'modulename' in pkg['spec']:
            self.exts_processed_normalized.append(pkg['spec']['modulename'])



    def get_package_url(self, pkg):
        """ Return URL and Description from PyPi """
        project = self.get_pypi_project(pkg)
        if project == 'not found':
            return "", "Project Summary not found"

        project = self.get_pypi_pkg_data({'name': project['info']['name']}, project['info']['version'])
        return project['info']['url'], project['info']['summary']

    def output_module(self, pkg):
        """Python version
        this method is used with --search, otherwise, framework is used
        """
        space = " "
        if 'spec' in pkg:
            output = f"('{pkg['name']}', '{pkg['version']}"
            for item in pkg['spec'].keys():
                output += f"{space:8}('{item}', '{pkg['spec'][item]}', {{"
            output += f"{space:4}}}),"
        else:
            output = f"{space:4}('{pkg['name']}', '{pkg['version']}'),"
        return output

    def exts_description(self, exts_list):
        """ Print the 'summary' metadata from the PyPi metadata for each extension in exts_list """
        ext_list_len = len(exts_list)
        ext_counter = 1
        pkg = {}
        for ext in exts_list:
            pkg = {'name': ext[0], 'version': ext[1], 'meta': {}}
            project = self.get_pypi_project(pkg)
            if project == "not found":
                ext_description = 'Package Not Found in PyPi'
            else:
                ext_description = project['info']['summary']
            counter = f"[{ext_list_len}, {ext_counter}]"
            print(f"{counter:10} {pkg['name']}-{pkg['version']} : {ext_description}")
            ext_counter += 1

    def pypi_query(self, exts_list, full_path_name):
        """ query pypi for package dependencies """
        fname = Path(full_path_name).stem
        print(f'digraph {fname} {{')
        for ext in exts_list:
            pkg = {'name': ext[0], 'version': ext[1], 'meta': {}}
            status = self.get_package_info(pkg)
            dot_name = self.normalize_project_name(pkg['name']);
            if status == "not found":
                print(f"  {dot_name}: not found in PyPi", file=sys.stderr)
            else:
                if 'meta' in pkg and len(pkg['meta']['requires']) > 0:
                    package_list = ', '.join([f'{r[0]}' for r in pkg['meta']['requires']])
                    dep_names = self.normalize_project_name(package_list)
                    print(f"  {dot_name} -> {dep_names}")
                else:
                    print(f"  {dot_name}")
        print('}')

    def print_dependencies(self, eb):
        """ Print dependencies data from dep_exts."""
        for pkg in eb.dep_exts:
            if len(pkg) == 3:
                print(f"{pkg[0]} - {pkg[1]}: {pkg[2]}")
            else:
                print(f"{pkg[0]} - missing Dictionary")


    def normalize_name(self, name):
        """Normalize a package name. PEP508 specifies that package names are case-insensitive,
        and that they should be normalized to lowercase.
        """
        return re.sub(r"[-_.]+", "-", name).lower()


def add_to_python_dep_exts(dep_eb, easyconfig, dep_exts):
    """ Python Dependants have many ways to specify the module name.
        add package to dep_exts if not already in list
        - PythonPackage does not have exts_list. Add 'name' and 'verstion' to dep_exts
    """
    if 'easyblock' in dep_eb.__dict__:
        easyblock = dep_eb.easyblock
    elif 'default_easyblock' in dep_eb.__dict__:
        easyblock = dep_eb.default_easyblock
    elif 'Python' in dep_eb.name:
        easyblock = 'Python'
    else:
        easyblock = ''

    if easyblock in ['PythonPackage', 'PythonBundle', 'Python']:
        dep_exts.append([dep_eb.name, dep_eb.version, {'module': easyconfig}])
        easyconfig_name = self.normalize_name(dep_eb.name)
        if easyconfig_name != dep_eb.name:
            dep_exts.append([easyconfig_name, dep_eb.version, {'module': easyconfig}])
        if 'options' in dep_eb.__dict__ and 'modulename' in dep_eb.options:
            modulename = dep_eb.options['modulename']
            normalized_moudlename = self.normalize_name(modulename)
            if modulename != normalized_moudlename:
                dep_exts.append([normalized_moudlename, dep_eb.version, {'module': easyconfig}])
            else:
                dep_exts.append([modulename, dep_eb.version, {'module': easyconfig}])
        if 'exts_list' in dep_eb.__dict__:
            for ext in dep_eb.exts_list:
                normalized_name = self.normalize_name(ext[0])
                if normalized_name not in dep_exts:
                    dep_exts.append([normalized_name, ext[1]])
                    if len(ext) > 2 and 'module' in ext[2]:
                        dep_exts.append([ext[2]['module'], ext[1]])


def main():
    pass


if __name__ == '__main__':
    main()

