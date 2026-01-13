from flask import Flask, flash, session, send_from_directory, send_file, Response, redirect, url_for, request, session, abort, jsonify, render_template
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bson import objectid
import pandas as pd
import os

# Flask 애플리케이션 설정
app = Flask(__name__)
UPLOAD_FOLDER = 'hdf-files-upload'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# MongoDB 클라이언트 설정
client = MongoClient('mongodb://localhost:27017/')  # MongoDB 서버 주소
db = client['your_database_name']  # 데이터베이스 이름
collection = db['your_collection_name']  # 컬렉션 이름

# 업로드 폴더가 존재하지 않으면 생성
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # MongoDB에 파일 이름 저장
        collection.insert_one({"filename": filename})

        return jsonify({"message": f"File {filename} has been uploaded and saved."}), 200

@app.route('/files', methods=['GET'])
def list_files():
    files = collection.find()
    file_list = [file['filename'] for file in files]
    return jsonify(file_list), 200

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)