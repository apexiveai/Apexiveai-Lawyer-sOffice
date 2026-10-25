from typing import Any

from mcp.server.fastmcp import FastMCP

from apexive_mcp.http_client import backend_request

def register_analysis_tools(mcp: FastMCP) -> None:

    @mcp.tool()

    async def create_trademark_analysis(

        job_id: str,

    ) -> dict[str, Any]:

        """

        Start trademark conflict analysis for an uploaded PDF/XLSX job.

        """

        return await backend_request(

            method="POST",

            path=f"/api/analysis/{job_id}",

        )

    @mcp.tool()

    async def get_analysis_status(

        job_id: str,

    ) -> dict[str, Any]:

        """

        Get processing status and progress for a trademark analysis job.

        """

        return await backend_request(

            method="GET",

            path=f"/api/analysis/{job_id}/status",

        )

    @mcp.tool()

    async def get_analysis_summary(

        job_id: str,

    ) -> dict[str, Any]:

        """

        Get the completed trademark analysis result.

        """

        return await backend_request(

            method="GET",

            path=f"/api/results/{job_id}",

        )