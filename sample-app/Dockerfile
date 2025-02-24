FROM python:3.9-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .

RUN opentelemetry-bootstrap --action=install

ENV OTEL_SERVICE_NAME="random-number-service"
ENV OTEL_TRACES_EXPORTER="otlp"
ENV OTEL_METRICS_EXPORTER="otlp"
ENV OTEL_LOGS_EXPORTER="otlp"
ENV OTEL_EXPORTER_OTLP_ENDPOINT="http://otel-collector:4318"
ENV OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
ENV OTEL_RESOURCE_ATTRIBUTES="service.version=1.0,deployment.environment=test"
ENV OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED="true"

CMD ["opentelemetry-instrument", "python", "app.py"]

EXPOSE 8000