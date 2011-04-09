import zimr, urllib, sys
from urlparse import urlparse
from StringIO import StringIO

# http://www.python.org/dev/peps/pep-0333/
# http://en.wikipedia.org/wiki/Web_Server_Gateway_Interface

class ZimrLogIO( StringIO ):

	def flush( self ):
		zimr.log( self.getValue() )
		return cStringIO.flush( self )

def call_application( app, environ ):
	body = []
	status_headers = [None, None]

	def start_response(status, headers):
		status_headers[:] = [status, headers]
		return body.append

	app_iter = app(environ, start_response)

	try:
		for item in app_iter:
			body.append(item)
	finally:
		if hasattr(app_iter, 'close'):
			app_iter.close()

	return status_headers[0], status_headers[1], ''.join(body)

def connection_handler(  application, connection ):
	server = urlparse( connection.website.protocol + connection.website.url )

	environ = {
		'REQUEST_METHOD': connection.request.method,
		'SCRIPT_NAME': '/' + server.path.strip('/') if server.path != '/' else '',
		'PATH_INFO': '/' + connection.request.url if connection.request.url else '',
		'QUERY_STRING': '&'.join([k+'='+urllib.quote(str(v)) for (k,v) in connection.request.params.items()]),
		'CONTENT_TYPE': connection.request.headers['Content-Type'],
		'CONTENT_LENGTH': connection.request.headers['Content-Length'],
		'SERVER_NAME': server.hostname,
		'SERVER_PORT': server.port if server.port else ( 443 if server.scheme == 'https' else 80 ),
		'SERVER_PROTOCOL': 'HTTP/1.1',
		'wsgi.version': (1,0),
		'wsgi.url_scheme': server.scheme,
		'wsgi.input': StringIO( connection.request.post_body ),
		'wsgi.errors': sys.stderr,
		'wsgi.multithread': False,
		'wsgi.multiprocess': False,
		'wsgi.run_once': False
	}

	if server.scheme == 'https':
		environ['HTTPS'] = 'on'

	for name in connection.request.headers.keys():
		environ['HTTP_' + name.upper()] = connection.request.headers[name]

	status, headers, body = call_application( application, environ )

	connection.response.setStatus( int(status[:3]) )

	for name, val in headers:
		connection.response.headers[ name ] = val

	connection.send( body )
