"""A Python module that provides classes to talk to the Elsevier ScienceDirect
    API for searching for references and downloading metadata and PDFs

    This is based on an open source python client provided by Elsevier at
    https://github.com/ElsevierDev/elsapy

    BUT has been MUCH stripped down and simplified for MGI's purposes and
    modified to support:
    (1) use of the SciDirect PUT API interface instead of the old, depricated
       GET interface
    (2) downloading of PDFs
    (elsapy also does not seem to be supported much):

    Documentation for the API itself (not elsapy)
    * The PUT API takes a json payload to specify the query parameters and
        returns a json result set.

    * Best docs for this json exchange that I've found:
        https://dev.elsevier.com/tecdoc_sdsearch_migration.html
            (but it is a little confusing because it is couched in terms of
            the old GET API)

    * more API docs, but doesn't explain the json payloads:
        https://dev.elsevier.com/documentation/ScienceDirectSearchAPI.wadl

    * overview of different Elsevier APIs - we are most concerned with
        ScienceDirect which includes full text search.
        (Scopus only supports abstracts)
        https://dev.elsevier.com/support.html

    * interactively play with the API here:
        https://dev.elsevier.com/sciencedirect.html#/

Class Overview
    class ElsClient
    - low level client for sending http requests to the API & getting results
    - does throttling, writing http requests to log file
    - knows how to construct http request header w/ appropriate API key, 
        institutional token, and user agent
    - executes a GET request(url, contentType)
        with result content-type either json or pdf.
        Returns the unserialized json payload or the pdf bytes
    - executes a PUT request(url, json_params) and returns unserialized json
        payload.

    class SciDirectSearch
    - Does a search against the SciDirect API and provides access to the search
        results in various ways.
    - search params are specified as a python dict
    - can get count of matching results, unserialized results, or as
        iterator of SciDirectReference objects (below)
    - saves search results json to a file (for debugging).
        TODO: make this configurable.
    - fetches the query results in increments & has an overall maximum result
        set size to be polite to the API

    class SciDirectReference
    - represents a reference object (article) at SciDirect
    - has article metadata: reference IDs, Journal, title, abstract, pdf, etc.
    - lazily makes requests to the API to get additional metadata/pdf

There are automated tests for this module: # includes usage examples
    cd tests
    python test_SciDirectLib.py [-v]
"""

import requests, json, time, os, logging
from copy import deepcopy

