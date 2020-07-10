[TOC]

# Deployment

Here you will find everything necessary to configure and run the `MainServer`
of the app.  There's actually two of everything you need, the idea being that a
_deployment_ server can be running where someone who depends on the service can
use the last working version of the server, while you can be playing around and
tweaking things on the _dev_ server.

## Files

### Overview

file                   | description
-----------------------| -----------
es\_database.init.yml  | used to create the elasticsearch index
main.py                | a minimal script to run the server
main\_server.cfg       | configuration file for the server
pretty\_explain.py     | used to print out the _explain log_ in a pretty manner
pretty\_qa.py          | used to print out the _qa log_ in a pretty manner
interactive.py         | a helper script to do interactive testing of the server
elasticsearch\_config/ | directory pointed to from `elasticsearch/config`
questions              | directory containing items related to experiments

### Details

#### es\_database.init.yml
This file contains two objects: `index` and `creation`.  `index` is simply the
name of the index, while `creation` is an object that will be passed to
elasticsearch when the index is created.

#### main.py
The only things to mention here is that `'..'` is appended to `sys.path` to
bring in the implementation, and the configuration file name `main_server.cfg`
is passed to the constructor of `MainServer`.

#### main\_server.cfg
This is the main configuration file for `MainServer`.  It deals with nearly all
aspects of the server, and is documented with comments in the .cfg file.

#### pretty\_\*.py
The prettifiers for the logs are intended to be run like:

    tail -f qa_log.jsonl | python pretty_qa.py
    tail -f es_explain.jsonl | python pretty_explain.py

The logs are in _jsonl_ format (one json object per line), and the prettifiers
just try to make the output of `tail -f` easier to parse by a human.

#### interactive.py
This was a script made to make testing the server more convenient.  It's main
functionality is provided by `query_and_test()`.  It assumes that you have a
question stored in the global variable `q`, and then it proceeds to query the
server with `q`.  Then, it queries the elasticsearch index to get all possible
matches for `q`, and then outputs the paragraphs retrieved as well as the
results of running the question `q` against all the pipelines created earlier in
the script.  The output is quite verbose, but it uses some coloring to make the
results easier to read.  The script also

A typical workflow would be to run `python main.dev.py`, then load the
interactive script with `python -i interactive.py`.  Then, set `q = "what is
clokke?"`, and run `query_and_test()`.  Observe the output.  If it doesn't seem
that the best context was provided to the models, then check the output of the
`es_explain.dve.jsonl` _explain log_.  If it happens that erronious documents
were retrieved, then maybe add update the list of stopwords or synonyms, restart
the server, and do it again.

