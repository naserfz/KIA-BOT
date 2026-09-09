from __future__ import annotations

import json
import urllib.request
import tkinter as tk
from tkinter import messagebox
from pathlib import Path


class MarketSelector:

    API_URL = "https://apiv2.nobitex.ir/market/stats"
    STATE_FILE = Path(__file__).with_name("market_state.json")

    def __init__(self) -> None:
        self.selected_market: str | None = None
        self.markets: list[str] = []
        self.active_market: str | None = self.load_active_market()

    def load_active_market(self) -> str | None:

        if not self.STATE_FILE.exists():
            return None

        try:
            data = json.loads(
                self.STATE_FILE.read_text(
                    encoding="utf-8"
                )
            )

            market = data.get("active_market")

            if market:
                return str(market).upper()

        except Exception:
            pass

        return None

    def save_active_market(self) -> None:

        data = {
            "active_market": self.active_market
        }

        self.STATE_FILE.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def load_markets(self) -> list[str]:

        request = urllib.request.Request(
            self.API_URL,
            headers={
                "User-Agent": "KIA-BOT/1.0",
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=20,
        ) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

        if data.get("status") != "ok":
            raise RuntimeError(
                f"Nobitex API error: {data}"
            )

        stats = data.get("stats", {})

        if not isinstance(stats, dict):
            raise RuntimeError(
                "Invalid Nobitex market response."
            )

        markets = []

        for symbol in stats:

            symbol = str(symbol).strip().lower()

            if "-" not in symbol:
                continue

            markets.append(
                symbol.replace("-", "").upper()
            )

        markets = sorted(set(markets))

        if not markets:
            raise RuntimeError(
                "No Nobitex markets received."
            )

        print(
            f"NOBITEX MARKETS RECEIVED: {len(markets)}"
        )

        return markets

    def show(self) -> str | None:

        self.markets = self.load_markets()

        # Unique base cryptocurrencies
        quote_currencies = {
            "USDT",
            "RLS",
        }

        cryptocurrencies = set()

        for market in self.markets:

            for quote in quote_currencies:

                if market.endswith(quote):

                    base = market[:-len(quote)]

                    if base:
                        cryptocurrencies.add(base)

                    break

        root = tk.Tk()
        root.title(
            "KIA BOT - Nobitex Market Selector"
        )
        root.geometry("620x760")
        root.resizable(False, False)

        # ==================================================
        # TITLE
        # ==================================================

        tk.Label(
            root,
            text="NOBITEX MARKET SELECTOR",
            font=("Segoe UI", 17, "bold"),
        ).pack(pady=(15, 5))

        # ==================================================
        # COUNTERS
        # ==================================================

        counter_frame = tk.Frame(root)
        counter_frame.pack(pady=8)

        tk.Label(
            counter_frame,
            text=f"TOTAL MARKETS: {len(self.markets)}",
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left", padx=15)

        tk.Label(
            counter_frame,
            text=f"CRYPTOCURRENCIES: {len(cryptocurrencies)}",
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left", padx=15)

        # ==================================================
        # ACTIVE MARKET
        # ==================================================

        active_frame = tk.Frame(
            root,
            relief="groove",
            borderwidth=2,
            padx=15,
            pady=10,
        )
        active_frame.pack(
            fill="x",
            padx=20,
            pady=10,
        )

        tk.Label(
            active_frame,
            text="ACTIVE MARKET",
            font=("Segoe UI", 10, "bold"),
        ).pack()

        active_text = tk.StringVar()

        def update_active_display():

            if self.active_market:

                active_text.set(
                    f" {self.active_market}"
                )

            else:

                active_text.set(
                    " NONE"
                )

        active_label = tk.Label(
            active_frame,
            textvariable=active_text,
            font=("Segoe UI", 15, "bold"),
        )
        active_label.pack()

        update_active_display()

        # ==================================================
        # SEARCH
        # ==================================================

        search_frame = tk.Frame(root)
        search_frame.pack(
            fill="x",
            padx=20,
            pady=5,
        )

        search_var = tk.StringVar()

        search_entry = tk.Entry(
            search_frame,
            textvariable=search_var,
            font=("Segoe UI", 12),
        )
        search_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 8),
        )

        # ==================================================
        # MARKET LIST
        # ==================================================

        list_frame = tk.Frame(root)
        list_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=10,
        )

        scrollbar = tk.Scrollbar(
            list_frame
        )
        scrollbar.pack(
            side="right",
            fill="y",
        )

        listbox = tk.Listbox(
            list_frame,
            font=("Consolas", 12),
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE,
        )

        listbox.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.config(
            command=listbox.yview
        )

        def refresh_list():

            query = (
                search_var.get()
                .strip()
                .upper()
            )

            listbox.delete(
                0,
                tk.END,
            )

            for market in self.markets:

                if (
                    not query
                    or query in market
                ):
                    listbox.insert(
                        tk.END,
                        market,
                    )

            # Highlight current active market
            for index in range(
                listbox.size()
            ):

                if (
                    self.active_market
                    and listbox.get(index)
                    == self.active_market
                ):
                    listbox.selection_set(index)
                    listbox.see(index)
                    break

        def search():

            refresh_list()

            query = (
                search_var.get()
                .strip()
                .upper()
            )

            if not query:
                return

            for index in range(
                listbox.size()
            ):

                if listbox.get(index) == query:

                    listbox.selection_clear(
                        0,
                        tk.END,
                    )

                    listbox.selection_set(
                        index
                    )

                    listbox.see(index)

                    break

        def clear_search():

            search_var.set("")
            refresh_list()

        # ==================================================
        # SEARCH BUTTONS
        # ==================================================

        tk.Button(
            search_frame,
            text="SEARCH",
            command=search,
            font=("Segoe UI", 10, "bold"),
            width=10,
        ).pack(
            side="left",
            padx=(0, 5),
        )

        tk.Button(
            search_frame,
            text="CLEAR",
            command=clear_search,
            font=("Segoe UI", 10),
            width=8,
        ).pack(
            side="left"
        )

        search_entry.bind(
            "<Return>",
            lambda event: search()
        )

        # ==================================================
        # STATUS
        # ==================================================

        status_text = tk.StringVar(
            value="No market selected"
        )

        tk.Label(
            root,
            textvariable=status_text,
            font=("Segoe UI", 10),
        ).pack(pady=5)

        # ==================================================
        # ACTIVATE
        # ==================================================

        def activate():

            selection = listbox.curselection()

            if not selection:

                messagebox.showwarning(
                    "KIA BOT",
                    "Please select a market first.",
                )

                return

            market = listbox.get(
                selection[0]
            )

            self.active_market = market
            self.selected_market = market

            self.save_active_market()

            update_active_display()

            status_text.set(
                f"ACTIVE: {market}"
            )

            refresh_list()

            print(
                f"ACTIVE MARKET: {market}"
            )

        # ==================================================
        # DEACTIVATE
        # ==================================================

        def deactivate():

            if not self.active_market:

                messagebox.showinfo(
                    "KIA BOT",
                    "There is no active market.",
                )

                return

            old_market = self.active_market

            self.active_market = None
            self.selected_market = None

            self.save_active_market()

            update_active_display()

            status_text.set(
                "No active market"
            )

            refresh_list()

            print(
                f"MARKET DEACTIVATED: {old_market}"
            )

        # ==================================================
        # BUTTONS
        # ==================================================

        button_frame = tk.Frame(root)
        button_frame.pack(
            pady=(5, 20)
        )

        tk.Button(
            button_frame,
            text="ACTIVATE MARKET",
            command=activate,
            font=("Segoe UI", 11, "bold"),
            width=20,
            height=2,
        ).pack(
            side="left",
            padx=8,
        )

        tk.Button(
            button_frame,
            text="DEACTIVATE",
            command=deactivate,
            font=("Segoe UI", 11, "bold"),
            width=16,
            height=2,
        ).pack(
            side="left",
            padx=8,
        )

        refresh_list()

        root.mainloop()

        return self.active_market


if __name__ == "__main__":

    selector = MarketSelector()

    market = selector.show()

    print(
        f"FINAL ACTIVE MARKET: {market}"
    )
