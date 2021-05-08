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

# end class ElsClient_tests
######################################


if __name__ == '__main__':
    unittest.main()
