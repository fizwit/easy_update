# easy_update Release Notes

### 2.2.3 refactor command line arguments one more time.

  - `--exts-update` will detect language (R or Python)
  - remove `--exts-update-r` and `--exts-update-python`
  - Refactor arg-parse to use subparsers.  This will allow for more options in the future.
    continue to improve Python dependency checking.  The PEP508 parser is used to evaluate 
    the output of the parser.  This is used to check for Python dependencies. 
    rename pep_508 to pep508_eval to be more descriptive. PyPi already has a module named pep_508

### 2.2.2 refactor pypi_requires_dist to use pep508 pareser
    This will allow for much more
    reliable parsing of package dependencies.  The pep508 parser is used to evaluate the
    output of the parser.

    pkg['meta']['requires'] is a list of lists.  The first element is the package name
    and the second element is the type of dependency.  This is used to track where the
    package was requested from.  This is useful when updating packages.  The package
    name is used to search for the package in the exts_list.  The type of dependency
    is used to determine if the package is a 'Depends', 'Imports', or 'LinkingTo' type.

    Command line flags have changed to use '--exts-' as a prefix. The use of '--update' is
    over used. Need to explicitly request the type of update; --exts-update-r or --exts-update-python
    this might change again after integrating the EB framework.

    Updating Python is still very broken.  Should update to use pyproject.toml. 

### 2.2.1 Sept 2021 
  - Explicitly request type of update via cli flags: `--update_python_exts`, `--update_R_exts`
    remove detect_language() from framework
    Pillow ~= pillow
    Was only implemented for R, and the Python side was broken. 

### 2.2.0 Aug 11, 2020
  - Dig deep to find all dependent Python libraries. Every dependency needs to be checked
 to determine if it contains Python modules. Inspect every dependency for PythonBundle or PythonPackage,
 easyblock type.

### 2.1.5 July 8, 2021 - fix bug in find_easyconfig_paths
   Add additonal headers 'SOURCE_WHL',  'SOURCE_PY3_WHL'; from caspar@SURFsara

### 2.1.4 May 20, 2021 - remove requirment for local_biocver. Issue a warning if local_biocver is
                     not set.
### 2.1.3 Feb 3, 2021 - bug Fix
      AttributeError: 'FrameWork' object has no attribute 'base_path'

### 2.1.2 Jan 28, 2021 - support constant OS_PKG_OPENSSL_DEV

### 2.1.1 Jan 6, 2021 - clean up requirements.txt with pigar

### 2.1.0 Nov 22, 2020 - Major changes to framework. See framework.py for more details.

### 2.0.8.10 July 29 minor bug fixes

### 2.0.8.9 July 6, 2020 CNVkit, dependencies on both R and Python. fix bug so easy_update could
        not determine language of exts_list. Fix base_path to find to of easyconfig
        directory tree. Did not reconize R-bundel-Bioconductor as an R depenency, fixed.
### 2.0.8.8 June 9, 2020 fix R package dependency lookups. Support for "local_biocver"

### 2.0.8.7 Jan 26, 2020 Fix multi file dependency to support bundles

### 2.0.8.6 Oct 1, 2019 PR #17 merged from ccoulombe

    R modules are not necessarily installed with extensions. Fix the AttributeError when
    the R EasyConfig file does not contains exts_list.

    PR #18 from ccoulombe  - Using importlib.util.module_from_spec(None) is not possible,
    therefore using types.ModuleType() is the solution.


### 2.0.8.5 Oct 1, 2019 Bug Fix: File "./easy_update.py", line 105, in __init__
    UpdateExts.__init__(self, args, eb)
  File "updateexts.py", line 91, in __init__
    if eb.dep_exts:
AttributeError: 'NoneType' object has no attribute 'dep_exts'

### 2.0.8.4 Sept 26, 2019 Bug Fix: File "./easy_update.py", line 378, in get_pypi_release
    for ver in project['releases'][new_version]:
    NameError: name 'new_version' is not defined

### 2.0.8.3 Sept 25, 2019 Bug Fix: File "updateexts.py", line 91, in __init__
    if eb.dep_exts:
    AttributeError: 'NoneType' object has no attribute 'dep_exts'
AttributeError: 'NoneType' object has no attribute 'dep_exts'

### 2.0.8.2 Sept 20, 2019 - more bug fixes for --search.  Fixed dependency issues
    when checking agaist easyconfigs with the search feature.

### 2.0.8.1 Sep 18, 2019 Bug fix - output_module was broken when framework was
    seperated from updateexts

### 2.0.8 Sep 13, 2019 refactor pypi_requires_dist. Use the Marker tool
    pkg_resources to check Python dependencies.
    keep track of package dependencies and display from which dist a package was requested
    use with --verbose and Python:  Example verbose output

