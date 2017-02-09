# easy_update
If you support R and Python easyconfigs, this tool will automate the process of updating module versions and recursively check for dependent modules. Easy_update is a tool to help maintain EasyBuild easyconfig files for Python, R and R-Bioconductor. Easy_update rewrites easyconfig files with updated version information for each module in exts_list[]. Easy_update also checks for dependencies recursively and adds any missing dependent modules to exts_list.  If you have been maintaining package lists by hand, you will notice that easy_update will reorder your exts_list based on the correct dependency hierarchy. 

Easy_update will give a warning if the filename does not match the version and name in the easyconfig file.  A warning message is written if a package can not be found on PyPI, CRAN or Bioconductor. Easy_update does not follow source_urls which are not standard package repositories.  Easy_update can only be as good as the information that is provided from the repositories.

### Usage
easy_update takes a single argument which is the path to an easyconfig file.  A new easyconfig file is written to a filename based on the  easyconfig package name with ".update" file extension.

~~
./easy_update.py Python-2.7.12-foss-2016b.eb
~~

### Flags
Add flags to end of the command.

> easy_update.py Python-2.7.12-foss-2016b.eb **--verbose**
> **--verbose** output status of every module to standard out
> **--add [filename]**   Add additional modules to the updated easyconfig file. Place a single module name on each line of the file. Version numbers are not required.

### TODO
Accept arguments to update the ``--version``, ``--versionsuffix`` and ``--toolchain``. Write a new easyconfig with the updated content and updated version information.
