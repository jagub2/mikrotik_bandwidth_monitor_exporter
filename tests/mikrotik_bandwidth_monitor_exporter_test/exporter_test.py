"""Test suite for mikrotik_bandwidth_monitor_exporter module."""
# pylint: disable=protected-access
from functools import wraps

import json
import pytest
import requests
import requests_mock
import mikrotik_bandwidth_monitor_exporter.exporter as exporter_module


devices_mock = [
    {
        ".id": "*1",
        "activity": "",
        "blocked": "false",
        "bytes-down": "42069",
        "bytes-up": "2137",
        "disabled": "false",
        "dynamic": "true",
        "idle-time": "1m1s",
        "ip-address": "192.168.88.2",
        "limited": "false",
        "mac-address": "AA:BB:CC:DD:EE:FF",
        "name": "foobar",
        "rate-down": "0",
        "rate-up": "0",
        "user": ""
    },
    {
        ".id": "*2",
        "activity": "",
        "blocked": "false",
        "bytes-down": "69420",
        "bytes-up": "7312",
        "disabled": "false",
        "dynamic": "true",
        "idle-time": "1m1s",
        "ip-address": "192.168.88.3",
        "limited": "false",
        "mac-address": "AA:BB:CC:DD:EE:00",
        "name": "",
        "rate-down": "0",
        "rate-up": "0",
        "user": ""
    },
]


@pytest.fixture(name="mikrotik_dataclass")
def mikrotik_dataclass_fixture():
    """Fixture of MikrotikDataclass."""
    return exporter_module.MikrotikDataclass(
        'http://192.168.88.1', 'admin', '')


def flask_app_wrapper(func):
    """Decorator for flask app."""
    @wraps(func)
    def inner_flask_app(*args, **kwargs):
        with exporter_module.app.app_context():
            return func(*args, **kwargs)
    return inner_flask_app


@pytest.fixture(name="requests_warning_mock")
def requests_warnings_fixture(mocker):
    """Fixture of disabling warnings of requests package urllib3."""
    return mocker.patch.object(
        requests.packages.urllib3,  # pylint: disable=no-member
        "disable_warnings")


@pytest.fixture(name="serve_mock")
def serve_mock_fixture(mocker):
    """Mock of serve() from waitress module."""
    return mocker.patch.object(exporter_module, "serve")


class TestMikrotikDataclass:
    """Test for MikrotikDataclass."""
    def test_fields(self, mikrotik_dataclass):
        """Test field values."""
        assert mikrotik_dataclass.webfig_url == 'http://192.168.88.1'
        assert mikrotik_dataclass.api_login == 'admin'
        assert mikrotik_dataclass.api_password == ''
        assert mikrotik_dataclass.request_timeout == 30
        assert not mikrotik_dataclass.verify_ssl

    def test_generate_auth(self, mikrotik_dataclass):
        """Test generate_auth()."""
        web_auth = mikrotik_dataclass.generate_auth()
        assert isinstance(web_auth, requests.auth.HTTPBasicAuth)
        assert web_auth.username == mikrotik_dataclass.api_login
        assert web_auth.password == mikrotik_dataclass.api_password


class TestHttpResponses:
    """Class for HTTP response tests."""
    def test_correct_http_response(self):
        """Test for correct HTTP response code."""
        assert exporter_module.is_http_code_ok(200)

    @pytest.mark.parametrize("http_code", [400, 401, 420, 500])
    def test_incorrect_http_response(self, http_code):
        """Test for incorrect HTTP response code."""
        assert not exporter_module.is_http_code_ok(http_code)


