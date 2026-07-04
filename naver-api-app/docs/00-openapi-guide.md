# 네이버 오픈 API 공통 가이드

> 출처: https://developers.naver.com/docs/common/openapiguide/

## 개요

네이버 오픈 API는 네이버 플랫폼의 로그인, 지도, 검색 등의 기능을 외부 개발자가 웹/SDK 형태로 사용할 수 있도록 공개한 API입니다. 이 프로젝트(naver-api-app)는 이 중 **검색 API(블로그/뉴스/카페글/쇼핑)** 와 **데이터랩(검색어 트렌드) API** 를 사용합니다.

## 사전 준비 사항 (공통)

1. 네이버 개발자 센터(https://developers.naver.com) 에 로그인 후 **Application > 애플리케이션 등록** 메뉴에서 애플리케이션을 등록합니다.
2. **사용 API** 항목에서 필요한 API(검색, 데이터랩 등)를 선택합니다.
3. 비로그인 오픈 API 서비스 환경(WEB 설정 등 웹 서비스 URL)을 등록합니다.
4. 등록이 끝나면 **클라이언트 아이디(Client ID)** 와 **클라이언트 시크릿(Client Secret)** 이 발급됩니다. 이 값은 모든 API 호출 시 HTTP 헤더에 실어 보내야 합니다.

## 공통 요청 헤더

| 헤더 | 설명 |
| --- | --- |
| `X-Naver-Client-Id` | 발급받은 클라이언트 아이디 |
| `X-Naver-Client-Secret` | 발급받은 클라이언트 시크릿 |

검색 API(REST, GET 방식) 호출 시 위 두 헤더만 있으면 되고, 데이터랩 API는 헤더는 동일하지만 `Content-Type: application/json` 을 추가하고 POST 로 요청 바디에 JSON을 담아 보냅니다.

## 공통 오류 코드 패턴

대부분의 검색 API는 `errorCode` / `errorMessage` 형태로 오류를 반환하며, 이 프로젝트에서 다루는 각 API의 오류 코드는 해당 API 문서 파일(예: [02-search-blog.md](./02-search-blog.md))의 "오류 코드" 절을 참고하세요.

- **403 오류**: 애플리케이션 등록 시 해당 API(검색/데이터랩)를 사용 API로 추가하지 않은 경우 발생합니다. 네이버 개발자 센터 > Application > 내 애플리케이션 > API 설정에서 사용 여부를 확인하세요.

## 이 저장소의 API 문서 목록

| 파일 | API |
| --- | --- |
| [01-datalab-search-trend.md](./01-datalab-search-trend.md) | 데이터랩 통합 검색어 트렌드 |
| [02-search-blog.md](./02-search-blog.md) | 검색 - 블로그 |
| [03-search-news.md](./03-search-news.md) | 검색 - 뉴스 |
| [04-search-cafearticle.md](./04-search-cafearticle.md) | 검색 - 카페글 |
| [05-search-shopping.md](./05-search-shopping.md) | 검색 - 쇼핑 |
