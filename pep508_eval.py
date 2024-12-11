#!/usr/bin/env python

import sys
import platform
from packaging import specifiers
import os
from pep508_parser import parser


class Pep508_eval():
    """ Evaluate PEP 508 environment markers from the pep508_parser.
        The pep508 markers are procesed from the 'requires_dist' provided by PyPi.
    """
    def __init__(self) -> None:
        self.environment = {}
        self.set_enviroment_variables()

    def format_full_version(self, info):
        impl_version = '{0.major}.{0.minor}.{0.micro}'.format(info)
        kind = info.releaselevel
        if kind != 'final':
            impl_version += kind[0] + str(info.serial)
        return impl_version

    def set_enviroment_variables(self):
        environment = {
            'os_name': os.name,
            'sys_platform': sys.platform,
            'platform_machine': platform.machine(),
            'platform_python_implementation': platform.python_implementation(),
            'platform_release': platform.release(),
            'platform_system': platform.system(),
            'platform_version': platform.version(),
            'python_version': '.'.join(platform.python_version_tuple()[:2]),
            'python_full_version': platform.python_version(),
            'implementation_name': sys.implementation.name,
        }
        if hasattr(sys, 'implementation'):
            environment['implementation_version'] = self.format_full_version(sys.implementation.version)
        else:
            environment['implementation_version'] = "0"
        globals().update(environment)

    def set_dependency_variables(self):
        """ add list of name = version variables to support dependency 
            checking in the environment markers.
            example: numpy = 1.20.3, pytest-freezer = 0.4.8 etc...
        """
        pass

    def evaluate_version_specifier(spec_tuple, package_version):
        """ Evaluate a version specifier tuple. Can optionally be called from eval_508 if
            the <package_version> is provided.
            return: True if the package version satisfies the specifier, False otherwise.
            This code is intionally not used in the current implementation.
        """
        operator, version_str = spec_tuple
        spec = specifiers.SpecifierSet(f"{operator}{version_str}")
        return spec.contains(package_version)

    def eval_508(self, expr, package_version=None):
        """ Recursively evaluate the parsed expression.
            return: True if the expression is True, False otherwise
        """
        if isinstance(expr, tuple):
            if len(expr) == 4:  # Handle the 4-element tuple from pep508_parser
                package_name, version_spec, extras, env_markers = expr
                if env_markers:
                    env_result = self.eval_508(env_markers)
                else:
                    env_result = True  # No environment markers
                return env_result

            operator = expr[0]
            if operator == 'and':
                return all(self.eval_508(sub_expr) for sub_expr in expr[1:])
            elif operator == 'or':
                return any(self.eval_508(sub_expr) for sub_expr in expr[1:])
            elif operator == '==':
                left, right = expr[1], expr[2]
                return self.environment.get(left, left) == self.environment.get(right, right)
            elif operator == '!=':
                left, right = expr[1], expr[2]
                return self.environment.get(left, left) != self.environment.get(right, right)
            elif operator in ('>', '<', '>=', '<=', '~='):
                left, right = expr[1], expr[2]
                left_value = self.environment.get(left, left)
                right_value = self.environment.get(right, right)

                # Create a SpecifierSet for the comparison
                spec = specifiers.SpecifierSet(f"{operator}{right_value}")

                # Check if the left value satisfies the specifier
                return spec.contains(left_value)
                # Add other operators as needed
        else:
            return expr  # For simple boolean values


def main():
    """ Test the evaluation of the parsed requirements when run from the command line.
    """
    tests = [
        ('importlib_metadata',
         ['zipp>=0.5', 'typing-extensions>=3.6.4; python_version < "3.8"',
          'sphinx>=3.5; extra == "doc"', 'jaraco.packaging>=9.3; extra == "doc"', 'rst.linker>=1.9; extra == "doc"',
          'furo; extra == "doc"', 'sphinx-lint; extra == "doc"', 'jaraco.tidelift>=1.4; extra == "doc"', 
          'ipython; extra == "perf"', 'pytest!=8.1.*,>=6; extra == "test"', 'pytest-checkdocs>=2.4; extra == "test"',
          'pytest-cov; extra == "test"', 'pytest-mypy; extra == "test"', 'pytest-enabler>=2.2; extra == "test"',
          'pytest-ruff>=0.2.1; extra == "test"', 'packaging; extra == "test"', 'pyfakefs; extra == "test"',
          'flufl.flake8; extra == "test"', 'pytest-perf>=0.9.2; extra == "test"', 'jaraco.test>=5.4; extra == "test"',
          'importlib-resources>=1.3; python_version < "3.9" and extra == "test"']),
        ('keyring',
         ['jaraco.classes', 'jaraco.functools', 'jaraco.context', 'importlib-metadata>=4.11.4; python_version < "3.12"',
          'importlib-resources; python_version < "3.9"', 'SecretStorage>=3.2; sys_platform == "linux"',
          'jeepney>=0.4.2; sys_platform == "linux"', 'pywin32-ctypes>=0.2.0; sys_platform == "win32"',
          'shtab>=1.1.0; extra == "completion"', 'sphinx>=3.5; extra == "docs"', 'jaraco.packaging>=9.3; extra == "docs"',
          'rst.linker>=1.9; extra == "docs"', 'furo; extra == "docs"', 'sphinx-lint; extra == "docs"',
          'jaraco.tidelift>=1.4; extra == "docs"', 'pytest!=8.1.*,>=6; extra == "testing"',
          'pytest-checkdocs>=2.4; extra == "testing"', 'pytest-cov; extra == "testing"', 'pytest-mypy; '
          'extra == "testing"', 'pytest-enabler>=2.2; extra == "testing"', 'pytest-ruff>=0.2.1; extra == "testing"']),
    ]

    pep508 = Pep508_eval()

    for (pkg, requires_dist) in tests:
        print(f' == {pkg} requires: {requires_dist}')
        for req in requires_dist:
            try:
                parsed = parser.parse(req)
            except Exception as e:
                print(f' ** Parse error: {req} -> {e}')
                continue
            pkg_name = parsed[0]
            if pep508.eval_508(parsed):
                print(f' == add require: {pkg_name} {req} -> True')
            else:
                print(f' == add require: {pkg_name} {req} -> False')
    return 0


if __name__ == '__main__':
    main()
    print('Done')
