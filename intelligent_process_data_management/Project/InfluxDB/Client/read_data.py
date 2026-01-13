from influxdb import InfluxDBClient
import pandas as pd
import time

# InfluxDB 연결
client = InfluxDBClient(host='localhost', port=8086)
client.switch_database('solutionist')

while True:
    try:
        # 모든 measurement 불러오기
        measurements = [m['name'] for m in client.query('SHOW MEASUREMENTS').get_points()]

        for measurement in measurements:
            # 최신 1개 데이터만 가져오기 (DESC 정렬 후 LIMIT 1)
            query = f"SELECT * FROM {measurement} ORDER BY time DESC LIMIT 1"
            result = client.query(query)
            points = list(result.get_points())

            if points:
                df = pd.DataFrame(points)
                print(f"\n==== 최신 {measurement} 데이터 ====")
                print(df)

        time.sleep(0.1)  # 주기 조절 (1초 간격)

    except KeyboardInterrupt:
        print("사용자 종료")
        break

    except Exception as e:
        print(f"❗ 오류 발생: {e}")
        time.sleep(1)
