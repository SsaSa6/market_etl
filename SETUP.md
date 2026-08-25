# 설치 및 실행

> 프로젝트 개요와 설계 배경은 [README.md](README.md) 참조.

## 요구 사항

- Docker, Docker Compose v2
- 메모리 4GB 이상 권장

## 로컬 실행

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

**작성 규칙 — 지키지 않으면 기동에 실패한다**

| 규칙 | 이유 |
|---|---|
| 값을 따옴표로 감싸지 않는다 | Compose의 `${}` 치환과 `env_file` 주입은 서로 다른 파서를 쓴다. 따옴표가 한쪽에만 남으면 같은 `.env`인데 컨테이너마다 값이 달라진다 |
| 등호 앞뒤에 공백을 넣지 않는다 | Compose의 `.env` 파서는 공백을 허용하지 않는다 |
| `@`, `$`, `#` 등 특수문자를 쓰지 않는다 | PostgreSQL 접속 문자열이 `user:password@host/db` 형식이라 비밀번호의 `@`가 구분자로 해석된다 |
| `AIRFLOW_UID`는 `id -u` 결과를 넣는다 | 값이 맞지 않으면 컨테이너가 `logs/`에 쓰지 못해 태스크가 실패한다 |

**포트 두 개의 역할이 다르다**

- `MYSQL_HOST_PORT` — MySQL을 호스트의 몇 번 포트로 열 것인가
- `DB_HOST` / `DB_PORT` — 파이썬이 접속할 주소

컨테이너 내부에서는 `docker-compose.yml`의 `environment` 블록이 `DB_HOST=db`, `DB_PORT=3306`으로 덮어쓴다. 같은 코드가 호스트에서는 `localhost:3308`, 컨테이너에서는 `db:3306`을 쓰게 되는 구조다.

### 3. Fernet 키 생성

```bash
docker compose run --rm airflow-init -c "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
```

출력된 문자열을 `.env`의 `FERNET_KEY`에 넣는다.

Airflow가 Connection·Variable의 비밀번호를 암호화하는 키다. **비워둔 채로 운영하다가 나중에 설정하면 기존 값을 복호화하지 못한다.** 처음에 넣는 편이 낫다.

### 4. 기동

```bash
docker compose config    # 문법·변수 치환 검증
docker compose up -d
docker compose ps -a
```

정상 상태:

| 서비스 | 상태 |
|---|---|
| `db`, `postgres` | Up (healthy) |
| `airflow-init` | **Exited (0)** |
| `airflow-apiserver`, `airflow-scheduler`, `airflow-dag-processor` | Up (healthy) |

`airflow-init`은 DB 마이그레이션과 관리자 계정 생성을 수행하고 종료하는 서비스다. 종료 코드가 `0`이어야 한다.

최초 기동 시 DB·계정 생성과 `SQL/table_sql.sql` 실행이 자동으로 이뤄진다.

```bash
docker compose logs db | grep -i "Creating\|initdb"
```

### 5. UI 접속

`http://localhost:8080` — `.env`의 `_AIRFLOW_WWW_USER_*` 계정으로 로그인.

**다그스** 메뉴에서 `Market_ELT`의 토글을 켠다. 새 DAG는 일시정지 상태로 등록된다.

### 6. 적재 확인

```bash
docker compose exec db mysql -u etl_user -p market_database \
  -e "SELECT market, slot_at, collected_at, trade_price FROM data_set ORDER BY slot_at DESC LIMIT 5;"
```

---

## 원격 서버 배포

AWS Lightsail(2 vCPU / 4GB / 80GB, Ubuntu 24.04) 기준.

### 1. 서버 준비

**Docker 설치**

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

`usermod` 이후 **재접속해야** 그룹 변경이 적용된다. 소속 그룹은 로그인 시점에 셸에 부여되므로 기존 세션에는 반영되지 않는다.

```bash
docker run hello-world    # 확인
```

**swap 설정**

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

`chmod 600`은 swap에 메모리 내용이 그대로 담기기 때문이다. `/etc/fstab` 등록은 재부팅 후에도 유지되게 한다.

### 2. 배포

로컬과 동일하다. `git clone` → `.env` 작성 → `docker compose up -d`.

**`.env`는 로컬과 다른 비밀번호를 사용한다.** 한쪽이 유출돼도 다른 쪽이 영향받지 않도록 분리한다.

### 3. 방화벽

**SSH(22)만 열고 소스 IP를 제한한다. 8080과 3306은 열지 않는다.**

