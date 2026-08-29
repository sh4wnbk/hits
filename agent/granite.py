"""
agent/granite.py — the watsonx Granite client, and the only place a credential
is read.

Isolated from agent/explain.py on purpose. The generate-and-gate loop must be
provably independent of whether credentials exist, because the offline path is
a design gate rather than a fallback nobody exercises: CLAUDE.md requires that
the tool work with no API key, and tests/test_explain.py drives the whole loop
with a stub that never touches this module.

Credentials come from the environment and nowhere else. They are never taken
from a request, never written to disk, and never logged. `.env` is in
.gitignore and CI is required to fail if one is ever tracked.

Missing credentials are not an error. `from_env()` returns None, the loop
serves the deterministic floor, and the response says `deterministic_floor` so
the offline result is never mis-credited to Granite.

## What is not verified here

The default model id and the default region host are configurable defaults, not
claims. This machine has no watsonx credentials, so neither has been confirmed
against the live catalogue, and a wrong id fails the same way any other
unavailable model does: the call errors, the attempt is recorded, and the floor
is served. Set WATSONX_MODEL_ID and WATSONX_URL to the values the deployment
actually has.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

IAM_URL = "https://iam.cloud.ibm.com/identity/token"
IAM_GRANT_TYPE = "urn:ibm:params:oauth:grant-type:apikey"

DEFAULT_URL = "https://us-south.ml.cloud.ibm.com"
DEFAULT_MODEL_ID = "ibm/granite-4-1-8b-instruct"
GENERATION_PATH = "/ml/v1/text/generation"
GENERATION_VERSION = "2023-05-29"

# Deterministic decoding. The gate is dispositive either way, but a sampled
# explanation that passes once and fails the next time on the same solve makes
# the served_by field noise rather than a record.
DEFAULT_PARAMETERS = {
    "decoding_method": "greedy",
    "max_new_tokens": 600,
    "repetition_penalty": 1.05,
}

# Refresh an IAM token this many seconds before it actually expires, so a call
# cannot start with a token that dies mid-flight.
TOKEN_MARGIN_S = 120

REQUEST_TIMEOUT_S = 60


class GraniteError(RuntimeError):
    """A watsonx call that did not return a usable completion."""


@dataclass
class GraniteClient:
    """
    One watsonx text-generation endpoint.

    `generate(prompt) -> str` is the whole surface the loop uses, which is what
    lets a stub stand in for it without importing anything from this file.
    """
    api_key: str
    project_id: str
    url: str = DEFAULT_URL
    model_id: str = DEFAULT_MODEL_ID

    _token: str = ""
    _token_expires_at: float = 0.0

    # -- authentication -----------------------------------------------------

    def _bearer(self) -> str:
        if self._token and time.time() < self._token_expires_at:
            return self._token
        import requests
        response = requests.post(
            IAM_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": IAM_GRANT_TYPE, "apikey": self.api_key},
            timeout=REQUEST_TIMEOUT_S,
        )
        if response.status_code != 200:
            # The body can echo the key back on some IAM errors, so the status
            # is reported and the body is not.
            raise GraniteError(
                f"IAM token request failed with status {response.status_code}")
        payload = response.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.time() + payload["expires_in"] - TOKEN_MARGIN_S
        return self._token

    # -- generation ---------------------------------------------------------

    def generate(self, prompt: str) -> str:
        import requests
        response = requests.post(
            f"{self.url.rstrip('/')}{GENERATION_PATH}",
            params={"version": GENERATION_VERSION},
            headers={
                "Authorization": f"Bearer {self._bearer()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "model_id": self.model_id,
                "project_id": self.project_id,
                "input": prompt,
                "parameters": DEFAULT_PARAMETERS,
            },
            timeout=REQUEST_TIMEOUT_S,
        )
        if response.status_code != 200:
            raise GraniteError(
                f"watsonx generation failed with status {response.status_code}")
        results = response.json().get("results") or []
        if not results:
            raise GraniteError("watsonx returned no results")
        return results[0].get("generated_text", "").strip()


def from_env() -> Optional[GraniteClient]:
    """
    A client if the environment carries credentials, None if it does not.

    None is an ordinary outcome, not a failure. It is what the no-key path
    looks like, and the caller turns it into a `deterministic_floor` response.
    """
    api_key = os.environ.get("WATSONX_API_KEY", "").strip()
    project_id = os.environ.get("WATSONX_PROJECT_ID", "").strip()
    if not api_key or not project_id:
        return None
    return GraniteClient(
        api_key=api_key,
        project_id=project_id,
        url=os.environ.get("WATSONX_URL", "").strip() or DEFAULT_URL,
        model_id=os.environ.get("WATSONX_MODEL_ID", "").strip() or DEFAULT_MODEL_ID,
    )


def credentials_present() -> bool:
    """Whether the environment has what a client needs. Reads no secret value."""
    return from_env() is not None
