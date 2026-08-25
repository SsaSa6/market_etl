# market_etl

업비트 시세를 1분 주기로 수집해 MySQL에 적재하는 데이터 파이프라인.
Airflow로 스케줄링하며, AWS Lightsail에서 상시 운영 중이다.

데이터 엔지니어링 학습 목적으로 만들었다.

## 목표

> 업비트 시세를 주기적으로 자동 수집해 MySQL에 적재하고, 일별 집계 테이블까지 생성한다.

### 완료 조건

- [x] 로컬 PC가 꺼져 있어도 계속 동작한다 (클라우드 배포)
- [x] 두 번 실행해도 데이터가 중복되거나 깨지지 않는다 (멱등성)
- [x] 처음 보는 사람이 README만 보고 실행할 수 있다
- [ ] 실패하면 감지할 수 있다 (알림)
- [ ] 한 달치 이상 데이터가 실제로 축적되어 있다
- [ ] raw 테이블과 집계(mart) 테이블이 분리되어 있다

## 아키텍처

```
                    ┌─────────────── AWS Lightsail (Ubuntu 24.04) ───────────────┐
                    │                                                            │
 Upbit API  ──────► │  Airflow (LocalExecutor)          MySQL 8                  │
                    │   ├─ scheduler                     └─ data_set (raw)       │
                    │   ├─ dag-processor                                         │
                    │   ├─ api-server (UI)              PostgreSQL 16            │
                    │   └─ DAG: Market_ELT               └─ Airflow 메타데이터    │
                    │        extract ──► load                                    │
                    └────────────────────────────────────────────────────────────┘
                                            ▲
                                    SSH 터널 (외부 포트 미개방)
                                            │
                                        로컬 PC
```

전 구성이 하나의 Docker Compose로 관리된다. 컨테이너 간에는 서비스 이름(`db`, `postgres`)으로 통신한다.

### ELT를 택한 이유

원본을 변환 없이 raw 테이블에 적재하고, 집계는 DB 안에서 SQL로 수행한다.

- **재처리가 가능하다.** 집계 로직에 오류가 있어도 원본이 남아 있어 다시 계산할 수 있다. 시세 API는 과거 데이터를 돌려주지 않으므로, 적재 시점에 원본을 잃으면 복구가 불가능하다
- **변환 로직 수정이 빠르다.** 파이썬 코드 수정·재배포보다 SQL 수정이 가볍다
- **데이터 규모가 작다.** 1분 주기 기준 하루 약 1,440행으로 DB가 충분히 감당한다

원본에 민감정보가 있거나 데이터 규모가 커서 적재 비용이 문제가 되는 경우라면 ETL이 적합하지만, 이 프로젝트는 해당하지 않는다.

## 설계 결정

| 항목 | 결정 | 이유 |
|---|---|---|
| DB | MySQL 8 | 사용 경험이 있어 학습 초점을 파이프라인 구조에 둘 수 있음. PostgreSQL 전환은 별도 과제로 예정 |
| 데이터 소스 | 업비트 Quotation API | 인증키 불필요, 초 단위 변동, 분당 600회 제한으로 여유 있음 |
| 대상 종목 | `KRW-BTC` 단일 | 완주를 우선. 스키마에 `market` 컬럼을 두어 확장 시 DDL 변경 불필요 |
| 금액·수량 타입 | `DECIMAL` | `FLOAT`은 유효숫자 약 7자리로, 누적 거래대금에서 수천 원 오차가 발생함을 실측으로 확인 |
| 기본 키 | `(market, slot_at)` 자연키 | 대리키(`auto_increment`) 제거. InnoDB는 PK 순서로 물리 저장하므로 종목·시간순 범위 조회에 유리 |
| 중복 처리 | `ON DUPLICATE KEY UPDATE market = market` | 같은 슬롯의 첫 값을 유지. 덮어쓰면 재실행 시점에 따라 과거 데이터가 바뀌어 멱등성이 깨짐 |
| 실행 환경 | Docker Compose | Airflow와 DB를 같은 네트워크에 두어 서비스 이름으로 통신. 로컬↔클라우드 이식이 `git clone` + `.env` 작성으로 끝남 |
| Airflow Executor | `LocalExecutor` | 태스크 2개, 1분 주기에 CeleryExecutor는 과잉. redis·worker 제거로 컨테이너 10개 → 5개 |
| DB 접속 계정 | 전용 계정 (`etl_user`) | 파이프라인은 지정된 DB에만 접근. root 권한 노출 회피 |
| 외부 포트 | SSH(22)만 개방 | Airflow UI(8080)와 MySQL(3306)은 미개방. 접근은 SSH 터널 경유 |

### 시각을 세 종류로 나눈 이유

