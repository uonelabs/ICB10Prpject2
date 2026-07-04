# 검색 API - 뉴스

> 출처: https://developers.naver.com/docs/serviceapi/search/news/news.md

## 개요

검색어로 네이버 뉴스 기사를 검색하는 API입니다.

## 요청

| 요청 URL | 반환 형식 |
| --- | --- |
| `https://openapi.naver.com/v1/search/news.xml` | XML |
| `https://openapi.naver.com/v1/search/news.json` | JSON |

Method: `GET`. 인증 헤더는 [00-openapi-guide.md](./00-openapi-guide.md#공통-요청-헤더) 참고.

### 파라미터

| 파라미터 | 타입 | 필수 여부 | 설명 |
| --- | --- | --- | --- |
| query | String | Y | 검색어 (UTF-8 인코딩 필요) |
| display | Integer | N | 한 번에 표시할 검색 결과 개수 (기본값 10, 최댓값 100) |
| start | Integer | N | 검색 시작 위치 (기본값 1, 최댓값 1000) |
| sort | String | N | 정렬 방법: `sim`(정확도순, 기본값) / `date`(날짜순) |

### 요청 예시

```
GET https://openapi.naver.com/v1/search/news.json?query=검색어&display=10&start=1&sort=sim
```

## 응답

| 요소 | 타입 | 설명 |
| --- | --- | --- |
| lastBuildDate | dateTime | 검색 결과를 생성한 시간 |
| total | Integer | 총 검색 결과 개수 |
| start | Integer | 검색 시작 위치 |
| display | Integer | 한 번에 표시할 검색 결과 개수 |
| items[].title | String | 뉴스 기사 제목 (검색어 일치 부분은 `<b>` 태그로 강조) |
| items[].originallink | String | 뉴스 기사 원문 URL |
| items[].link | String | 네이버 뉴스 URL (미제공 기사는 원문 URL) |
| items[].description | String | 기사 내용 요약 (검색어 일치 부분은 `<b>` 태그로 강조) |
| items[].pubDate | String | 기사가 네이버에 제공된 시간 |

### 응답 예시 (JSON)

```json
{
  "lastBuildDate": "Thu, 04 Jul 2026 12:00:00 +0900",
  "total": 5432,
  "start": 1,
  "display": 10,
  "items": [
    {
      "title": "예시 <b>검색어</b> 관련 뉴스 제목",
      "originallink": "https://news.example.com/article/1",
      "link": "https://news.naver.com/article/1",
      "description": "기사 내용 요약에서 <b>검색어</b>와 일치하는 부분",
      "pubDate": "Thu, 04 Jul 2026 09:00:00 +0900"
    }
  ]
}
```

## 오류 코드

| 오류 코드 | HTTP 상태 코드 | 오류 메시지 | 설명 |
| --- | --- | --- | --- |
| SE01 | 400 | Incorrect query request | 요청 URL의 프로토콜, 파라미터 오류 확인 |
| SE02 | 400 | Invalid display value | display 값이 1~100 범위인지 확인 |
| SE03 | 400 | Invalid start value | start 값이 1~1000 범위인지 확인 |
| SE04 | 400 | Invalid sort value | sort 값 오타 확인 |
| SE06 | 400 | Malformed encoding | 검색어를 UTF-8로 인코딩 |
| SE05 | 404 | Invalid search api | 요청 URL 오타 확인 |
| SE99 | 500 | System Error | 서버 내부 오류, 개발자 포럼에 신고 |

## 호출 예시 (Node.js)

```js
const axios = require('axios');

async function searchNews(query) {
  const res = await axios.get('https://openapi.naver.com/v1/search/news.json', {
    params: { query, display: 10, start: 1, sort: 'sim' },
    headers: {
      'X-Naver-Client-Id': process.env.NAVER_CLIENT_ID,
      'X-Naver-Client-Secret': process.env.NAVER_CLIENT_SECRET,
    },
  });
  return res.data;
}
```
