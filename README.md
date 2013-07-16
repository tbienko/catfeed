CatFeed
=======

Generate feed for local catalog and download files directly in your favourite podcast player!

How it works?
-------------

It is quite simple python script that scans catalog and generates atom feed from found files. Feed is further served on given (or automatically resolved) ip adress and port. The script is serving these files too, so they can be downloaded. Afrer that, files are moved to special subcatalog (or removed if you want).

How to use?
-----------

Download catfeed.py and run it via shell. The simplest version of command:

    python catfeed.py .

It is good idea to startup CatFeed along with your system. Consider using fixed host and port like this:

     python path/to/catfeed.py --host 192.168.1.123 --port 8888 /path/to/catalog

Commandline parameters
----------------------
There are some more options, it is quote from `--help` command:

    positional arguments:
      catalog               catalog to generate feed from (absolute or relative path)
    optional arguments:
      -h, --help            show this help message and exit
      -H HOST, --host HOST  host to start server on (default: auto)
      -p PORT, --port PORT  port to start server on (default: 8888)
      -m PATH, --moveto PATH catalog to move downloaded files (absolute or relative path, default: Downloaded)
      -d, --delete          remove downloaded files instead of moving to other catalog
      -t TITLE, --title TITLE title of feed (default: name of catalog)
      -v {0,1,2,3}, --verbosity {0,1,2,3} level of logging (0-ERROR ... 3-DEBUG)