def get_logger(name):
    ## Adapted from https://docs.python.org/3/howto/logging-cookbook.html

    # create logger with module name
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    # create log path, if not already there
    logPath = './logs'
    if not os.path.exists(logPath):
        os.mkdir(logPath)
    logFileName = 'SciDirectLib-%s.log' % time.strftime('%Y%m%d')
    logFilePath = os.path.join(logPath, logFileName)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logFilePath)
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    # create formatter and add it to the handlers
    formatter = logging.Formatter( \
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.info("SciDirectLib log started.")
    return logger

# TODO: add option to disable logging, configure location of log file
#       maybe we just want to pass an open log file to write to instead of 
#       using the logging framework?
logger = get_logger(__name__)
url_base = "https://api.elsevier.com/"

class ElsClient(object):
    """ See class overview above
    """
    __user_agent = "MGI-SciDirectClient"
    __min_req_interval = 0.5        ## min num seconds between requests
    __ts_last_req = 0.0           ## time of the last request (in sec)
 
    def __init__(self, api_key, inst_token=None, ):
        """Initializes a client with a given API Key and, optionally,
            institutional token,
        """
        self.api_key = api_key
        self.inst_token = inst_token
    # end __init__() -----------------

    def execGetRequest(self, URL, contentType='json'):
        """Send GET request. Return response.
           Supported contentTypes: 'json' or 'pdf'.
           If contentType = 'json', returns the unserialized json payload
           if contentType= 'pdf', returns the raw bytes
        """
        ## Validate contentType
        if contentType not in ['json', 'pdf']:
            msg = "invalid contentType '%s', only pdf and json are supported" \
                                                % contentType
            raise ValueError(msg + '\n')

        ## Throttle request, if need be
        interval = time.time() - self.__ts_last_req
        if (interval < self.__min_req_interval):
            time.sleep( self.__min_req_interval - interval )
        
        ## Construct and execute request
        headers = {
            "X-ELS-APIKey"  : self.api_key,
            "User-Agent"    : self.__user_agent,
            "Accept"        : 'application/%s' % contentType
            }
        if self.inst_token:
            headers["X-ELS-Insttoken"] = self.inst_token
        logger.info("Sending GET request to %s contentType='%s'" % \
                                                            (URL, contentType))
        r = requests.get(URL, headers=headers)

        self.__ts_last_req = time.time()
        self._status_code=r.status_code

        ## Check results
        if r.status_code != 200:        # bail out
            self._status_msg="HTTP " + str(r.status_code) + \
                                " Error from " + URL + \
                                " using headers " + str(headers) + \
                                ":\n" + r.text
            logger.info(self._status_msg)       # logger.error() instead?
            raise requests.HTTPError(self._status_msg)

        ## Success
        self._status_msg='%s data retrieved' % contentType
        if contentType == 'json':
            return json.loads(r.text)
        else:
            return r.content        # binary content
    # end execGetRequest() -------------------

    def execPutRequest(self, URL, jsonParams):
        """ Send request using the PUT method.
            Return the unserialized json payload
            jsonParams should be json payload with the API query params
        """
        ## Throttle request, if need be
        interval = time.time() - self.__ts_last_req
        if (interval < self.__min_req_interval):
            time.sleep( self.__min_req_interval - interval )

        ## Construct and execute request
        headers = {
            "X-ELS-APIKey"  : self.api_key,
            "User-Agent"    : self.__user_agent,
            "Accept"        : 'application/json'
            }
        if self.inst_token:
            headers["X-ELS-Insttoken"] = self.inst_token
        logger.info('Sending PUT request to ' + URL)
        logger.info('Params:  ' + str(jsonParams))

        r = requests.put(URL, headers=headers, data=jsonParams)

        self.__ts_last_req = time.time()
        self._status_code=r.status_code

        ## Check results
        if r.status_code != 200:        # bail out
            self._status_msg="HTTP " + str(r.status_code) + \
                                " Error from " + URL + \
                                "\nusing headers: " + str(headers) +  \
                                "\nand data: " + str(jsonParams) +  \
                                ":\n" + r.text
            logger.info(self._status_msg)       # logger.error() instead?
            raise requests.HTTPError(self._status_msg)

        ## Success
        self._status_msg='data retrieved'
        return json.loads(r.text)
    # end execPutRequest() -------------------

    def getRequestStatus(self):
    	'''Return the status of the request response, '''
    	return {'status_code':self._status_code, 'status_msg': self._status_msg}
# end class ElsClient -------------------------

class SciDirectSearch(object):
    """ See class overview above
    """
    def __init__(self, elsClient,
                query,             # dict that defines query params for PUT API
                getAll=False,      # if False, only get one API call of results 
                maxResults=5000,   # max num of matching results to pull down
                increment=100,     # num results to get w/each API call
                ):
        """ Instantiate search object.
            See https://dev.elsevier.com/tecdoc_sdsearch_migration.html
              for details of the PUT API
        """
        self._elsClient = elsClient
        self._getAll = getAll
        self._maxResults = maxResults
        self._increment = increment
        self._query = query
        if type(self._query) != type({}):
            raise TypeError('query is not a dictionary')

        self._results = []       # the results pulled down so far
        self._tot_num_res = None # total num of matching results at SciDirect

    def execute(self):
        """Executes the search using the API V2 PUT method.
            If getAll = False, this retrieves
                the default number of results specified for the API.
            If getAll = True, multiple API calls will be made to iteratively
                get all results for the search, up to a maximum.
        """
        url = url_base + 'content/search/sciencedirect'

        if self._getAll:        # take over the display 'show' & 'offset' attrs
            query = deepcopy(self._query)
            displayField = query.get('display', {})
            displayField['show'] = self._increment
            if 'offset' not in displayField:
                displayField['offset'] = 0
            query['display'] = displayField
        else:
            query = self._query

        ## do 1st API call
        queryJson = json.dumps(query)
        api_response = self._elsClient.execPutRequest(url, queryJson)
        self._tot_num_res = int(api_response['resultsFound'])

        if self._tot_num_res == 0:
            self._results = []
            return self

        # got some matching results
        self._results = api_response['results']

        if self._getAll:     ## do any needed additional API calls
            while (len(self._results) < self._tot_num_res) and \
                                not (len(self._results) >= self._maxResults):
                query['display']['offset'] += self._increment

                queryJson = json.dumps(query)
                api_response = self._elsClient.execPutRequest(url, queryJson)
                self._results += api_response['results']

        with open('dump.json', 'w') as f:
            f.write(json.dumps(self._results, sort_keys=True, indent=2))
        return self

    def getTotalNumResults(self): return self._tot_num_res
    def getNumResults(self):      return len(self._results)

    def getResults(self):
        """ Return the list of raw result records from the API."""
        return self._results

    def getIterator(self):
        """ Return iterator of SciDirectReference objects from the results"""
        it = (SciDirectReference(self._elsClient, r) for r in self._results)
        return it

    def getElsClient(self):   return self._elsClient
    def getQuery(self):       return self._query

# end class SciDirectSearch -------------------------

class SciDirectReference(object):
    """
    IS:   a reference at ScienceDirect.
    HAS:  IDs, basic metadata fields: title, journal, dates, ...
    DOES: loads metadata lazily. Gets PDF.
    """
    def __init__(self, elsClient, searchResult):
        """ Instantiate a reference object.
            searchResult = record/dict from SciDirectSearch results from the API
        """
        self._elsClient = elsClient

        # unpack fields from SciDirectSearch results
        self._searchResultsFields = searchResult
        self._unpackSciDirectResult()

        # fields we have to load from a ref details API call
        self._detailFields = None      # the results from the details API call
        self._pmid = None
        self._pubType = None
        self._abstract = None
        self._volume = None

        # the binary pdf contents are loaded from a subsequent API call
        self._pdf = None

    def _unpackSciDirectResult(self):
        """ unpack the dict from SciDirectSearch result representing the ref
        """
        self._pii             = self._searchResultsFields['pii']
        self._doi             = self._searchResultsFields['doi']
        self._journal         = self._searchResultsFields['sourceTitle']
        self._title           = self._searchResultsFields['title']
        self._loadDate        = self._searchResultsFields['loadDate']
        self._publicationDate = self._searchResultsFields['publicationDate']

    # getters for fields from SciDirectSearch result
    def getPii(self):         return self._pii
    def getDoi(self):         return self._doi
    def getJournal(self):     return self._journal
    def getTitle(self):       return self._title
    def getLoadDate(self):    return self._loadDate
    def getPublicationDate(self): return self._publicationDate
    def getSearchResultsFields(self): return self._searchResultsFields

    def getElsClient(self):   return self._elsClient

    # getters for fields from ref details API call
    def getPmid(self):
        self._getDetails()
        return self._pmid
    def getPubType(self):
        self._getDetails()
        return self._pubType
    def getAbstract(self):
        self._getDetails()
        return self._abstract
    def getVolume(self):
        self._getDetails()
        return self._volume
    def getDetails(self):
        self._getDetails()
        return self._detailFields

    def _getDetails(self):
        """ load the reference details from the API if they have not already
            been loaded.
        """
        if not self._detailFields:
            url = url_base + 'content/article/pii/' + str(self._pii)
            response = self._elsClient.execGetRequest(url)

            # TODO: should we dump json output somewhere for debugging?
            r = response['full-text-retrieval-response']
            self._detailFields = r

            # unpack the fields, just these for now.
            # Other fields are avail, including the full text in xml fmt
            self._pmid     = r.get('pubmed-id', 'no PMID')
            self._pubType  = r['coredata'].get('pubType', 'no pubType')
            self._abstract = r['coredata'].get('dc:description', 'no abstract')
            self._volume   = r['coredata'].get('prism:volume', 'no volume')

    # getters for the PDF
    def getPdf(self):
        self._getPdf()
        return self._pdf

    def _getPdf(self):
        """ Get the PDF from the API if we have not already done so
        """
        if not self._pdf:
            url = url_base + 'content/article/pii/' + str(self._pii)
            self._pdf = self._elsClient.execGetRequest(url, contentType='pdf')

# end class SciDirectReference -------------------------
