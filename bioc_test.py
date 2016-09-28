from exts_list import BioC
#r = BioC('R-bundle-Bioconductor-3.3-foss-2016b-R-3.3.1-fh1.eb', verbose=True)
r = BioC('R-bundle-Bioconductor-3.3-foss-2016b-R-3.3.1-fh1.eb')

r.update_exts()
r.print_update()
