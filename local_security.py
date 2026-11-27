"""Loopback-only request protection. This is not remote authentication."""
import re
import secrets
from urllib.parse import urlsplit
from flask import request, session, abort, has_request_context


def install_security(app):
    app.secret_key = secrets.token_hex(32)
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict', MAX_CONTENT_LENGTH=2*1024*1024)

    @app.url_defaults
    def protected_link(endpoint, values):
        if endpoint in {'open_source','reveal_in_finder'} and has_request_context():
            values.setdefault('_csrf', session.get('_csrf',''))

    @app.before_request
    def protect():
        if urlsplit('http://' + request.host).hostname not in {'localhost','127.0.0.1','::1'}:
            abort(400)
        token = session.get('_csrf')
        if not token:
            token = session['_csrf'] = secrets.token_urlsafe(32)
        protected = request.method not in {'GET','HEAD','OPTIONS'} or request.path in {'/open','/reveal'}
        if protected:
            origin = request.headers.get('Origin')
            if origin and origin != request.host_url.rstrip('/'):
                abort(403)
            if request.headers.get('Sec-Fetch-Site') == 'cross-site':
                abort(403)
            supplied = request.form.get('_csrf', '') if request.method == 'POST' else request.args.get('_csrf', '')
            if not secrets.compare_digest(token, supplied):
                abort(403)

    @app.after_request
    def secure_response(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cache-Control'] = 'no-store'
        if response.mimetype == 'text/html' and not response.direct_passthrough:
            token = session.get('_csrf','')
            html = response.get_data(as_text=True)
            html = re.sub(r'(<form\b[^>]*\bmethod=["\x27]post["\x27][^>]*>)',
                          lambda m: m[1] + '<input type="hidden" name="_csrf" value="'+token+'">', html, flags=re.I)
            html = re.sub(r'(href=["\x27])(/(?:open|reveal)\?[^"\x27]*)(["\x27])',
                          lambda m: m[1]+m[2]+'&amp;_csrf='+token+m[3], html)
            response.set_data(html)
        return response
