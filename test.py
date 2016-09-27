from exts_list import R
r = R('R-3.3.1-foss-2016b.eb') 

r.update_exts()
r.diff_exts()
print "------"
r.print_exts()
