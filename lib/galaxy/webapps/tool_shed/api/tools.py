import json
import logging
import os
from collections import namedtuple
from galaxy import web
from galaxy import util
from galaxy.web import _future_expose_api_raw_anonymous_and_sessionless as expose_api_raw_anonymous_and_sessionless
from galaxy.web.base.controller import BaseAPIController
from galaxy.webapps.tool_shed.search.tool_search import ToolSearch
from galaxy.exceptions import NotImplemented
from galaxy.exceptions import RequestParameterInvalidException
from galaxy.exceptions import ConfigDoesNotAllowException

log = logging.getLogger( __name__ )

class ToolsController( BaseAPIController ):
    """RESTful controller for interactions with tools in the Tool Shed."""

    @expose_api_raw_anonymous_and_sessionless
    def index( self, trans, **kwd ):
        """
        GET /api/tools
        Displays a collection of tools with optional criteria.

        :param q:        (optional)if present search on the given query will be performed
        :type  q:        str 

        :param page:     (optional)requested page of the search
        :type  page:     int

        :param jsonp:    (optional)flag whether to use jsonp format response, defaults to False
        :type  jsonp:    bool

        :param callback: (optional)name of the function to wrap callback in
                         used only when jsonp is true, defaults to 'callback'
        :type  callback: str

        :returns dict:   object containing list of results and metadata

        Examples:
            GET http://localhost:9009/api/tools
            GET http://localhost:9009/api/tools?q=fastq
        """
        q = kwd.get( 'q', '' )
        if not q:
            raise NotImplemented( 'Listing of all the tools is not implemented. Provide parameter "q" to search instead.' )
        else:
            page = kwd.get( 'page', 1 )
            try:
                page = int( page )
            except ValueError:
                raise RequestParameterInvalidException( 'The "page" requested has to be an integer.' )
            return_jsonp = util.asbool( kwd.get( 'jsonp', False ) )
            callback = kwd.get( 'callback', 'callback' )
            search_results = self._search( trans, q, page )
            if return_jsonp:
                response = str( '%s(%s);' % ( callback, json.dumps( search_results ) ) )
            else:
                response = json.dumps( search_results )
            return response

    def _search( self, trans, q, page=1 ):
        """
        Perform the search over TS tools index.
        Note that search works over the Whoosh index which you have
        to pre-create with scripts/tool_shed/build_ts_whoosh_index.sh manually.
        Also TS config option toolshed_search_on has to be True and
        whoosh_index_dir has to be specified.
        """
        conf = self.app.config
        if not conf.toolshed_search_on:
            raise ConfigDoesNotAllowException( 'Searching the TS through the API is turned off for this instance.' )
        if not conf.whoosh_index_dir:
            raise ConfigDoesNotAllowException( 'There is no directory for the search index specified. Please contact the administrator.' )
        search_term = q.strip()
        if len( search_term ) < 3:
            raise RequestParameterInvalidException( 'The search term has to be at least 3 characters long.' )

        tool_search = ToolSearch()

        Boosts = namedtuple( 'Boosts', [ 'tool_name_boost',
                                         'tool_description_boost',
                                         'tool_help_boost',
                                         'tool_repo_owner_username_boost' ] )
        boosts = Boosts( float( conf.get( 'tool_name_boost', 1.2 ) ),
                         float( conf.get( 'tool_description_boost', 0.6 ) ),
                         float( conf.get( 'tool_help_boost', 0.4 ) ),
                         float( conf.get( 'tool_repo_owner_username_boost', 0.3 ) ) )

        results = tool_search.search( trans,
                                      search_term,
                                      page,
                                      boosts )
        results[ 'hostname' ] = web.url_for( '/', qualified = True )
        return results
