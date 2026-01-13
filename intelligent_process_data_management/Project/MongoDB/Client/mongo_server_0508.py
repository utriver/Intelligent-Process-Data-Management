from flask import Flask, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)
client = MongoClient('mongodb://localhost:27017/')
db = client['test_0416']
collection = db['data_collection1']

@app.route('/upload', methods=['POST'])
def upload_data():
    try:
        data = request.json

        if isinstance(data, dict) and data.get("type") == "dye_stock":
            collection.delete_many({"type": "dye_stock"})
            collection.insert_one(data)
            return jsonify({"status": "success", "inserted": 1})

        if isinstance(data, list):
            collection.insert_many(data)
            return jsonify({"status": "success", "inserted": len(data)})

        if isinstance(data, dict):
            collection.insert_one(data)
            return jsonify({"status": "success", "inserted": 1})

        return jsonify({"status": "error", "message": "Invalid data format"}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_all', methods=['GET'])
def get_all():
    try:
        docs = list(collection.find({}, {'_id': 0}))  # _id 제외
        return jsonify(docs)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/get/dye_stock', methods=['GET'])
def get_dye_stock():
    try:
        dye = collection.find_one({"type": "dye_stock"}, {'_id': 0})
        if dye:
            return jsonify(dye)
        else:
            return jsonify({"status": "not_found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/clear_all_data', methods=['POST'])
def clear_all_data():
    try:
        result = collection.delete_many({})
        return jsonify({"status": "cleared", "deleted_count": result.deleted_count})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)