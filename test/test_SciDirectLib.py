#!/usr/bin/env python3

"""
These are tests for SciDirectLib.py

Usage:   python test_SciDirectLib.py [-v]
"""
import sys
import unittest
import os
import os.path
import json
import requests
import SciDirectLib as sdl

## Load configuration   - TODO: need to get these from Env or something
con_file = open("../config.json")
config = json.load(con_file)
con_file.close()

## Initialize Elsevier API client
elsClient = sdl.ElsClient(config['apikey'], inst_token=config['insttoken'])

######################################

class ElsClient_tests(unittest.TestCase):
    def setUp(self):
        pass

    def test_execGetRequest_getarticle(self):
        pii = 'S0021925821005226'
        doi = '10.1016/j.jbc.2021.100733'
        url = sdl.url_base + 'content/article/pii/' + str(pii)
        ref = elsClient.execGetRequest(url)['full-text-retrieval-response']
        #print(ref.keys())
        #print(json.dumps(ref['coredata'], sort_keys=True, indent="  "))
        self.assertEqual(ref['coredata']['prism:doi'], doi)

    def test_execGetRequest_httperror(self):
        url = sdl.url_base + 'content/article/pii/' + 'foo'
        self.assertRaises(requests.HTTPError, elsClient.execGetRequest, url)
    
    def test_execGetRequest_getpdf(self):
        pii = 'S0021925821005226'
        url = sdl.url_base + 'content/article/pii/' + str(pii)
        pdf = elsClient.execGetRequest(url, contentType='pdf')
        self.assertEqual(pdf[:8], b'%PDF-1.7')
        self.assertEqual(len(pdf), 4101559)

    # test_execPutRequest

# end class ElsClient_tests ######################################

class SciDirectReference_tests(unittest.TestCase):
    ref1Data = {      # taken from SciDirect search results. PMID 33417945
        "authors": [
          {
            "name": "Hongqiao Zhang",
            "order": 1
          },
          {
            "name": "Todd E. Morgan",
            "order": 2
          },
          {
            "name": "Henry Jay Forman",
            "order": 3
          }
        ],
        "doi": "10.1016/j.abb.2020.108749",
        "loadDate": "2021-01-05T00:00:00.000Z",
        "openAccess": False,
        "pages": {
          "first": "108749"
        },
        "pii": "S0003986120307578",
        "publicationDate": "2021-03-15",
        "sourceTitle": "Archives of Biochemistry and Biophysics",
        "title": "Age-related alteration in HNE elimination enzymes",
        "uri": "https://www.sciencedirect.com/science/article/pii/S0003986120307578?dgcid=api_sd_search-api-endpoint",
        "volumeIssue": "Volume 699"
        }

    def test_constructor_getters(self):
        r1 = sdl.SciDirectReference(elsClient, data=self.ref1Data) 
        self.assertEqual("S0003986120307578", r1.getPii())
        self.assertEqual("10.1016/j.abb.2020.108749", r1.getDoi())
        self.assertEqual("Archives of Biochemistry and Biophysics", r1.getJournal())
        self.assertEqual("Age-related alteration in HNE elimination enzymes", r1.getTitle())
        self.assertEqual("Volume 699", r1.getVolumeIssue())
        self.assertEqual("2021-01-05T00:00:00.000Z", r1.getLoadDate())
        self.assertEqual("2021-03-15", r1.getPublicationDate())

    def test_fetching_details(self):
        r1 = sdl.SciDirectReference(elsClient, data=self.ref1Data) 
        self.assertEqual("33417945", r1.getPmid())
        self.assertEqual("rev", r1.getPubType())
        self.assertEqual("4-hydroxynonena", r1.getAbstract()[:15])

    def test_fetching_pdf(self):
        r1 = sdl.SciDirectReference(elsClient, data=self.ref1Data) 
        self.assertEqual(b'%PDF-1.7', r1.getPdf()[:8])
        self.assertEqual(1173669, len(r1.getPdf()))
        #fp = open(r1.getPii() + '.pdf', 'wb')
        #fp.write(r1.getPdf())
        #fp.close()

# end class SciDirectReference_tests ######################################


if __name__ == '__main__':
    unittest.main()