| 컬럼 | 의미 | 역할 |
|---|---|---|
| `trade_timestamp` | 거래소에서 체결이 일어난 시각 | 원본 데이터 (UTC epoch ms) |
| `collected_at` | API를 실제로 호출한 시각 | 수집 지연 측정 |
| `slot_at` | 이 데이터가 속한 수집 슬롯 | **중복 판단 키** |

`slot_at`은 Airflow의 `data_interval_start`를 사용한다. 실패한 실행을 나중에 재시도해도 같은 값이 나오므로, 재실행이 같은 슬롯을 덮어쓰지 않는다. `datetime.now()`를 쓰면 재실행할 때마다 값이 달라져 멱등성이 깨진다.

**시각은 모두 KST(naive)로 저장한다.** Airflow는 UTC 기준으로 스케줄링하므로 적재 직전에 변환한다.

<details>
<summary>타임존 처리에서 겪은 문제</summary>

pendulum의 `DateTime`은 표준 `datetime`의 하위 타입이지만 **동일한 타입은 아니다.** pymysql은 정확히 일치하는 타입만 인식하므로 pendulum 객체를 문자열로 변환하는데, 그 결과에 `+09:00` 오프셋이 포함된다.

MySQL 8은 오프셋이 붙은 datetime 리터럴을 받으면 세션 타임존(UTC)으로 환산해 저장한다. 그래서 코드에서는 KST인데 DB에는 UTC로 들어갔다.

```
naive datetime  ->  '2026-08-16 10:30:00'
표준 tz-aware   ->  '2026-08-16 10:30:00'
pendulum        ->  '2026-08-16 10:30:00+09:00'   ← 오프셋 포함
```

`replace(tzinfo=None)`으로 naive 객체를 만들어 넘기는 것으로 해결했다.
</details>

## 기술 스택

| 구분 | 사용 |
|---|---|
| 언어 | Python 3.13 |
| 라이브러리 | `requests`, `pymysql`, `python-dotenv`, `pendulum` |
| 오케스트레이션 | Apache Airflow 3.3.0 (LocalExecutor) |
| 저장소 | MySQL 8 (시세), PostgreSQL 16 (Airflow 메타데이터) |
| 인프라 | Docker Compose, AWS Lightsail |

## 프로젝트 구조

```
market_etl/
├── ELT/
│   ├── main.py            # 로컬 단독 실행용 진입점
│   ├── extract.py         # 업비트 API 호출, collected_at 생성
│   ├── load.py            # MySQL 적재 (upsert)
│   └── db.py              # DB 커넥션 생성
├── dags/
│   └── db_dag.py          # Airflow DAG. extract → load
├── SQL/
│   └── table_sql.sql      # 테이블 DDL. MySQL 컨테이너 최초 기동 시 자동 실행
├── docker-compose.yml     # MySQL, PostgreSQL, Airflow 5개 서비스
├── .env.example           # 필요한 환경변수 목록
└── .env                   # 실제 값 (git 추적 제외)
```

## 실행 방법

**요구 사항**: Docker, Docker Compose v2

### 1. 저장소 준비

```bash
git clone https://github.com/SsaSa6/market_etl.git
cd market_etl
cp .env.example .env
```

### 2. 환경변수 작성

`.env`를 열어 값을 채운다.

```
MYSQL_ROOT_PASSWORD=관리자_비밀번호
MYSQL_DATABASE=market_database
MYSQL_USER=etl_user
MYSQL_PASSWORD=파이프라인_계정_비밀번호
DB_HOST=localhost
DB_PORT=3308
MYSQL_HOST_PORT=3308

POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow_비밀번호
POSTGRES_DB=airflow

AIRFLOW_UID=1000
FERNET_KEY=생성한_키

_AIRFLOW_WWW_USER_USERNAME=admin
_AIRFLOW_WWW_USER_PASSWORD=긴_비밀번호
```

**주의사항**

- **값을 따옴표로 감싸지 않는다.** 감싸면 파서에 따라 따옴표가 값에 포함된다
- **`@`, `$`, `#` 등 특수문자를 쓰지 않는다.** PostgreSQL 접속 문자열(`user:password@host/db`)에서 `@`가 구분자로 해석돼 호스트 파싱이 깨진다
- **`AIRFLOW_UID`는 `id -u` 결과를 넣는다.** 값이 맞지 않으면 컨테이너가 `logs/`에 쓰지 못해 태스크가 실패한다
- **`MYSQL_HOST_PORT`는 호스트 쪽 포트, `DB_PORT`는 파이썬이 접속할 포트다.** 컨테이너 내부에서는 compose의 `environment`가 이 값을 `db:3306`으로 덮어쓴다

`FERNET_KEY` 생성:

```bash
docker compose run --rm airflow-init -c "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
```

### 3. 기동

