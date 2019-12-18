import sys, getopt, boto3

# define arguments
unixOpts = "a:bc"
gnuOpts = ["eey","bee","see"]

# read arguments
argsList = sys.argv[1:]
try:
    args, vals = getopt.getopt(argsList,unixOpts,gnuOpts)
except getopt.error as err:
    # handling for unrecognized options
    print (str(err))
    sys.exit(2)

# handle arguments
for arg, val in args:
    if arg in ("-a", "--eey"):
        print (("a provided with %s") % (val))
    elif arg in ("-b", "--bee"):
        print ("Option b provided")
    elif arg in ("-c", "--see"):
        print ("Option c provided")    