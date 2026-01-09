from influxdb import InfluxDBClient

DB_NAME = 'solutionist'
HOST = 'localhost'
PORT = 8086
USERNAME = 'admin'
PASSWORD = '12345'

def connect():
    return InfluxDBClient(host=HOST, port=PORT, username=USERNAME, password=PASSWORD)

def create_db(client):
    if DB_NAME not in [db['name'] for db in client.get_list_database()]:
        client.create_database(DB_NAME)
        print(f"✅ 데이터베이스 '{DB_NAME}' 생성 완료")
    else:
        print(f"ℹ️ 데이터베이스 '{DB_NAME}' 이미 존재")

def show_dbs(client):
    print("📂 현재 데이터베이스 목록:")
    for db in client.get_list_database():
        print(f" - {db['name']}")

def delete_db(client):
    if DB_NAME in [db['name'] for db in client.get_list_database()]:
        client.drop_database(DB_NAME)
        print(f"🗑️ 데이터베이스 '{DB_NAME}' 삭제 완료")
    else:
        print(f"⚠️ 데이터베이스 '{DB_NAME}' 존재하지 않음")

def main():
    client = connect()

    while True:
        print("\n📡 InfluxDB 관리 메뉴")
        print("1. 데이터베이스 생성")
        print("2. 데이터베이스 목록 조회")
        print("3. 데이터베이스 삭제")
        print("4. 종료")
        choice = input("👉 번호 선택: ").strip()

        if choice == "1":
            create_db(client)
        elif choice == "2":
            show_dbs(client)
        elif choice == "3":
            delete_db(client)
        elif choice == "4":
            print("👋 종료합니다.")
            break
        else:
            print("❌ 유효하지 않은 입력입니다. 다시 선택하세요.")

if __name__ == "__main__":
    main()
