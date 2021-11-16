import sys

open("version.txt", "w").write(sys.argv[-1])
spec_replacement=str(open("_00_GUI.spec", "r").readlines()).replace('name=\'_00_GUI\'', sys.argv[-1])
open("_00_GUI.spec", "w").write(spec_replacement)