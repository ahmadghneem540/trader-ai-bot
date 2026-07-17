from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import httpx


class MT5BridgeClient:
    def __init__(self, base_url: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.request(method, url, json=json, params=params)
            response.raise_for_status()
            payload = response.json()
        if isinstance(payload, dict) and "data" in payload and "success" in payload:
            if not payload["success"]:
                raise RuntimeError(payload.get("error") or payload.get("message") or "MT5 bridge request failed")
            return payload.get("data")
        return payload

    def connect(self, login: Optional[int], password: Optional[str], server: Optional[str]) -> Dict[str, Any]:
        payload = {"login": login, "password": password, "server": server}
        return self._request("POST", "/connect", json=payload)

    def disconnect(self) -> Dict[str, Any]:
        return self._request("POST", "/disconnect")

    def status(self) -> Dict[str, Any]:
        return self._request("GET", "/status")

    def account(self) -> Optional[Dict[str, Any]]:
        return self._request("GET", "/account")

    def symbols(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/symbols")

    def tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        return self._request("GET", f"/tick/{symbol}")

    def candles(self, symbol: str, timeframe: str, count: int) -> Optional[List[Dict[str, Any]]]:
        return self._request("GET", f"/candles/{symbol}/{timeframe}", params={"count": count})

    def positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {"symbol": symbol} if symbol else None
        return self._request("GET", "/open_positions", params=params)

    def orders(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/orders")

    def history(self, date_from: Any = None, date_to: Any = None) -> List[Dict[str, Any]]:
        params = {}
        if date_from is not None:
            params["date_from"] = date_from.isoformat() if hasattr(date_from, "isoformat") else str(date_from)
        if date_to is not None:
            params["date_to"] = date_to.isoformat() if hasattr(date_to, "isoformat") else str(date_to)
        return self._request("GET", "/history", params=params or None)

    def buy(self, symbol: str, volume: float, sl: Optional[float] = None, tp: Optional[float] = None) -> SimpleNamespace:
        data = self._request("POST", "/buy", json={"symbol": symbol, "volume": volume, "sl": sl, "tp": tp})
        return SimpleNamespace(**data)

    def sell(self, symbol: str, volume: float, sl: Optional[float] = None, tp: Optional[float] = None) -> SimpleNamespace:
        data = self._request("POST", "/sell", json={"symbol": symbol, "volume": volume, "sl": sl, "tp": tp})
        return SimpleNamespace(**data)

    def close(self, ticket: int) -> SimpleNamespace:
        data = self._request("POST", "/close", json={"ticket": ticket})
        return SimpleNamespace(**data)

    def modify(self, ticket: int, sl: Optional[float] = None, tp: Optional[float] = None) -> SimpleNamespace:
        data = self._request("POST", "/modify", json={"ticket": ticket, "sl": sl, "tp": tp})
        return SimpleNamespace(**data)
