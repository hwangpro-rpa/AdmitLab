# AdmitLab · 합격 예측 랩

대학어디가(adiga.kr)가 공시한 대학별 전형 요강을 바탕으로, 정시·학생부교과·학생부종합의 실제 반영 방식을 계산해보는 미니 데모 사이트. 메가스터디교육 "고등 온라인 입시 데이터 분석" 직무 지원용으로 제작.

**데모: https://admitlab.hwangpro-rpa.workers.dev**

## 데이터 출처

모든 반영비율/산출식은 [대학어디가](https://www.adiga.kr) "전형 요강 및 결과" 페이지에서 직접 조회했다 (2026학년도 기준, 고려대학교[본교] `unvCd=0000069`, 서울대학교 `unvCd=0000019`, 연세대학교 `unvCd=0000149`).

이 페이지는 `criteriaAndResultPopup.do?unvCd=...&searchSyr=...&tsrdCmphSlcnArtclUpCd=...`로 뼈대만 로드되고, 실제 본문은 CSRF 토큰이 필요한 `criteriaAndResultItemAjax.do` POST 응답으로 채워진다 (아코디언 클릭 시 AJAX). `tsrdCmphSlcnArtclUpCd`는 전형 대분류(10=공통, 20=학생부종합, 30=학생부교과, 40=수능위주), 개별 항목은 페이지 내 `fnItemSearch(this, "코드")`의 코드로 조회한다.

- **정시(수능위주) 일반전형 — 고려대**: 국어 200 + 수학 200 + 탐구 160 (자연/체능 계열은 배점이 다름), 영어·한국사는 등급별 감점표를 그대로 사용.
- **학생부교과 학교추천전형 — 고려대**: 교과평균등급(과목별 석차등급 × 이수단위의 가중평균) → 등급별 반영점수표(1등급 100 ~ 9등급 0) → 학생부(교과) 반영점수 = 교과평균등급점수 × 0.9, + 서류 10. 등급 구간 사이 보간식은 원문이 이미지 수식이라 텍스트로 완전히 옮겨지지 않아, 표준적인 선형보간으로 재구성했다(사이트 내 명시).
- **학생부종합 학업우수전형 — 고려대**: 서류 100% 정성평가, 평가요소 비중(학업역량 50 / 자기계발역량 30 / 공동체역량 20)만 공개되고 산출식은 없음 — 그대로 정보성 카드로 표시.
- **대학별 반영구조 비교 — 고려대/서울대/연세대**: 세 대학의 정시 일반전형을 나란히 조회해보면 반영구조 자체가 다르다 — 고려대는 순수 수능 백분위 합산형, 서울대는 1단계 수능 100% → 2단계 수능성적80+정성 교과평가(A/B/C 등급)20의 혼합형, 연세대는 수능 응시유형(Ⅰ~Ⅳ)별로 탐구 가산점이 갈리는 유형 분기형. "정시=단순 합산"이라는 통념이 실제로는 대학마다 다르다는 것을 보여주기 위해 계산기 대신 요약 비교 카드로 넣었다 (서울대·연세대는 다단계+정성평가가 섞여 있어 근사 계산기로 만들면 오히려 부정확해질 위험이 있다고 판단).

## 데이터 파이프라인 (Python + SQL)

사이트에 들어간 반영비율·산출식 원문은 전부 [`scripts/collect_adiga_criteria.py`](scripts/collect_adiga_criteria.py)로 직접 수집했다.

```bash
pip install -r scripts/requirements.txt
python scripts/collect_adiga_criteria.py --unv-cd 0000069 --syr 2026 --upper-cd 40 --item-cd 41
```

동작 방식:

1. **세션 확보(GET)**: 대상 페이지는 폼 뼈대와 CSRF 토큰만 서버 렌더링하고, 실제 콘텐츠는 없다.
2. **콘텐츠 요청(POST)**: 같은 세션 쿠키 + CSRF 토큰(폼 필드·헤더 양쪽)을 실어 `criteriaAndResultItemAjax.do`에 POST해야 실제 반영비율·산출식 HTML을 내려준다 — 프론트엔드에서는 아코디언 클릭 시 이 요청이 나간다.
3. **정제**: BeautifulSoup으로 표/문단 구조를 유지한 채 plain text로 변환.
4. **적재**: SQLite(`admission_criteria` 테이블)에 원본 HTML과 정제 텍스트를 함께 UPSERT — 대학·연도·전형별로 재수집해도 중복되지 않는다.

수집 후 SQL로 바로 조회 가능:

```sql
SELECT unv_cd, syr, upper_cd, item_cd, length(parsed_text) AS chars, fetched_at
FROM admission_criteria
ORDER BY fetched_at DESC;
```

## 원칙

- 실제 산출식과 근사치를 명확히 구분해 표기한다 (백분위 기반 정시 계산은 단순화 근사, 학생부교과 등급표는 원문 그대로).
- "합격 예측"이 아니라 "반영 방식 이해용 데모"임을 상단 배너와 각 패널에 반복 고지한다.
- 정성평가 전형(학생부종합)은 억지로 숫자화하지 않고 평가 기준만 보여준다.

## 구조

- `index.html` / `style.css` / `script.js` — 단일 페이지, 탭 전환(정시/학생부교과/학생부종합/대학별 반영구조 비교), 계산 결과에 stamp 애니메이션.
- `scripts/collect_adiga_criteria.py` — 데이터 수집 스크립트 (위 "데이터 파이프라인" 참고).
- 사이트 자체는 백엔드 없음, 정적 호스팅(Cloudflare Workers/Pages)으로 배포 — `admitlab.hwangpro-rpa.workers.dev`가 이 레포와 연결되어 push할 때마다 자동 재배포된다.
