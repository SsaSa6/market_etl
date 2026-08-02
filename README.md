# market_etl

업비트 시세를 주기적으로 수집해 MySQL에 적재하고, 일별 집계 테이블까지 생성하는 데이터 파이프라인.

데이터 엔지니어링 학습 목적으로 만들고 있음.

## 목표

> 업비트 시세를 주기적으로 자동 수집해 MySQL에 적재하고, 일별 집계 테이블까지 생성한다.

### 완료 조건

- [ ] 로컬 PC가 꺼져 있어도 계속 동작한다 (클라우드 배포)
- [ ] 두 번 실행해도 데이터가 중복되거나 깨지지 않는다 (멱등성)
- [ ] 실패하면 감지할 수 있다 (알림 / 로그)
- [ ] 한 달치 이상 데이터가 실제로 축적되어 있다
- [ ] 처음 보는 사람이 README만 보고 5분 안에 실행할 수 있다
- [ ] raw 테이블과 집계(mart) 테이블이 분리되어 있다

## 아키텍처

```
Upbit API  →  extract.py  →  load.py  →  MySQL (raw)  →  SQL 집계  →  MySQL (mart)
```

### ELT를 택한 이유

원본을 변환 없이 raw 테이블에 적재하고, 집계는 DB 안에서 SQL로 수행한다.

- **재처리가 가능하다.** 집계 로직에 오류가 있어도 원본이 남아 있어 다시 계산할 수 있다. 시세 API는 과거 데이터를 돌려주지 않으므로, 적재 시점에 원본을 잃으면 복구가 불가능하다
- **변환 로직 수정이 빠르다.** 파이썬 코드 수정·재배포보다 SQL 수정이 가볍다
- **데이터 규모가 작다.** 1분 주기 기준 하루 약 1,440행으로 DB가 충분히 감당한다

원본에 민감정보가 있거나 데이터 규모가 커서 적재 비용이 문제가 되는 경우라면 ETL이 적합하지만, 이 프로젝트는 해당하지 않는다.

## 설계 결정

| 항목           | 결정                       | 이유                                                                                                        |
| -------------- | -------------------------- | ----------------------------------------------------------------------------------------------------------- |
| DB             | MySQL                      | 사용 경험이 있어 학습 초점을 파이프라인 구조에 둘 수 있음. 후반부에 PostgreSQL 전환을 별도 과제로 진행 예정 |
| 데이터 소스    | 업비트 Quotation API       | 인증키 불필요, 초 단위 변동, 분당 600회 제한으로 여유 있음                                                  |
| 대상 종목      | `KRW-BTC` 단일             | 완주를 우선. 종목 확장은 파라미터 추가만으로 가능하도록 스키마에 `market` 컬럼 유지                         |
| 금액·수량 타입 | `DECIMAL`                  | `FLOAT`은 유효숫자 약 7자리로, 누적 거래대금에서 수천 원 단위 오차가 발생함을 실측으로 확인                 |
| 중복 판단 기준 | `UNIQUE (market, slot_at)` | 재실행 시 중복 적재를 DB 레벨에서 차단                                                                      |
| DB 실행 환경   | Docker 컨테이너            | 이후 추가할 Airflow와 같은 Compose 네트워크에 두어 서비스 이름으로 통신. 클라우드 배포 시에도 구성이 유지됨 |
| DB 접속 계정   | 전용 계정 (`etl_user`)     | 파이프라인은 지정된 DB에만 접근. root 권한 노출을 피함                                                     |

### 시각 컬럼을 세 종류로 나눈 이유

| 컬럼              | 의미                                      | 역할             |
| ----------------- | ----------------------------------------- | ---------------- |
| `trade_timestamp` | 거래소에서 체결이 일어난 시각             | 원본 데이터      |
| `collected_at`    | API를 실제로 호출한 시각                  | 수집 지연 측정   |
| `slot_at`         | 이 데이터가 속한 수집 슬롯 (초 단위 절삭) | **중복 판단 키** |

`collected_at`을 키로 쓰면 재실행할 때마다 값이 달라져 멱등성이 깨진다. 실행 시각이 아니라 "어느 슬롯의 데이터인가"를 키로 삼아 같은 슬롯 내 재실행을 차단한다.

## 기술 스택

- Python (`requests`, `pymysql`, `python-dotenv`)
- Docker
- MySQL
- Airflow

## 진행 상황

- [x] 업비트 API 호출 및 응답 파싱
- [x] raw 테이블 스키마 설계 및 생성
- [x] Python ↔ MySQL 연결
- [x] 모듈 분리 (`extract.py` / `db.py` / `main.py`)
- [x] 접속 정보 `.env` 분리
- [x] `load.py` — DB 적재
- [x] 멱등성 확보 (중복 실행 시 무시)
- [x] Docker로 mysql 서버 올리기
- [ ] Airflow 전환
- [ ] 일별 집계(mart) 테이블
- [ ] 실패 알림
- [ ] 대시보드
- [ ] 클라우드 배포

## 프로젝트 구조

```
market_etl/
├── ELT/
│   ├── main.py            # 진입점. slot_at 생성 및 각 단계 호출
│   ├── extract.py         # 업비트 API 호출, collected_at 생성
│   ├── load.py            # MySQL 적재 (upsert)
│   └── db.py              # DB 커넥션 생성
├── SQL/
│   └── table_sql.sql      # 테이블 DDL. 컨테이너 최초 기동 시 자동 실행
├── docker-compose.yml     # MySQL 컨테이너 정의
├── .env.example           # 필요한 환경변수 목록
└── .env                   # 실제 접속 정보 (git 추적 제외)
```

## 실행 방법

**요구 사항**: Docker, Python 3.10+

**1. 환경변수 설정**

`.env.example`을 `.env`로 복사하고 값을 채운다.

```
MYSQL_ROOT_PASSWORD=관리자_비밀번호
MYSQL_DATABASE=market_database
MYSQL_USER=etl_user
MYSQL_PASSWORD=파이프라인_계정_비밀번호
DB_HOST=localhost
DB_PORT=3308
```

`DB_PORT`는 호스트 쪽 포트다. 로컬에 MySQL이 이미 설치돼 있다면 3306과 겹치지 않는 값을 쓴다.

**2. DB 컨테이너 기동**

```bash
docker compose up -d
```

최초 기동 시 DB·계정 생성과 `SQL/table_sql.sql` 실행까지 자동으로 이뤄진다. 초기화에 30초가량 걸리므로 아래 로그에서 `ready for connections`를 확인한 뒤 진행한다.

```bash
docker compose logs db
```

**3. 파이썬 의존성 설치**

```bash
pip install requests pymysql python-dotenv
```

**4. 실행**

```bash
python ELT/main.py
```

**5. 적재 확인**

```bash
docker compose exec db mysql -u etl_user -p market_database
```

```sql
SELECT market, slot_at, trade_price FROM data_set ORDER BY slot_at DESC LIMIT 5;
```

### 참고

- 컨테이너와 데이터를 모두 삭제하려면 `docker compose down -v`. `-v`는 볼륨까지 지우므로 적재된 데이터가 사라진다
- `SQL/table_sql.sql`은 **볼륨이 비어 있을 때만** 실행된다. DDL을 수정한 뒤 반영하려면 `down -v` 후 다시 기동해야 한다
