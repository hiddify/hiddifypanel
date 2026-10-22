"""The project's donation wallets: the one list both admin UIs show.

The translated ``Donation.description`` only marks where they go (``WALLETS_MARK``), so an address is changed
here once instead of in every translation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from markupsafe import Markup, escape

WALLETS_MARK = "<div class='donation-wallets'></div>"


@dataclass(frozen=True)
class Wallet:
    id: str  # Admin V2 picks the coin icon by it
    name: str
    network: str  # the coin / chain to send on: a transfer on another network is lost
    address: str


WALLETS: tuple[Wallet, ...] = (
    Wallet("bitcoin", "Bitcoin", "BTC", "bc1quepmxl4pmfvy5sdrnmd4sxgnn83xd70lu30gkx"),
    Wallet("usdt-bep20", "Tether", "BEP20", "0x2036cBd7e0fb883c8614FA14f5182e2828Fd90a5"),
    Wallet("tron", "Tron", "TRX", "TMfrMgzY4DrjhyZh5s67YvCyrcHvJAkXjb"),
    Wallet("litecoin", "Litecoin", "LTC", "ltc1qwyd2hdn5wc04fkvp2mj7glayy5galxfm3luftg"),
    Wallet("ton", "Gram", "TON", "UQDGA32X8-xgRrZnzW0uPP-ChssO2dRLQ5NPubKj3sBqHwNp"),
)


def wallets() -> list[dict[str, str]]:
    return [asdict(w) for w in WALLETS]


def legacy_description(text: str) -> Markup:
    """The translated text with the wallets as the classic modal's copy buttons (copy-link + share-link)."""
    items = "".join(
        f"<li><div class='btn-group'>"
        f"<a role='button' data-copy='{escape(w.address)}' class='btn btn-secondary copy-link'><i class='fa-regular fa-copy'></i></a>"
        f"<a role='button' data-copy='{escape(w.address)}' class='btn btn-info share-link'>{escape(w.name)} ({escape(w.network)})</a>"
        f"</div></li>"
        for w in WALLETS
    )
    return Markup(str(text).replace(WALLETS_MARK, f"<ul>{items}</ul>"))
