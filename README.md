# easy_update
Update EasyBuild package configuration files for R and Python bundles

R and Python EasyBuild configurations can have a large number of modules defined with
exts_list.  easy_update will check and update software speicfied in EasyBuild exts_lists.

### Usage 
easy_update takes a single arument which is the path to an easyconfig 
file. Output is written to the same path/filename with the extension of
.update

### TODO
accept arguments to update the --version, --versionsuffix and --toolchain. Write a new file
with the updated content and file name.
