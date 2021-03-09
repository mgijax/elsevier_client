Python client to talk to Elsevier API (for ScienceDirect and Scopus) adapted
for MGI by Jim in March 2021.

This is based on the elsapy package, https://github.com/ElsevierDev/elsapy,
originally written by Elsevier.
elsapy appears to not be supported (much).

## The major adaptations made by Jim:

* Added executePUT method to access the API via the recommended PUT interface.
    The original elsapy package only supported GET access to the legacy API,
    and I could not get the date queries to work in this legacy API
    i.e.,
    https://api.elsevier.com/content/search/scidir?query=title(mice)+and+pub-date+aft+20180601
    gave weird errors.
    Adding PUT access affected elssearch.py and elsclient.py


## Documentation:
* The PUT API takes a json payload to specify the query parameters and returns
    a json result set.

* Best docs for this json exchange that I've found:
    https://dev.elsevier.com/tecdoc_sdsearch_migration.html
        (but it is a little confusing because it is couched in terms of the old
        GET API)

* more API docs, but doesn't explain the json payloads:
    https://dev.elsevier.com/documentation/ScienceDirectSearchAPI.wadl

* overview of different Elsevier APIs - we are most concerned with
    ScienceDirect which includes full text search. Scopus only supports
    abstracts
    https://dev.elsevier.com/support.html

* interactively play with the API here:
    https://dev.elsevier.com/sciencedirect.html#/



## Features of the client:
0) ElsClient does do some throttling so it appears is should not overwhelm API
1) ElsSearch object takes a query and a ElsClient and returns results
    as json
    as pandas DataFrame - haven't looked in to what that might buy us.
    currently has a limit of 5000 results
2) ElsSearch object always writes latest query results to dump.json file in
    the current directory.
    Need to make this configurable or something.
3) logs/ subdirectory:  writes a daily log file of API accesses here
4) data/ subdirectory:  the client creates this directory, not sure why