```bash
docker compose up -d
docker compose ps -a
```

정상 상태:

| 서비스 | 상태 |
|---|---|
| `db`, `postgres` | Up (healthy) |
| `airflow-init` | **Exited (0)** |
| `airflow-apiserver`, `airflow-scheduler`, `airflow-dag-processor` | Up (healthy) |

최초 기동 시 DB·계정 생성과 `SQL/table_sql.sql` 실행이 자동으로 이뤄진다.

```bash
docker compose logs db | grep -i "Creating\|initdb"
```

### 4. UI 접속

`http://localhost:8080` — `.env`의 `_AIRFLOW_WWW_USER_*` 계정으로 로그인.

**다그스** 메뉴에서 `Market_ELT`의 토글을 켠다. 새 DAG는 일시정지 상태로 등록된다.

### 5. 적재 확인

```bash
docker compose exec db mysql -u etl_user -p market_database \
  -e "SELECT market, slot_at, collected_at, trade_price FROM data_set ORDER BY slot_at DESC LIMIT 5;"
```

## 원격 서버 배포

AWS Lightsail(2 vCPU / 4GB / 80GB) 기준.

### 1. 서버 준비

```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# 재접속 후 적용됨

# swap (메모리 부족 시 OOM 방지)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 2. 배포

로컬과 동일하다. `git clone` → `.env` 작성 → `docker compose up -d`.

**`.env`는 로컬과 다른 비밀번호를 사용한다.** 한쪽이 유출돼도 다른 쪽이 영향받지 않도록 분리한다.

### 3. 방화벽

**SSH(22)만 개방하고 소스 IP를 제한한다.** 8080, 3306은 열지 않는다.

Airflow UI를 인터넷에 노출하면 스캐너가 곧 찾아낸다. Airflow는 임의의 파이썬 코드를 실행하는 도구이므로 침해 시 서버 전체를 내주는 것과 같다.

### 4. 접속 — SSH 터널

```powershell
ssh -i "키경로.pem" -L 18080:localhost:8080 -L 13308:localhost:3308 ubuntu@서버IP
```

- Airflow UI → `http://localhost:18080`
- MySQL → `localhost:13308`

로컬에서도 같은 스택을 돌리고 있다면 포트가 겹치므로, `-L`의 **왼쪽(로컬 포트)만** 다른 번호로 바꾼다.

## 앞으로 할 일

### 다음 단계

- [ ] **정리 DAG** — `airflow db clean`으로 메타DB의 오래된 레코드 삭제, `logs/`의 오래된 파일 삭제. 매일 실행, 30일 보존. XCom에 시세 JSON이 매 실행마다 저장되므로 이 테이블이 가장 빨리 증가한다
- [ ] **종목 확장 (5~10종목)** — URL의 `markets` 파라미터에 나열. `load.py`가 현재 `data[0]`만 처리하므로 반복 적재로 변경 필요. 저가 코인 추가 시 `DECIMAL` 자릿수 검증 필요
- [ ] **일별 집계(mart) 테이블** — raw에서 일별 시가/고가/저가/종가 산출. `acc_trade_volume`은 하루 단위로 리셋되는 누적값이므로 단순 합계로 계산하면 안 됨
- [ ] **실패 알림** — 현재는 UI를 열어야만 실패를 알 수 있다. 배포 후에는 확인 빈도가 낮아지므로 필요

### 이후

- [ ] 대시보드
- [ ] `requirements.txt` + 커스텀 Dockerfile — 의존성 버전 고정
- [ ] 데이터 소스 확장 (호가, 캔들, 타 거래소)
- [ ] PostgreSQL 전환 — DB 교체 시 코드가 얼마나 깨지는지 확인하는 과제

### 정리 대상

- `SQL/insert_sql.sql` — 개발 초기 수동 INSERT문. 현재 미사용
- `airflow-compose.yaml` — 공식 파일 원본. 참조용으로만 보관 중
- `load.py`의 변수명 (`test`, `values_sum`)
- `dags/db_dag.py` 파일명 — 내용은 `Market_ELT` DAG

## 운영 메모

- **환경변수를 바꾸면 컨테이너를 재생성해야 한다.** `restart`로는 반영되지 않는다 — `docker compose up -d --force-recreate`
- **DB 계정·비밀번호는 볼륨 최초 생성 시에만 적용된다.** `.env`를 바꿨다면 해당 볼륨을 삭제하거나 DB 안에서 직접 변경해야 한다
- **`docker compose down -v`는 사용하지 않는다.** MySQL과 PostgreSQL 볼륨이 모두 삭제된다. 특정 볼륨만 지울 때는 `docker volume rm <이름>`
- `SQL/table_sql.sql`은 **볼륨이 비어 있을 때만** 실행된다