```
              R.methodsS3 : 1.7.1                           (keep) [692, 226]
                     R.oo : 1.22.0                          (keep) [692, 227]
                 jsonlite : 1.6 from httr                    (add) [692, 228]
                      sys : 3.3 from askpass                 (add) [692, 229]
                  askpass : 1.1 from openssl                 (add) [692, 230]
                  openssl : 1.4.1 from httr                  (add) [692, 231]
                     httr : 1.4.1 from cgdsr                 (add) [692, 232]
                    cgdsr : 1.2.10 -> 1.3.0               (update) [692, 233]
                  R.utils : 2.8.0 -> 2.9.0                (update) [692, 234]
                 R.matlab : 3.6.2                           (keep) [692, 235]
                gridExtra : 2.3                             (keep) [692, 236]
                      gbm : 2.1.5                           (keep) [692, 237]
                  Formula : 1.2-3                           (keep) [692, 238]
```
  - option --tree had been removed, the new "from" tracking is better.

### 2.0.7 Aug 15, 2019 framework is a module, remove from this file. Update
    to use new features of Framwork which were added to support easy_annotate.

### 2.0.6 July 9, 2019 easy_anotate read dependinces, add framework, pep8 issues

### 2.0.5 July 8, 2019 Only one flag for debugging metadata '--meta'.
    Used with --verbose all Metadata is output from Pypi. Try to fix package
    counter. Why was R Bioconductor broken?
### 2.0.4 Python issues, fixed bugs, but still not perfect

### 2.0.3 more issues with Pypi

### 2.0.2 fixed issue: could not open easyconfig if it was not in the present
   working directory.

### 2.0.1 2019.03.08 improve parse_pypi_requires to remove 'dev', 'tests' and
   'docs' related dependencies. Dependencies for pytest when fom 173 packages
   to 27. --Meta and --tree have been added as options to help with debugging
   Python dependencies.

### 2.0.0 2019-02-26 New feature to resolve dependent packages
   for R and Python bundles. Read exts_list for R and Python listed in
    dependencies. Refactor code into Two major classes: FrameWork and
    UpdateExts. Rename subclasses for for R and Python: UpdateR UpdatePython.
    This will help with migration into the EB FrameWork.
    Fix bug with pkg_update counter

### 1.3.2 2018-12-19 follow "LinkingTo" for BioConductor packages
   reported by Maxime Boissonneault

### 1.3.1 2018-11-28 fix bugs with pypi
  easy_update was adding incorrect package names from requests_dist.
  Verify package names and update easyconfig with name corrections.
  Package names from pypi.requests_dist are not always correct.
  Pypi Project names do not match package names
```
   ipython-genutils -> ipython_genutils
   jupyter-core -> jupyter_core
   ipython-genutils -> ipython_genutils
   pyncacl -> PyNaCl
```


## updateexts.py

### 2.0.1 2019.03.08
Improve parse_pypi_requires to remove 'dev', 'tests' and
   'docs' related dependencies. Dependencies for pytest when fom 173 packages
   to 27. --Meta and --tree have been added as options to help with debugging
   Python dependencies.

### 2.0.0 2019-02-26
  
  New feature to resolve dependent packages
   for R and Python bundles. Read exts_list for R and Python listed in
    dependencies. Refactor code into Two major classes: FrameWork and
    UpdateExts. Rename subclasses for for R and Python: UpdateR UpdatePython.
    This will help with migration into the EB FrameWork.
    Fix bug with pkg_update counter

### 1.3.0 July 2018
  * update to use pypi.org JSON API
  ```
  Project API:  GET /pypi/<project_name>/json
  Release API: GET /pypi/<project_name>/<version>/json
  ```

# framework.py

### 1.0.6 2.28.2025 - 1.0.6
    * replace find(name) with find("'"+name+"'") to avoid finding substrings
    
    
### 1.0.5 11.10.2024 
  * Add back in the ability to read the EasyConfig file to determine the language.
  * Enable the "description" feature

### 1.0.4 01.11.2022
  * no long try to guess the language by reading the EasyConfig. Lang must be speicified as a command line argument.
  * remove "detect_language"
  * only call "framework" if an EasyConfig needs updating
  * Add  "templates.py" from EasyBuild Framework

### 1.0.3 16.12.2020  (Beethoven's 250th birthday)
  *  R does not have an easyblock, so don't check for one.

###  1.0.2  21.11.2020
  * Fix issue with not being able to read Python dependancies for minimal toolchain. Python-3.7.3-foss-2019b.eb should be Python-3.7.4-GCCcore-8.3.0.eb

  * Require EasyBuild to be loaded. Use "eb" path to find easybuild/easyconfigs

    <find_easyconfig> now supports a list of paths, $PWD plus EasyBuild easyconfig path
    search easyconfig asumes slphabet soup of directory names.
    ie: SciPy-bundle-2020.06-foss-2020a-Python-3.8.2.eb will be search for in the directory: s/SciPy-bundle
    <build_dep_filename> now supports a list of file names based on minimal toolchain

    add logging.debug()

### 1.0.1  15.08.2019
    fix search_dependencies
    For the case of reading Python dependancies, conver the
    case of 'Biopython-1.74-foss-2016b-Python-3.7.4'
    Search dependcies for versionsuffix == '-Python-%(pyver)s'
    add dep_exts are exts_list from dependent packages

    - remove the variable dep_eb
    - All to resolve dependancie in the FrameWork, FrameWork only
      needs a single argument. It had three.

### 1.0.0 07.08.2019
    framework.py becomes seperate package. Share code
    between easy_update and easy_annotate

  * Read exts_list for R and Python listed in dependencies.
