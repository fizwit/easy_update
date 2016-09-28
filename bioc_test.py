from exts_list import BioC
r = BioC('R-bundle-Bioconductor-3.3-foss-2016a-R-3.3.0.eb', verbose=True)

r.update_exts()
r.print_update()