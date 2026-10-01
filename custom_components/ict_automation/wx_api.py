import hashlib
import logging
from urllib.parse import unquote_plus

import aiohttp

_LOGGER = logging.getLogger(__name__)


class ProtegeWXAPI:
    """Small HTTPS client used only to retrieve Protege WX record metadata."""

    def __init__(self, host: str, username: str, password: str):
        self.host = host.strip()
        self.username = username.strip()
        self.password = password
        self._session = None

    @staticmethod
    def _sha1(value: str) -> str:
        return hashlib.sha1(value.encode("utf-8")).hexdigest().upper()

    @staticmethod
    def _xor_fn(value: str, number: int) -> str:
        """Match ICT's documented XOR helper for WX operator authentication."""
        number_bytes = [
            (number >> 0) & 0xFF,
            (number >> 8) & 0xFF,
            (number >> 16) & 0xFF,
            (number >> 24) & 0xFF,
        ]
        return "".join(
            f"{((ord(char) & 0xFF) ^ number_bytes[index % 4]):02X}"
            for index, char in enumerate(value)
        )

    async def _request(self, parameters: str) -> str:
        """Send one WX DLL API request while preserving the operator session.

        ICT's current API example sends the parameter string in the POST body.
        Older controllers/documentation also show query-string GET requests, so
        retain GET as a compatibility fallback if POST is not supported.
        """
        url = f"https://{self.host}/PRT_CTRL_DIN_ISAPI.dll"

        async with self._session.post(url, data=parameters, ssl=False) as response:
            if response.status == 200:
                return (await response.text()).strip()
            if response.status not in (404, 405, 501):
                raise RuntimeError(f"WX API returned HTTP {response.status}")

        async with self._session.get(f"{url}?{parameters}", ssl=False) as response:
            if response.status != 200:
                raise RuntimeError(f"WX API returned HTTP {response.status}")
            return (await response.text()).strip()

    async def _login(self) -> bool:
        if not self.username or not self.password:
            return False

        first_random_text = await self._request(
            "Command&Type=Session&SubType=InitSession"
        )
        try:
            first_random = int(first_random_text)
        except ValueError:
            _LOGGER.warning(
                "WX API InitSession returned unexpected data: %s",
                first_random_text[:120],
            )
            return False

        password_hash = hashlib.sha1(self.password.encode("utf-8")).hexdigest().lower()
        hash_xor_username = self._sha1(
            self._xor_fn(self.username, first_random + 1)
        )
        hash_xor_password = self._sha1(
            self._xor_fn(password_hash, first_random)
        )

        result = await self._request(
            "Command&Type=Session&SubType=CheckPasswordServer"
            f"&Name={hash_xor_username}&Password={hash_xor_password}"
        )
        if result.upper().startswith("FAIL"):
            _LOGGER.warning("WX API operator authentication rejected: %s", result[:120])
            return False
        return True

    async def _logout(self) -> None:
        try:
            await self._request("Command&Type=Session&SubType=CloseSession")
        except Exception:
            pass

    @staticmethod
    def _parse_name_list(response: str):
        """Return (valid_response, names) for one WX list response."""
        if response is None:
            return False, {}

        text = response.strip()
        if text.upper().startswith("FAIL") or "<html" in text.lower():
            return False, {}

        names = {}
        if not text:
            return True, names

        saw_record_pair = False
        for part in text.split("&"):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            try:
                record_id = int(unquote_plus(key))
            except ValueError:
                continue
            saw_record_pair = True
            name = unquote_plus(value).strip()
            if name:
                names[record_id] = name

        return saw_record_pair, names

    async def _fetch_lists(self, tables: dict[str, str]):
        result = {}
        valid = True
        total_records = 0

        for key, table in tables.items():
            response = await self._request(f"Request&Type=List&SubType={table}")
            response_valid, names = self._parse_name_list(response)
            if not response_valid:
                valid = False
            result[key] = names
            total_records += len(names)

        return valid and total_records > 0, result

    async def fetch_name_maps(self, tables: dict[str, str]) -> dict[str, dict[int, str]]:
        """Return record-name maps using an authenticated Protege WX operator."""
        if not self.username or not self.password:
            raise RuntimeError("WX operator credentials are not configured")

        timeout = aiohttp.ClientTimeout(total=10)
        cookie_jar = aiohttp.CookieJar(unsafe=True)

        async with aiohttp.ClientSession(
            timeout=timeout,
            cookie_jar=cookie_jar,
        ) as session:
            self._session = session
            logged_in = False
            try:
                if not await self._login():
                    raise RuntimeError("WX API operator authentication failed")
                logged_in = True

                valid, result = await self._fetch_lists(tables)
                if not valid:
                    raise RuntimeError(
                        "WX API operator login succeeded but database list lookup failed"
                    )
                return result
            finally:
                if logged_in:
                    await self._logout()
                self._session = None

    async def validate_operator(self) -> bool:
        """Validate the configured Protege WX operator credentials."""
        if not self.username or not self.password:
            return False

        timeout = aiohttp.ClientTimeout(total=10)
        cookie_jar = aiohttp.CookieJar(unsafe=True)
        async with aiohttp.ClientSession(
            timeout=timeout,
            cookie_jar=cookie_jar,
        ) as session:
            self._session = session
            logged_in = False
            try:
                logged_in = await self._login()
                return logged_in
            finally:
                if logged_in:
                    await self._logout()
                self._session = None
