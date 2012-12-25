#!/usr/bin/python3

import sys
import collections
import itertools
import logging
import subprocess
import os

logging.basicConfig(format='%(message)s',level=logging.INFO)

def mangle_args(args):
    """Extracts arguments specific to this script from a list of
    arguments otherwise intended for partialAlign, in a not very
    clean way."""
    script_path = os.path.dirname(os.path.realpath(__file__))
    partialAlign = os.path.join(script_path, "partialAlign2.py")
    hunalign = os.path.abspath(os.path.join(script_path, "../src/hunalign/hunalign"))
    realign = False
    accumulate = False

    def extract(arg):
        """If arg is an argument intended for this script, its
        value is noted and False is returned. True is returned
        otherwise."""
        if len(arg) < 3:
            return True
        elif arg.startswith("--partialAlign="):
            partialAlign = arg.replace("--partialAlign=", "")
        elif arg.startswith("--hunalign="):
            hunalign = arg.replace("--hunalign=", "")
        elif "--realign".startswith(arg):
            realign = True
        elif "--accumulate".startswith(arg):
            realign = True
            accumulate = True
        else:
            return True
        return False
    
    mangled = [arg for arg in args if extract(arg)]

    # If help is asked for, don't return any arguments
    if any(arg in args for arg in ("--help", "-help", "-?")):
        mangled = None

    return mangled, partialAlign, hunalign, realign, accumulate

def main():
    """This does the actual work of the script, i.e. it executes
    partialAlign and hunalign according to the command line
    arguments."""

    partialAlign_args, partialAlign, hunalign, realign, accumulate = mangle_args(sys.argv)
    if partialAlign_args == None or len(sys.argv) == 1:
        print(("This script splits a corpus into manageable chunks using \n"
               "partialAlign2.py then aligns it using hunalign. \n"
               "If --realign is specified, hunalign re-aligns each chunk \n"
               "using a dictionary generated from its first alignment. \n"
               "With --accumulate, the dictionaries are combined and the \n"
               "final dictionary is used to realign all chunks. \n\n"
               "Usage: {0} \n"
               "       [--partialAlign=/path/to/partialAlign2.py] \n"
               "       [--hunalign=/path/to/hunalign] \n"
               "       [--realign] \n"
               "       [--accumulate] \n"
               "       PARTIALALIGN-ARGUMENTS... \n\n"
               "If partialAlign is in the correct location, its argument \n"
               "list will now be shown. \n").format(sys.argv[0]))
        process = subprocess.Popen((partialAlign, "--help"))
        process.wait()
        return
    
    partialAlign_args[0] = partialAlign
    with open("hunalign_batch", "w") as batch_file:
        process = subprocess.Popen(partialAlign_args, stdout=batch_file)
        process.wait()
        if process.returncode != 0:
            raise RuntimeError("Partial align failed")
    
    # Run HunAlign once to generate a dictionary
    if realign: 
        try:
            os.remove("autodict")
        except OSError:
            pass
        # Generating the autodict does no harm whether or not accumulation
        # is set, so we do it in both cases
        hunalign_args = (hunalign, "-realign", "-autodict=autodict",
                         "-batch", "/dev/null", "hunalign_batch")
    else:
        hunalign_args = (hunalign, "-batch", "/dev/null", "hunalign_batch")
    process = subprocess.Popen(hunalign_args)
    process.wait()
    # HunAlign always returns nonzero, god bless its kind soul
    #if process.returncode != 0:
    #    raise RuntimeError("HunAlign failed")
    
    if accumulate:
        # Run it again, now using this generated dictionary
        hunalign_args = (hunalign, "-batch", "autodict", "hunalign_batch")
        process = subprocess.Popen(hunalign_args)
        process.wait()

    # And yet again we don't know if it really finished, so let's tell the user
    print("\nPlease check the output for errors. HunAlign always finishes \n"
          "with an error code, so the script can't automatically do that \n"
          "for you. (Not reliably, at least.)")

if __name__ == "__main__":
    main()
