from typing import Any

from mcp.server.fastmcp import FastMCP

from apexive_mcp.http_client import backend_request

from apexive_mcp.config import EVIDENCE_PUBLIC_BASE_URL

def register_evidence_tools(mcp: FastMCP) -> None:

    @mcp.tool()

    async def get_conflict_evidence(

        job_id: str,

        match_index: int,

    ) -> dict[str, Any]:

        """

        Return evidence for a specific conflict including

        PDF/client images, bounding boxes and evidence URLs.

        """

        result = await backend_request(

            method="GET",

            path=f"/api/results/{job_id}",

        )

        matches = result.get("matches", [])

        if match_index < 0 or match_index >= len(matches):

            return {

                "job_id": job_id,

                "match_index": match_index,

                "error": "Match index out of range.",

            }

        match = matches[match_index]

        response = {

            "job_id": job_id,

            "match_index": match_index,
            "match_number": match_index + 1,

            "match_type": match.get("match_type"),

            "match_reason": match.get("match_reason"),

            "application_no": match.get("application_no"),

            "pdf_page": match.get("pdf_page"),

            "pdf_owner": match.get("pdf_owner"),

            "client_owner": match.get("client_owner"),

            "mark": match.get("mark"),

            "confidence": match.get("confidence"),

            "pdf_evidence": match.get("pdf_evidence"),

            "client_evidence": match.get("client_evidence"),
            "text_match": match.get("text_match"),
            "visual_match": match.get("visual_match"),
            "similarity_percent": match.get("similarity_percent"),
        }

        logo_match = match.get("_logo_match")

        if isinstance(logo_match, dict):

            response["similarity_percent"] = (

                logo_match.get("similarity_percent")

            )

        return response

    @mcp.tool()

    async def get_evidence_url(

        job_id: str,

        filename: str,

    ) -> dict[str, str]:

        """

        Build a browser-accessible evidence URL for a generated evidence image.

        """

        base = EVIDENCE_PUBLIC_BASE_URL.rstrip("/")
        result = await backend_request(
            method="GET",
            path=f"/api/results/{job_id}",
        )
        evidence = next(
            (
                item
                for item in result.get("files", [])
                if item.get("filename") == filename
            ),
            None,
        )
        signed_path = evidence.get("url") if evidence else None
        if not isinstance(signed_path, str) or "/evidence/" not in signed_path:
            return {
                "job_id": job_id,
                "filename": filename,
                "error": "Evidence file not found for this job.",
            }
        signed_suffix = signed_path.split("/evidence/", 1)[1]
        return {

            "job_id": job_id,

            "filename": filename,

            "url": f"{base}/{signed_suffix}",

        }