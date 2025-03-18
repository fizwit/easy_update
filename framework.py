#!/usr/bin/env python3

import os
import sys
import types
import logging
from templates import TEMPLATE_CONSTANTS
from constants import EASYCONFIG_CONSTANTS
from updatePython import add_to_python_dep_exts

# from easybuild.tools.toolchain.constants import ALL_MAP_CLASSES
# from easybuild.framework.easyconfig.templates import TEMPLATE_CONSTANTS

"""

"""

__version__ = '1.0.5'
__maintainer__ = 'John Dey jfdey@fredhutch.org'
__date__ = 'Oct 10, 2024'

logging.basicConfig(format='%(levelname)s [%(filename)s:%(lineno)-4d] %(message)s',
                    level=logging.WARN)
# logging.getLogger().setLevel(logging.DEBUG)


class FrameWork:
    """provide access to EasyBuild Config file variables
    name, version, toolchain, eb.exts_list, dependencies, modulename, biocver,
    """
    def __init__(self, easyconfig, verbose, no_dependencies):
        self.easyconfig = easyconfig
        self.verbose = verbose
        self.language = None
        self.code = None
        self.pyver = None
        self.rver = None
        self.search_pkg = None
        self.indent_n = 4
        self.indent = ' ' * self.indent_n
        self.ptr_head = 0
        self.modulename = None
        self.dep_exts = []
        self.exts_list = []
        self.find_easyconfig_paths(easyconfig)
        logging.debug("EasyConfig search paths: {}".format(self.base_paths))

        # update EasyConfig exts_list
        self.eb_header = self.build_eb_header_constant()

        eb = self.parse_eb(easyconfig, primary=True)
        self.exts_list = eb.exts_list
        self.toolchain = eb.toolchain
        self.name = eb.name
        self.version = eb.version
        self.pyver = self.rver = None
        self.find_language_version(eb)
        self.interpolate = {'name': self.name,
                            'namelower': self.name.lower(),
                            'version': self.version,
                            'pyver': self.pyver,
                            'rver': self.rver,
                            'cudaver': ""}
        if no_dependencies:
            return
        if 'versionsuffix' in eb.__dict__:
            self.versionsuffix = eb.versionsuffix % self.interpolate
        else:
            self.versionsuffix = None
        if self.language == 'R' and self.rver is None:
            print('== R EasyConfig without version')
            sys.exit(1)
        elif self.language == 'Python' and self.pyver is None:
            print('== Python EasyConfig without version')
            sys.exit(1)
        self.search_dependencies(eb.dependencies)

        self.modulename = eb.name + '-' + eb.version
        self.modulename += '-' + eb.toolchain['name']
        self.modulename += '-' + eb.toolchain['version']
        if self.versionsuffix:
            self.modulename += self.versionsuffix
        logging.debug('modulename: %s' % self.modulename)
        self.dependencies = None
        try:
            self.dependencies = eb.dependencies
        except AttributeError:
            logging.WARN('WARNING: no dependencies defined!')
        try:
            self.biocver = eb.local_biocver
        except AttributeError:
            self.biocver = None
        self.check_eb_package_name(easyconfig)
        self.out = open(easyconfig[:-3] + ".update", 'w')

    def parse_eb(self, file_name, primary):
        """ interpret EasyConfig file with 'exec'.  Interperting fails if
        constants that are not defined within the EasyConfig file.  Add
        undefined constants to <header>. Copy templates.py from EasyBuild
        """
        eb = types.ModuleType("EasyConfig")
        try:
            with open(file_name, "r") as f:
                code = f.read()
        except IOError as err:
            logging.debug("Error reading %s: %s" % (file_name, err))
            sys.exit(1)

        # Define a safe execution environment
        safe_globals = {"__builtins__": None}
        safe_locals = eb.__dict__
        try:
            exec(self.eb_header + code, safe_locals)
        except Exception as err:
            logging.error('interperting EasyConfig error: %s' % err)
            sys.exit(1)
        if primary:     # save original text of source code
            self.code = code
        return eb

    def find_language_version(self, eb):
        """
            find the language and version from the EasyConfig file """
        if (eb.name == 'Python' or
            ('easyblock' in eb.__dict__ and eb.easyblock == 'PythonBundle' or eb.easyblock == 'PythonPackage') or
            ('exts_defaultclass' in eb.__dict__ and eb.exts_defaultclass == 'PythonPackage')
            ):
            print('== Python EasyConfig')
            self.language = 'Python'
            if self.name == 'Python':
                self.pyver = eb.version
            else:
                for dep in eb.dependencies:
                    if dep[0] == 'Python':
                        self.pyver = dep[1]
                        break
        elif (eb.name == 'R' or
              ('easyblock' in eb.__dict__ and eb.easyblock == 'RPackage') or
              ('exts_defaultclass' in eb.__dict__ and eb.exts_defaultclass == 'RPackage')
              ):
            self.language = 'R'
            if self.name == 'R':
                self.rver = eb.version
            else:
                for dep in eb.dependencies:
                    if dep[0] == 'R':
                        self.rver = dep[1]
                        break
        else:
            msg = """Unknown language exts_list type. Expecting Python or R based easyconfig
    easyblock: ['PythonBundle', 'RPackage'] or
    exts_defaultclass: ['PythonPackage', 'RPackage']"""
            print('Error: {} {}'.format(eb.name, msg))

    def build_eb_header_constant(self):
        """ build a string of constants from the EasyConfig file
        """
        header = ''
        for constant in TEMPLATE_CONSTANTS:
            header += f'{constant[0]} = "{constant[1]}"\n'
        for constant in EASYCONFIG_CONSTANTS:
            header += f'{constant} = "{EASYCONFIG_CONSTANTS[constant]}"\n'
        return header

    def find_easyconfig_paths(self, filename):
        """find the paths to EasyConfigs, search within the path given by the easyconfig
        given to update. Search for eb command
        """
        userPath = os.path.expanduser(filename)
        fullPath = os.path.abspath(userPath)
        (head, tail) = os.path.split(fullPath)
        self.base_paths = []
        local_path = None
        while tail:
            if 'easyconfigs' in tail:
                self.base_paths.append(os.path.join(head, tail))
                logging.debug('local path to easyconfigs: {}'.format(self.base_paths[-1]))
                local_path = head + '/' + tail
                break
            (head, tail) = os.path.split(head)
        if local_path is None:
            logging.error('You are not working in an EB repository, Quiting because I can not find dependancies.')
            sys.exit(1)
        self.base_paths.append(local_path)
        eb_root = os.getenv('EBROOTEASYBUILD')
        if eb_root is None:
            logging.error('Could not find path to EasyBuild Root, EasyBuild module must be loaded')
            sys.exit(1)
        else:
            self.base_paths.append(os.path.join(eb_root, 'easybuild/easyconfigs'))
        logging.debug('easyconfig search paths: {}'.format(self.base_paths))

    def find_easyconfig(self, name, easyconfigs):
        """ search base_paths for easyconfig filename """
        found = None
        first_letter = easyconfigs[0][0].lower()
        for easyconfig in easyconfigs:
            for ec_dir in self.base_paths:
                narrow = ec_dir + '/' + first_letter + '/' + name
                logging.debug('find_easyconfig: search for {} in {} '.format(easyconfig, narrow))
                for r,d,f in os.walk(narrow):
                    for filename in f:
                        if filename == easyconfig:
                            found = os.path.join(r,filename)
                            return found
        return None

    def build_dep_filename(self, dep):
        """build a list of possible filenames from a dependency object.
           This is a Hack for minimal toolchain support
           Only supports foss toolchains
        """
        toolchains = [
            ['fosscuda-2019a', 'foss-2019a', 'GCCcore-8.2.0'],
            ['fosscuda-2019b', 'foss-2019b', 'GCCcore-8.3.0'],
            ['fosscuda-2020a', 'foss-2020a', 'GCCcore-9.3.0', 'GCC-9.3.0', 'gompi-2020a'],
            ['fosscuda-2020b', 'foss-2020b', 'GCCcore-10.2.0', 'GCC-10.2.0', 'gompi-2020b'],
            ['fosscuda-2021a', 'foss-2021a', 'GCCcore-10.3.0', 'GCC-10.3.0', 'gompi-2021a'],
            ['foss-2021b', 'GCCcore-11.2.0', 'GCC-11.2.0', 'gompi-2021b'],
            ['foss-2022a', 'GCCcore-11.3.0', 'GCC-11.3.0', 'gompi-2022a'],
            ['foss-2022b', 'GCCcore-12.2.0', 'GCC-12.2.0', 'gompi-2022b', 'gfbf-2022b'],
            ['foss-2023a', 'GCCcore-12.3.0', 'GCC-12.3.0', 'gompi-2023a', 'gfbf-2023a'],
            ['foss-2023b', 'GCCcore-13.2.0', 'GCC-13.2.0', 'gompi-2023b', 'gfbf-2023b'],
            ['foss-2024a', 'GCCcore-13.3.0', 'GCC-13.3.0', 'gompi-2024a', 'gfbf-2024a'],
        ]
        tc_versions = {
            '8.2.0': toolchains[0], '2019a': toolchains[0],
            '8.3.0': toolchains[1], '2019b': toolchains[1],
            '9.3.0': toolchains[2], '2020a': toolchains[2],
            '10.2.0': toolchains[3], '2020b': toolchains[3],
            '10.3.0': toolchains[4], '2021a': toolchains[4],
            '11.2.0': toolchains[5], '2021b': toolchains[5],
            '11.3.0': toolchains[6], '2022a': toolchains[6],
            '12.2.0': toolchains[7], '2022b': toolchains[7],
            '12.3.0': toolchains[8], '2023a': toolchains[8],
            '13.2.0': toolchains[9], '2023b': toolchains[9],
            '13.3.0': toolchains[10], '2024a': toolchains[10],
        }
        prefix = dep[0] + '-' + dep[1]
        if (len(dep)) == 4 and dep[3] == 'System toolchain':
            dep_filenames = prefix + '.eb'
            return [dep_filenames]
        tc_version = self.toolchain['version']
        if tc_version not in tc_versions:
            ('Could not figure out what toolchain you are using.')
            sys.exit(1)
        dep_filenames = []
        for tc in tc_versions[tc_version]:
            if len(dep) > 2 and dep[2] == 'versionsuffix':
                dep_filenames.append('{}-{}{}.eb'.format(prefix, tc, self.versionsuffix))
            else:
                dep_filenames.append('{}-{}.eb'.format(prefix, tc))
        return dep_filenames

    def search_dependencies(self, dependencies):
        """ inspect dependencies for R and Python easyconfigs,
        if found add the exts_list to the list of dependent
        exts  <dep_exts>
        """
        if self.verbose:
            print('== searching dependencies')
        for dep in dependencies:
            dep_filenames = self.build_dep_filename(dep)
            easyconfig_path = self.find_easyconfig(dep[0], dep_filenames)
            if not easyconfig_path:
                print('== dependency Not Found: {}'.format(dep_filenames[0]))
                continue
            logging.debug('dependency file name: %s', dep_filenames)
            dep_eb = self.parse_eb(str(easyconfig_path), False)
            if self.language == 'Python':
                print(f'== adding deps lang: {self.language} dep: {(os.path.basename(easyconfig_path))}')
                add_to_python_dep_exts(dep_eb, easyconfig_path, self.dep_exts)
            elif self.language == 'R':
                if 'exts_list' in dep_eb.__dict__:
                    self.dep_exts.extend(dep_eb.exts_list)
            if self.verbose:
                print('== adding dependencies: {}'.format(os.path.basename(easyconfig_path)))


    def check_eb_package_name(self, filename):
        """" check that easybuild filename matches package name
        easyconfig is original filename
        """
        eb_name = os.path.basename(filename)[:-3]
        if eb_name != self.modulename:
            logging.info("Warning: file name does not match easybuild module name.")
            logging.info("   file name: %s\n module name: %s", eb_name, self.modulename)

    def write_chunk(self, indx):
        self.out.write(self.code[self.ptr_head:indx])
        # print(f"{self.code[self.ptr_head:indx]}", end='')
        self.ptr_head = indx

    def output_module(self, lang, pkg):
        """write exts_list entry
        """
        output = None
        if lang == 'R':
            output = "%s('%s', '%s')," % (self.indent, pkg['name'], pkg['version'])
        elif lang == 'Python':
            # TODO all the python should should be in UpdatePython
            # from easy_update import UpdatePython # static method
            # UpdatePython.output_module(pkg)
            output = self.python_output_module(pkg)
        return output

    def python_output_module(self, pkg):
        """Python version"""
        pkg_fmt = self.indent + "('{}', '{}', {{\n"
        item_fmt = self.indent + self.indent + "'%s': %s,\n"
        if 'spec' in pkg:
            output = pkg_fmt.format(pkg['name'], pkg['version'])
            for item in pkg['spec'].keys():
                output += item_fmt % (item, pkg['spec'][item])
            output += self.indent + "}),"
        else:
            output = "('{}', '{}),".format(pkg['name'], pkg['version'])
        return output

    def rewrite_extension_name(self, pkg):
        """ rewrite exts_list 'name' without change """
        target = f"'{pkg['name']}', "
        name_index = self.code[self.ptr_head:].find(target)
        if name_index == -1:
            logging.error('No name found for %s', pkg['name'])
            print(f"body: {self.code[self.ptr_head:]}")
            sys.exit(1)
        self.write_chunk(name_index+self.ptr_head+len(target))

    def rewrite_extension(self, pkg):
        """ rewrite exts_list entry without change """
        self.rewrite_extension_name(pkg)
        end_index = self.code[self.ptr_head:].find('),')
        self.write_chunk(self.ptr_head+end_index+3)

    def update_extension(self, pkg):
        """ rewrite exts_list entry with updated version """
        self.rewrite_extension_name(pkg)
    
        version_string = f"'{pkg['orig_version']}'"
        orig_ver_index = self.code[self.ptr_head:].find(version_string)
        if orig_ver_index == -1:
            logging.error('No version found for %s', pkg['name'])
            sys.exit(1)
        new_version = f"'{pkg['version']}'"
        self.out.write(new_version)
        self.ptr_head += len(version_string)
        indx = self.code[self.ptr_head:].find('),') + self.ptr_head + 3
        self.write_chunk(indx)

    def print_update(self, lang, exts_processed):
        """ this needs to be re-written in a Pythonesque manor
        if module name matches extension name then skip
        """
        indx = self.code.find('exts_list = [\n')
        self.write_chunk(indx + 14)

        for extension in exts_processed:
            name = extension['name']
            if 'action' not in extension:
                logging.error('No action for library %s', name)
                sys.exit(1)

            if lang.lower() == lang:
                # special case for bundles, if "name" is used in exts_list
                indx = self.code[self.ptr_head:].find('),') + 2
                indx += self.ptr_head
                self.write_chunk(indx)
            elif extension['from'] == 'base':  # R base library with no version
                indx = self.code[self.ptr_head:].find("'"+name+"'")
                indx += self.ptr_head + len(name) + 3
                self.write_chunk(indx)
            elif extension['action'] == 'keep':
                self.rewrite_extension(extension)
            elif extension['action'] == 'update':
                self.update_extension(extension)
            elif extension['action'] in ['processed', 'duplicate']:
                name_indx = self.code[self.ptr_head:].find(f"'{name}', ")
                name_indx += self.ptr_head + len(name) + 4
                indx = self.code[name_indx:].find('),') + name_indx + 3
                self.ptr_head = indx
                continue
            elif extension['action'] in ['add', 'dep']:
                output = self.output_module(lang, extension)
                self.out.write("%s\n" % output)
        self.out.write(self.code[self.ptr_head:])


if __name__ == '__main__':
    """ create unit test """
    print('none')
