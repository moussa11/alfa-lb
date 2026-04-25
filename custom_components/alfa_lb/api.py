"""Alfa Lebanon mobile-API client.

Reverse-engineered from the official Android app (com.apps2you.alfa v5.2.86):
all calls POST to ``/V2/Default`` with an AES-256-CBC encrypted JSON body
wrapped as ``{"Data": "<base64 ciphertext>"}``. The plaintext carries the
operation name in a ``Method`` field plus a few platform metadata fields.
The user logs in with phone number + password — no captcha, no cookies.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import random
import time
from datetime import date, datetime
from typing import Any

import aiohttp
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

_LOGGER = logging.getLogger(__name__)

API_URL = "https://wsitranslator-live.alfa.com.lb/V2/Default"

_AES_KEY = b"CXLI1C3iCLHRQk5MH9aDvdYYQfAFlte2"
_AES_IV = b"t0dmo_999@999---"

_HEADERS = {
    "Content-Type": "application/json; charset=UTF-8",
    "Accept": "application/json",
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 16; Pixel 7a Build/CP1A.260305.018)",
    "Language": "en",
}

# Status codes returned in the decrypted payload (from the app's StatusCodes).
_STATUS_OK = {2000, 8081, 8090, 8101}
_STATUS_AUTH_FAILED = {3000, 3001, 3002, 4000, 4001, 4002}


class AlfaAuthError(Exception):
    """Credentials rejected by the Alfa API."""


class AlfaApiError(Exception):
    """Transport / parsing / non-auth API error."""


def _encrypt(plaintext: str) -> str:
    cipher = AES.new(_AES_KEY, AES.MODE_CBC, _AES_IV)
    return base64.b64encode(cipher.encrypt(pad(plaintext.encode(), 16))).decode()


def _decrypt(ciphertext: str) -> str:
    cipher = AES.new(_AES_KEY, AES.MODE_CBC, _AES_IV)
    return unpad(cipher.decrypt(base64.b64decode(ciphertext)), 16).decode()


def _parse_money(raw: str | None) -> float | None:
    """`"$ 63.05"` → ``63.05``."""
    if not raw:
        return None
    import re
    m = re.search(r"-?\d+(?:\.\d+)?", raw)
    return float(m.group(0)) if m else None


def _parse_dmy(raw: str | None) -> date | None:
    """`"19/05/2026"` → ``date(2026, 5, 19)``."""
    if not raw:
        return None
    parts = raw.strip().split("/")
    if len(parts) != 3:
        return None
    try:
        d, m, y = (int(x) for x in parts)
        return date(y, m, d)
    except ValueError:
        return None


def _to_mb(value: str | None, unit: str | None) -> float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    u = (unit or "").upper()
    if u == "GB":
        return num * 1024
    if u == "KB":
        return num / 1024
    return num


class AlfaClient:
    """Async client for the Alfa mobile API.

    Holds the credentials and a (cached) ``accesstoken``. Re-authenticates
    transparently on token expiry; raises :class:`AlfaAuthError` only when
    the password itself is wrong.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        mobile: str,
        password: str,
    ) -> None:
        self._session = session
        self._mobile = mobile.strip()
        self._password = password
        self._token: str | None = None

    @property
    def mobile_number(self) -> str:
        return self._mobile

    async def _call(self, method: str, body: dict[str, Any]) -> dict[str, Any]:
        ts = int(time.time())
        payload = {
            **body,
            "Method": method,
            "Platform": "android",
            "App_version": "5.2.86",
            "TimeStamp": ts,
            "Signature": f"{random.randint(0, 100)}{ts}",
        }
        encrypted = _encrypt(json.dumps(payload, separators=(",", ":")))
        envelope = {"Data": encrypted}
        try:
            async with self._session.post(
                API_URL,
                json=envelope,
                headers=_HEADERS,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                text = await resp.text()
                if resp.status >= 500:
                    raise AlfaApiError(f"HTTP {resp.status} from Alfa: {text[:200]}")
                if resp.status >= 400:
                    raise AlfaApiError(f"HTTP {resp.status}: {text[:200]}")
                try:
                    outer = json.loads(text)
                except ValueError as err:
                    raise AlfaApiError(f"Bad JSON envelope: {err}") from err
                if isinstance(outer, dict) and outer.get("Error"):
                    raise AlfaApiError(f"Alfa API error: {outer['Error']}")
                data_blob = outer.get("Data") if isinstance(outer, dict) else None
                if not data_blob:
                    raise AlfaApiError(f"No Data field in response: {text[:200]}")
                try:
                    decrypted = _decrypt(data_blob)
                except Exception as err:  # noqa: BLE001
                    raise AlfaApiError(f"Decrypt failed: {err}") from err
                try:
                    result = json.loads(decrypted)
                except ValueError as err:
                    raise AlfaApiError(f"Bad inner JSON: {err}") from err
                _LOGGER.debug("Alfa %s -> Status=%s", method, result.get("Status"))
                return result
        except aiohttp.ClientError as err:
            raise AlfaApiError(str(err)) from err
        except asyncio.TimeoutError as err:
            raise AlfaApiError(f"Timeout calling {method}") from err

    async def _signin(self) -> None:
        result = await self._call(
            "Signin",
            {
                "Username": self._mobile,
                "UserPassword": self._password,
                "PlayerId": "",
            },
        )
        status = result.get("Status")
        token = result.get("accesstoken")
        if status in _STATUS_AUTH_FAILED or not token:
            msg = result.get("Message") or f"Status {status}"
            raise AlfaAuthError(f"Signin rejected: {msg}")
        if status not in _STATUS_OK:
            raise AlfaApiError(f"Unexpected Signin Status={status}")
        self._token = token

    async def _authed_call(self, method: str, body: dict[str, Any]) -> dict[str, Any]:
        if not self._token:
            await self._signin()
        full = {**body, "AccessToken": self._token}
        result = await self._call(method, full)
        status = result.get("Status")
        if status in _STATUS_AUTH_FAILED:
            # Token expired — re-Signin once and retry.
            self._token = None
            await self._signin()
            full = {**body, "AccessToken": self._token}
            result = await self._call(method, full)
        return result

    async def async_validate(self) -> dict[str, Any]:
        """Verify credentials by signing in. Returns the Profile block."""
        await self._signin()
        # GetAccountDetails confirms the line is provisioned.
        details = await self._authed_call(
            "GetAccountDetails", {"MSISDN": self._mobile}
        )
        return {
            "MobileNumberValue": details.get("MobileNumberValue") or self._mobile,
            "TypeValue": details.get("TypeValue"),
            "SubTypeValue": details.get("SubTypeValue"),
        }

    async def async_get_account_data(self) -> dict[str, Any]:
        """Fetch account, expiry, and recharge history; normalise."""
        if not self._token:
            await self._signin()
        details, expiry, recharge = await asyncio.gather(
            self._authed_call("GetAccountDetails", {"MSISDN": self._mobile}),
            self._authed_call("GetPrepaidExpiryDate", {"MSISDN": self._mobile}),
            self._authed_call("GetRechargeHistory", {"MSISDN": self._mobile}),
            return_exceptions=False,
        )

        result: dict[str, Any] = {
            "mobile": details.get("MobileNumberValue") or self._mobile,
            "balance_usd": _parse_money(details.get("CurrentBalanceValue")),
            "balance_raw": details.get("CurrentBalanceValue"),
            "response_code": details.get("Status"),
            "services": [],
            "last_recharge_amount": None,
            "last_recharge_date": None,
            "days_until_expiry": None,
            "data_used_mb": None,
            "data_total_mb": None,
            "data_remaining_mb": None,
            "plan_name": None,
            "validity": None,
        }

        primary_used: float | None = None
        primary_total: float | None = None
        primary_validity: date | None = None
        primary_plan: str | None = None

        for svc in details.get("ServiceInformationValue") or []:
            name = svc.get("ServiceNameValue")
            for det in svc.get("ServiceDetailsInformationValue") or []:
                used = _to_mb(det.get("ConsumptionValue"), det.get("ConsumptionUnitValue"))
                total = _to_mb(det.get("PackageValue"), det.get("PackageUnitValue"))
                validity = _parse_dmy(det.get("ValidityDateValue"))
                entry = {
                    "service": name,
                    "description": det.get("DescriptionValue"),
                    "used_mb": used,
                    "total_mb": total,
                    "remaining_mb": (
                        total - used if used is not None and total is not None else None
                    ),
                    "validity": validity.isoformat() if validity else None,
                }
                result["services"].append(entry)
                if primary_used is None and used is not None and total is not None:
                    primary_used = used
                    primary_total = total
                    primary_validity = validity
                    primary_plan = name or det.get("DescriptionValue")

        result["data_used_mb"] = primary_used
        result["data_total_mb"] = primary_total
        result["data_remaining_mb"] = (
            (primary_total - primary_used)
            if primary_used is not None and primary_total is not None
            else None
        )
        result["plan_name"] = primary_plan
        result["validity"] = (
            datetime.combine(primary_validity, datetime.min.time()).astimezone()
            if primary_validity
            else None
        )

        # Last recharge — newest first.
        recharges = recharge.get("MSISDNRecharges") or []
        if recharges:
            top = recharges[0]
            try:
                amt = top.get("Amount")
                result["last_recharge_amount"] = float(amt) if amt is not None else None
            except (TypeError, ValueError):
                pass
            d = _parse_dmy(top.get("TimeStamp"))
            if d:
                result["last_recharge_date"] = datetime.combine(
                    d, datetime.min.time()
                ).astimezone()

        # Days until expiry — derive from PrepaidExpiryDate (DD/MM/YYYY).
        exp_date = _parse_dmy(expiry.get("PrepaidExpiryDate"))
        if exp_date:
            result["days_until_expiry"] = (exp_date - date.today()).days

        return result
