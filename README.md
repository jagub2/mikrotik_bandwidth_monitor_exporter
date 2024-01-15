# MikroTik Bandwidth Monitor Exporter

This is a bandwidth monitor exporter for Prometheus intended for use with MikroTiks.

## How to set up MikroTik router

This exporter is based on MikroTik's Kid-control mechanism. To enable it, you need to do the following:

`/ip kid-control add name=Monitor mon=0s-1d tue=0s-1d wed=0s-1d thu=0s-1d fri=0s-1d sat=0s-1d sun=0s-1d`

The name can be arbitrary, it does not matter.

Then I strongly recommend to create a separate account than admin just for the sake of this exporter. Remember that that you need to give this account `write` permissions, as the exporter resets device counters after each query (to keep track of the used bandwidth).

The exporter relies on the REST API, so you need make ensure WebFig is running.

## How to run it

The repository contains a Docker stack with Grafana and Prometheus as a sample distribution. You can tune their needs, especially to integrate this exporter for your needs.

Prometheus is set to poll the exporter every 15 minutes. I tried 1 minute intervals and it just worked fine for my hAP ac.

The exporter relies on environment variables, you can set:

- `MIKROTIK_IP`: IP to your MikroTik router (default value: `192.168.88.1`),
- `MIKROTIK_WEBFIG_PORT`: port number to your MikroTik router WebFig (default value: `80`),
- 1MIKROTIK_REST_API_METHOD`: method of querying WebFig, one could use `http` or `https` (default value: `http`),
- `MIKROTIK_USER`: username of used account on the MikroTik (default: `admin`, however I suggest to change it),
- `MIKROTIK_PASSWORD`: self explainatory, password to the user account on the MikroTik,
- `MIKROTIK_REST_API_VERIFY_SSL`: Bash "boolean" whether REST API SSL certificate should be checked (default: `0` (False)),
- `MIKROTIK_REQUEST_TIMEOUT`: timeout for quering MikroTik WebFig,
- `LISTEN_ADDRESS`: address to listen on (default: `0.0.0.0`, good enough for Docker, I suggest changing it on bare-metal deployments),
- `LISTEN_PORT`: port number to listeon on (default: `9180`), keep in mind to update Prometheus config.

## Something's not working?

Well, I tested it on my environment, it worked. I guess we could find a solution, feel free to contact me.

## License

This project is licensed under MIT license, [more details here](LICENSE.txt).