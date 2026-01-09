import time
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import shutil

client = MongoClient("mongodb://localhost:27017/")
db = client["smart_factory_db"]
print("MongoDB 연결 확인:", client.list_database_names())
datetime_fields = {
    "product_inventory": ["event_time"],
    "robot_operations": ["operation_time"]
}

def insert_csv(path: Path):
    name = path.stem
    if name not in datetime_fields:
        return

    df = pd.read_csv(path)
    for col in datetime_fields[name]:
        df[col] = pd.to_datetime(df[col])

    # ↓ 여기를 아래로 교체 ↓
    time_col = datetime_fields[name][0]
    last = db[name].find_one({}, sort=[(time_col, -1)])
    if last:
        new_df = df[df[time_col] > last[time_col]]
    else:
        new_df = df

    if not new_df.empty:
        db[name].insert_many(new_df.to_dict("records"))
        print(f"✅ {name}: {len(new_df)}건 삽입 완료")
    else:
        print(f"ℹ {name}: 신규 레코드 없음")

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith(".csv"):
            time.sleep(0.5)
            insert_csv(Path(event.src_path))

    def on_moved(self, event):
        # 에디터가 temp → real 로 바꿀 때
        if event.dest_path.endswith(".csv"):
            time.sleep(0.5)
            insert_csv(Path(event.dest_path))

if __name__ == "__main__":
    watch_dir = Path("csv_path")
    watch_dir.mkdir(exist_ok=True)

    print(f"📥 기존 CSV 먼저 삽입 시작")
    for file in watch_dir.glob("csv_files-upload"):
        insert_csv(file)

    print(f"👁️ 실시간 감시 시작: {watch_dir.resolve()}")
    obs = Observer()
    obs.schedule(Handler(), str(watch_dir), recursive=False)
    obs.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        obs.stop()
        obs.join()
