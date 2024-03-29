# Easy Update
If you support `R` and `Python` easyconfigs, this tool will automate the process of updating
module versions and recursively check for dependent modules. *Easy_Update* is a tool for maintaining EasyBuild
easyconfig files for `Python` and `R`. R-Bioconductor libararies are also supported. Easy_update rewrites easyconfig
files with updated version information for each module in `exts_list[]`. Easy_update also checks
for dependencies recursively and adds any missing dependent modules to `exts_list`.  If you have
been maintaining package lists by hand, you will notice that easy_update will reorder your 
`exts_list` based on the correct dependency hierarchy.
Easy_update writes dependent packages ahead of the parent module.  If dependent
packages are found further within `exts_list`, they will will be treated as 
duplicates and removed.  If you are running easy update for the first time I would 
suggest that you run it twice to ensure that the modules are in the correct order. 

### Update notes November 2020
easy_update will look for eb and search easyconfigs from EasyBuild. The primary search path will based on the path of the earyconfig being updated.

### Update Notes March 2019
*Easy_Update* now supports PythonPackage and RPackage easyconfigs. *Easy_Update* will read exts_list from
R and Python easyconfig listed in the depencies of the R or Python package. Only the package name will
be verifed from the dependent language. Version information will be updated for the priamry EasyConfig 
R or Python easyconfig that is specified. The --add feature has been removed.

### Usage
easy_update takes a single argument which is the path to an easyconfig file. The output is written to a new file;
with the extension ".update".

<dl>
  <dd><b>Usage:</b> ./easy_update.py Python-2.7.12-foss-2016b.eb</dd>
  <dd><b>Output:</b> Python-2.7.12-foss-2016b.update</dd>
</dl>

**Note:** When using BioConductor modules in easyconfig files the variable ``local_biocver`` must be set, otherwise
BioConductor will not be searched. **Example** ``local_biocver = 3.11``.

### Flags

* **--verbose** output the action that will be taken for each module along with the version number.
    Possible actions are 'keep', 'update', 'dep', 'add' or 'duplicate'
    'keep' no changes are needed
    'update' there is a new version available for the package
    'dep' A new package will be added as the result of finding dependencies
    'duplicate'  A duplicate package name has been found

Verbose output explains why new dependencies are being added. Updating **breakaway**
required adding **phyloseq**, which required **bioformat**.
```
                      pbs : 1.1                             (keep) [444, 316]
                   RLRsim : 3.1-6 -> 3.1-8                (update) [444, 317]
                   refund : 0.1-24                          (keep) [444, 318]
               biomformat : 1.22.0 from phyloseq             (add) [444, 319]
                 phyloseq : 1.38.0 from breakaway            (add) [444, 320]
                breakaway : 3.0 -> 4.7.9                  (update) [444, 321]
```

### Python Notes
Making sense of Pypi metadata can be problematic. 
https://dustingram.com/articles/2018/03/05/why-pypi-doesnt-know-dependencies/
Easy_Update processes info mation from Pypi.org. Most of the packing tools are designed
for read setup.py files. The format for Requires_dist is speicified in PEP566

### Note
Easy Update makes many asumptions about the format of the easyconfig file. If
only and update is being made the original text is preserved and only the
version number is updated.  If a new package needs to be added then it is written
using these conventions. All output is indented 4 spaces. Python easyconfigs are
output in a multi line format.
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
R modules are writte in a single line.  It is asumed that `ext_options` 
and `bioconductor_options` are 
defined outside of the `ext_list` declaration.
```
    ('packrat', '0.4.8-1'),
    ('PKI', '0.1-5.1'),
    ('rsconnect', '0.8.5'),
    ('zlibbioc', '1.24.0'),
    ('BiocGenerics', '0.24.0'),
```

### TODO
Integrate with EasyBuild FrameWork. Version two of EasyUpdate has been refactored to 
seperate core update features from framework features. The new refactoring should 
make integration easier.

Nov 2020
Meta search features have been removed from easy_update. In a future relase they will be supported by a different application: meta_search.py.  All these flags are removed from easy_update

* **--search** [modulename] Search is used to lookup a single module as an argument.  Search does not read or write to a file. Dependencies will be output if found. This is handy for checking new packages.
Search requires the command line arguments; --pyver or --rver and --biocver to determine which repository to search.

* **--meta** Display metadata available from the repository.  The output is very verbose and should be used for debugging purposes. The output is written to stdout.

* **--Meta** Use with --search only. Output package metadata and exit.

* **--tree** For use with --search option, output inverted dependancy tree for a package.
 
* **--pyver**  Only use in conjunction with search.  Specify only the major minor version numbers; --pyver 3.6.

* **--rver, --biocver** Only use in conjunction with search.  Specify only the major minor version numbers
