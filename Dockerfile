FROM python:3.12-alpine AS builder
WORKDIR /app
COPY src pyproject.toml ./
RUN python -m pip install --no-cache-dir pip setuptools && \
	python -m pip install --no-cache-dir --prefix=/install . && \
	find /install '(' -type d -regex '.*/tests?' ')' -o \
		'(' -type f  -regex '.*/[^/]+\.py[co]$' ')' \
		-print -exec rm -rf '{}' + && \
	python -m pip cache purge && \
	rm -rf /app/build

FROM python:3.12-alpine
RUN adduser -D mikrotik

WORKDIR /app
COPY --from=builder /install /usr/local

USER mikrotik
CMD ["mikrotik_bandwidth_monitor_exporter"]
HEALTHCHECK --timeout=10s CMD wget -T 1 --spider http://localhost:9180/
