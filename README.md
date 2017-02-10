# easy_update
If you support `R` and `Python` easyconfigs, this tool will automate the process of updating module versions and recursively check for dependent modules.
`Easy_update` is a tool to help maintain EasyBuild easyconfig files for
`Python`, `R` and `R-Bioconductor`. Easy_update rewrites easyconfig files with
updated version information for each module in `exts_list[]`. Easy_update also
checks for dependencies recursively and adds any missing dependent modules to
`exts_list`.  If you have been maintaining package lists by hand, you will
notice that easy_update will reorder your `exts_list` based on the correct
dependency hierarchy.

Easy_update writes dependent packages ahead of the parent module.  If dependent
packages are found further within `exts_list`, they will be treated as duplicate modules and removed.

### Usage
easy_update takes a single argument which is the path to an easyconfig file.  A new easyconfig file is written to a filename based on the  easyconfig package name with ".update" file extension.


``./easy_update.py Python-2.7.12-foss-2016b.eb``

### Flags
Add flags to the end of the command: ``easy_update.py Python-2.7.12-foss-2016b.eb --verbose``


```
--verbose output the action that will be taken for each module along with the version number.
    Possible actions are 'keep', 'update', 'new' or 'duplicate'
    'keep' no changes need to be made to the package
    'update' there is a new version available for the package
    'new' A new package will be added. This is the result of finding dependencies.
    'duplicate'  A duplicate package name has been found.

```
```
--add [filename]  Add additional modules to the updated easyconfig file.
    Place a single module name on each line of the file. Version numbers are not required.
```

### TODO
Accept arguments to update the ``--version``, ``--versionsuffix`` and ``--toolchain``. Write a new easyconfig with the updated content and updated version information.
