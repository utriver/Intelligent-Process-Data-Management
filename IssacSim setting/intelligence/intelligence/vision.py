import h5py
import os
import time
from pymongo import MongoClient
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import numpy as np
import cv2

class ImageEventHandler(FileSystemEventHandler):
    def __init__(self):
        self.mongo_client = MongoClient('mongodb://172.18.73.63:27017/')
        self.db = self.mongo_client['smart_factory_db']
        self.collection = self.db['image_files']
        self.hdf5_files = self.db['vision_to_hdf5_files']
        self.hdf5_dir = "vision_to_hdf5"
        
        if not os.path.exists(self.hdf5_dir):
            os.makedirs(self.hdf5_dir)
    
    def get_daily_h5_file(self):
        today = datetime.now().strftime('%Y%m%d')
        h5_filename = os.path.join(self.hdf5_dir, f'vision_data_{today}.h5')
        
        # HDF5 파일 정보를 MongoDB에 업데이트
        h5_doc = {
            'filename': f'vision_data_{today}.h5',
            'full_path': h5_filename,
            'created_date': today,
            'last_updated': datetime.now(),
            'total_images': 0,
            'status': 'active'
        }
        
        # upsert를 사용하여 새로 생성하거나 업데이트
        self.hdf5_files.update_one(
            {'filename': h5_doc['filename']},
            {'$set': h5_doc},
            upsert=True
        )
        
        return h5_filename
        
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(('.jpg', '.png', '.jpeg')):
            try:
                image_path = event.src_path
                time.sleep(0.1)
                
                img = cv2.imread(image_path)
                if img is None:
                    print(f"Failed to read image: {image_path}")
                    return
                
                h5_filename = self.get_daily_h5_file()
                current_time = datetime.now()
                image_name = os.path.basename(image_path).split('.')[0]
                
                with h5py.File(h5_filename, 'a') as f:
                    if 'images' not in f:
                        images_group = f.create_group('images')
                        timestamps_group = f.create_group('timestamps')
                    else:
                        images_group = f['images']
                        timestamps_group = f['timestamps']
                    
                    if img.size == 0:
                        print(f"Empty image data for: {image_path}")
                        return
                    
                    # Store image with original filename
                    images_group.create_dataset(image_name, data=img, compression='gzip')
                    
                    # Store datetime components separately
                    timestamp_str = current_time.strftime('%Y-%m-%d %H:%M:%S.%f')
                    timestamps_group.create_dataset(image_name, data=timestamp_str)
                    
                    f.attrs['last_updated'] = current_time.isoformat()
                    f.attrs['total_images'] = len(images_group)
                    total_images = len(images_group)
                self.hdf5_files.update_one(
                    {'filename': os.path.basename(h5_filename)},
                    {
                        '$set': {
                            'last_updated': current_time,
                            'total_images': total_images
                        },
                        '$push': {
                            'image_list': {
                                'image_name': image_name,
                                'timestamp': timestamp_str
                            }
                        }
                    }
                )
                doc = {
                    'image_name': image_name,
                    'hdf5_file': os.path.basename(h5_filename),
                    'created_at': current_time,
                    'timestamp': timestamp_str,
                    'image_size': img.shape
                }
                self.collection.insert_one(doc)
                print(f"Added {image_name} to {h5_filename} with datetime {current_time}")
                
            except Exception as e:
                print(f"Error processing {image_path}: {str(e)}")
                import traceback
                traceback.print_exc()

def start_monitoring(path_to_watch):
    if not os.path.exists(path_to_watch):
        os.makedirs(path_to_watch)
        print(f"Created directory: {path_to_watch}")
        
    event_handler = ImageEventHandler()
    observer = Observer()
    observer.schedule(event_handler, path_to_watch, recursive=False)
    observer.start()
    print(f"Started monitoring: {path_to_watch}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    WATCH_PATH = "C:/isaacsim_4.2.0/intelligence/vision_raw"
    start_monitoring(WATCH_PATH)