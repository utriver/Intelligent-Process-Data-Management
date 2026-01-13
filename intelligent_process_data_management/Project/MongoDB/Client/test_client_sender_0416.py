import requests
import random
from datetime import datetime, timedelta


url = 'http://172.19.87.149:5000'

base_date = datetime(2025, 4, 1)

def send_dummy_data():
    base_date = datetime(2025, 4, 1)
    dummy_data = []

    for i in range(7):
        date = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
        item = {
            "date": date,
            "production": random.randint(1500, 2200),
            "cycle_count": random.randint(300, 350),
            "defect_ratio": round(random.uniform(9.0, 19.0), 2)
        }
        dummy_data.append(item)

    response = requests.post(f'{url}/upload', json=dummy_data)
    print("📡 서버 응답:", response.status_code)
    print(response.json())

def send_dye_stock():
    dye_data = {
        "type": "dye_stock",
        "dye_inventory": {
            "청색": random.randint(100, 130),
            "적색": random.randint(70, 90),
            "노랑": random.randint(40, 60),
            "흑색": random.randint(30, 50)
        }
    }
    response = requests.post(f'{url}/upload', json=dye_data)
    print("🎨 염료 재고 응답:", response.status_code)
    print(response.json())

    
def get_all_data():
    response = requests.get(f'{url}/get_all')
    print("📋 전체 데이터:")
    print(response.json())

def get_dye_stock():
    response = requests.get(f'{url}/get/dye_stock')
    print("🎯 최신 염료 재고:")
    print(response.json())

def clear_all_data():
    response = requests.post(f'{url}/clear_all_data')
    print("🗑️ 전체 데이터 삭제 결과:")
    print(response.json())

def main():
    while True:
        print("\n====== 작업 선택 ======")
        print("1. 랜덤 생산 데이터 전송")
        print("2. 랜덤 염료 재고 전송")
        print("3. 전체 데이터 조회")
        print("4. 염료 재고 조회")
        print("5. 전체 데이터 삭제")
        print("0. 종료")
        choice = input("번호 선택: ").strip()

        if choice == '1':
            send_dummy_data()
        elif choice == '2':
            send_dye_stock()
        elif choice == '3':
            get_all_data()
        elif choice == '4':
            get_dye_stock()
        elif choice == '5':
            clear_all_data()
        elif choice == '0':
            print("종료합니다.")
            break
        else:
            print("잘못된 입력입니다.")

if __name__ == '__main__':
    main()