"""A Python module that provides classes to talk to the Elsevier ScienceDirect
   API for searching for references and downloading meta-data and PDFs
   API documentation (JIM: is this right?)
   * https://dev.elsevier.com
   * https://api.elsevier.com

Class Overview
    class ElsClient
    - low level client for sending http requests to the API & getting results
    - does throttling, writing http requests to log file
    - knows how to construct http request header w/ appropriate API key, 
        institutional token, and user agent
    - exec_requestGet(url, contentType) executes a GET request with
        result content-type either json or pdf
    - exec_requestPut(url, params) executes a PUT request after coding the
        params in json. Returns json result.

    class SciDirectSearch
    - Does a search against the SciDirect API and provides access to the search
        results in various ways.
    - search params are specified as a python dict (that will be encoded
        as json to the ElsClient (and subsequently the SciDirect API)
    - can get count of matching results, results as json string, or as
        iterator of SciDirectReference objects (below)
    - optionally saves search results json to a file (for debugging)
    - fetches the query results in increments & has an overall maximum result
        set size to be polite to the API

    class SciDirectReference
    - represents a reference object (article) at SciDirect
    - has article metadata: reference IDs, Journal, title, abstract, full text,
        pdf, etc.
    - lazily makes requests to the API to get additional metadata/pdf
"""

import requests, json, time, os, logging

def get_logger(name):
    # TODO: add option to disable logging, configure location of log file
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

logger = get_logger(__name__)
url_base = "https://api.elsevier.com/"

class ElsClient:
    """A class that implements a Python interface to api.elsevier.com"""

    __user_agent = "MGI-SciDirectClient"
    __min_req_interval = 1                      ## Min. request interval in sec
    __ts_last_req = time.time()                 ## Tracker for throttling
 
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
        """
        ## Validate contentType

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
            return json.loads(r.text)   # or just return the json string?
        else:
            return r.content        # binary content
    # end execGetRequest() -------------------

    def execPutRequest(self, URL, params=None):
        """Send request using the PUT method. Return response.
            params should be the API query params coded as json.
            JIM: should params be json already?
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
        logger.info('Params:  ' + str(params))

        r = requests.put( URL, headers=headers, data=params)

        self.__ts_last_req = time.time()
        self._status_code=r.status_code

        ## Check results
        if r.status_code != 200:        # bail out
            self._status_msg="HTTP " + str(r.status_code) + \
                                " Error from " + URL + \
                                "\nusing headers: " + str(headers) +  \
                                "\nand data: " + str(params) +  \
                                ":\n" + r.text
            logger.info(self._status_msg)       # logger.error() instead?
            raise requests.HTTPError(self._status_msg)

        ## Success
        self._status_msg='data retrieved'
        return json.loads(r.text)       # or just return the json string?
    # end execPutRequest() -------------------

    # properties
    @property
    def api_key(self):
        """Get the apiKey for the client instance"""
        return self._api_key
    @api_key.setter
    def api_key(self, api_key):
        """Set the apiKey for the client instance"""
        self._api_key = api_key

    @property
    def inst_token(self):
        """Get the instToken for the client instance"""
        return self._inst_token
    @inst_token.setter
    def inst_token(self, inst_token):
        """Set the instToken for the client instance"""
        self._inst_token = inst_token

    @property
    def req_status(self):
    	'''Return the status of the request response, '''
    	return {'status_code':self._status_code, 'status_msg': self._status_msg}
# end class ElsClient -------------------------

