"""adiga.kr(대입정보포털) "전형 요강 및 결과" 페이지에서 대학별 반영비율·산출식
원문을 수집해 SQLite에 적재하는 스크립트.

이 사이트(admitlab)의 계산기에 들어간 반영비율·산출식 데이터는 전부 이 스크립트로
직접 수집했다. adiga.kr의 해당 페이지는 뼈대(폼 + CSRF 토큰)만 서버 렌더링되고,
실제 반영비율·산출식 본문은 CSRF 토큰이 필요한 AJAX POST 응답으로 채워지는 구조라서
단순 GET 크롤링으로는 콘텐츠를 가져올 수 없다.

사용법:
    python collect_adiga_criteria.py --unv-cd 0000069 --syr 2026 --upper-cd 40 --item-cd 41

    --unv-cd    대학 코드 (예: 고려대 0000069, 서울대 0000019, 연세대 0000149)
    --syr       학년도
    --upper-cd  전형 대분류 (10=공통, 20=학생부종합, 30=학생부교과, 40=수능위주)
    --item-cd   페이지 내 아코디언 항목 코드 (대분류별로 다름, 소스보기로 확인)
    --db        결과를 적재할 SQLite 파일 (기본: adiga_criteria.sqlite3)

의존성:
    pip install curl_cffi beautifulsoup4
"""

import argparse
import re
import sqlite3
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from curl_cffi import requests

BASE_URL = "https://www.adiga.kr"
POPUP_PATH = "/uct/acd/ade/criteriaAndResultPopup.do"
AJAX_PATH = "/uct/acd/ade/criteriaAndResultItemAjax.do"

SCHEMA = """
CREATE TABLE IF NOT EXISTS admission_criteria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unv_cd TEXT NOT NULL,
    syr TEXT NOT NULL,
    upper_cd TEXT NOT NULL,
    item_cd TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    source_url TEXT NOT NULL,
    raw_html TEXT NOT NULL,
    parsed_text TEXT NOT NULL,
    UNIQUE(unv_cd, syr, upper_cd, item_cd)
);
"""


def fetch_criteria_item(unv_cd: str, syr: str, upper_cd: str, item_cd: str) -> tuple[str, str, str]:
    """(source_url, raw_html, parsed_text) 튜플을 반환한다."""
    session = requests.Session(impersonate="safari")
    popup_url = f"{BASE_URL}{POPUP_PATH}?unvCd={unv_cd}&searchSyr={syr}&tsrdCmphSlcnArtclUpCd={upper_cd}"

    # 1단계: 팝업 페이지 GET — 폼 뼈대와 함께 서버가 발급한 CSRF 토큰을 확보한다.
    # 이 시점의 응답에는 실제 반영비율/산출식 콘텐츠가 없다 (아코디언이 비어있음).
    shell = session.get(popup_url, headers={"Referer": BASE_URL + "/"})
    csrf_match = re.search(r'name="_csrf" value="([^"]+)"', shell.text)
    if not csrf_match:
        raise RuntimeError("CSRF 토큰을 찾지 못했습니다 — 페이지 구조가 바뀌었을 수 있습니다.")
    csrf_token = csrf_match.group(1)

    # 2단계: AJAX POST — 1단계와 같은 세션 쿠키 + CSRF 토큰(폼 필드와 헤더 둘 다)이
    # 있어야 실제 콘텐츠 HTML을 내려준다. 프론트엔드에서는 아코디언 클릭 시 이 요청이 나간다.
    form_data = {
        "_csrf": csrf_token,
        "searchSyr": syr,
        "searchStdClsfRgnCn": "",
        "searchUnvNm": "",
        "unvCd": unv_cd,
        "compUnvCd": "",
        "searchUnvComp": "0",
        "tsrdCmphSlcnArtclUpCd": upper_cd,
        "tsrdCmphSlcnArtclCd": item_cd,
    }
    content = session.post(
        f"{BASE_URL}{AJAX_PATH}",
        data=form_data,
        headers={
            "X-CSRF-TOKEN": csrf_token,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": popup_url,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    raw_html = content.text
    parsed_text = BeautifulSoup(raw_html, "html.parser").get_text("\n", strip=True)
    return popup_url, raw_html, parsed_text


def save_to_db(
    db_path: str,
    unv_cd: str,
    syr: str,
    upper_cd: str,
    item_cd: str,
    source_url: str,
    raw_html: str,
    parsed_text: str,
) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    conn.execute(
        """
        INSERT INTO admission_criteria
            (unv_cd, syr, upper_cd, item_cd, fetched_at, source_url, raw_html, parsed_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(unv_cd, syr, upper_cd, item_cd) DO UPDATE SET
            fetched_at = excluded.fetched_at,
            source_url = excluded.source_url,
            raw_html = excluded.raw_html,
            parsed_text = excluded.parsed_text
        """,
        (unv_cd, syr, upper_cd, item_cd, datetime.now(timezone.utc).isoformat(), source_url, raw_html, parsed_text),
    )
    conn.commit()
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="adiga.kr 전형 요강 및 결과 수집기")
    parser.add_argument("--unv-cd", default="0000069", help="대학 코드 (기본: 고려대 0000069)")
    parser.add_argument("--syr", default="2026", help="학년도")
    parser.add_argument("--upper-cd", default="40", help="전형 대분류 (10=공통 20=학생부종합 30=학생부교과 40=수능위주)")
    parser.add_argument("--item-cd", default="41", help="아코디언 항목 코드")
    parser.add_argument("--db", default="adiga_criteria.sqlite3", help="저장할 SQLite 파일 경로")
    args = parser.parse_args()

    source_url, raw_html, parsed_text = fetch_criteria_item(args.unv_cd, args.syr, args.upper_cd, args.item_cd)
    save_to_db(args.db, args.unv_cd, args.syr, args.upper_cd, args.item_cd, source_url, raw_html, parsed_text)

    print(f"[OK] unv_cd={args.unv_cd} syr={args.syr} upper_cd={args.upper_cd} item_cd={args.item_cd}")
    print(f"     -> {args.db} 에 저장 (텍스트 {len(parsed_text)}자)")
    print("\n--- 미리보기 (첫 400자) ---")
    print(parsed_text[:400])


if __name__ == "__main__":
    main()
