import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api import results as results_api
from app.core.auth import Principal, _claims_to_principal
from app.core.authorization import get_accessible_job
from app.core.evidence_links import sign_evidence_url, verify_evidence_url
from app.db.database import Base
from app.models.job import AnalysisJob
from app.services.jurisdiction import (
    CitationMetadata,
    GoodsServices,
    TrademarkRecord,
    compare_records,
)
from app.worker import _goods_services_assessment


class TenantAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.session.add(
            AnalysisJob(
                job_id="a" * 32,
                tenant_id="tenant-a",
                owner_id="user-a",
                status="UPLOADED",
                progress=0,
                message="uploaded",
                nice_classes="[]",
            )
        )
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_job_is_only_visible_to_its_tenant(self):
        principal = Principal("user-a", "tenant-a", frozenset({"analyst"}))
        job = get_accessible_job("a" * 32, principal, self.session)
        self.assertEqual(job.tenant_id, "tenant-a")

        other_tenant = Principal(
            "user-b", "tenant-b", frozenset({"admin"})
        )
        with self.assertRaises(HTTPException) as error:
            get_accessible_job("a" * 32, other_tenant, self.session)
        self.assertEqual(error.exception.status_code, 404)

    def test_oidc_claims_map_to_tenant_and_roles(self):
        claims = _claims_to_principal(
            {"sub": "user-1", "tenant_id": "tenant-1", "roles": ["Analyst"]}
        )
        self.assertEqual(claims.subject, "user-1")
        self.assertEqual(claims.tenant_id, "tenant-1")
        self.assertEqual(claims.roles, frozenset({"analyst"}))

    def test_missing_tenant_claim_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            _claims_to_principal({"sub": "user-1"})
        self.assertEqual(error.exception.status_code, 403)

    def test_legacy_unassigned_tenant_cannot_authenticate(self):
        with self.assertRaises(HTTPException) as error:
            _claims_to_principal(
                {"sub": "user-1", "tenant_id": "legacy-unassigned"}
            )
        self.assertEqual(error.exception.status_code, 403)

    def test_signed_evidence_link_is_scoped_and_expires(self):
        signature = sign_evidence_url(
            "tenant-a", "a" * 32, "evidence.png", 2_000_000_000
        )
        self.assertTrue(
            verify_evidence_url(
                "tenant-a", "a" * 32, "evidence.png", 2_000_000_000, signature
            )
        )
        self.assertFalse(
            verify_evidence_url(
                "tenant-b", "a" * 32, "evidence.png", 2_000_000_000, signature
            )
        )

    def test_result_file_links_are_signed_for_the_job_tenant(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            evidence_root = Path(temporary_directory)
            evidence_dir = evidence_root / ("a" * 32)
            evidence_dir.mkdir()
            (evidence_dir / "evidence.png").write_bytes(b"image")
            (evidence_dir / "analysis_result.json").write_text(
                json.dumps({"matches": []}),
                encoding="utf-8",
            )

            with patch.object(results_api, "EVIDENCE_DIR", evidence_root):
                result = asyncio.run(
                    results_api.get_results(
                        "a" * 32,
                        Principal("user-a", "tenant-a", frozenset({"analyst"})),
                        self.session,
                    )
                )

        evidence_url = urlparse(result["files"][0]["url"])
        query = parse_qs(evidence_url.query)
        self.assertTrue(
            verify_evidence_url(
                "tenant-a",
                "a" * 32,
                "evidence.png",
                int(query["expires"][0]),
                query["signature"][0],
            )
        )


class JurisdictionAnalysisIntegrationTests(unittest.TestCase):
    def test_goods_services_scope_uses_uploaded_job_data(self):
        job = AnalysisJob(
            job_id="b" * 32,
            tenant_id="tenant-a",
            owner_id="user-a",
            status="UPLOADED",
            progress=0,
            message="uploaded",
            nice_classes="[]",
            left_jurisdiction="MM",
            right_jurisdiction="MM",
            left_nice_classes=json.dumps([9]),
            right_nice_classes=json.dumps([9]),
            left_goods_services="Downloadable computer software",
            right_goods_services="Downloadable computer software",
        )
        result = _goods_services_assessment(job)
        self.assertEqual(result["disposition"], "conflict")
        self.assertEqual(result["shared_nice_classes"], [9])

    def test_missing_scope_is_reported_as_review_not_a_match(self):
        job = AnalysisJob(
            job_id="c" * 32,
            tenant_id="tenant-a",
            owner_id="user-a",
            status="UPLOADED",
            progress=0,
            message="uploaded",
        )
        result = _goods_services_assessment(job)
        self.assertEqual(result["disposition"], "NEEDS_REVIEW")
        self.assertIn("review_reasons", result)

    def test_different_jurisdictions_are_not_declared_conflicts(self):
        result = compare_records(
            TrademarkRecord(
                jurisdiction="MM",
                goods_services=(GoodsServices(9, "software"),),
                citation=CitationMetadata(),
            ),
            TrademarkRecord(
                jurisdiction="US",
                goods_services=(GoodsServices(9, "software"),),
                citation=CitationMetadata(),
            ),
        )
        self.assertEqual(result.disposition.value, "needs_review")
