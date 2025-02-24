from flask import Flask, jsonify
from random import randint
from datetime import datetime
import logging
import os
from opentelemetry.instrumentation.flask import FlaskInstrumentor

app = Flask(__name__)
PORT = os.getenv("PORT", 8000)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
FlaskInstrumentor().instrument_app(app)

@app.route("/random")
def get_random_data():
    timestamp = datetime.now().isoformat()
    value = randint(1, 100)

    logger.info("Generating random data {timestamp=%s, value=%s}", timestamp, value)
    return jsonify({
        "timestamp": timestamp,
        "value": value
    })

if __name__ == "__main__":
    logger.info(f"Starting app on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)