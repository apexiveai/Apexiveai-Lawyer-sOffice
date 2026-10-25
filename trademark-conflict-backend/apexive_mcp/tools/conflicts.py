from typing import Any

from mcp.server.fastmcp import FastMCP

from apexive_mcp.http_client import backend_request

def register_conflict_tools(mcp: FastMCP) -> None:

    @mcp.tool()

    async def get_all_conflicts(

        job_id: str,

    ) -> dict[str, Any]:

        """

        Return all detected trademark conflicts for a completed job.

        """

        result = await backend_request(

            method="GET",

            path=f"/api/results/{job_id}",

        )

        return {

            "job_id": job_id,

            "conflicts": result.get("matches", []),

            "total": len(result.get("matches", [])),

        }

    @mcp.tool()

    async def get_application_matches(

        job_id: str,

    ) -> dict[str, Any]:

        """

        Return application-number conflicts only.

        """

        result = await backend_request(

            method="GET",

            path=f"/api/results/{job_id}",

        )

        matches = [

            item

            for item in result.get("matches", [])

            if "application"
            in str(item.get("match_type", "")).lower()

        ]

        return {

            "job_id": job_id,

            "match_type": "application",

            "total": len(matches),

            "matches": matches,

        }

    @mcp.tool()

    async def get_logo_matches(

        job_id: str,

    ) -> dict[str, Any]:

        """

        Return visual/logo trademark conflicts including similarity evidence.

        """

        result = await backend_request(

            method="GET",

            path=f"/api/results/{job_id}",

        )

        matches = [

            item

            for item in result.get("matches", [])

            if "logo"
            in str(item.get("match_type", "")).lower()

        ]

        return {

            "job_id": job_id,

            "match_type": "logo",

            "total": len(matches),

            "matches": matches,

        }

    @mcp.tool()

    async def get_company_matches(

        job_id: str,

    ) -> dict[str, Any]:

        """

        Return company/owner conflicts.

        """

        result = await backend_request(

            method="GET",

            path=f"/api/results/{job_id}",

        )

        matches = [

            item

            for item in result.get("matches", [])

            if "company"
            in str(item.get("match_type", "")).lower()

        ]

        return {

            "job_id": job_id,

            "match_type": "company",

            "total": len(matches),

            "matches": matches,

        }

    @mcp.tool()

    async def get_phone_matches(

        job_id: str,

    ) -> dict[str, Any]:

        """

        Return phone-number conflicts.

        """

        result = await backend_request(

            method="GET",

            path=f"/api/results/{job_id}",

        )

        matches = [

            item

            for item in result.get("matches", [])

            if "phone"
            in str(item.get("match_type", "")).lower()

        ]

        return {

            "job_id": job_id,

            "match_type": "phone",

            "total": len(matches),

            "matches": matches,

        }

    @mcp.tool()

    async def search_trademark_conflicts(

        job_id: str,

        query: str,

    ) -> dict[str, Any]:

        """

        Search detected trademark conflicts by application number,

        company owner, mark, client, or phone number.

        """

        result = await backend_request(

            method="GET",

            path=f"/api/results/{job_id}",

        )

        query_normalized = query.strip().lower()

        if not query_normalized:

            return {

                "job_id": job_id,

                "query": query,

                "total": 0,

                "matches": [],

            }

        matches = []

        for item in result.get("matches", []):

            searchable = " ".join(

                str(value)

                for value in [

                    item.get("match_type"),

                    item.get("application_no"),

                    item.get("pdf_application_no"),

                    item.get("client_application_no"),

                    item.get("pdf_owner"),

                    item.get("client_owner"),

                    item.get("client"),

                    item.get("mark"),

                    item.get("phone"),

                ]

                if value is not None

            ).lower()

            if query_normalized in searchable:

                matches.append(item)

        return {

            "job_id": job_id,

            "query": query,

            "total": len(matches),

            "matches": matches,

        }