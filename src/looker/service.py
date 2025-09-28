"""Looker service for API interactions - Migrated from boats_agent_base."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

from .exceptions import LookerAuthError, LookerAPIError

logger = logging.getLogger(__name__)


class LookerService:
    """Service for interacting with Looker API."""

    def __init__(self, base_url: str, client_id: str, client_secret: str, default_limit: int = 500) -> None:
        """Initialize Looker service."""
        self.base_url = base_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.default_limit = default_limit

        self.client: Optional[httpx.AsyncClient] = None
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

        logger.info("LookerService initialized", extra={
            "base_url": self.base_url,
            "client_id": self.client_id,
            "default_limit": self.default_limit,
            "has_client_secret": bool(self.client_secret)
        })

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=30.0)
        return self.client

    async def authenticate(self) -> None:
        """Authenticate with Looker API and get access token."""
        client = await self._ensure_client()

        try:
            logger.info("Authenticating with Looker API", extra={
                "base_url": self.base_url,
                "client_id": self.client_id
            })

            # Build query parameters for authentication
            auth_params = {
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }

            # Make POST request to login endpoint with query parameters
            url = f"{self.base_url}/login?{urlencode(auth_params)}"
            response = await client.post(url)

            if response.status_code != 200:
                error_msg = f"Authentication failed with status {response.status_code}"
                logger.error("Looker authentication failed", extra={
                    "status_code": response.status_code,
                    "response_text": response.text[:500]
                })
                raise LookerAuthError(error_msg)

            # Parse response to get access token
            auth_data = response.json()
            if "access_token" not in auth_data:
                logger.error("No access token in authentication response", extra={
                    "response_keys": list(auth_data.keys())
                })
                raise LookerAuthError("No access token received from Looker API")

            self.access_token = auth_data["access_token"]

            # Set token expiration (default to 1 hour if not provided)
            expires_in = auth_data.get("expires_in", 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)  # 60s buffer

            logger.info("Looker authentication successful", extra={
                "token_expires_in": expires_in,
                "token_expires_at": self.token_expires_at.isoformat()
            })

        except httpx.RequestError as e:
            error_msg = f"Network error during authentication: {str(e)}"
            logger.error("Looker authentication network error", extra={
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise LookerAuthError(error_msg) from e
        except Exception as e:
            if isinstance(e, LookerAuthError):
                raise
            error_msg = f"Unexpected error during authentication: {str(e)}"
            logger.error("Looker authentication unexpected error", extra={
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise LookerAuthError(error_msg) from e

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token."""
        now = datetime.now()

        if (self.access_token is None or
            self.token_expires_at is None or
            now >= self.token_expires_at):

            logger.info("Access token expired or missing, refreshing", extra={
                "has_token": bool(self.access_token),
                "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
                "current_time": now.isoformat()
            })
            await self.authenticate()

    async def run_inline_query(self, body: Dict[str, Any], query_timezone: str = "UTC") -> List[Dict[str, Any]]:
        """
        Run an inline query using Looker API.

        Args:
            body: Query parameters for the inline query
            query_timezone: Query timezone (default: UTC)

        Returns:
            List of dictionaries representing query results

        Raises:
            LookerAPIError: If the query fails
            LookerAuthError: If authentication fails
        """
        await self._ensure_authenticated()
        client = await self._ensure_client()

        # Add default parameters if not provided
        query_body = body.copy()
        if "query_timezone" not in query_body:
            query_body["query_timezone"] = query_timezone
        if "limit" not in query_body:
            query_body["limit"] = self.default_limit

        logger.info("Running Looker inline query", extra={
            "query_timezone": query_body.get("query_timezone"),
            "limit": query_body.get("limit"),
            "filters": query_body.get("filters", {}),
            "body_keys": list(query_body.keys())
        })

        headers = {
            "Authorization": f"token {self.access_token}",
            "Content-Type": "application/json"
        }

        try:
            url = f"{self.base_url}/queries/run/json"
            response = await client.post(url, json=query_body, headers=headers)

            if response.status_code == 401:
                logger.warning("Received 401, refreshing token and retrying")
                # Token might be expired, refresh and retry once
                await self.authenticate()
                headers["Authorization"] = f"token {self.access_token}"
                response = await client.post(url, json=query_body, headers=headers)

            if response.status_code != 200:
                error_msg = f"Query failed with status {response.status_code}: {response.text}"
                logger.error("Looker inline query failed", extra={
                    "status_code": response.status_code,
                    "response_text": response.text[:500],
                    "query_body": query_body
                })
                raise LookerAPIError(error_msg)

            # Parse and return results
            results = response.json()

            # Ensure we return a list
            if not isinstance(results, list):
                logger.error("Unexpected response format, expected list", extra={
                    "response_type": type(results).__name__,
                    "response_sample": str(results)[:200] if results else None
                })
                raise LookerAPIError("Unexpected response format from Looker API")

            logger.info("Looker inline query successful", extra={
                "result_count": len(results),
                "first_result_keys": list(results[0].keys()) if results else []
            })

            return results

        except httpx.RequestError as e:
            error_msg = f"Network error during query: {str(e)}"
            logger.error("Looker query network error", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "query_body": query_body
            })
            raise LookerAPIError(error_msg) from e
        except Exception as e:
            if isinstance(e, (LookerAPIError, LookerAuthError)):
                raise
            error_msg = f"Unexpected error during query: {str(e)}"
            logger.error("Looker query unexpected error", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "query_body": query_body
            })
            raise LookerAPIError(error_msg) from e

    async def get_explore_schema(self, model: str, explore: str) -> Dict[str, Any]:
        """
        Get schema information for a Looker Explore.

        Args:
            model: Looker model name
            explore: Looker explore name

        Returns:
            Dictionary with explore schema information
        """
        await self._ensure_authenticated()
        client = await self._ensure_client()

        headers = {
            "Authorization": f"token {self.access_token}",
            "Content-Type": "application/json"
        }

        try:
            url = f"{self.base_url}/lookml_models/{model}/explores/{explore}"
            response = await client.get(url, headers=headers)

            if response.status_code == 401:
                logger.warning("Received 401, refreshing token and retrying")
                await self.authenticate()
                headers["Authorization"] = f"token {self.access_token}"
                response = await client.get(url, headers=headers)

            if response.status_code != 200:
                error_msg = f"Schema query failed with status {response.status_code}: {response.text}"
                logger.error("Looker schema query failed", extra={
                    "status_code": response.status_code,
                    "response_text": response.text[:500],
                    "model": model,
                    "explore": explore
                })
                raise LookerAPIError(error_msg)

            schema = response.json()
            logger.info("Looker schema query successful", extra={
                "model": model,
                "explore": explore,
                "dimensions_count": len(schema.get("dimensions", [])),
                "measures_count": len(schema.get("measures", []))
            })

            return schema

        except httpx.RequestError as e:
            error_msg = f"Network error during schema query: {str(e)}"
            logger.error("Looker schema query network error", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "model": model,
                "explore": explore
            })
            raise LookerAPIError(error_msg) from e
        except Exception as e:
            if isinstance(e, (LookerAPIError, LookerAuthError)):
                raise
            error_msg = f"Unexpected error during schema query: {str(e)}"
            logger.error("Looker schema query unexpected error", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "model": model,
                "explore": explore
            })
            raise LookerAPIError(error_msg) from e

    async def aclose(self) -> None:
        """Close the HTTP client and clean up resources."""
        if self.client is not None:
            await self.client.aclose()
            self.client = None

        self.access_token = None
        self.token_expires_at = None

        logger.info("LookerService client closed and resources cleaned up")