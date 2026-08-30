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

## Why the chat endpoint and not text/generation

The first wiring used /ml/v1/text/generation, which hands the prompt to the
model raw. An instruct model given a raw prompt has not been told where the
instruction ends and its own turn begins, and Granite returned incoherent token
spam on a prompt that reads perfectly well to a person. That is not a prompt
problem and no amount of rewording fixes it: the chat template is part of how
the model was trained, and skipping it is using a different model than the one
that was evaluated.

/ml/v1/text/chat takes a messages array and applies the model's own chat
template server-side, so the template can never drift from what the model
expects. The loop's surface is unchanged: generate(prompt) still takes one
string, and this module turns it into the user turn.

The failure was worth the cost of finding, because it is the failure mode this
whole layer is built around, wearing a different hat. Token spam is obviously
wrong to a reader. A fluent paragraph with one invented number is not, and the
gate is what catches the second.

## What is and is not confirmed

Confirmed on this account: region us-south, and ibm/granite-4-h-small servable.
Confirmed by a live call: see docs/BOB_USAGE.md for the run and its date.

Not confirmed: ibm/granite-4-1-8b-instruct, the previous default, 404s on this
account and has been removed. WATSONX_MODEL_ID and WATSONX_URL still override
everything here, because a deployment on another account or region is the
ordinary case and a wrong id fails safely: the call errors, the attempt is
recorded, and the floor is served.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

IAM_URL = "https://iam.cloud.ibm.com/identity/token"
IAM_GRANT_TYPE = "urn:ibm:params:oauth:grant-type:apikey"

DEFAULT_URL = "https://us-south.ml.cloud.ibm.com"
DEFAULT_MODEL_ID = "ibm/granite-4-h-small"

# The chat endpoint, which applies the model's own instruct template. Not
# text/generation: see the note above on what a raw prompt does to an instruct
# model.
CHAT_PATH = "/ml/v1/text/chat"

# The dated API version every ml/v1 call carries. Overridable by
# WATSONX_API_VERSION, because it is the parameter most likely to move under a
# deployment and the least interesting to redeploy code for.
DEFAULT_API_VERSION = "2023-05-29"

# One line, stating the constraint the gate will enforce anyway. The system
# turn is where an instruct model expects its standing instructions, and the
# quote-only rule is the only standing instruction this layer has.
SYSTEM_MESSAGE = (
    "You explain the output of a deterministic orbital-mechanics solver that "
    "has already run. You never produce a figure of your own: every number you "
    "write must be one you were given, copied exactly."
)

# Deterministic decoding. The gate is dispositive either way, but a sampled
# explanation that passes once and fails the next time on the same solve makes
# the served_by field noise rather than a record.
DEFAULT_PARAMETERS = {
    "temperature": 0,
    "max_tokens": 700,
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
    One watsonx chat endpoint.

    `generate(prompt) -> str` is the whole surface the loop uses, which is what
    lets a stub stand in for it without importing anything from this file. The
    messages array is built here and nowhere else, so the loop cannot acquire
    an opinion about the chat template.
    """
    api_key: str
    project_id: str
    url: str = DEFAULT_URL
    model_id: str = DEFAULT_MODEL_ID
    api_version: str = DEFAULT_API_VERSION

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

    def messages(self, prompt: str) -> list:
        """
        The prompt as a chat exchange.

        Separated from generate() so the shape sent to watsonx can be inspected
        and asserted on without a credential or a network call.
        """
        return [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ]

    def generate(self, prompt: str) -> str:
        import requests
        response = requests.post(
            f"{self.url.rstrip('/')}{CHAT_PATH}",
            params={"version": self.api_version},
            headers={
                "Authorization": f"Bearer {self._bearer()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "model_id": self.model_id,
                "project_id": self.project_id,
                "messages": self.messages(prompt),
                **DEFAULT_PARAMETERS,
            },
            timeout=REQUEST_TIMEOUT_S,
        )
        if response.status_code != 200:
            # The status alone is not enough to debug a 400 from watsonx, and
            # the chat endpoint's errors name the offending field rather than
            # echoing the payload, so the body is included. The credential is
            # in a header, never in the body, so it cannot come back this way.
            raise GraniteError(
                f"watsonx chat failed with status {response.status_code}: "
                f"{response.text[:400]}")
        choices = response.json().get("choices") or []
        if not choices:
            raise GraniteError("watsonx returned no choices")
        content = (choices[0].get("message") or {}).get("content", "")
        if not content.strip():
            raise GraniteError("watsonx returned an empty completion")
        return content.strip()


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
        api_version=(os.environ.get("WATSONX_API_VERSION", "").strip()
                     or DEFAULT_API_VERSION),
    )


def credentials_present() -> bool:
    """Whether the environment has what a client needs. Reads no secret value."""
    return from_env() is not None
