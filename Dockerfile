FROM python:3.12-alpine

RUN adduser -D mikrotik

WORKDIR /app
COPY src pyproject.toml ./
RUN python -m pip install . && rm -rf build

USER mikrotik
CMD ["mikrotik_bandwidth_monitor_exporter"]
HEALTHCHECK --timeout=10s CMD wget -T 1 --spider http://localhost:9180/
