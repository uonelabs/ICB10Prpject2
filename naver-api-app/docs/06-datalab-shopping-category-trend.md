# 데이터랩 - 쇼핑인사이트 분야별 트렌드 API

> 참고: 네이버 쇼핑인사이트(datalab.naver.com) 서비스에서 사용하는 분야(카테고리) 코드 기반 트렌드 API입니다.
> 이 프로젝트의 다른 문서와 달리 developers.naver.com 원본 레퍼런스 문서를 직접 수집하지 않고,
> 사용자가 제공한 분야 선택 목록(카테고리명-코드 매핑)을 바탕으로 정리했습니다. 실제 사용 전 네이버 개발자센터에서
> 최신 스펙을 다시 확인하는 것을 권장합니다.

## 요청

- **URL**: `https://openapi.naver.com/v1/datalab/shopping/categories`
- **Method**: `POST`
- **Content-Type**: `application/json`
- 인증 헤더는 [00-openapi-guide.md](./00-openapi-guide.md#공통-요청-헤더) 참고

### 요청 파라미터 (JSON body)

| 파라미터 | 타입 | 필수 여부 | 설명 |
| --- | --- | --- | --- |
| startDate | string | Y | 조회 기간 시작 날짜 (yyyy-mm-dd) |
| endDate | string | Y | 조회 기간 종료 날짜 (yyyy-mm-dd) |
| timeUnit | string | Y | 구간 단위: `date`(일간) / `week`(주간) / `month`(월간) |
| category | array(JSON) | Y | 분야 이름-코드 쌍의 배열. 최대 3개까지 비교 가능 |
| category[].name | string | Y | 분야명 (결과 표시용) |
| category[].param | array(string) | Y | 분야 코드(cid) 배열 |
| device | string | N | 미설정(전체) / `pc` / `mo` |
| gender | string | N | 미설정(전체) / `m` / `f` |
| ages | array(string) | N | 연령대 코드 (01-datalab-search-trend.md 와 동일한 코드 체계) |

### 분야(카테고리) 코드표

| 분야명 | cid |
| --- | --- |
| 패션의류 | 50000000 |
| 패션잡화 | 50000001 |
| 화장품/미용 | 50000002 |
| 디지털/가전 | 50000003 |
| 가구/인테리어 | 50000004 |
| 출산/육아 | 50000005 |
| 식품 | 50000006 |
| 스포츠/레저 | 50000007 |
| 생활/건강 | 50000008 |
| 여가/생활편의 | 50000009 |
| 면세점 | 50000010 |
| 도서 | 50005542 |

### 요청 예시

```json
{
  "startDate": "2024-01-01",
  "endDate": "2024-01-31",
  "timeUnit": "date",
  "category": [
    { "name": "패션의류", "param": ["50000000"] },
    { "name": "디지털/가전", "param": ["50000003"] }
  ]
}
```

## 응답

응답 구조는 [01-datalab-search-trend.md](./01-datalab-search-trend.md#응답) 의 통합 검색어 트렌드 API와 동일합니다 (`results[].title`, `results[].data[].period`, `results[].data[].ratio`).

## 코드 내 구현 위치

- 분야 코드 매핑: [naver-api-app/src/naver_api.py](../src/naver_api.py) `SHOPPING_CATEGORIES`
- API 호출 함수: [naver-api-app/src/naver_api.py](../src/naver_api.py) `datalab_shopping_category_trend()`
- 대시보드 UI: [naver-api-app/src/pages/6_📈_쇼핑트렌드.py](../src/pages/6_📈_쇼핑트렌드.py) "쇼핑 카테고리(분야)" 모드