class TestGetKidControlDataMetrics():
    """Test get_kid_control_data_metrics."""
    def prepare(self, exporter_mod, mocker, mikrotik_dataclass, **kwargs):
        """Preparation for tests in this class."""
        requests_mocker = kwargs['requests_mocker']
        exporter = exporter_mod
        current_app_mock = mocker.patch.object(exporter, "current_app")
        current_app_mock.config = {'MIKROTIK_DATA': mikrotik_dataclass}
        make_wsgi_app_mock = mocker.patch.object(exporter, "make_wsgi_app")
        return requests_mocker, exporter, current_app_mock, make_wsgi_app_mock

    @flask_app_wrapper
    @requests_mock.Mocker(kw='requests_mocker')
    def test_get_metrics(self, mocker, mikrotik_dataclass, **kwargs):
        """Test for get_kid_control_data_metrics() where everything works."""
        requests_mocker, exporter, _, make_wsgi_app_mock = \
            self.prepare(exporter_module, mocker, mikrotik_dataclass, **kwargs)
        requests_mocker.get('http://192.168.88.1/rest/ip/kid-control/device',
                            text=json.dumps(devices_mock))
        requests_mocker.post('http://192.168.88.1/rest/ip/kid-control/device'
                             '/reset-counters')
        result = exporter.get_kid_control_data_metrics()
        assert result is make_wsgi_app_mock.return_value
        assert [s.value for s in exporter.bytes_down._samples()] == \
            [42069.0, 69420.0]
        assert [s.value for s in exporter.bytes_up._samples()] == \
            [2137.0, 7312.0]
        assert {'AA:BB:CC:DD:EE:FF', 'AA:BB:CC:DD:EE:00'} & \
            set(s.labels['mac'] for s in exporter.bytes_down._samples()) & \
            set(s.labels['mac'] for s in exporter.bytes_up._samples())
        assert {'foobar', 'AA:BB:CC:DD:EE:00'} & \
            set(s.labels['name'] for s in exporter.bytes_down._samples()) & \
            set(s.labels['name'] for s in exporter.bytes_up._samples())

    @flask_app_wrapper
    @requests_mock.Mocker(kw='requests_mocker')
    def test_get_metrics_but_it_fails_1st(self, mocker, mikrotik_dataclass,
                                          **kwargs):
        """Test for get_kid_control_data_metrics() with fail, 1st scenario."""
        requests_mocker, exporter, _, make_wsgi_app_mock = \
            self.prepare(exporter_module, mocker, mikrotik_dataclass, **kwargs)
        requests_mocker.get('http://192.168.88.1/rest/ip/kid-control/device',
                            status_code=500)
        with pytest.raises(requests.exceptions.HTTPError) as exception:
            exporter.get_kid_control_data_metrics()
        assert str(exception.value) == "Data request failed"
        make_wsgi_app_mock.assert_not_called()

    @flask_app_wrapper
    @requests_mock.Mocker(kw='requests_mocker')
    def test_get_metrics_but_it_fails_2nd(self, mocker, mikrotik_dataclass,
                                          **kwargs):
        """Test for get_kid_control_data_metrics() with fail, 1st scenario."""
        requests_mocker, exporter, _, make_wsgi_app_mock = \
            self.prepare(exporter_module, mocker, mikrotik_dataclass, **kwargs)
        requests_mocker.get('http://192.168.88.1/rest/ip/kid-control/device',
                            text=json.dumps(devices_mock))
        requests_mocker.post('http://192.168.88.1/rest/ip/kid-control/device'
                             '/reset-counters', status_code=500)
        with pytest.raises(requests.exceptions.HTTPError) as exception:
            exporter.get_kid_control_data_metrics()
        assert str(exception.value) == "Reset request failed"
        make_wsgi_app_mock.assert_not_called()


def test_main_page():
    """Test main_page()"""
    assert exporter_module.main_page() == \
        "<h1>Welcome to Mikrotik Bandwidth-Monitor data exporter.</h1>" + \
        "Metrics are available: <a href='/metrics'>here</a>."


class TestMain():
    """Test main()"""
    def test_init(self, serve_mock, requests_warning_mock):
        """Test default initialization."""
        exporter_module.main()
        mikrotik_dataclass = exporter_module.app.config['MIKROTIK_DATA']
        assert mikrotik_dataclass.webfig_url == 'http://192.168.88.1:80'
        assert mikrotik_dataclass.api_login == 'admin'
        assert mikrotik_dataclass.api_password == ''
        assert mikrotik_dataclass.request_timeout == 30
        assert not mikrotik_dataclass.verify_ssl
        assert isinstance(
            mikrotik_dataclass, exporter_module.MikrotikDataclass)
        requests_warning_mock.assert_called()
        serve_mock.assert_called_with(exporter_module.app,
                                      host="0.0.0.0", port=9180)

    def test_init_with_env_variables(
            self, serve_mock, requests_warning_mock, mocker):
        """Test initialization with environment variables."""
        mocker.patch.dict("os.environ", {
            "LISTEN_ADDRESS": "127.0.0.1",
            "LISTEN_PORT": "2137",
            "MIKROTIK_REST_API_METHOD": "https",
            "MIKROTIK_IP": "192.168.1.1",
            "MIKROTIK_WEBFIG_PORT": "443",
            "MIKROTIK_USER": "api",
            "MIKROTIK_PASSWORD": "e1m1",
            "MIKROTIK_REST_API_VERIFY_SSL": "1",
            "MIKROTIK_REQUEST_TIMEOUT": "10"
        })
        exporter_module.main()
        mikrotik_dataclass = exporter_module.app.config['MIKROTIK_DATA']
        assert mikrotik_dataclass.webfig_url == 'https://192.168.1.1:443'
        assert mikrotik_dataclass.api_login == 'api'
        assert mikrotik_dataclass.api_password == 'e1m1'
        assert mikrotik_dataclass.request_timeout == 10
        assert mikrotik_dataclass.verify_ssl
        requests_warning_mock.assert_not_called()
        serve_mock.assert_called_with(exporter_module.app,
                                      host="127.0.0.1", port=2137)
