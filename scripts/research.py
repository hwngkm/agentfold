"""Tra nhanh các nguồn nghiên cứu công khai — CHỈ dùng thư viện chuẩn Python, không MCP, không cài thêm gói.

    python -m scripts.research github "agent coordination git" --limit 5
    python -m scripts.research hf-models "vietnamese embedding" --limit 5
    python -m scripts.research hf-datasets "vietnamese medical"
    python -m scripts.research arxiv "retrieval augmented generation"
    python -m scripts.research openalex "drug interaction alert fatigue"
    python -m scripts.research pubmed "drug interaction alert fatigue"
    python -m scripts.research semantic-scholar "retrieval augmented generation"
    python -m scripts.research pypi fastapi        # tra theo TÊN gói, không phải tìm kiếm
    python -m scripts.research npm next
    ... --json                                     # máy đọc

Vì sao có công cụ này: mọi agent (Codex, Copilot, Cursor, Antigravity, Claude Code…) đều chạy được Python, nhưng không
phải agent nào cũng có MCP/connector nghiên cứu. Một lệnh, đầu ra cùng khuôn cho mọi nguồn — so sánh được ngay.

Biến môi trường (tuỳ chọn, KHÔNG bao giờ in ra): GITHUB_TOKEN (tăng hạn mức GitHub), HF_TOKEN, HF_ENDPOINT (gương
Hugging Face khi huggingface.co bị chặn, vd. https://hf-mirror.com), S2_API_KEY (Semantic Scholar — không có khoá thì
hay bị 429), NCBI_API_KEY (PubMed). Kết quả là ĐIỂM BẮT ĐẦU: mở nguồn gốc và đọc trước khi trích (skill
`literature-review`, `repo-research`, `model-hub-research`).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

USER_AGENT = "agentfold-research/1.0 (+https://github.com/hwngkm/agentfold)"
TIMEOUT_SECONDS = 25


class ResearchError(RuntimeError):
    """Nguồn không trả lời được — thông điệp nói rõ làm gì tiếp."""


@dataclass(frozen=True)
class Record:
    source: str
    id: str
    title: str
    url: str
    date: str = ""
    metric: str = ""  # sao, lượt tải, lượt trích dẫn — kèm đơn vị
    license: str = ""
    note: str = ""


def _get(url: str, headers: dict[str, str] | None = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310 — URL do code dựng
            return response.read()
    except urllib.error.HTTPError as exc:
        hint = " — hết hạn mức: chờ rồi thử lại, hoặc đặt khoá API (xem đầu file)" if exc.code in (403, 429) else ""
        raise ResearchError(f"{urllib.parse.urlsplit(url).netloc} trả HTTP {exc.code}{hint}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ResearchError(
            f"không kết nối được {urllib.parse.urlsplit(url).netloc} ({exc}) — mạng chặn hoặc chậm; thử nguồn khác "
            "(vd. openalex thay arxiv) hoặc gương (HF_ENDPOINT)"
        ) from exc


def fetch_json(url: str, headers: dict[str, str] | None = None) -> Any:
    return json.loads(_get(url, headers).decode("utf-8"))


def fetch_text(url: str, headers: dict[str, str] | None = None) -> str:
    return _get(url, headers).decode("utf-8")


def _q(text: str) -> str:
    return urllib.parse.quote(text)


def _auth(env: str, header: str, prefix: str = "") -> dict[str, str]:
    value = os.environ.get(env, "").strip()
    return {header: f"{prefix}{value}"} if value else {}


# ---- từng nguồn: dựng URL → gọi → chuẩn hoá về Record ------------------------------------------------------------


def github(query: str, limit: int) -> list[Record]:
    url = f"https://api.github.com/search/repositories?q={_q(query)}&sort=stars&order=desc&per_page={limit}"
    data = fetch_json(
        url, {"Accept": "application/vnd.github+json", **_auth("GITHUB_TOKEN", "Authorization", "Bearer ")}
    )
    return [
        Record(
            source="github",
            id=item["full_name"],
            title=(item.get("description") or "").strip(),
            url=item["html_url"],
            date=(item.get("pushed_at") or "")[:10],
            metric=f"{item.get('stargazers_count', 0)} sao",
            license=((item.get("license") or {}).get("spdx_id") or ""),
            note="ĐÃ LƯU TRỮ (archived)" if item.get("archived") else f"{item.get('open_issues_count', 0)} issue mở",
        )
        for item in data.get("items", [])[:limit]
    ]


def _hf_base() -> str:
    return os.environ.get("HF_ENDPOINT", "https://huggingface.co").rstrip("/")


def _hf(kind: str, query: str, limit: int) -> list[Record]:
    url = f"{_hf_base()}/api/{kind}?search={_q(query)}&sort=downloads&direction=-1&limit={limit}"
    data = fetch_json(url, _auth("HF_TOKEN", "Authorization", "Bearer "))
    prefix = "" if kind == "models" else "datasets/"
    records = []
    for item in data[:limit]:
        tags = item.get("tags") or []
        licence = next((t.split(":", 1)[1] for t in tags if t.startswith("license:")), "")
        notes = [item.get("library_name") or "", "GATED — cần đồng ý điều khoản" if item.get("gated") else ""]
        records.append(
            Record(
                source=f"hf-{kind}",
                id=item["id"],
                title=item.get("pipeline_tag") or item.get("library_name") or "",
                url=f"https://huggingface.co/{prefix}{item['id']}",
                date=(item.get("lastModified") or item.get("createdAt") or "")[:10],
                metric=f"{item.get('downloads', 0)} lượt tải · {item.get('likes', 0)} thích",
                license=licence,
                note=", ".join(n for n in notes if n),
            )
        )
    return records


def hf_models(query: str, limit: int) -> list[Record]:
    return _hf("models", query, limit)


def hf_datasets(query: str, limit: int) -> list[Record]:
    return _hf("datasets", query, limit)


_ATOM = "{http://www.w3.org/2005/Atom}"


def parse_arxiv(xml_text: str, limit: int) -> list[Record]:
    root = ET.fromstring(xml_text)
    records = []
    for entry in root.findall(f"{_ATOM}entry")[:limit]:
        authors = [a.findtext(f"{_ATOM}name", "") for a in entry.findall(f"{_ATOM}author")]
        url = entry.findtext(f"{_ATOM}id", "").strip()
        records.append(
            Record(
                source="arxiv",
                id=url.rsplit("/abs/", 1)[-1],
                title=" ".join(entry.findtext(f"{_ATOM}title", "").split()),
                url=url,
                date=entry.findtext(f"{_ATOM}published", "")[:10],
                note="preprint, chưa bình duyệt · " + ", ".join(authors[:3]) + (" …" if len(authors) > 3 else ""),
            )
        )
    return records


def arxiv(query: str, limit: int) -> list[Record]:
    url = f"https://export.arxiv.org/api/query?search_query=all:{_q(query)}&start=0&max_results={limit}"
    return parse_arxiv(fetch_text(url), limit)


def openalex(query: str, limit: int) -> list[Record]:
    data = fetch_json(f"https://api.openalex.org/works?search={_q(query)}&per-page={limit}")
    records = []
    for work in data.get("results", [])[:limit]:
        venue = ((work.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
        records.append(
            Record(
                source="openalex",
                id=work.get("id", "").rsplit("/", 1)[-1],
                title=work.get("display_name") or "",
                url=work.get("doi") or work.get("id", ""),
                date=str(work.get("publication_year") or ""),
                metric=f"{work.get('cited_by_count', 0)} trích dẫn",
                note=venue,
            )
        )
    return records


def pubmed(query: str, limit: int) -> list[Record]:
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    key = os.environ.get("NCBI_API_KEY", "").strip()
    suffix = f"&api_key={_q(key)}" if key else ""
    ids = fetch_json(f"{base}/esearch.fcgi?db=pubmed&term={_q(query)}&retmode=json&retmax={limit}{suffix}")
    uids = ids.get("esearchresult", {}).get("idlist", [])[:limit]
    if not uids:
        return []
    summary = fetch_json(f"{base}/esummary.fcgi?db=pubmed&id={','.join(uids)}&retmode=json{suffix}")
    result = summary.get("result", {})
    return [
        Record(
            source="pubmed",
            id=uid,
            title=result.get(uid, {}).get("title", ""),
            url=f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
            date=result.get(uid, {}).get("pubdate", ""),
            note=" · ".join(
                filter(None, [result.get(uid, {}).get("source", ""), ", ".join(result.get(uid, {}).get("pubtype", []))])
            ),
        )
        for uid in uids
    ]


def semantic_scholar(query: str, limit: int) -> list[Record]:
    fields = "title,year,citationCount,externalIds,url,venue"
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={_q(query)}&limit={limit}&fields={fields}"
    data = fetch_json(url, _auth("S2_API_KEY", "x-api-key"))
    return [
        Record(
            source="semantic-scholar",
            id=paper.get("paperId", ""),
            title=paper.get("title") or "",
            url=paper.get("url") or "",
            date=str(paper.get("year") or ""),
            metric=f"{paper.get('citationCount', 0)} trích dẫn",
            note=paper.get("venue") or "",
        )
        for paper in (data.get("data") or [])[:limit]
    ]


def pypi(name: str, _limit: int) -> list[Record]:
    data = fetch_json(f"https://pypi.org/pypi/{_q(name)}/json")
    info = data.get("info", {})
    uploaded = (data.get("urls") or [{}])[0].get("upload_time_iso_8601", "")[:10]
    return [
        Record(
            source="pypi",
            id=f"{info.get('name', name)}=={info.get('version', '')}",
            title=info.get("summary") or "",
            url=info.get("project_url") or f"https://pypi.org/project/{name}/",
            date=uploaded,
            license=info.get("license_expression") or (info.get("license") or "")[:40],
            note=f"Python {info.get('requires_python') or '?'}",
        )
    ]


def npm(name: str, _limit: int) -> list[Record]:
    data = fetch_json(f"https://registry.npmjs.org/{_q(name)}/latest")
    repo = data.get("repository")
    return [
        Record(
            source="npm",
            id=f"{data.get('name', name)}@{data.get('version', '')}",
            title=data.get("description") or "",
            url=f"https://www.npmjs.com/package/{name}",
            license=str(data.get("license") or ""),
            note=(repo.get("url", "") if isinstance(repo, dict) else str(repo or "")),
        )
    ]


SOURCES: dict[str, Callable[[str, int], list[Record]]] = {
    "github": github,
    "hf-models": hf_models,
    "hf-datasets": hf_datasets,
    "arxiv": arxiv,
    "openalex": openalex,
    "pubmed": pubmed,
    "semantic-scholar": semantic_scholar,
    "pypi": pypi,
    "npm": npm,
}


def to_markdown(records: list[Record]) -> str:
    if not records:
        return "(không có kết quả)"
    rows = [
        "| Nguồn | Mã | Tiêu đề / mô tả | Ngày | Chỉ số | Giấy phép | Ghi chú | Link |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in records:
        cells = [r.source, r.id, r.title[:90], r.date, r.metric, r.license, r.note[:60], r.url]
        rows.append("| " + " | ".join(c.replace("|", "/").replace("\n", " ") for c in cells) + " |")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        prog="python -m scripts.research", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("source", choices=sorted(SOURCES))
    parser.add_argument("query", help="từ khoá tìm kiếm (với pypi/npm: tên gói)")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 50:
        parser.error("--limit phải từ 1 đến 50")
    try:
        records = SOURCES[args.source](args.query, args.limit)
    except ResearchError as exc:
        print(f"🔴 {exc}", file=sys.stderr)
        return 1
    print(json.dumps([asdict(r) for r in records], ensure_ascii=False, indent=2) if args.json else to_markdown(records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
