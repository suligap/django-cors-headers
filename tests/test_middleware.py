from django.test import TestCase
from django.test.utils import override_settings

from corsheaders.middleware import (
    ACCESS_CONTROL_ALLOW_CREDENTIALS, ACCESS_CONTROL_ALLOW_HEADERS, ACCESS_CONTROL_ALLOW_METHODS,
    ACCESS_CONTROL_ALLOW_ORIGIN, ACCESS_CONTROL_EXPOSE_HEADERS, ACCESS_CONTROL_MAX_AGE
)
from corsheaders.models import CorsModel

from .utils import append_middleware, temporary_check_request_hander


class CorsMiddlewareTests(TestCase):

    def test_get_no_origin(self):
        resp = self.client.get('/')
        assert ACCESS_CONTROL_ALLOW_ORIGIN not in resp

    @override_settings(CORS_ORIGIN_WHITELIST=['example.com'])
    def test_get_not_in_whitelist(self):
        resp = self.client.get('/', HTTP_ORIGIN='http://foobar.it')
        assert ACCESS_CONTROL_ALLOW_ORIGIN not in resp

    @override_settings(CORS_ORIGIN_WHITELIST=['example.com', 'foobar.it'])
    def test_get_in_whitelist(self):
        resp = self.client.get('/', HTTP_ORIGIN='http://foobar.it')
        assert resp[ACCESS_CONTROL_ALLOW_ORIGIN] == 'http://foobar.it'

    @override_settings(
        CORS_ORIGIN_ALLOW_ALL=True,
        CORS_EXPOSE_HEADERS=['accept', 'origin', 'content-type'],
    )
    def test_get_expose_headers(self):
        resp = self.client.get('/', HTTP_ORIGIN='http://example.com')
        assert resp[ACCESS_CONTROL_EXPOSE_HEADERS] == 'accept, origin, content-type'

    @override_settings(CORS_ORIGIN_ALLOW_ALL=True)
    def test_get_dont_expose_headers(self):
        resp = self.client.get('/', HTTP_ORIGIN='http://example.com')
        assert ACCESS_CONTROL_EXPOSE_HEADERS not in resp

    @override_settings(
        CORS_ALLOW_CREDENTIALS=True,
        CORS_ORIGIN_ALLOW_ALL=True,
    )
    def test_get_allow_credentials(self):
        resp = self.client.get('/', HTTP_ORIGIN='http://example.com')
        assert resp[ACCESS_CONTROL_ALLOW_CREDENTIALS] == 'true'

    @override_settings(CORS_ORIGIN_ALLOW_ALL=True)
    def test_get_dont_allow_credentials(self):
        resp = self.client.get('/', HTTP_ORIGIN='http://example.com')
        assert ACCESS_CONTROL_ALLOW_CREDENTIALS not in resp

    @override_settings(
        CORS_ALLOW_HEADERS=['content-type', 'origin'],
        CORS_ALLOW_METHODS=['GET', 'OPTIONS'],
        CORS_PREFLIGHT_MAX_AGE=1002,
        CORS_ORIGIN_ALLOW_ALL=True,
    )
    def test_options_allowed_origin(self):
        resp = self.client.options(
            '/',
            HTTP_ORIGIN='http://example.com',
        )
        assert resp[ACCESS_CONTROL_ALLOW_HEADERS] == 'content-type, origin'
        assert resp[ACCESS_CONTROL_ALLOW_METHODS] == 'GET, OPTIONS'
        assert resp[ACCESS_CONTROL_MAX_AGE] == '1002'

    @override_settings(
        CORS_ALLOW_HEADERS=['content-type', 'origin'],
        CORS_ALLOW_METHODS=['GET', 'OPTIONS'],
        CORS_PREFLIGHT_MAX_AGE=0,
        CORS_ORIGIN_ALLOW_ALL=True,
    )
    def test_options_no_max_age(self):
        resp = self.client.options('/', HTTP_ORIGIN='http://example.com')
        assert resp[ACCESS_CONTROL_ALLOW_HEADERS] == 'content-type, origin'
        assert resp[ACCESS_CONTROL_ALLOW_METHODS] == 'GET, OPTIONS'
        assert ACCESS_CONTROL_MAX_AGE not in resp

    @override_settings(
        CORS_ALLOW_METHODS=['OPTIONS'],
        CORS_ALLOW_CREDENTIALS=True,
        CORS_ORIGIN_WHITELIST=('localhost:9000',),
    )
    def test_options_whitelist_with_port(self):
        resp = self.client.options('/', HTTP_ORIGIN='http://localhost:9000')
        assert resp[ACCESS_CONTROL_ALLOW_CREDENTIALS] == 'true'

    @override_settings(
        CORS_ALLOW_METHODS=['OPTIONS'],
        CORS_ALLOW_CREDENTIALS=True,
        CORS_ORIGIN_REGEX_WHITELIST=[r'^http?://(\w+\.)?google\.com$'],
    )
    def test_options_adds_origin_when_domain_found_in_origin_regex_whitelist(self):
        resp = self.client.options('/', HTTP_ORIGIN='http://foo.google.com')
        assert resp[ACCESS_CONTROL_ALLOW_ORIGIN] == 'http://foo.google.com'

    @override_settings(
        CORS_ALLOW_METHODS=['OPTIONS'],
        CORS_ALLOW_CREDENTIALS=True,
        CORS_ORIGIN_REGEX_WHITELIST=('^http?://(\w+\.)?yahoo\.com$',),
    )
    def test_options_will_not_add_origin_when_domain_not_found_in_origin_regex_whitelist(self):
        resp = self.client.options('/', HTTP_ORIGIN='http://foo.google.com')
        assert ACCESS_CONTROL_ALLOW_ORIGIN not in resp

    @override_settings(CORS_MODEL='corsheaders.CorsModel')
    def test_get_when_custom_model_enabled(self):
        CorsModel.objects.create(cors='foo.google.com')
        resp = self.client.get('/', HTTP_ORIGIN='http://foo.google.com')
        assert resp[ACCESS_CONTROL_ALLOW_ORIGIN] == 'http://foo.google.com'

    def test_options(self):
        resp = self.client.options(
            '/',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='value',
        )
        assert resp.status_code == 200

    def test_options_empty_request_method(self):
        resp = self.client.options(
            '/',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='',
        )
        assert resp.status_code == 200

    def test_options_no_header(self):
        resp = self.client.options('/')
        assert resp.status_code == 404

    @override_settings(
        CORS_ALLOW_CREDENTIALS=True,
        CORS_ORIGIN_ALLOW_ALL=True,
    )
    def test_allow_all_origins_get(self):
        resp = self.client.get('/', HTTP_ORIGIN='http://foobar.it')
        assert resp.status_code == 200
        assert resp[ACCESS_CONTROL_ALLOW_ORIGIN] == 'http://foobar.it'
        assert resp['Vary'] == 'Origin'

    @override_settings(
        CORS_ALLOW_CREDENTIALS=True,
        CORS_ORIGIN_ALLOW_ALL=True,
    )
    def test_allow_all_origins_options(self):
        resp = self.client.options(
            '/',
            HTTP_ORIGIN='http://foobar.it',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='value',
        )
        assert resp.status_code == 200
        assert resp[ACCESS_CONTROL_ALLOW_ORIGIN] == 'http://foobar.it'
        assert resp['Vary'] == 'Origin'

    @override_settings(
        CORS_ALLOW_CREDENTIALS=True,
        CORS_ORIGIN_ALLOW_ALL=True,
    )
    def test_non_200_headers_still_set(self):
        """
        It's not clear whether the header should still be set for non-HTTP200
        when not a preflight request. However this is the existing behaviour for
        django-cors-middleware, so at least this test makes that explicit, especially
        since for the switch to Django 1.10, special-handling will need to be put in
        place to preserve this behaviour. See `ExceptionMiddleware` mention here:
        https://docs.djangoproject.com/en/1.10/topics/http/middleware/#upgrading-pre-django-1-10-style-middleware
        """
        resp = self.client.get('/test-401/', HTTP_ORIGIN='http://foobar.it')
        assert resp.status_code == 401
        assert resp[ACCESS_CONTROL_ALLOW_ORIGIN] == 'http://foobar.it'

    @override_settings(
        CORS_ALLOW_CREDENTIALS=True,
        CORS_ORIGIN_ALLOW_ALL=True,
    )
    def test_auth_view_options(self):
        """
        Ensure HTTP200 and header still set, for preflight requests to views requiring
        authentication. See: https://github.com/ottoyiu/django-cors-headers/issues/3
        """
        resp = self.client.options(
            '/test-401/',
            HTTP_ORIGIN='http://foobar.it',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='value',
        )
        assert resp.status_code == 200
        assert resp[ACCESS_CONTROL_ALLOW_ORIGIN] == 'http://foobar.it'

    def test_signal_handler_that_returns_false(self):
        def handler(*args, **kwargs):
            return False

        with temporary_check_request_hander(handler):
            resp = self.client.options(
                '/',
                HTTP_ORIGIN='http://foobar.it',
                HTTP_ACCESS_CONTROL_REQUEST_METHOD='value',
            )

            assert resp.status_code == 200
            assert ACCESS_CONTROL_ALLOW_ORIGIN not in resp

    def test_signal_handler_that_returns_true(self):
        def handler(*args, **kwargs):
            return True

        with temporary_check_request_hander(handler):
            resp = self.client.options(
                '/',
                HTTP_ORIGIN='http://foobar.it',
                HTTP_ACCESS_CONTROL_REQUEST_METHOD='value',
            )
            assert resp.status_code == 200
            assert resp[ACCESS_CONTROL_ALLOW_ORIGIN] == 'http://foobar.it'

    @override_settings(CORS_ORIGIN_WHITELIST=['example.com'])
    def test_signal_handler_allow_some_urls_to_everyone(self):
        def allow_api_to_all(sender, request, **kwargs):
            return request.path.startswith('/api/')

        with temporary_check_request_hander(allow_api_to_all):
            resp = self.client.options(
                '/',
                HTTP_ORIGIN='http://example.org',
                HTTP_ACCESS_CONTROL_REQUEST_METHOD='value',
            )
            assert resp.status_code == 200
            assert ACCESS_CONTROL_ALLOW_ORIGIN not in resp

            resp = self.client.options(
                '/api/something/',
                HTTP_ORIGIN='http://example.org',
                HTTP_ACCESS_CONTROL_REQUEST_METHOD='value',
            )
            assert resp.status_code == 200
            assert resp[ACCESS_CONTROL_ALLOW_ORIGIN] == 'http://example.org'

    @override_settings(CORS_ORIGIN_WHITELIST=['example.com'])
    def test_signal_called_once_during_normal_flow(self):
        def allow_all(sender, request, **kwargs):
            allow_all.calls += 1
            return True
        allow_all.calls = 0

        with temporary_check_request_hander(allow_all):
            self.client.get('/', HTTP_ORIGIN='http://example.org')

            assert allow_all.calls == 1


