
import urllib
import urllib2
from urllib2 import urlopen as urlopener  # don't change the name: tests override it
import socket
import base64
import re
import sys
import warnings

import jsonlayer
from KeyCaseInsensitiveDict import KeyCaseInsensitiveDict
from SPARQLExceptions import QueryBadFormed, EndPointNotFound, EndPointInternalError
from SPARQLUtils import deprecated
from SPARQLWrapper import __agent__

#  Possible output format keys...
JSON   = "json"
JSONLD = "json-ld"
XML    = "xml"
TURTLE = "n3"
N3     = "n3"
RDF    = "rdf"
_allowedFormats = [JSON, XML, TURTLE, N3, RDF]

# Possible HTTP methods
POST = "POST"
GET  = "GET"
_allowedRequests = [POST, GET]

# Possible HTTP Authentication methods
BASIC = "BASIC"
DIGEST = "DIGEST"
_allowedAuth = [BASIC, DIGEST]

# Possible SPARQL/SPARUL query type
SELECT     = "SELECT"
CONSTRUCT  = "CONSTRUCT"
ASK        = "ASK"
DESCRIBE   = "DESCRIBE"
INSERT     = "INSERT"
DELETE     = "DELETE"
CREATE     = "CREATE"
CLEAR      = "CLEAR"
DROP       = "DROP"
LOAD       = "LOAD"
COPY       = "COPY"
MOVE       = "MOVE"
ADD        = "ADD"
_allowedQueryTypes = [SELECT, CONSTRUCT, ASK, DESCRIBE, INSERT, DELETE, CREATE, CLEAR, DROP,
                      LOAD, COPY, MOVE, ADD]

# Possible methods to perform requests
URLENCODED = "urlencoded"
POSTDIRECTLY = "postdirectly"
_REQUEST_METHODS  = [URLENCODED, POSTDIRECTLY]


_SPARQL_DEFAULT  = ["application/sparql-results+xml", "application/rdf+xml", "*/*"]
_SPARQL_XML      = ["application/sparql-results+xml"]
_SPARQL_JSON     = ["application/sparql-results+json", "text/javascript", "application/json"]
_RDF_XML         = ["application/rdf+xml"]
_RDF_N3          = ["text/rdf+n3", "application/n-triples", "application/turtle", "application/n3", "text/n3", "text/turtle"]
_RDF_JSONLD      = ["application/x-json+ld", "application/ld+json"]
_ALL             = ["*/*"]
_RDF_POSSIBLE    = _RDF_XML + _RDF_N3
_SPARQL_POSSIBLE = _SPARQL_XML + _SPARQL_JSON + _RDF_XML + _RDF_N3
_SPARQL_PARAMS   = ["query"]

try:
    import rdflib_jsonld
    _allowedFormats.append(JSONLD)
    _RDF_POSSIBLE = _RDF_POSSIBLE + _RDF_JSONLD
except ImportError:
    #warnings.warn("JSON-LD disabled because no suitable support has been found", RuntimeWarning)
    pass


_returnFormatSetting = ["format", "output", "results"]

#######################################################################################################


