# 명세: URL 단축기

이 문서는 두 가지 충돌 해결 방식으로 URL을 저장하고 조회하는 단축기를 정의한다.
구현은 Python 표준 라이브러리만 사용하며, 저장소의 `src/`에서는 `dict`, `set`,
내장 `hash()`를 사용하지 않는다.

## 1. 무엇을 만드는가

사용자가 HTTP(S) URL을 입력하면 짧은 코드를 돌려주고, 코드로 원래 URL을 조회한다.
같은 URL을 반복해서 단축하면 기존 코드를 돌려준다.

## 2. base62 인코딩

`src.base62.encode(number)`와 `src.base62.decode(code)`를 제공한다. 알파벳 순서는
`0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ`이며 숫자 0은 `"0"`이다.
입력은 음수가 아닌 정수와 비어 있지 않은 알파벳 문자열이다. 음수·빈 문자열·알파벳
밖의 문자는 `ValueError`, 정수가 아닌 숫자나 문자열이 아닌 코드는 `TypeError`다.

## 3. 해시 테이블

체이닝과 선형 탐지 해시 테이블은 각각 `HashTable`과 `LinearProbingHashTable`로
제공하며, 문자열 키와 임의의 값을 저장하고 `put(key, value)`, `get(key)`,
`contains(key)`, `items()`, `probe_count(key)`를 제공한다. 키는 대소문자를 구분한다.
같은 키에 다시 `put`하면 기존 값을 교체하며 원소 수를 늘리지 않는다. 없는 키의
`get`은 `None`, `contains`는 `False`를 반환한다.

문자열 해시는 `h = (31 * h + ord(character)) % capacity`로 계산하는 호너 방식이다.
초기 용량은 8이고, 적재율이 0.75를 초과하기 전에 용량을 두 배로 늘려 모든 항목을
재삽입한다. 체이닝 방식은 버킷별 연결 리스트(리스트로 표현)를 사용하며, 탐색 비용은
조회 과정에서 키를 비교한 항목 수다. 선형 탐지 방식은 다음 칸으로 순차 이동하고
끝에서 처음으로 돌아온다. 탐색 비용은 확인한 칸 수다. 성공·실패 모두 빈 칸 또는
키를 찾을 때까지의 탐색을 세며, 선형 탐지는 한 바퀴(용량만큼) 후 종료한다.
설정된 적재율 1.0으로 테이블이 가득 찬 상태에서 새 키를 넣으면 `OverflowError`를
내고 무한 탐색하지 않는다. 두 방식 모두 `probe_count`와 사람이 읽을 수 있는 탐색
근거를 제공한다. 선형 탐지는 비어 있는 칸 없이 한 바퀴를 모두 확인해도 키가 없으면
탐색을 종료하고, 새 항목 삽입은 `OverflowError`를 낸다.

## 4. 단축기

`src.shortener.URLShortener`는 `chaining`(기본값) 또는 `linear` 전략을 선택할 수 있다.
`shorten(url)`은 절대 HTTP 또는 HTTPS URL만 받는다.
호스트가 없거나 스킴이 다르거나 URL이 빈 문자열이면 `ValueError`다. 같은 URL은
같은 코드를 반환한다. `expand(code)`는 저장되지 않은 코드에 `KeyError`를 낸다.
각 단축기의 ID는 0부터 증가하며 base62로 인코딩한다.

## 5. 웹 서버

`python3 src/server.py --port PORT [--strategy chaining|linear]`는 로컬 HTTP 서버를
실행한다. `/`는 URL 입력 폼과
결과를, `POST /shorten`은 폼 필드 `url`을 받아 단축 결과를 보여준다. `GET /r/CODE`는
저장된 원 URL로 302 리다이렉트하고, 없는 코드는 404다. `GET /table`은 현재 테이블의
버킷·항목, 탐색한 칸, 호너 해시 계산 근거를 HTML로 보여준다. 외부 네트워크나
영구 저장은 요구하지 않는다.

## 6. 경계 사례

- base62의 0, 알파벳 경계(61, 62), 큰 정수 왕복, 잘못된 타입·문자열
- 해시 충돌과 같은 키 갱신, 없는 키 조회, 대소문자 구별, 적재율 경계와 재해싱
- 선형 탐지의 끝 칸에서 0번 칸으로 순환, 가득 찬 테이블의 종료와 삽입 오류
- 빈 테이블, 충돌 버킷, 성공·실패 조회의 탐색 비용과 근거
- URL 중복 단축, 잘못된 scheme/host, 없는 코드, ID 0
- 서버의 폼 응답, 단축 URL 리다이렉트, 없는 코드 404, `/table` 출력
