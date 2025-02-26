from flask import Flask, jsonify
from random import randint
from datetime import datetime
import logging
import os
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.metrics import get_meter_provider



app = Flask("flask-app")
PORT = os.getenv("PORT", 8000)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flask-app")
FlaskInstrumentor().instrument_app(app)

meter = get_meter_provider().get_meter("flask-app", "0.1.2")

request_counter = meter.create_up_down_counter("request_count_total")

@app.route("/random")
def get_random_data():
    timestamp = datetime.now().isoformat()
    value = randint(1, 100)

    logger.info("Generating random data {timestamp=%s, value=%s}", timestamp, value)
    request_counter.add(1)
    return jsonify({
        "timestamp": timestamp,
        "value": value
    })

if __name__ == "__main__":
    logger.info(f"Starting app on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)