class SPARQLWrapper(object):
    
    pattern = re.compile(r"""
        ((?P<base>(\s*BASE\s*<.*?>)\s*)|(?P<prefixes>(\s*PREFIX\s+.+:\s*<.*?>)\s*))*
        (?P<queryType>(CONSTRUCT|SELECT|ASK|DESCRIBE|INSERT|DELETE|CREATE|CLEAR|DROP|LOAD|COPY|MOVE|ADD))
    """, re.VERBOSE | re.IGNORECASE)

    def __init__(self, endpoint, updateEndpoint=None, returnFormat=XML, defaultGraph=None, agent=__agent__):
        self.endpoint = endpoint
        self.updateEndpoint = updateEndpoint if updateEndpoint else endpoint
        self.agent = agent
        self.user = None
        self.passwd = None
        self.http_auth = BASIC
        self._defaultGraph = defaultGraph

        if returnFormat in _allowedFormats:
            self._defaultReturnFormat = returnFormat
        else:
            self._defaultReturnFormat = XML

        self.resetQuery()

    def resetQuery(self):
        """Reset the query, ie, return format, query, default or named graph settings, etc,
        are reset to their default values."""
        self.parameters = {}
        if self._defaultGraph:
            self.addParameter("default-graph-uri", self._defaultGraph)
        self.returnFormat = self._defaultReturnFormat
        self.method = GET
        self.setQuery("""SELECT * WHERE{ ?s ?p ?o }""")
        self.timeout = None
        self.requestMethod = URLENCODED

    def setReturnFormat(self, format):
        """Set the return format. If not an allowed value, the setting is ignored.

        @param format: Possible values: are L{JSON}, L{XML}, L{TURTLE}, L{N3}, L{RDF} (constants in this module). All other cases are ignored.
        @type format: str
        """
        if format in _allowedFormats :
            self.returnFormat = format
        elif format == JSONLD:
            raise ValueError("Current instance does not support JSON-LD; you might want to install the rdflib-json package.")
        else:
            raise ValueError("Invalid format '%s'; current instance supports: %s.", (format, ", ".join(_allowedFormats)))

    def supportsReturnFormat(self, format):
        """Check if a return format is supported.

        @param format: Possible values: are L{JSON}, L{XML}, L{TURTLE}, L{N3}, L{RDF} (constants in this module). All other cases are ignored.
        @type format: bool
        """
        return (format in _allowedFormats)

    def setTimeout(self, timeout):
        """Set the timeout (in seconds) to use for querying the endpoint.

        @param timeout: Timeout in seconds.
        @type timeout: int
        """
        self.timeout = int(timeout)

    def setRequestMethod(self, method):
        """Set the internal method to use to perform the request for query or
        update operations, either URL-encoded (C{SPARQLWrapper.URLENCODED}) or 
        POST directly (C{SPARQLWrapper.POSTDIRECTLY}).
        Further details at U{http://www.w3.org/TR/sparql11-protocol/#query-operation}
        and U{http://www.w3.org/TR/sparql11-protocol/#update-operation}.

        @param method: method
        @type method: str
        """
        if method in _REQUEST_METHODS:
            self.requestMethod = method
        else:
            warnings.warn("invalid update method '%s'" % method, RuntimeWarning)

    @deprecated
    def addDefaultGraph(self, uri):
        """
            Add a default graph URI.
            @param uri: URI of the graph
            @type uri: string
            @deprecated: use addParameter("default-graph-uri", uri) instead of this method
        """
        self.addParameter("default-graph-uri", uri)

    @deprecated
    def addNamedGraph(self, uri):
        """
            Add a named graph URI.
            @param uri: URI of the graph
            @type uri: string
            @deprecated: use addParameter("named-graph-uri", uri) instead of this method
        """
        self.addParameter("named-graph-uri", uri)

    @deprecated
    def addExtraURITag(self, key, value):
        """
            Some SPARQL endpoints require extra key value pairs.
            E.g., in virtuoso, one would add C{should-sponge=soft} to the query forcing 
            virtuoso to retrieve graphs that are not stored in its local database.
            @param key: key of the query part
            @type key: string
            @param value: value of the query part
            @type value: string
            @deprecated: use addParameter(key, value) instead of this method
        """
        self.addParameter(key, value)

    @deprecated
    def addCustomParameter(self, name, value):
        """
            Method is kept for backwards compatibility. Historically, it "replaces" parameters instead of adding
            @param name: name 
            @type name: string
            @param value: value
            @type value: string
            @rtype: bool
            @deprecated: use addParameter(name, value) instead of this method
        """
        self.clearParameter(name)
        return self.addParameter(name, value)

    def addParameter(self, name, value):
        """
            Some SPARQL endpoints allow extra key value pairs.
            E.g., in virtuoso, one would add C{should-sponge=soft} to the query forcing 
            virtuoso to retrieve graphs that are not stored in its local database.
            @param name: name 
            @type name: string
            @param value: value
            @type value: string
            @rtype: bool
        """
        if name in _SPARQL_PARAMS:
            return False
        else:
            if name not in self.parameters:
                self.parameters[name] = []
            self.parameters[name].append(value)
            return True

    def clearParameter(self, name):
        """
            Clear the values ofd a concrete parameter.
            @param name: name 
            @type name: string
            @rtype: bool
        """
        if name in _SPARQL_PARAMS:
            return False
        else:
            try:
                del self.parameters[name]
                return True
            except KeyError:
                return False

    def setCredentials(self, user, passwd):
        """
            Set the credentials for querying the current endpoint
            @param user: username
            @type user: string
            @param passwd: password
            @type passwd: string
        """
        self.user = user
        self.passwd = passwd

    def setHTTPAuth(self, auth):
        """
           Set the HTTP Authentication type (Basic or Digest)
           @param auth: auth type
           @type auth: string
        """
        if not isinstance(auth, str):
            raise TypeError('setHTTPAuth takes a string')
        elif auth.upper() in _allowedAuth:
            self.http_auth = auth.upper()
        else:
            valid_types = ", ".join(_allowedAuth)
            raise ValueError("Value should be one of {0}".format(valid_types))
                    
    def setQuery(self, query):
        """
            Set the SPARQL query text. Note: no check is done on the validity of the query 
            (syntax or otherwise) by this module, except for testing the query type (SELECT, 
            ASK, etc). Syntax and validity checking is done by the SPARQL service itself.
            @param query: query text
            @type query: string
            @bug: #2320024
        """
        if sys.version < '3':  # have to write it like this, for 2to3 compatibility
            if isinstance(query, unicode):
                pass
            elif isinstance(query, str):
                query = query.decode('utf-8')
            else:
                raise TypeError('setQuery takes either unicode-strings or utf-8 encoded byte-strings')
        else:
            if isinstance(query, str):
                pass
            elif isinstance(query, bytes):
                query = query.decode('utf-8')
            else:
                raise TypeError('setQuery takes either unicode-strings or utf-8 encoded byte-strings')

        self.queryString = query
        self.queryType   = self._parseQueryType(query)

    def _parseQueryType(self,query):
        """
            Parse the SPARQL query and return its type (ie, L{SELECT}, L{ASK}, etc).

            Note that the method returns L{SELECT} if nothing is specified. This is just to get all other
            methods running; in fact, this means that the query is erronous, because the query must be,
            according to the SPARQL specification, one of Select, Ask, Describe, or Construct. The
            SPARQL endpoint should raise an exception (via urllib) for such syntax error.

            @param query: query text
            @type query: string
            @rtype: string
        """
        try:
            query = query if type(query)==str else query.encode('ascii', 'ignore')
            query = re.sub(re.compile("#.*?\n" ), "" , query) # remove all occurance singleline comments (issue #32)
            r_queryType = self.pattern.search(query).group("queryType").upper()
        except AttributeError:
            warnings.warn("not detected query type for query '%s'" % query.replace("\n", " "), RuntimeWarning)
            r_queryType = None
    
        if r_queryType in _allowedQueryTypes :
            return r_queryType
        else :
            #raise Exception("Illegal SPARQL Query; must be one of SELECT, ASK, DESCRIBE, or CONSTRUCT")
            warnings.warn("unknown query type '%s'" % r_queryType, RuntimeWarning)
            return SELECT

    def setMethod(self,method):
        """Set the invocation method. By default, this is L{GET}, but can be set to L{POST}.
        @param method: should be either L{GET} or L{POST}. Other cases are ignored.
        """
        if method in _allowedRequests : self.method = method

    def setUseKeepAlive(self):
        """Make urllib2 use keep-alive.
        @raise ImportError: when could not be imported urlgrabber.keepalive.HTTPHandler
        """
        try:
            from urlgrabber.keepalive import HTTPHandler
            keepalive_handler = HTTPHandler()
            opener = urllib2.build_opener(keepalive_handler)
            urllib2.install_opener(opener)
        except ImportError:
            warnings.warn("urlgrabber not installed in the system. The execution of this method has no effect.")

    def isSparqlUpdateRequest(self):
        """ Returns TRUE if SPARQLWrapper is configured for executing SPARQL Update request
        @return: bool
        """
        return self.queryType in [INSERT, DELETE, CREATE, CLEAR, DROP, LOAD, COPY, MOVE, ADD]

    def isSparqlQueryRequest(self):
        """ Returns TRUE if SPARQLWrapper is configured for executing SPARQL Query request
        @return: bool
        """
        return not self.isSparqlUpdateRequest()

    def _getRequestEncodedParameters(self, query=None):
        query_parameters = self.parameters.copy()

        if query and type(query) == tuple and len(query) == 2:
            #tuple ("query"/"update", queryString)
            query_parameters[query[0]] = [query[1]]

        
        for f in _returnFormatSetting:
            query_parameters[f] = [self.returnFormat]

        pairs = (
            "%s=%s" % (
                urllib.quote_plus(param.encode('UTF-8'), safe='/'),
                urllib.quote_plus(value.encode('UTF-8'), safe='/')
            )
            for param, values in query_parameters.items() for value in values
        )

        return '&'.join(pairs)

    def _getAcceptHeader(self):
        if self.queryType in [SELECT, ASK]:
            if self.returnFormat == XML:
                acceptHeader = ",".join(_SPARQL_XML)
            elif self.returnFormat == JSON:
                acceptHeader = ",".join(_SPARQL_JSON)
            else:
                acceptHeader = ",".join(_ALL)
        elif self.queryType in [INSERT, DELETE]:
            acceptHeader = "*/*"
        else:
            if self.returnFormat == N3 or self.returnFormat == TURTLE:
                acceptHeader = ",".join(_RDF_N3)
            elif self.returnFormat == XML:
                acceptHeader = ",".join(_RDF_XML)
            elif self.returnFormat == JSONLD and JSONLD in _allowedFormats:
                acceptHeader = ",".join(_RDF_JSONLD)
            else:
                acceptHeader = ",".join(_ALL)
        return acceptHeader

    def _createRequest(self):
        
        request = None

        if self.isSparqlUpdateRequest():
            #protocol details at http://www.w3.org/TR/sparql11-protocol/#update-operation
            uri = self.updateEndpoint

            if self.method != POST:
                warnings.warn("update operations MUST be done by POST")

            if self.requestMethod == POSTDIRECTLY:
                request = urllib2.Request(uri + "?" + self._getRequestEncodedParameters())
                request.add_header("Content-Type", "application/sparql-update")
                request.data = self.queryString.encode('UTF-8')
            else:  # URL-encoded
                request = urllib2.Request(uri)
                request.add_header("Content-Type", "application/x-www-form-urlencoded")
                request.data = self._getRequestEncodedParameters(("update", self.queryString)).encode('ascii')
        else:
            #protocol details at http://www.w3.org/TR/sparql11-protocol/#query-operation
            uri = self.endpoint

            if self.method == POST:
                if self.requestMethod == POSTDIRECTLY:
                    request = urllib2.Request(uri + "?" + self._getRequestEncodedParameters())
                    request.add_header("Content-Type", "application/sparql-query")
                    request.data = self.queryString.encode('UTF-8')
                else:  # URL-encoded
                    request = urllib2.Request(uri)
                    request.add_header("Content-Type", "application/x-www-form-urlencoded")
                    request.data = self._getRequestEncodedParameters(("query", self.queryString)).encode('ascii')
            else:  # GET
                request = urllib2.Request(uri + "?" + self._getRequestEncodedParameters(("query", self.queryString)))

        request.add_header("User-Agent", self.agent)
        request.add_header("Accept", self._getAcceptHeader())
        if self.user and self.passwd:
            if self.http_auth == BASIC:
                credentials = "%s:%s" % (self.user, self.passwd)
                request.add_header("Authorization", "Basic %s" % base64.encodestring(credentials.encode('utf-8')))
            elif self.http_auth == DIGEST:
                realm = "SPARQL"
                pwd_mgr = urllib2.HTTPPasswordMgr()
                pwd_mgr.add_password(realm, uri, self.user, self.passwd)
                opener = urllib2.build_opener()
                opener.add_handler(urllib2.HTTPDigestAuthHandler(pwd_mgr))
                urllib2.install_opener(opener)
            else:
                valid_types = ", ".join(_allowedAuth)
                raise NotImplementedError("Expecting one of: {0}, but received: {1}".format(valid_types,
                                                                                            self.http_auth))

        return request

    def _query(self):
        """Internal method to execute the query. Returns the output of the
        C{urllib2.urlopen} method of the standard Python library

        @return: tuples with the raw request plus the expected format
        """
        if self.timeout:
            socket.setdefaulttimeout(self.timeout)

        request = self._createRequest()

        try:
            response = urlopener(request)
            return response, self.returnFormat
        except urllib2.HTTPError, e:
            if e.code == 400:
                raise QueryBadFormed(e.read())
            elif e.code == 404:
                raise EndPointNotFound(e.read())
            elif e.code == 500:
                raise EndPointInternalError(e.read())
            else:
                raise e

    def query(self):
        
        return QueryResult(self._query())

    def queryAndConvert(self):
        """Macro like method: issue a query and return the converted results.
        @return: the converted query result. See the conversion methods for more details.
        """
        res = self.query()
        return res.convert()

