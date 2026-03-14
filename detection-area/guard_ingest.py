from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/ingest", methods=["POST"])
def ingest():
    data = request.get_json(silent=True)
    if data:
        print("RECEIVED EVENT:")
        print(data)
        print("-" * 40)
    else:
        print("RECEIVED EMPTY / INVALID JSON")

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    print("ADL-TEST-GUARD ingest listening on 0.0.0.0:8080")
    app.run(host="0.0.0.0", port=8080)

