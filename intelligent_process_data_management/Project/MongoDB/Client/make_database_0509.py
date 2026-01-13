# create_collections.py
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid

def main():
    # 1. MongoDB 서버에 접속
    client = MongoClient("mongodb://localhost:27017/")

    # 2. 데이터베이스 선택 (없으면 이 시점에 생성됨)
    db = client["smart_factory_db"]
    print("▶ 사용할 데이터베이스:", db.name)

    # 3. 생성할 컬렉션 목록
    collections_to_create = ["product_inventory", "robot_operations"]

    # 4. 기존 컬렉션 조회
    existing = db.list_collection_names()
    print("▶ 현재 컬렉션:", existing)

    # 5. 컬렉션 생성
    for coll in collections_to_create:
        if coll in existing:
            print(f"ℹ 이미 존재하는 컬렉션: {coll}")
        else:
            try:
                db.create_collection(coll)
                print(f"✅ 컬렉션 생성 완료: {coll}")
            except CollectionInvalid:
                print(f"⚠ 생성 실패 또는 이미 존재: {coll}")

    # 6. 접속 종료
    client.close()

if __name__ == "__main__":
    main()
