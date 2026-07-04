# 검색 API - 쇼핑

> 출처: https://developers.naver.com/docs/serviceapi/search/shopping/shopping.md

## 개요

검색어로 네이버쇼핑에 등록된 상품을 검색하는 API입니다.

## 요청

| 요청 URL | 반환 형식 |
| --- | --- |
| `https://openapi.naver.com/v1/search/shop.xml` | XML |
| `https://openapi.naver.com/v1/search/shop.json` | JSON |

Method: `GET`. 인증 헤더는 [00-openapi-guide.md](./00-openapi-guide.md#공통-요청-헤더) 참고.

### 파라미터

| 파라미터 | 타입 | 필수 여부 | 설명 |
| --- | --- | --- | --- |
| query | String | Y | 검색어 (UTF-8 인코딩 필요) |
| display | Integer | N | 한 번에 표시할 검색 결과 개수 (기본값 10, 최댓값 100) |
| start | Integer | N | 검색 시작 위치 (기본값 1, 최댓값 1000) |
| sort | String | N | 정렬 방법: `sim`(정확도순, 기본값) / `date`(날짜순) / `asc`(가격 오름차순) / `dsc`(가격 내림차순) |
| filter | String | N | 포함할 상품 유형: 미설정(전체, 기본값) / `naverpay`(네이버페이 연동 상품) |
| exclude | String | N | 제외할 상품 유형. `exclude={option}:{option}` 형태 (예: `exclude=used:cbshop`). 옵션: `used`(중고), `rental`(렌탈), `cbshop`(해외직구/구매대행) |

### 요청 예시

```
GET https://openapi.naver.com/v1/search/shop.json?query=검색어&display=10&start=1&sort=sim
```

## 응답

| 요소 | 타입 | 설명 |
| --- | --- | --- |
| lastBuildDate | dateTime | 검색 결과를 생성한 시간 |
| total | Integer | 총 검색 결과 개수 |
| start | Integer | 검색 시작 위치 |
| display | Integer | 한 번에 표시할 검색 결과 개수 |
| items[].title | String | 상품명 (검색어 일치 부분은 `<b>` 태그로 강조) |
| items[].link | String | 상품 정보 URL |
| items[].image | String | 상품 이미지 URL |
| items[].lprice | Integer | 최저가 (없으면 0) |
| items[].hprice | Integer | 최고가 (없으면 0) |
| items[].mallName | String | 판매 쇼핑몰 이름 |
| items[].productId | Integer | 네이버쇼핑 상품 ID |
| items[].productType | Integer | 상품군/상품 종류에 따른 타입 코드 (아래 표 참고) |
| items[].maker | String | 제조사 |
| items[].brand | String | 브랜드 |
| items[].category1~4 | String | 상품 카테고리 (대~세분류) |

### productType 코드표

| 상품군 | 상품 종류 | 타입 |
| --- | --- | --- |
| 일반상품 | 가격비교 상품 | 1 |
| 일반상품 | 가격비교 비매칭 일반상품 | 2 |
| 일반상품 | 가격비교 매칭 일반상품 | 3 |
| 중고상품 | 가격비교 상품 | 4 |
| 중고상품 | 가격비교 비매칭 일반상품 | 5 |
| 중고상품 | 가격비교 매칭 일반상품 | 6 |
| 단종상품 | 가격비교 상품 | 7 |
| 단종상품 | 가격비교 비매칭 일반상품 | 8 |
| 단종상품 | 가격비교 매칭 일반상품 | 9 |
| 판매예정상품 | 가격비교 상품 | 10 |
| 판매예정상품 | 가격비교 비매칭 일반상품 | 11 |
| 판매예정상품 | 가격비교 매칭 일반상품 | 12 |

### 응답 예시 (JSON)

```json
{
  "lastBuildDate": "Thu, 04 Jul 2026 12:00:00 +0900",
  "total": 987,
  "start": 1,
  "display": 10,
  "items": [
    {
      "title": "예시 <b>검색어</b> 상품",
      "link": "https://shopping.naver.com/product/1",
      "image": "https://shop-phinf.pstatic.net/example.jpg",
      "lprice": "15000",
      "hprice": "0",
      "mallName": "예시몰",
      "productId": "123456789",
      "productType": "1",
      "maker": "예시제조사",
      "brand": "예시브랜드",
      "category1": "생활/건강",
      "category2": "생활용품",
      "category3": "예시소분류",
      "category4": ""
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

async function searchShopping(query) {
  const res = await axios.get('https://openapi.naver.com/v1/search/shop.json', {
    params: { query, display: 10, start: 1, sort: 'sim' },
    headers: {
      'X-Naver-Client-Id': process.env.NAVER_CLIENT_ID,
      'X-Naver-Client-Secret': process.env.NAVER_CLIENT_SECRET,
    },
  });
  return res.data;
}
```
