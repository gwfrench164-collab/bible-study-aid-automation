"""Keep the local web app from being driven by other websites.

The app listens on this computer only, but any web page open in your browser can
still send requests to it. These checks stop that:

* Requests must be addressed to this computer (or a host you list in
  BIBLE_STUDY_ALLOWED_HOSTS, e.g. a private phone-access address later on).
* Requests that browsers mark as coming from a different website are refused.
* Anything that changes data must come from the app's own pages.
"""
import os

from flask import abort, request

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def allowed_hosts():
    extra = {h.strip().lower() for h in os.environ.get("BIBLE_STUDY_ALLOWED_HOSTS", "").split(",") if h.strip()}
    return LOCAL_HOSTS | extra


def host_name(host_header):
    host = (host_header or "").strip().lower()
    if host.startswith("["):  # [::1]:5055
        return host[1:].split("]", 1)[0]
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


def check_request():
    """Refuse requests that did not come from the app's own pages."""
    if host_name(request.host) not in allowed_hosts():
        abort(400, "Unexpected host name.")
    site = request.headers.get("Sec-Fetch-Site", "")
    if site == "cross-site":
        abort(403, "Requests from other websites are not allowed.")
    changes_things = request.method not in {"GET", "HEAD", "OPTIONS"} or request.path in {"/open", "/reveal"}
    if changes_things:
        if site == "same-site":
            abort(403, "Requests from other local sites are not allowed.")
        origin = request.headers.get("Origin")
        if origin and origin.split("://", 1)[-1] != request.host:
            abort(403, "Requests from other sites are not allowed.")
        # Older browsers send no Sec-Fetch-Site; fall back to the page that linked here.
        referer = request.headers.get("Referer")
        if not site and referer and referer.split("://", 1)[-1].split("/", 1)[0] != request.host:
            abort(403, "Requests from other sites are not allowed.")


def register_guard(app):
    app.before_request(check_request)
