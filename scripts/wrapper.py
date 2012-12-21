#!/usr/bin/python3

import sys
import collections
import itertools
import logging
import subprocess
import os

logging.basicConfig(format='%(message)s',level=logging.INFO)

def mangle_args(args): # Oh god what am I doing
    script_path = os.path.dirname(os.path.realpath(__file__))
    paths = {"partialAlign": os.path.join(script_path, "partialAlign2.py"), 
             "hunalign": os.path.abspath(os.path.join(script_path, "../src/hunalign/hunalign"))}
    def extract(arg):
        if arg.startswith("--partialAlign="):
            paths["partialAlign"] = arg.replace("--partialAlign=", "")
        elif arg.startswith("--hunalign="):
            paths["hunalign"] = arg.replace("--hunalign=", "")
        else:
            return True
        return False
    mangled = [arg for arg in args if extract(arg)]
    return mangled, paths["partialAlign"], paths["hunalign"]        

def main():
    # Split the corpus into a batch job using partialAlign
    partialAlign_args, partialAlign, hunalign = mangle_args(sys.argv)
    partialAlign_args[0] = partialAlign
    with open("hunalign_batch", "w") as batch_file:
        process = subprocess.Popen(partialAlign_args, stdout=batch_file)
        process.wait()
        if process.returncode != 0:
            raise RuntimeError("Partial align failed")
    
    # Run HunAlign once to generate a dictionary
    os.remove("autodict");
    hunalign_args = (hunalign, "-realign", 
                     "-autodict=autodict",
                     "-batch", "/dev/null", "hunalign_batch")
    process = subprocess.Popen(hunalign_args)
    process.wait()
    # HunAlign always returns nonzero, god bless its kind soul
    #if process.returncode != 0:
    #    raise RuntimeError("HunAlign failed")
    
    # Run it again, now using this generated dictionary
    hunalign_args = (hunalign, "-batch", "autodict", "hunalign_batch")
    process = subprocess.Popen(hunalign_args)
    process.wait()
    # And yet again we don't know if it really finished

if __name__ == "__main__":
    main()
