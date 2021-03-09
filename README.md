# elsevier_client

Experimental code for playing with full text searching for Elsevier journals
using Elsevier's ScienceDirect API.

Ultimate goal would be to search Elsevier journals for mouse papers and
download their PDFs to be loaded into MGI by the littriageload.

Currently, we don't have access to their PDFs, but we are working on getting
permission to access those.
Brian Smith is our contact at Elsevier:  B.Smith.1@elsevier.com

elslib/  contains python client code for talking to the Elsevier API

journalSearch.py is an example search script using this client.
