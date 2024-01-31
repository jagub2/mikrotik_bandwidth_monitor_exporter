"""Mikrotik Bandwidth Monitor Exporter Python module."""
import logging
import os
from dataclasses import dataclass
from typing import Callable
import requests
from flask import current_app, Flask
from prometheus_client import make_wsgi_app, Gauge
from waitress import serve

app = Flask("Mikrotik-Bandwidth-Monitor-Exporter")

FORMAT_STRING = 'level=%(levelname)s datetime=%(asctime)s %(message)s'
logging.basicConfig(encoding='utf-8',
                    level=logging.DEBUG,
                    format=FORMAT_STRING)

log = logging.getLogger('waitress')
log.disabled = True

bytes_down = Gauge('bytes_down', 'Bytes down for given host',
                   labelnames=['mac', 'name'])
bytes_up = Gauge('bytes_up', 'Bytes up for given host',
                 labelnames=['mac', 'name'])


@dataclass(frozen=True)
class MikrotikDataclass:
    """Class for Mikrotik data."""
    webfig_url: str
    api_login: str
    api_password: str
    verify_ssl: bool = False
    request_timeout: int = 30

    def generate_auth(self) -> requests.auth.HTTPBasicAuth:
        """Return HTTPBasicAuth with login data."""
        return requests.auth.HTTPBasicAuth(self.api_login, self.api_password)


def is_http_code_ok(request_status_code: requests.codes) -> bool:
    """Check whether request's HTTP status code was OK."""
    # pylint: disable=no-member
    return request_status_code == requests.codes.ok


@app.route("/metrics")
def get_kid_control_data_metrics() -> Callable:
    """Function to query MikroTik Kid Control data to return the metrics."""
    mikrotik_data = current_app.config['MIKROTIK_DATA']
    mikrotik_auth = mikrotik_data.generate_auth()
    data_request = requests.get(
            f"{mikrotik_data.webfig_url}/rest/ip/kid-control/device",
            auth=mikrotik_auth,
            verify=mikrotik_data.verify_ssl,
            timeout=mikrotik_data.request_timeout,
    )
    if is_http_code_ok(data_request.status_code):
        devices = {
            entry['mac-address'].upper(): entry
            for entry in data_request.json()
        }
        for device, device_data in devices.items():
            device_name = device_data['name']
            if not device_name:
                device_name = device
            bytes_down.labels(mac=device, name=device_name).\
                set(device_data['bytes-down'])
            bytes_up.labels(mac=device, name=device_name).\
                set(device_data['bytes-up'])
        reset_request = requests.post(
            f"{mikrotik_data.webfig_url}/rest/ip/kid-control/device/"
            "reset-counters",
            auth=mikrotik_auth,
            headers={"Content-Type": "application/json"},
            data={},
            verify=mikrotik_data.verify_ssl,
            timeout=mikrotik_data.request_timeout,
        )
        if not is_http_code_ok(reset_request.status_code):
            raise requests.exceptions.HTTPError("Reset request failed")
    else:
        raise requests.exceptions.HTTPError("Data request failed")

    return make_wsgi_app()


@app.route("/")
def main_page() -> str:
    """Serve the main page.

    Returns:
        str: basic HTML with main page
    """
    return ("<h1>Welcome to Mikrotik Bandwidth-Monitor data exporter.</h1>" +
            "Metrics are available: <a href='/metrics'>here</a>.")


def main():
    """Main processing function."""
    address = os.getenv("LISTEN_ADDRESS", "0.0.0.0")
    port = os.getenv("LISTEN_PORT", "9180")
    logging.info("Starting Mikrotik-Bandwidth-Monitor-Exporter on "
                 "http://localhost:%s", str(port))
    mikrotik_webfig_url = f"{os.getenv('MIKROTIK_REST_API_METHOD', 'http')}" \
        f"://{os.getenv('MIKROTIK_IP', '192.168.88.1')}:" \
        f"{os.getenv('MIKROTIK_WEBFIG_PORT', '80')}"
    mikrotik_dataclass = MikrotikDataclass(
        webfig_url=mikrotik_webfig_url,
        api_login=os.getenv("MIKROTIK_USER", "admin"),
        api_password=os.getenv("MIKROTIK_PASSWORD", ""),
        verify_ssl=os.getenv("MIKROTIK_REST_API_VERIFY_SSL", "0") == "1",
        request_timeout=int(os.getenv("MIKROTIK_REQUEST_TIMEOUT", "30"))
    )
    if not mikrotik_dataclass.verify_ssl:
        requests.packages.urllib3.\
            disable_warnings()  # pylint: disable=no-member
    app.config['MIKROTIK_DATA'] = mikrotik_dataclass
    serve(app, host=address, port=int(port))
