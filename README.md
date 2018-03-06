# Easy Update
**Easy Update** is a tool to help maintain EasyBuild easyconfig files for `Python`, `R` and `R-Bioconductor`.  If you support `R` and `Python` easyconfigs, this tool will automate the process of updating module versions and recursively check for dependent modules.  Easy_update rewrites easyconfig files with updated version information for each module in `exts_list[]`. Easy_update also checks for dependencies recursively and adds any missing dependent modules to `exts_list`.  If you have been maintaining package lists by hand, you will notice that easy_update will reorder your `exts_list` based on the correct dependency hierarchy.

Easy_update writes dependent packages ahead of the parent module.  If dependent packages are found further within `exts_list`, they will will be treated as duplicates and removed.  If you are running easy update for the first time I would suggest that you run it twice to ensure that the modules are in the correct order. 

### Usage
easy_update takes a single argument which is the path to an easyconfig file. The output is written to a new file; with the extension ".update".

<dl>
  <dd><b>Usage:</b> ./easy_update.py Python-2.7.12-foss-2016b.eb</dd>
  <dd><b>Output:</b> Python-2.7.12-foss-2016b.update</dd>
</dl>

**Note:** When using BioConductor modules in easyconfig files the variable ``biocver`` must be set, otherwise
BioConductor will not be searched. **Example** ``biocver = 3.6``.

### Flags

* **--verbose** output the action that will be taken for each module along with the version number.
    Possible actions are 'keep', 'update', 'dep', 'add' or 'duplicate'
    'keep' no changes are needed
    'update' there is a new version available for the package
    'dep' A new package will be added ad the result of finding dependencies
    'add' Packages added via the --add argument
    'duplicate'  A duplicate package name has been found

* **--add** [filename]  Add additional modules to be added the easyconfig file.
    Place a single module name on each line of the file. Version numbers are not required.

* **--search** [modulename] Search is used to lookup a single module as an argument.  Search does not read or write to a file. Dependencies will be output if found. This is handy for checking new packages.
Search requires the command line arguments; --pyver or --rver and --biocver to determine which repository to search.

* **--meta** Display all metadata available from a repository.  The output is very verbose and should be used for debugging purposes. The output is written to stdout.

* **--pyver**  Only use in conjunction with search.  Specify only the major minor version numbers; --pyver 3.6.

* **--rver, --biocver** Only use in conjunction with search.  Specify only the major minor version numbers

### Note
Easy Update makes many asumptions about the format of the easyconfig file. If only and update is being made the original text is preserved and only the version number is updated.  If a new package needs to be added then it is written using these conventions. All output is indented 4 spaces. Python easyconfigs are output in a multi line format.
```
    ('pep8', '1.7.1', {
        'source_urls': ['https://pypi.python.org/packages/source/p/pep8/'],
    }),
    ('ndg-httpsclient', '0.4.4', {
         'modulename': 'ndg.httpsclient',
         'source_urls': ['https://pypi.python.org/packages/source/n/ndg-httpsclient'],
         'source_tmpl': 'ndg_httpsclient-0.4.4.tar.gz',
    }),
```
R modules are writte in a single line.  It is asumed that `ext_options` and `bioconductor_options` are defined outside of the `ext_list` declaration.
```
    ('packrat', '0.4.8-1', ext_options),
    ('PKI', '0.1-5.1', ext_options),
    ('rsconnect', '0.8.5', ext_options),
    ('zlibbioc', '1.24.0', bioconductor_options),
    ('BiocGenerics', '0.24.0', bioconductor_options),
```

### TODO
Accept arguments to update the ``--version``, ``--versionsuffix`` and ``--toolchain``. Write a new easyconfig with the updated content and updated version information.
