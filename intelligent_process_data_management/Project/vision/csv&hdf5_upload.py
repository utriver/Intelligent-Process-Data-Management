import os
import cv2
import h5py
import time
import numpy as np
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from influxdb import InfluxDBClient
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 폴더 경로
CSV_DIR = 'csv_logs/'
HDF5_DIR = 'hdf5_storage/'
os.makedirs(HDF5_DIR, exist_ok=True)
os.makedirs(CSV_DIR, exist_ok=True)

# 데이터베이스 설정
MONGODB_URL = 'mongodb://localhost:27017/'
INFLUXDB_CONFIG = {
    'host': 'localhost',
    'port': 8086,
    'username': 'admin',
    'password': '12345',
    'database': 'solutionist'
}
class MongoDBUploader:
    def __init__(self, url='mongodb://localhost:27017/', db_name='smart_factory_db'):
        self.client = MongoClient(url)
        self.db = self.client[db_name]
        self.logger = logging.getLogger(__name__)
        self.last_upload_time = {}

    def upload_csv_data(self, csv_path, collection_name):
        """CSV 파일의 새로운 데이터만 MongoDB에 업로드"""
        try:
            collection = self.db[collection_name]
            df = pd.read_csv(csv_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # 마지막 업로드 시간 이후의 데이터만 필터링
            last_time = self.last_upload_time.get(collection_name)
            if last_time:
                new_data = df[df['timestamp'] > last_time]
            else:
                # 컬렉션의 마지막 타임스탬프 확인
                last_doc = collection.find_one(sort=[('timestamp', -1)])
                if last_doc and 'timestamp' in last_doc:
                    last_time = pd.to_datetime(last_doc['timestamp'])
                    new_data = df[df['timestamp'] > last_time]
                else:
                    new_data = df

            if new_data.empty:
                self.logger.debug(f"새로운 데이터 없음: {collection_name}")
                return 0

            # 데이터 변환 및 업로드
            records = new_data.to_dict('records')
            for record in records:
                record['timestamp'] = record['timestamp'].to_pydatetime()
                collection.update_one(
                    {'timestamp': record['timestamp']},
                    {'$set': record},
                    upsert=True
                )

            # 마지막 업로드 시간 업데이트
            self.last_upload_time[collection_name] = new_data['timestamp'].max()
            
            self.logger.info(f"MongoDB 업로드 완료: {collection_name} ({len(records)} 레코드)")
            return len(records)

        except Exception as e:
            self.logger.error(f"MongoDB 업로드 실패 {collection_name}: {str(e)}")
            return 0
        
    def upload_hdf5_filename(self, filename, date_str):
        """HDF5 파일 이름과 처리 일시를 MongoDB에 기록"""
        try:
            collection = self.db['hdf5_files']
            document = {
                'filename': filename,
                'timestamp': datetime.now(),
                'date_str': date_str
            }
            collection.insert_one(document)
            self.logger.info(f"HDF5 파일 정보 MongoDB에 저장: {filename}")
        except Exception as e:
            self.logger.error(f"HDF5 파일 정보 MongoDB 저장 실패: {str(e)}")

class DataLogger:
    def __init__(self):
        self.mongo_client = MongoClient(MONGODB_URL)
        self.influx_client = InfluxDBClient(**INFLUXDB_CONFIG)
        self.db = self.mongo_client.smart_factory_db
        self.collection = self.db.vision_datasets
        self.mongo_uploader = MongoDBUploader(MONGODB_URL)
        
        
        # 필드 매핑 정의
        self.field_groups = {
            'robot_arm_torque': ['joint_0', 'joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5'],
            'logistics_robot_position_rotation': ['x', 'y'],
            'finished_product_count': ['normal_count', 'defect_count'],
            'pressure_Mpa': ['pressure_mpa'],
            'temperature_c': ['temperature_c'],
            'linear_velocity_mm_s': ['linear_velocity_mm_s'],
            'humidity_percent': ['humidity_percent']
        }

    def get_hdf5_path(self):
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"dataset_{date_str}.h5"
        return os.path.join(HDF5_DIR, filename), date_str

    def export_process_data(self):
        logger.info("InfluxDB 데이터 내보내기 시작")
        date_str = datetime.now().strftime('%Y-%m-%d')
        data_folder = os.path.join(CSV_DIR, date_str)
        os.makedirs(data_folder, exist_ok=True)
        
        logger.info("데이터 내보내기 시작")
        current_time = datetime.now()
        # 모든 measurement에서 데이터 조회
        for measurement in self.influx_client.get_list_measurements():       
            measurement_name = measurement['name']
            
            query = f"""
                SELECT *
                FROM {measurement_name}
                WHERE time > now() - 1m
                ORDER BY time ASC
            """
            
            try:
                result = self.influx_client.query(query)
                points = list(result.get_points())
                
                if not points:
                    logger.debug(f"{measurement_name}에 새로운 데이터 없음")
                    continue
                    
                df = pd.DataFrame(points)
                if 'time' not in df.columns:
                    continue
                    
                # 시간 처리 및 정렬
                df['timestamp'] = pd.to_datetime(df['time'])
                df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Seoul').dt.tz_localize(None)
                df = df.drop('time', axis=1)
                df = df.sort_values('timestamp')  # 시간순 정렬
                
                # 각 필드 그룹별로 데이터 저장
                for group_name, fields in self.field_groups.items():
                    available_fields = [f for f in fields if f in df.columns]
                    if not available_fields:
                        continue
                        
                    data = df[['timestamp'] + available_fields].copy()
                    csv_path = os.path.join(data_folder, f"{group_name}.csv")
                    
                    if os.path.exists(csv_path):
                        existing = pd.read_csv(csv_path)
                        existing['timestamp'] = pd.to_datetime(existing['timestamp'])
                        data = pd.concat([existing, data])
                        data = data.drop_duplicates('timestamp', keep='last')
                        data = data.sort_values('timestamp')  # 병합 후 다시 정렬
                    
                    data.to_csv(csv_path, index=False)
                    logger.info(f"{group_name} 저장 완료 (레코드 수: {len(data)})")
                        
            except Exception as e:
                logger.error(f"{measurement_name} 처리 중 오류: {str(e)}")
    def update_hdf5(self):
        hdf5_path, date_str = self.get_hdf5_path()
        data_folder = os.path.join(CSV_DIR, date_str)
        
        if not os.path.exists(data_folder):
            logger.warning(f"데이터 폴더 없음: {data_folder}")
            return
                    
        with h5py.File(hdf5_path, 'a') as f:
            for filename in os.listdir(data_folder):
                if not filename.endswith('.csv'):
                    continue
                    
                group_name = filename.replace('.csv', '')
                csv_path = os.path.join(data_folder, filename)
                
                try:
                    # CSV 파일 읽기
                    new_df = pd.read_csv(csv_path)
                    if new_df.empty:
                        continue

                    new_df['timestamp'] = pd.to_datetime(new_df['timestamp'])
                    new_df = new_df.sort_values('timestamp')

                    grp = f.require_group(group_name)
                    
                    # 기존 HDF5 데이터 로드
                    if set(new_df.columns).issubset(grp.keys()):
                        existing_data = {}
                        for col in new_df.columns:
                            if col in grp:
                                existing_data[col] = grp[col][:]
                                if col == 'timestamp':
                                    existing_data[col] = [ts.decode() for ts in existing_data[col]]
                        
                        # 기존 데이터를 DataFrame으로 변환
                        existing_df = pd.DataFrame(existing_data)
                        if not existing_df.empty:
                            existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'])
                            
                            # 새 데이터와 기존 데이터 병합
                            merged_df = pd.concat([existing_df, new_df])
                            merged_df = merged_df.drop_duplicates(subset=['timestamp'], keep='last')
                            merged_df = merged_df.sort_values('timestamp')
                    else:
                        merged_df = new_df

                    # 기존 데이터셋 삭제
                    for col in merged_df.columns:
                        if col in grp:
                            del grp[col]

                    # 병합된 데이터 저장
                    for col in merged_df.columns:
                        try:
                            data = merged_df[col].values
                            if col == 'timestamp':
                                data = np.array(merged_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S.%f')).astype('S')
                            else:
                                if 'raw_material' in col:
                                    data = data.astype(np.int32)
                                else:
                                    data = data.astype(np.float64)
                            grp.create_dataset(col, data=data, compression="gzip")
                        except Exception as e:
                            logger.error(f"컬럼 {col} 저장 중 오류: {str(e)}")
                            continue
                    
                    logger.info(f"HDF5 누적 업데이트 완료: {filename} (전체 레코드 수: {len(merged_df)})")
                    
                except Exception as e:
                    logger.error(f"HDF5 업데이트 실패 {filename}: {str(e)}")
                    continue
            self.mongo_uploader.upload_hdf5_filename(hdf5_path, date_str)
            
            hdf5_path, date_str = self.get_hdf5_path()
            data_folder = os.path.join(CSV_DIR, date_str)
            
            if not os.path.exists(data_folder):
                logger.warning(f"데이터 폴더 없음: {data_folder}")
                return
                    
            with h5py.File(hdf5_path, 'a') as f:
                for filename in os.listdir(data_folder):
                    if not filename.endswith('.csv'):
                        continue
                        
                    group_name = filename.replace('.csv', '')
                    csv_path = os.path.join(data_folder, filename)
                    
                    try:
                        df = pd.read_csv(csv_path)
                        if df.empty:
                            continue

                        df['timestamp'] = pd.to_datetime(df['timestamp'])
                        df = df.sort_values('timestamp')

                        grp = f.require_group(group_name)
                        
                        # 타임스탬프 비교 로직 수정
                        if 'timestamp' in grp:
                            last_ts = pd.to_datetime(grp['timestamp'][-1].decode())
                            df = df[df['timestamp'] > last_ts]
                            
                            if df.empty:
                                logger.debug(f"새로운 데이터 없음: {filename}")
                                continue

                        # 데이터셋 새로 생성
                        for col in df.columns:
                            if col in grp:
                                del grp[col]
                            
                            data = df[col].values
                            if col == 'timestamp':
                                data = np.array(df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S.%f')).astype('S')
                            else:
                                data = data.astype(float)
                            
                            grp.create_dataset(col, data=data, compression="gzip")
                        
                        logger.info(f"HDF5 업데이트 완료: {filename} ({len(df)} 레코드)")
                            
                    except Exception as e:
                        logger.error(f"HDF5 업데이트 실패 {filename}: {str(e)}")
                        continue  

def main():
    data_logger = DataLogger()
    
    observer = Observer()

    observer.start()

    last_upload = time.time()

    try:
        while True:
            now = time.time()
            data_logger.export_process_data()
            data_logger.update_hdf5()
            date_str = datetime.now().strftime('%Y-%m-%d')
            csv_day_folder = os.path.join(CSV_DIR, date_str)
                
            if now - last_upload >= 1:
                date_str = datetime.now().strftime('%Y-%m-%d')
                csv_day_folder = os.path.join(CSV_DIR, date_str)
                if os.path.exists(csv_day_folder):
                    for group in data_logger.field_groups:
                        csv_path = os.path.join(csv_day_folder, f"{group}.csv")
                        if os.path.exists(csv_path):
                            uploaded_count = data_logger.mongo_uploader.upload_csv_data(csv_path, group)
                            logger.info(f"{group} → MongoDB 업로드 완료 ({uploaded_count}개)")
                else:
                    logger.warning(f"CSV 폴더 없음: {csv_day_folder}")
                last_upload = now
            time.sleep(0.01)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    main()