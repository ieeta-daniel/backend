from flask import Flask, request, jsonify
from handler import EndpointHandler
from healthcheck import HealthCheck
import logging

# from waitress import serve

app = Flask(__name__)

health = HealthCheck(app, "/healthz")

handler = EndpointHandler("something")

logging.basicConfig(filename='record.log',
                    level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

logging.info("Starting the application")


def health_check():
    return True, "Application is healthy"


health.add_check(health_check)


@app.route("/", methods=["GET", "POST"])
def root():
    if request.method == "GET":
        app.logger.info("Received GET request")
        return "Hello, World!", 200

    elif request.method == "POST":
        if request.is_json:
            input_data = request.get_json()
            result = handler(input_data)
            app.logger.info(f"Received POST request with JSON data: {input_data}")
            return jsonify(result), 200
        else:
            app.logger.warning("Received POST request with no JSON data")
            return jsonify({"error": "Unsupported Media Type"}), 415


if __name__ == "__main__":
    # waitress.serve(app, port=8000, threads=6)
    app.run(debug=True)
