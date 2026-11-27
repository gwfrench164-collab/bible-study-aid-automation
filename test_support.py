"""Exercise protected routes with a real per-session token."""
from flask.testing import FlaskClient

class ProtectedClient(FlaskClient):
    def open(self, *args, **kwargs):
        with self.session_transaction() as session:
            token = session.setdefault('_csrf', 'test-session-token')
        method = kwargs.get('method','GET').upper()
        if method == 'POST':
            kwargs.setdefault('data', {})['_csrf'] = token
        elif args and isinstance(args[0], str) and args[0].split('?')[0] in {'/open','/reveal'}:
            if 'query_string' in kwargs:
                kwargs['query_string'] = dict(kwargs['query_string'], _csrf=token)
                return super().open(*args, **kwargs)
            path = args[0] + ('&' if '?' in args[0] else '?') + '_csrf=' + token
            args = (path, *args[1:])
        return super().open(*args, **kwargs)

def client(app):
    return ProtectedClient(app, app.response_class)