#######################################################################################################


class QueryResult(object):
    def __init__(self,result):
        """
        @param result: HTTP response stemming from a L{SPARQLWrapper.query} call, or a tuple with the expected format: (response,format)
        """
        if (type(result) == tuple):
            self.response = result[0]
            self.requestedFormat = result[1]
        else:
            self.response = result
        """Direct response, see class comments for details"""

    def geturl(self):
        """Return the URI of the original call.
        @return: URI
        @rtype: string
        """
        return self.response.geturl()

    def info(self):
        """Return the meta-information of the HTTP result.
        @return: meta information
        @rtype: dictionary
        """
        return KeyCaseInsensitiveDict(self.response.info())

    def __iter__(self):
        """Return an iterator object. This method is expected for the inclusion
        of the object in a standard C{for} loop.
        """
        return self.response.__iter__()

    def next(self):
        """Method for the standard iterator."""
        return self.response.next()

    @staticmethod
    def setJSONModule(module):
        """Set the Python module for encoding JSON data. If not an allowed value, the setting is ignored.
           JSON modules supported:
             - ``simplejson``: http://code.google.com/p/simplejson/
             - ``cjson``: http://pypi.python.org/pypi/python-cjson
             - ``json``: This is the version of ``simplejson`` that is bundled with the
               Python standard library since version 2.6
               (see http://docs.python.org/library/json.html)
        @param module: Possible values: are L{simplejson}, L{cjson}, L{json}. All other cases raise a ValueError exception.
        @type module: string
        """
        jsonlayer.use(module)

    def _convertJSON(self):
        """
        Convert a JSON result into a Python dict. This method can be overwritten in a subclass
        for a different conversion method.
        @return: converted result
        @rtype: Python dictionary
        """
        return jsonlayer.decode(self.response.read().decode("utf-8"))

    def _convertXML(self):
        """
        Convert an XML result into a Python dom tree. This method can be overwritten in a
        subclass for a different conversion method.
        @return: converted result
        @rtype: PyXlib DOM node
        """
        from xml.dom.minidom import parse
        return parse(self.response)

    def _convertRDF(self):
        """
        Convert a RDF/XML result into an RDFLib triple store. This method can be overwritten
        in a subclass for a different conversion method.
        @return: converted result
        @rtype: RDFLib Graph
        """
        try:
            from rdflib.graph import ConjunctiveGraph
        except ImportError:
            from rdflib import ConjunctiveGraph
        retval = ConjunctiveGraph()
        # this is a strange hack. If the publicID is not set, rdflib (or the underlying xml parser) makes a funny
        #(and, as far as I could see, meaningless) error message...
        retval.load(self.response, publicID=' ')
        return retval

    def _convertN3(self):
        """
        Convert a RDF Turtle/N3 result into a string. This method can be overwritten in a subclass
        for a different conversion method.
        @return: converted result
        @rtype: string
        """
        return self.response.read()

    def _convertJSONLD(self):
        """
        Convert a RDF JSON-LDresult into an RDFLib triple store. This method can be overwritten
        in a subclass for a different conversion method.
        @return: converted result
        @rtype: RDFLib Graph
        """
        from rdflib import ConjunctiveGraph
        retval = ConjunctiveGraph()
        retval.load(self.response, format='json-ld', publicID=' ')
        return retval

    def convert(self):
        """
        Encode the return value depending on the return format:
            - in the case of XML, a DOM top element is returned;
            - in the case of JSON, a simplejson conversion will return a dictionary;
            - in the case of RDF/XML, the value is converted via RDFLib into a Graph instance.
        In all other cases the input simply returned.

        @return: the converted query result. See the conversion methods for more details.
        """
        def _content_type_in_list(real, expected):
            return True in [real.find(mime) != -1 for mime in expected]

        def _validate_format(format_name, allowed, mime, requested):
            if requested not in allowed:
                message = "Format requested was %s, but %s (%s) has been returned by the endpoint"
                warnings.warn(message % (requested.upper(), format_name, mime), RuntimeWarning)

        if "content-type" in self.info():
            ct = self.info()["content-type"]

            if _content_type_in_list(ct, _SPARQL_XML):
                _validate_format("XML", [XML], ct, self.requestedFormat)
                return self._convertXML()
            elif _content_type_in_list(ct, _SPARQL_JSON):
                _validate_format("JSON", [JSON], ct, self.requestedFormat)
                return self._convertJSON()
            elif _content_type_in_list(ct, _RDF_XML):
                _validate_format("RDF/XML", [RDF, XML], ct, self.requestedFormat)
                return self._convertRDF()
            elif _content_type_in_list(ct, _RDF_N3):
                _validate_format("N3", [N3, TURTLE], ct, self.requestedFormat)
                return self._convertN3()
            elif _content_type_in_list(ct, _RDF_JSONLD):
                _validate_format("JSON(-LD)", [JSONLD, JSON], ct, self.requestedFormat)
                return self._convertJSONLD()

        warnings.warn("unknown response content type, returning raw response...", RuntimeWarning)
        return self.response.read()

    def print_results(self, minWidth=None):
        results = self._convertJSON()
        if minWidth :
            width = self.__get_results_width(results, minWidth)
        else :
            width = self.__get_results_width(results)
        index = 0
        for var in results["head"]["vars"] :
            print ("?" + var).ljust(width[index]),"|",
            index += 1
        print
        print "=" * (sum(width) + 3 * len(width))
        for result in results["results"]["bindings"] :
            index = 0
            for var in results["head"]["vars"] :
                result = self.__get_prettyprint_string_sparql_var_result(result[var])
                print result.ljust(width[index]),"|",
                index += 1
            print

    def __get_results_width(self, results, minWidth=2):
        width = []
        for var in results["head"]["vars"] :
            width.append(max(minWidth, len(var)+1))
        for result in results["results"]["bindings"] :
            index = 0
            for var in results["head"]["vars"] :
                result = self.__get_prettyprint_string_sparql_var_result(result[var])
                width[index] = max(width[index], len(result))
                index =+ 1
        return width

    def __get_prettyprint_string_sparql_var_result(self, result):
        value = result["value"]
        lang = result.get("xml:lang", None)
        datatype = result.get("datatype",None)
        if lang is not None:
            value+="@"+lang
        if datatype is not None:
            value+=" ["+datatype+"]"
        return value
