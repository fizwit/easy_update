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

### Usage

The main usage for easy_update is `--exts-update` which will update the version field of all extensions
in `exts_list`. The output is written to a new file, with extension `.update`.
 
#### Options
  *  -h, --help          show this help message and exit
  *  --version           show program's version number and exit
  *  -v, --verbose       Verbose; print lots of extra stuff
  *  --debug             set log level to debug, (default: false)
  *  --exts-update *easy_config*  update version info for exts_list in EasyConfig
  *  --exts-annotate *easy_config* Annotate all extensions from EasyConfig and dependencies. Output is Markdown
  *  --exts-dep-graph *easy_config* print Graph dependancies for exts
  *  --exts-description *easy_config* Output descrption for libraries in exts_list
  *  --exts-search-cran *package_name* output libray metadata from CRAN/BioConductor
  *  --exts-search-pypi *package_name* display library metadata from PyPi


<dl>
  <dd><b>Usage:</b> ./easy_update.py --exts-update Python-2.7.12-foss-2016b.eb</dd>
  <dd><b>Output:</b> Python-2.7.12-foss-2016b.update</dd>
</dl>

**Note:** When using BioConductor modules in easyconfig files the variable `local_biocver` or `biocver` must be set, otherwise
BioConductor will not be searched. **Example** ``local_biocver = 3.20``.

#### Verbose Flag

Verbose output show how each library is handled. Possible actions are: ['keep', 'update', 'processed', 'duplicate']. Modules that are added show the dependancy. R lanuage extensions who `shy` they are dependent: ['Depends', 'Imports', 'LinkingTo']

**tidyposterior Imports tune Imports dials Imports DiceDesign**

```
            collections : 0.3.7 Imports from EpiModel        (add) [730, 44]
                 EpiModel : 2.4.0 -> 2.5.0                (update) [730, 44]
...
               DiceDesign : 1.10 Imports from dials          (add) [730, 126]
                      sfd : 0.1.0 Imports from dials         (add) [730, 128]
                    dials : 1.4.0 Imports from tune          (add) [730, 129]
                 doFuture : 1.0.2 Imports from tune          (add) [730, 131]
                    GPfit : 1.0-8 Imports from tune          (add) [730, 133]
             sparsevctrs : 0.3.1 Imports from parsnip        (add) [730, 136]
                  parsnip : 1.3.1 Imports from tune          (add) [730, 137]
              modelenv : 0.2.0 Imports from workflows        (add) [730, 140]
                workflows : 1.2.0 Imports from tune          (add) [730, 141]
                yardstick : 1.3.2 Imports from tune          (add) [730, 143]
              tune : 1.3.0 Imports from tidyposterior        (add) [730, 144]
      workflowsets : 1.1.0 Imports from tidyposterior        (add) [730, 146]
            tidyposterior : 1.0.1                           (keep) [730, 146]
```

### Python Notes
Making sense of Pypi metadata can be problematic. 
Starting with the release of 2.3.0 `packaging` is used to parse and evalute the
`requires_dist` metadata from PyPi.org. `requires_dist` format is defined in PEP508.
Added PEP550 name normilization.

### TODO
Integrate with EasyBuild FrameWork. Version two of EasyUpdate has been refactored to 
seperate core update features from framework features. The `framework.py` performs: reading/parsing
easyconfig files, finding easyconfig files, rewritting easyconfig files, set easyblock type, create
module names from `dependencies` list. The new refactoring should 
make integration easier.