@override_settings(
    CORS_REPLACE_HTTPS_REFERER=True,
    CORS_ORIGIN_REGEX_WHITELIST=r'.*example.*',
)
class RefererReplacementCorsMiddlewareTests(TestCase):

    def test_get_replaces_referer_when_secure(self):
        resp = self.client.get(
            '/',
            HTTP_FAKE_SECURE='true',
            HTTP_HOST='example.com',
            HTTP_ORIGIN='https://example.org',
            HTTP_REFERER='https://example.org/foo'
        )
        assert resp.wsgi_request.META['HTTP_REFERER'] == 'https://example.com/'
        assert resp.wsgi_request.META['ORIGINAL_HTTP_REFERER'] == 'https://example.org/foo'

    @append_middleware('corsheaders.middleware.CorsPostCsrfMiddleware')
    def test_get_post_middleware_rereplaces_referer_when_secure(self):
        resp = self.client.get(
            '/',
            HTTP_FAKE_SECURE='true',
            HTTP_HOST='example.com',
            HTTP_ORIGIN='https://example.org',
            HTTP_REFERER='https://example.org/foo'
        )
        assert resp.wsgi_request.META['HTTP_REFERER'] == 'https://example.org/foo'
        assert 'ORIGINAL_HTTP_REFERER' not in resp.wsgi_request.META

    def test_get_does_not_replace_referer_when_insecure(self):
        resp = self.client.get(
            '/',
            HTTP_HOST='example.com',
            HTTP_ORIGIN='https://example.org',
            HTTP_REFERER='https://example.org/foo'
        )
        assert resp.wsgi_request.META['HTTP_REFERER'] == 'https://example.org/foo'
        assert 'ORIGINAL_HTTP_REFERER' not in resp.wsgi_request.META

    @override_settings(CORS_REPLACE_HTTPS_REFERER=False)
    def test_get_does_not_replace_referer_when_disabled(self):
        resp = self.client.get(
            '/',
            HTTP_FAKE_SECURE='true',
            HTTP_HOST='example.com',
            HTTP_ORIGIN='https://example.org',
            HTTP_REFERER='https://example.org/foo',
        )
        assert resp.wsgi_request.META['HTTP_REFERER'] == 'https://example.org/foo'
        assert 'ORIGINAL_HTTP_REFERER' not in resp.wsgi_request.META

    def test_get_does_not_fail_in_referer_replacement_when_referer_missing(self):
        resp = self.client.get(
            '/',
            HTTP_FAKE_SECURE='true',
            HTTP_HOST='example.com',
            HTTP_ORIGIN='https://example.org',
        )
        assert 'HTTP_REFERER' not in resp.wsgi_request.META
        assert 'ORIGINAL_HTTP_REFERER' not in resp.wsgi_request.META

    def test_get_does_not_fail_in_referer_replacement_when_host_missing(self):
        resp = self.client.get(
            '/',
            HTTP_FAKE_SECURE='true',
            HTTP_ORIGIN='https://example.org',
            HTTP_REFERER='https://example.org/foo',
        )
        assert resp.wsgi_request.META['HTTP_REFERER'] == 'https://example.org/foo'
        assert 'ORIGINAL_HTTP_REFERER' not in resp.wsgi_request.META
