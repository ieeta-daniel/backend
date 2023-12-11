from flask import Flask, request, jsonify
from handler import EndpointHandler
from healthcheck import HealthCheck
# from waitress import serve
import logging

app = Flask(__name__)

health = HealthCheck(app, "/healthz")

handler = EndpointHandler("something")

# filename='record.log',
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

logging.info("Starting the application")


def health_check():
    return True, "Hello, World!"

health.add_check(health_check)


@app.route("/", methods=["POST"])
def root():
    if request.method == "POST":
        if request.is_json:
            input_data = request.get_json()
            result = handler(input_data)
            app.logger.info(f"Received POST request with JSON data: {input_data}")
            return jsonify(result), 200

        app.logger.warning("Received POST request with no JSON data")
        return jsonify({"error": "Unsupported Media Type"}), 415


if __name__ == "__main__":
    # waitress.serve(app, port=8000, threads=6)
    app.run(debug=True, port=8000)
