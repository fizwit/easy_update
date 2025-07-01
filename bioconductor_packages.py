#!/usr/bin/env python3

import sys
import requests
import re
import logging
import json

logging.basicConfig(format='%(message)s',
                    level=logging.INFO)


class Bioconductor_packages:
    """
    Download and Parse Bioconductor package data into a dictionary.

    Args: Bionconductor version

    creates a dictionary with package names as keys and package details as values
    bioc_data['pkg']['Depends', 'Imports', 'LinkingTo', 'Biobase', 'graphics', 'URL']

    function get_bioc_package(pkg) is used by updateR.py to get package metadata
    from Bioconductor.
    """
    def __init__(self, biocver, verbose):
        """Initialize Bioconductor packages with the specified version.
            if biocver is None, no Bioconductor data is loaded.
            else check version of biocver and download the PACKAGES file
        """
        self.verbose = verbose
        self.bioc_data = {}
        if biocver is None:
            return
        if biocver not in ['3.20', '3.21', '3.22', '3.23', '3.24', '3.25']:
            print(f'Bioconductor version {biocver} is not supported.')
            sys.exit(1)
        self.biocver = biocver
        source_urls = [
            ('Software', f'https://bioconductor.org/packages/{biocver}/bioc/'),
            ('Annotation', f'https://bioconductor.org/packages/{biocver}/data/annotation/'),
            ('Experiment', f'https://bioconductor.org/packages/{biocver}/data/experiment/'),
        ]
        for view, url in source_urls:
            response = requests.get(url + 'src/contrib/PACKAGES', timeout=10)
            if response.status_code < 200 or response.status_code > 299:
                logging.error('get URL error: %s %s', response.status_code, url)
                sys.exit(1)
            self.parse_packages(view, response.text)
            if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
                self.bioc_stats()
            self.read_bioconductor_json(view, url)

    def get_bioc_package(self, pkg):
        """Extract Dependencies from BioCondutor json metadata
        inputs: pkg dictionary with 'name' and 'meta' keys
        Example:
        bioc_data['pkg']['Depends']
                    [u'R (>= 2.10)', u'BiocGenerics (>= 0.3.2)', u'utils']
        interesting fields from BioCoductor:
        """
        package_name = pkg['name']
        pkg['meta'] = {}
        pkg['meta']['requires'] = []
        if package_name in self.bioc_data:
            if 'Version' not in self.bioc_data[package_name]:
                print(f'Package {package_name} not found in Bioconductor data.')
                return "not found"
            if self.bioc_data[pkg['name']]['Version'] != pkg['version']:
                pkg['orig_version'] = pkg['version']
                pkg['version'] = self.bioc_data[package_name]['Version']
            else:
                pkg['orig_version'] = None
            for dep_type in ['Imports', 'Depends', 'LinkingTo']:
                if dep_type in self.bioc_data[package_name]:
                    for dep in self.bioc_data[package_name][dep_type]:
                        pkg['meta']['requires'].append([dep['name'], dep_type])
            if 'Title' in self.bioc_data[pkg['name']]:
                pkg['Title'] = self.bioc_data[pkg['name']]['Title']
        else:
            return "not found"
        return 'ok'

    def bioc_stats(self):
        """
            Return the number of packages in the Bioconductor repository
        """
        print(f' Number of bioconductor packages: {len(self.bioc_data)}')
        key_fields = {}
        status_types = ['package', 'archived', 'deprecated']
        for pkg_name, pkg_dict in self.bioc_data.items():
            for key, value in pkg_dict.items():
                if key in key_fields:
                    key_fields[key] += 1
                else:
                    key_fields[key] = 1
                if key == 'Status':
                    if value in status_types:
                        tag = 'Status.' + value
                        if tag not in key_fields:
                            key_fields[tag] = 1
                        else:
                            key_fields[tag] += 1                    
        print(f' Number of fields: {len(key_fields)}')
        for key, val in key_fields.items():
            print(f' {key}: {val}')

    def parse_packages(self, view, content):
        """
        Parse the PACKAGES file content into a dictionary.
        Args:
            view: The type of Bioconductor package (e.g., 'Software', 'Annotation', 'Experiment').
            content: The content of the PACKAGES file as a string.
        Returns:
            None, but populates self.bioc_data with package information.
        """
        packages = content.split('\n\n')
        for package in packages:
            current_key = None
            current_value = []
            lines = package.splitlines()

            # Initialize a dictionary for this package
            package_info = {}
            for line in lines:
                match = re.match(r'^([A-Za-z0-9]+):\s*(.*)', line)

                if match:
                    if match.group(1) == 'Package':
                        package_name = match.group(2)
                        package_info['Package'] = package_name
                        continue
                    elif match.group(1) == 'Version':
                        package_info['Version'] = match.group(2)
                        continue
                    # Save the previous field
                    elif current_key:
                        package_info[current_key] = ' '.join(current_value).strip()
                    current_key = match.group(1)
                    current_value = [match.group(2)]
                elif line.startswith(' ') and current_key:
                    # Continuation of previous field
                    current_value.append(line.strip())
                    continue
            # fix 'Imports', 'Depends', 'Suggests', 'Enhances', 'LinkingTo', 'Depends_list'
            for key in ['Imports', 'Depends', 'LinkingTo']:
                if key in package_info:
                    package_info[key] = self.parse_dependency_list(package_info[key])
            package_info['View'] = view
            package_info['Status'] = 'package'
            self.bioc_data[package_name] = package_info

    def parse_dependency_list(self, dependency_string):
        """
        Parse a dependency string into a list of dictionaries with package names and versions.

        Args:
            dependency_string: A string like "R (>= 3.5.0), gdsfmt (>= 1.36.0), methods"

        Returns:
           List of dictionaries with keys 'name' and 'version' (if specified)
        """
        if not dependency_string:
            return []

        result = []

        # Split by commas, but avoid splitting inside parentheses
        deps = re.findall(r'([^,]+(?:\([^)]*\))?)', dependency_string)

        for dep in deps:
            dep = dep.strip()
            if not dep:
                continue

            # Extract package name and version requirement
            version_match = re.match(r'([A-Za-z0-9.]+)\s*(\([^)]+\))?', dep)

            if version_match:
                dep_name = version_match.group(1).strip()
                dep_version = version_match.group(2)

                dep_info = {'name': dep_name}

                if dep_version:
                    # Clean up the version string removing parentheses
                    dep_version = dep_version.strip('()')
                    dep_info['version'] = dep_version

                result.append(dep_info)

        return result

    def add_JSON_package(self, pkg):
        """ Add JSON package to the Bioconductor dictionary
        """
        name = pkg['Package']
        self.bioc_data[name] = {}
        self.bioc_data[name]['Package'] = name
        self.bioc_data[name]['Version'] = pkg['Version']
        self.bioc_data[name]['Title'] = pkg['Title']
        self.bioc_data[name]['Description'] = pkg['Description']
        package_info = {}
        for dep_type in ['Imports', 'Depends', 'LinkingTo']:
            if dep_type in pkg:
                depenancy_string = ', '.join(pkg[dep_type])
                package_info[dep_type] = self.parse_dependency_list(depenancy_string)
        self.bioc_data[name].update(package_info)

    def check_archive(self, view, pkg):
        """ Check if the package is in the Bioconductor archive
        """
        #  print(f'Checking archive for package: {pkg}')
        bioc_archive = f'https://bioconductor.org/packages/release/bioc/html/{pkg["Package"]}.html'
        response = requests.get(bioc_archive, timeout=10)
        if response.status_code < 200 or response.status_code >= 300:
            pkg['Status'] = 'archived'
            logging.info('%s while checking archive for: %s from view: %s', response.status_code, pkg['Package'], view)
        elif 'This package has been removed from Bioconductor.' in response.text:
            pkg['Status'] = 'deprecated'

    def read_bioconductor_json(self, view, url):
        """ Download the Bioconductor JSON data
        The JSON can be out of date, so we use the PACKAGES file for the most current 'Version'
        The JSON data has Title and Description
        'Title' is used by easy_annotate to display the package description
        """
        json_data = {}
        #  packages: https://bioconductor.org/packages/{biocver}/bioc/PACKAGES',
        #  json      https://bioconductor.org/packages/json/{biocver} + '/bioc/packages.json'
        bioc_url = url.replace('packages', 'packages/json') + 'packages.json'
        response = requests.get(bioc_url, timeout=10)
        if response.status_code < 200 or response.status_code >= 300:
            logging.error('%s while downloading: %s', response.status_code, bioc_url)
            sys.exit(1)
        json_data.update(response.json())
        pkgcount = len(json_data.keys())
        mesg_index = bioc_url.find(self.biocver) + len(self.biocver) + 1
        if self.verbose:
            print(f' == downloading Bioconductor {bioc_url[mesg_index:]} - Package Count: {pkgcount}')
        for pkg_name, pkg_dict in json_data.items():
            if pkg_name in self.bioc_data:
                if 'Title' in json_data[pkg_name]:
                    self.bioc_data[pkg_name]['Title'] = json_data[pkg_name]['Title']
                if 'Description' in json_data[pkg_name]:
                    self.bioc_data[pkg_name]['Description'] = json_data[pkg_name]['Description']
            else:
                self.check_archive(view, json_data[pkg_name])

    def write_bioc_json(self, filename):
        """ Write the Bioconductor data to a JSON file
        This is useful for debugging and testing.
        """
        with open(filename, 'w') as f:
            json.dump(self.bioc_data, f, indent=4)
        f.close()


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s [%(filename)s:%(lineno)-4d] %(message)s',
                    level=logging.DEBUG)
    logging.basicConfig(format='%(message)s', level=logging.INFO)
    biocver = '3.21'    
    bioc = Bioconductor_packages(biocver, verbose=True)
    #  bioc.write_bioc_json('bioconductor_packages.json')

    test_packages = [
        {'name': 'scater', 'version': '1.20.0'},
        {'name': 'BiocHail', 'version': '1'},
        {'name': 'BiocGenerics', 'version': '0.44.0'},
        {'name': 'TxDb.Hsapiens.UCSC.hg19.knownGene', 'version': '3.2.2'},
    ]
    for pkg in test_packages:
        print(f" == Checking package: {pkg['name']} version {pkg['version']}")
        pkg['meta'] = {}
        pkg['orig_version'] = None
        pkg['version'] = pkg['version'].strip()
        if not re.match(r'^\d+(\.\d+)*$', pkg['version']):
            print(f"Invalid version format for package {pkg['name']}: {pkg['version']}")
            continue
        status = bioc.get_bioc_package(pkg)
        if status == 'ok':
            print(f"  - Package {pkg['name']} found with version {pkg['version']}")
            print(f"  - Requires: {pkg['meta']['requires']}")
        else:
            print(f"Package {pkg['name']} not found in Bioconductor data.")
    bioc.bioc_stats()
    bioc.write_bioc_json(f'bioconductor_packages-{biocver}.json')