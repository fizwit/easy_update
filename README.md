# easy_update
easy_update is a tool to help maintain EasyBuild easyconfig files for Python, R and Bioconductor. Easy_update updates the versions of each module from the ext_list of easyconfig files. Native API calls are used for each language to check for new versions of packages. Easy_update also checks for dependencies recursively and adds any missing dependent modules to the ext_list. If you support R and Python easyconfigs with hundreds of modules this tool will save you many hours of work. If you have been maintaining package lists by had easy_build my re-order your exts_list based on the correct decency chain. 

### Usage
easy_update takes a single argument which is the path to an easyconfig
file.  A new easyconfig is written written to the same filename with the file extension of .update

~~~
./easy_build.py Python-2.7.12-foss-2016b --verbose
~~~
Flags
* --verbose output status of every module to standard out
* --add <filename>  Add additional modules to the updated easyconfig file. Place a single module name on each line of the file. Version numbers are not required.

### TODO
Accept arguments to update the --version, --versionsuffix and --toolchain. Write a new easyconfig with the updated content and version information.  
