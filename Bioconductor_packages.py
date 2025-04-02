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

    Returns: Dictionary with package names as keys and package details as values
    bioc_data['pkg']['Depends', 'Imports', 'LinkingTo', 'Biobase', 'graphics', 'URL']

    """
    def __init__(self, biocver):
        self.bioc_data = {}
        url = f'https://bioconductor.org/packages/{biocver}/bioc/src/contrib/PACKAGES'
        response = requests.get(url)
        if response.status_code < 200 or response.status_code > 299:
            print('error')
            sys.exit(1)
        self.parse_packages(response.text)
        if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
            self.bioc_stats()
        self.read_bioconductor_JSON(biocver)

    def get_bioc_package(self, pkg):
        """Extract Dependencies from BioCondutor json metadata
        inputs: pkg dictionary with 'name' and 'meta' keys
        Example:
        bioc_data['pkg']['Depends']
                    [u'R (>= 2.10)', u'BiocGenerics (>= 0.3.2)', u'utils']
        interesting fields from BioCoductor:
        """
        status = 'ok'
        package_name = pkg['name']
        pkg['meta'] = {}
        pkg['meta']['requires'] = []
        if package_name in self.bioc_data:
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
            status = "not found"
        return status

    def bioc_stats(self):
        """Return the number of packages in the Bioconductor repository"""
        print(f' Number of bioconductor packages: {len(self.bioc_data)}')
        key_fields = {}
        for pkg in self.bioc_data.keys():
            for key in self.bioc_data[pkg].keys():
                if key in key_fields:
                    key_fields[key] += 1
                else:
                    key_fields[key] = 1
        print(f' Number of fields: {len(key_fields)}')
        for key in key_fields.keys():
            print(f' {key}: {key_fields[key]}')

    def parse_packages(self, content):
        packages = content.split("\n\n")
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

            # fix 'Imports', 'Depends', 'Suggests', 'Enhances', 'LinkingTo', 'Depends_list'
            for key in ['Imports', 'Depends', 'LinkingTo']:
                if key in package_info:
                    package_info[key] = self.parse_dependency_list(package_info[key])
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

    def add_JSSNON_package(self, pkg):
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

    def read_bioconductor_JSON(self, biocver):
        """ Download the Bioconductor JSON data
        The JSON can be out of date, so we use the PACKAGES file for the most current 'Version'
        The JSON data has Title and Description
        'Title' is used by easy_annotate to display the package description
        """
        json_data = {}
        base_url = f'https://bioconductor.org/packages/json/{biocver}'
        bioc_urls = ['%s/bioc/packages.json' % base_url]
        for url in bioc_urls:
            resp = requests.get(url)
            if resp.status_code < 200 or resp.status_code >= 300:
                logging.error('%s while downloading: %s', resp.status_code, url)
                sys.exit(1)
            json_data.update(resp.json())
            pkgcount = len(json_data.keys())
        logging.debug('Bioconductor JSON number of packages: %s', pkgcount)
        for pkg in json_data.keys():
            if pkg in self.bioc_data:
                if 'Title' in json_data[pkg]:
                    self.bioc_data[pkg]['Title'] = json_data[pkg]['Title']
                if 'Description' in json_data[pkg]:
                    self.bioc_data[pkg]['Description'] = json_data[pkg]['Description']
            else:
                logging.info('Package %s not found in Bioconductor PACKAGES file', pkg)
                self.add_JSSNON_package(json_data[pkg])

if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s [%(filename)s:%(lineno)-4d] %(message)s',
                    level=logging.DEBUG)
    logging.basicConfig(format='%(message)s', level=logging.INFO)
    
    bioc = Bioconductor_packages('3.20')
    pkg = {'name': 'scater', 'version': '1.20.0'}
    STATUS = bioc.get_bioc_package(pkg)
    if STATUS == 'ok':
        print(f"Package found: {pkg['name']}")
        print(f"Package: {json.dumps(pkg, indent=4)}")
    pkg = {'name': 'BiocHail', 'version': '1'}
    STATUS = bioc.get_bioc_package(pkg)
    if STATUS == 'ok':
        print(f"Package found: {pkg['name']}")
        print(f"Package: {json.dumps(pkg, indent=4)}")
