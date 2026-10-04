"""`scripts/research.py`: chuẩn hoá đầu ra của từng nguồn về cùng một khuôn — test bằng dữ liệu mẫu, không gọi mạng.

Dữ liệu mẫu lấy theo đúng hình dạng phản hồi thật của từng API (kiểm 03/10/2026); khoá API không bao giờ xuất hiện
trong đầu ra.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from scripts import research

ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2005.11401v4</id>
    <published>2020-05-22T17:49:36Z</published>
    <title>Retrieval-Augmented Generation for
      Knowledge-Intensive NLP Tasks</title>
    <author><name>Patrick Lewis</name></author><author><name>Ethan Perez</name></author>
    <author><name>A</name></author><author><name>B</name></author>
  </entry>
</feed>"""


@pytest.fixture
def fake_net(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    calls: dict[str, Any] = {"urls": [], "headers": []}
    payloads: dict[str, Any] = {}

    def fetch_json(url: str, headers: dict[str, str] | None = None) -> Any:
        calls["urls"].append(url)
        calls["headers"].append(headers or {})
        for key, value in payloads.items():
            if key in url:
                return value
        raise AssertionError(f"URL không có dữ liệu mẫu: {url}")

    monkeypatch.setattr(research, "fetch_json", fetch_json)
    monkeypatch.setattr(research, "fetch_text", lambda url, headers=None: ARXIV_XML)
    calls["payloads"] = payloads
    return calls


def test_github_chuan_hoa_va_canh_bao_repo_luu_tru(fake_net: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_bi_mat")
    fake_net["payloads"]["api.github.com"] = {
        "items": [
            {
                "full_name": "o/r",
                "description": "Agent mail",
                "html_url": "https://github.com/o/r",
                "pushed_at": "2026-10-01T00:00:00Z",
                "stargazers_count": 2183,
                "license": {"spdx_id": "MIT"},
                "archived": True,
                "open_issues_count": 3,
            }
        ]
    }
    [rec] = research.github("agent mail", 5)
    assert (rec.id, rec.metric, rec.license, rec.date) == ("o/r", "2183 sao", "MIT", "2026-10-01")
    assert "archived" in rec.note
    assert fake_net["headers"][0]["Authorization"] == "Bearer ghp_bi_mat"
    assert "ghp_bi_mat" not in research.to_markdown([rec])


def test_hugging_face_lay_giay_phep_tu_tag_va_ton_trong_guong(
    fake_net: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HF_ENDPOINT", "https://hf-mirror.com/")
    fake_net["payloads"]["/api/models"] = [
        {
            "id": "dangvantuan/vietnamese-document-embedding",
            "downloads": 90625,
            "likes": 29,
            "tags": ["sentence-transformers", "license:apache-2.0"],
            "pipeline_tag": "sentence-similarity",
            "createdAt": "2024-08-15T05:32:04.000Z",
        }
    ]
    [rec] = research.hf_models("vietnamese embedding", 3)
    assert fake_net["urls"][0].startswith("https://hf-mirror.com/api/models?search=vietnamese%20embedding")
    assert rec.license == "apache-2.0" and rec.metric.startswith("90625 lượt tải")
    assert rec.url == "https://huggingface.co/dangvantuan/vietnamese-document-embedding", "link luôn trỏ trang gốc"


def test_arxiv_ghi_ro_preprint_va_gon_tieu_de(fake_net: dict[str, Any]) -> None:
    [rec] = research.arxiv("rag", 1)
    assert rec.id == "2005.11401v4" and rec.date == "2020-05-22"
    assert rec.title == "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
    assert rec.note.startswith("preprint") and rec.note.endswith("…")


def test_pubmed_hai_buoc_va_khong_goi_tom_tat_khi_rong(fake_net: dict[str, Any]) -> None:
    fake_net["payloads"]["esearch.fcgi"] = {"esearchresult": {"idlist": []}}
    assert research.pubmed("không có gì", 3) == []
    assert len(fake_net["urls"]) == 1


def test_openalex_va_semantic_scholar_cung_khuon(fake_net: dict[str, Any]) -> None:
    fake_net["payloads"]["api.openalex.org"] = {
        "results": [
            {
                "id": "https://openalex.org/W1",
                "display_name": "RAG survey",
                "doi": "https://doi.org/10.1/x",
                "publication_year": 2024,
                "cited_by_count": 120,
                "primary_location": {"source": {"display_name": "ACL"}},
            }
        ]
    }
    fake_net["payloads"]["semanticscholar"] = {
        "data": [
            {
                "paperId": "p1",
                "title": "RAG",
                "year": 2020,
                "citationCount": 9,
                "url": "https://s2/p1",
                "venue": "NeurIPS",
            }
        ]
    }
    [a], [b] = research.openalex("rag", 1), research.semantic_scholar("rag", 1)
    assert (a.id, a.metric, a.url, a.note) == ("W1", "120 trích dẫn", "https://doi.org/10.1/x", "ACL")
    assert (b.metric, b.note) == ("9 trích dẫn", "NeurIPS")


def test_loi_mang_va_han_muc_thanh_thong_diep_doc_duoc(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    def boom(query: str, limit: int) -> list[research.Record]:
        raise research.ResearchError("api.semanticscholar.org trả HTTP 429 — hết hạn mức")

    monkeypatch.setitem(research.SOURCES, "semantic-scholar", boom)
    assert research.main(["semantic-scholar", "rag"]) == 1
    assert "429" in capsys.readouterr().err


def test_dau_ra_json_cho_may_doc(fake_net: dict[str, Any], capsys: pytest.CaptureFixture) -> None:
    fake_net["payloads"]["registry.npmjs.org"] = {
        "name": "next",
        "version": "16.3.8",
        "description": "React framework",
        "license": "MIT",
        "repository": {"url": "git+https://github.com/vercel/next.js.git"},
    }
    assert research.main(["npm", "next", "--json"]) == 0
    [row] = json.loads(capsys.readouterr().out)
    assert row["id"] == "next@16.3.8" and row["license"] == "MIT"
