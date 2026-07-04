# 데이터랩 - 통합 검색어 트렌드 API

> 출처: https://developers.naver.com/docs/serviceapi/datalab/search/search.md

## 개요

네이버 통합 검색에서 특정 검색어들이 얼마나 검색되었는지 확인할 수 있는 API입니다. 검색어(하나 이상)를 그룹으로 묶어 최대 5개 그룹까지 조회할 수 있으며, 그룹별 검색 결과는 개별 검색어의 결과를 합산해 반환합니다. 검색량은 절대적인 수치가 아니라, 조회 기간 내 최대 검색량을 100으로 두었을 때의 상대적인 비율로 제공됩니다.

## 요청

- **URL**: `https://openapi.naver.com/v1/datalab/search`
- **Method**: `POST`
- **Content-Type**: `application/json`
- 인증 헤더는 [00-openapi-guide.md](./00-openapi-guide.md#공통-요청-헤더) 참고

### 요청 파라미터 (JSON body)

| 파라미터 | 타입 | 필수 여부 | 설명 |
| --- | --- | --- | --- |
| startDate | string | Y | 조회 기간 시작 날짜 (yyyy-mm-dd). 2016-01-01 이후만 조회 가능 |
| endDate | string | Y | 조회 기간 종료 날짜 (yyyy-mm-dd) |
| timeUnit | string | Y | 구간 단위: `date`(일간) / `week`(주간) / `month`(월간) |
| keywordGroups | array(JSON) | Y | 주제어-검색어 묶음 배열. 최대 5개 |
| keywordGroups[].groupName | string | Y | 주제어 (검색어 묶음을 대표하는 이름) |
| keywordGroups[].keywords | array(string) | Y | 주제어에 해당하는 검색어. 최대 20개 |
| device | string | N | 검색 환경: 미설정(전체) / `pc` / `mo` |
| gender | string | N | 성별: 미설정(전체) / `m`(남성) / `f`(여성) |
| ages | array(string) | N | 연령대 코드 배열: `1`(0~12세) `2`(13~18) `3`(19~24) `4`(25~29) `5`(30~34) `6`(35~39) `7`(40~44) `8`(45~49) `9`(50~54) `10`(55~59) `11`(60세 이상) |

### 요청 예시

```json
{
  "startDate": "2024-01-01",
  "endDate": "2024-01-31",
  "timeUnit": "date",
  "keywordGroups": [
    { "groupName": "그룹A", "keywords": ["검색어1", "검색어2"] },
    { "groupName": "그룹B", "keywords": ["검색어3"] }
  ],
  "device": "",
  "gender": "",
  "ages": []
}
```

## 응답

| 속성 | 타입 | 설명 |
| --- | --- | --- |
| startDate | string | 조회 기간 시작 날짜 |
| endDate | string | 조회 기간 종료 날짜 |
| timeUnit | string | 구간 단위 |
| results[].title | string | 주제어 |
| results[].keywords | array | 해당 주제어에 포함된 검색어 목록 |
| results[].data[].period | string | 구간별 시작 날짜 |
| results[].data[].ratio | number | 구간별 상대적 검색 비율 (최대값=100 기준) |

### 응답 예시

```json
{
  "startDate": "2024-01-01",
  "endDate": "2024-01-31",
  "timeUnit": "date",
  "results": [
    {
      "title": "그룹A",
      "keywords": ["검색어1", "검색어2"],
      "data": [
        { "period": "2024-01-01", "ratio": 34.5 },
        { "period": "2024-01-02", "ratio": 41.2 }
      ]
    }
  ]
}
```

## 오류 코드

| 오류 코드 | HTTP 상태 코드 | 설명 |
| --- | --- | --- |
| 400 | 400 | 잘못된 요청 - 요청 URL의 프로토콜, 파라미터 등에 오류가 있는지 확인 |
| 500 | 500 | 서버 내부 오류 |

## 호출 예시 (Node.js)

```js
const axios = require('axios');

async function getSearchTrend() {
  const res = await axios.post(
    'https://openapi.naver.com/v1/datalab/search',
    {
      startDate: '2024-01-01',
      endDate: '2024-01-31',
      timeUnit: 'date',
      keywordGroups: [{ groupName: '그룹A', keywords: ['검색어1', '검색어2'] }],
    },
    {
      headers: {
        'X-Naver-Client-Id': process.env.NAVER_CLIENT_ID,
        'X-Naver-Client-Secret': process.env.NAVER_CLIENT_SECRET,
        'Content-Type': 'application/json',
      },
    }
  );
  return res.data;
}
```
