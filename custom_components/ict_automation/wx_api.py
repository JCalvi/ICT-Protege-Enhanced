import hashlib
import logging
from urllib.parse import unquote_plus

import aiohttp

_LOGGER = logging.getLogger(__name__)


class ProtegeWXAPI:
    """Small HTTPS client used only to retrieve Protege WX record metadata."""

    def __init__(self, host: str, username: str = "", password: str = ""):
        self.host = host.strip()
        self.username = username
        self.password = password
        self._session = None
        self.last_access_mode = None

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
        """Send one authenticated/session WX DLL API request.

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

    async def _request_get(self, parameters: str) -> str:
        """Send a plain read-only GET request.

        Many Protege WX controllers expose the Request&Type=List endpoints
        anonymously even though the normal WX web UI itself requires a login.
        """
        url = f"https://{self.host}/PRT_CTRL_DIN_ISAPI.dll?{parameters}"
        async with self._session.get(url, ssl=False) as response:
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
            # An empty list can be a valid table with no programmed records.
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

        # A non-empty response that contains no numeric record pairs is not a
        # usable list response (for example an authentication/error payload).
        return saw_record_pair, names

    async def _fetch_lists(self, tables: dict[str, str], anonymous: bool):
        result = {}
        valid = True
        total_records = 0

        for key, table in tables.items():
            parameters = f"Request&Type=List&SubType={table}"
            response = (
                await self._request_get(parameters)
                if anonymous
                else await self._request(parameters)
            )
            response_valid, names = self._parse_name_list(response)
            if not response_valid:
                valid = False
            result[key] = names
            total_records += len(names)

        # Do not accept four blank/meaningless HTTP 200 responses as a valid
        # database inventory. A real Protege installation will have at least
        # one programmed record across these tables.
        return valid and total_records > 0, result

    async def fetch_name_maps(self, tables: dict[str, str]) -> dict[str, dict[int, str]]:
        """Return record-name maps, trying anonymous read-only access first.

        Lookup order:
        1. Anonymous HTTPS Request&Type=List GET requests.
        2. Configured Protege WX operator credentials, if supplied.
        3. Raise so the caller can fall back to Automation Service probing.
        """
        timeout = aiohttp.ClientTimeout(total=10)
        cookie_jar = aiohttp.CookieJar(unsafe=True)
        self.last_access_mode = None

        async with aiohttp.ClientSession(
            timeout=timeout,
            cookie_jar=cookie_jar,
        ) as session:
            self._session = session
            logged_in = False
            try:
                try:
                    valid, result = await self._fetch_lists(tables, anonymous=True)
                except Exception as err:
                    _LOGGER.debug("Anonymous WX database lookup failed: %s", err)
                else:
                    if valid:
                        self.last_access_mode = "anonymous"
                        return result

                if not self.username or not self.password:
                    raise RuntimeError(
                        "Anonymous WX database lookup unavailable and no operator credentials configured"
                    )

                if not await self._login():
                    raise RuntimeError("WX API operator authentication failed")
                logged_in = True

                valid, result = await self._fetch_lists(tables, anonymous=False)
                if not valid:
                    raise RuntimeError(
                        "WX API operator login succeeded but database list lookup failed"
                    )

                self.last_access_mode = "operator"
                return result
            finally:
                if logged_in:
                    await self._logout()
                self._session = None

    async def validate_operator(self) -> bool:
        """Validate optional fallback operator credentials explicitly."""
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