Airflow는 임의의 파이썬 코드를 실행하는 도구다. UI가 인터넷에 노출되면 스캐너가 곧 찾아내고, 침해 시 서버 전체를 내주는 것과 같다.

Lightsail은 기본적으로 HTTP(80)가 열려 있으므로 **네트워킹 탭에서 삭제**한다.

**고정 IP**를 연결한다. 인스턴스에 연결된 동안은 무료이며, 재시작 시 주소가 바뀌는 것을 막는다. 인스턴스를 삭제할 때 고정 IP도 함께 삭제해야 한다(미연결 상태는 과금).

### 4. 접속 — SSH 터널

외부 포트를 열지 않았으므로 SSH 터널로 접근한다.

`~/.ssh/config`에 등록해두면 반복 입력이 필요 없다.

```
Host market
    HostName 서버_고정_IP
    User ubuntu
    IdentityFile 키_경로.pem
    LocalForward 18080 localhost:8080
    LocalForward 13308 localhost:3308
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

```powershell
ssh market
```

이 창을 열어둔 상태에서:

- Airflow UI → `http://localhost:18080`
- MySQL → `localhost:13308`

로컬에서도 같은 스택을 돌린다면 포트가 겹치므로 **로컬 쪽 포트만** 다른 번호를 쓴다.

`ServerAliveInterval`은 유휴 상태로 인한 연결 끊김을 막는다. 이것이 없으면 터널이 half-open 상태가 되어 DB 클라이언트가 응답 없이 대기하는 현상이 발생한다.

**Windows에서 키 파일 권한 오류가 나는 경우**

```powershell
icacls "키_경로.pem" /inheritance:r
icacls "키_경로.pem" /grant:r "${env:USERNAME}:(R)"
```

SSH는 다른 사용자가 읽을 수 있는 개인 키를 거부한다.

### 5. DB 클라이언트 연결 (DBeaver)

**Main 탭**

| 항목 | 값 |
|---|---|
| Host | `localhost` |
| Port | `3308` |
| Database | `market_database` |
| 사용자 | `etl_user` |

**SSH 탭** — `Use SSH Tunnel` 체크 후 서버 정보와 `.pem` 경로 입력.

DBeaver 내장 터널을 쓰면 Main 탭의 포트는 **서버 입장의 포트**(`3308`)를 넣는다. 명령줄 터널을 쓴다면 SSH 탭을 끄고 **로컬 포트**(`13308`)를 넣는다.

**드라이버 속성**에 `allowPublicKeyRetrieval=true`가 필요하다. MySQL 8의 `caching_sha2_password` 인증에서 JDBC 드라이버가 서버 공개키를 요청하는데, 기본적으로 차단돼 있기 때문이다.

SSL을 켜면(`sslMode=REQUIRED`) 채널이 암호화되어 공개키 검색 자체가 불필요해진다. 다만 자체 서명 인증서이므로 서버 인증서 검증은 해제해야 한다. 운영 환경이라면 정식 인증서로 `VERIFY_CA` 검증을 켜는 것이 맞다.

---

## 운영 메모

**환경변수를 바꾸면 컨테이너를 재생성해야 한다**

```bash
docker compose up -d --force-recreate
```

환경변수는 컨테이너 생성 시점에 주입된다. `restart`로는 반영되지 않는다.

**DB 계정·비밀번호는 볼륨 최초 생성 시에만 적용된다**

`.env`의 비밀번호를 바꿔도 이미 생성된 계정은 예전 값을 유지한다. 해당 볼륨을 삭제하거나 DB 안에서 `ALTER USER`로 직접 변경해야 한다.

**`docker compose down -v`는 사용하지 않는다**

MySQL과 PostgreSQL 볼륨이 모두 삭제된다. PostgreSQL이 지워지면 Airflow 계정과 실행 이력이 사라져 `airflow-init`부터 다시 해야 한다.

특정 볼륨만 삭제할 때:

```bash
docker volume ls
docker volume rm market_etl_dbdata
```

**초기화 스크립트는 볼륨이 비어 있을 때만 실행된다**

`SQL/table_sql.sql`을 수정한 뒤 반영하려면 볼륨을 삭제하고 다시 기동해야 한다.

**로그와 메타데이터는 계속 증가한다**

1분 주기 기준 태스크 로그가 하루 약 2,880개 파일씩 생성된다. Airflow 메타DB의 `xcom` 테이블에는 매 실행마다 시세 JSON이 저장된다.

```bash
du -sh logs/
df -h
```

정리는 `airflow db clean`(메타DB)과 오래된 로그 파일 삭제를 각각 수행해야 한다. `db clean`은 파일을 지우지 않는다.
