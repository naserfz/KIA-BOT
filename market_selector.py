from __future__ import annotations

import json
import urllib.request
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox


ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "market_selection.json"


class MarketSelector:

    EXCHANGES = {
        "NOBITEX": {
            "stats_url": "https://apiv2.nobitex.ir/market/stats"
        }
    }

    def __init__(self) -> None:
        self.selection: dict[str, dict] = {}
        self.markets_cache: dict[str, list[str]] = {}

        self.exchange_var = None
        self.search_var = None
        self.status_var = None
        self.count_var = None

        self.load_selection()

    # =========================================================
    # STORAGE
    # =========================================================

    def load_selection(self) -> None:
        if not STATE_FILE.exists():
            return

        try:
            data = json.loads(
                STATE_FILE.read_text(encoding="utf-8-sig")
            )

            for item in data.get("selections", []):
                exchange = str(
                    item.get("exchange", "")
                ).strip().upper()

                if not exchange:
                    continue

                symbols = {
                    str(x).strip().upper()
                    for x in item.get("symbols", [])
                    if str(x).strip()
                }

                analysis = {
                    str(x).strip().upper()
                    for x in item.get("analysis", [])
                    if str(x).strip()
                }

                self.selection[exchange] = {
                    "symbols": symbols,
                    "analysis": analysis & symbols,
                }

        except Exception:
            self.selection = {}

    def save_selection(self) -> None:
        output = []

        for exchange, data in sorted(
            self.selection.items()
        ):
            symbols = sorted(data["symbols"])
            analysis = sorted(
                data["analysis"] & data["symbols"]
            )

            if not symbols:
                continue

            output.append(
                {
                    "exchange": exchange,
                    "symbols": symbols,
                    "analysis": analysis,
                }
            )

        STATE_FILE.write_text(
            json.dumps(
                {"selections": output},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    # =========================================================
    # MARKET API
    # =========================================================

    def load_markets(self, exchange: str) -> list[str]:
        exchange = exchange.upper()

        if exchange in self.markets_cache:
            return self.markets_cache[exchange]

        config = self.EXCHANGES.get(exchange)

        if not config:
            return []

        request = urllib.request.Request(
            config["stats_url"],
            headers={
                "User-Agent": "KIA-BOT/1.0"
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=20,
        ) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

        stats = data.get("stats", {})

        if not isinstance(stats, dict):
            raise RuntimeError(
                f"Invalid {exchange} market response."
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

        self.markets_cache[exchange] = markets

        return markets

    # =========================================================
    # GUI
    # =========================================================

    def show(self) -> None:

        root = tk.Tk()

        self.exchange_var = tk.StringVar(
            master=root,
            value="NOBITEX",
        )

        self.search_var = tk.StringVar(
            master=root,
        )

        self.status_var = tk.StringVar(
            master=root,
            value="Ready",
        )

        self.count_var = tk.StringVar(
            master=root,
            value="0 markets | 0 analysis",
        )

        root.title("KIA BOT - Market & Exchange Manager")
        root.geometry("1180x760")
        root.minsize(1050, 680)

        style = ttk.Style(root)

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 22, "bold"),
        )

        style.configure(
            "Section.TLabel",
            font=("Segoe UI", 11, "bold"),
        )

        style.configure(
            "Action.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=8,
        )

        # -----------------------------------------------------
        # HEADER
        # -----------------------------------------------------

        header = ttk.Frame(
            root,
            padding=(22, 18),
        )
        header.pack(fill="x")

        ttk.Label(
            header,
            text="KIA BOT",
            style="Title.TLabel",
        ).pack(side="left")

        ttk.Label(
            header,
            text="  MARKET & EXCHANGE MANAGER",
            font=("Segoe UI", 11),
        ).pack(
            side="left",
            pady=(9, 0),
        )

        # -----------------------------------------------------
        # MAIN
        # -----------------------------------------------------

        main = ttk.Frame(
            root,
            padding=(18, 5),
        )
        main.pack(
            fill="both",
            expand=True,
        )

        # =====================================================
        # LEFT - EXCHANGES
        # =====================================================

        left = ttk.LabelFrame(
            main,
            text=" EXCHANGES ",
            padding=12,
        )

        left.pack(
            side="left",
            fill="y",
            padx=(0, 10),
        )

        ttk.Label(
            left,
            text="Select one or more exchanges",
            style="Section.TLabel",
        ).pack(
            anchor="w",
            pady=(0, 8),
        )

        exchange_list = tk.Listbox(
            left,
            selectmode=tk.MULTIPLE,
            font=("Segoe UI", 11),
            width=20,
            height=20,
            exportselection=False,
        )

        exchange_list.pack(
            fill="both",
            expand=True,
        )

        for exchange in sorted(self.EXCHANGES):
            exchange_list.insert(
                tk.END,
                exchange,
            )

        # =====================================================
        # CENTER - MARKETS
        # =====================================================

        center = ttk.LabelFrame(
            main,
            text=" MARKETS ",
            padding=12,
        )

        center.pack(
            side="left",
            fill="both",
            expand=True,
            padx=10,
        )

        toolbar = ttk.Frame(center)
        toolbar.pack(
            fill="x",
            pady=(0, 10),
        )

        ttk.Label(
            toolbar,
            text="Exchange:",
        ).pack(side="left")

        exchange_combo = ttk.Combobox(
            toolbar,
            textvariable=self.exchange_var,
            values=tuple(sorted(self.EXCHANGES)),
            state="readonly",
            width=15,
        )

        exchange_combo.pack(
            side="left",
            padx=8,
        )

        search = ttk.Entry(
            toolbar,
            textvariable=self.search_var,
        )

        search.pack(
            side="left",
            fill="x",
            expand=True,
            padx=8,
        )

        ttk.Button(
            toolbar,
            text="SEARCH",
            command=lambda: refresh_markets(),
        ).pack(side="left")

        market_frame = ttk.Frame(center)

        market_frame.pack(
            fill="both",
            expand=True,
        )

        scrollbar = ttk.Scrollbar(
            market_frame,
            orient="vertical",
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        market_list = tk.Listbox(
            market_frame,
            selectmode=tk.MULTIPLE,
            font=("Consolas", 11),
            yscrollcommand=scrollbar.set,
            exportselection=False,
        )

        market_list.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.config(
            command=market_list.yview
        )

        # =====================================================
        # RIGHT - SELECTION STATUS + ACTIONS
        # =====================================================

        right = ttk.LabelFrame(
            main,
            text=" SELECTION STATUS ",
            padding=10,
        )

        right.pack(
            side="left",
            fill="y",
            padx=(10, 0),
        )

        ttk.Label(
            right,
            textvariable=self.count_var,
            style="Section.TLabel",
        ).pack(
            anchor="w",
            pady=(0, 8),
        )

        # -----------------------------------------------------
        # DATABASE MARKETS
        # -----------------------------------------------------

        db_frame = ttk.LabelFrame(
            right,
            text=" DATABASE MARKETS ",
            padding=6,
        )

        db_frame.pack(
            fill="both",
            expand=True,
            pady=(0, 8),
        )

        db_list = tk.Listbox(
            db_frame,
            font=("Consolas", 9),
            width=28,
            height=9,
            exportselection=False,
        )

        db_list.pack(
            fill="both",
            expand=True,
        )

        # -----------------------------------------------------
        # ANALYSIS MARKETS
        # -----------------------------------------------------

        analysis_frame = ttk.LabelFrame(
            right,
            text=" ANALYSIS MARKETS ",
            padding=6,
        )

        analysis_frame.pack(
            fill="both",
            expand=True,
            pady=(0, 8),
        )

        analysis_list = tk.Listbox(
            analysis_frame,
            font=("Consolas", 9),
            width=28,
            height=7,
            exportselection=False,
        )

        analysis_list.pack(
            fill="both",
            expand=True,
        )

        # -----------------------------------------------------
        # ACTIONS
        # -----------------------------------------------------

        ttk.Button(
            right,
            text="ADD SELECTED",
            style="Action.TButton",
            command=lambda: add_selected(),
        ).pack(
            fill="x",
            pady=3,
        )

        ttk.Button(
            right,
            text="MARK FOR ANALYSIS",
            style="Action.TButton",
            command=lambda: mark_analysis(),
        ).pack(
            fill="x",
            pady=3,
        )

        ttk.Button(
            right,
            text="REMOVE SELECTED",
            style="Action.TButton",
            command=lambda: remove_selected(),
        ).pack(
            fill="x",
            pady=3,
        )

        ttk.Button(
            right,
            text="SAVE",
            style="Action.TButton",
            command=lambda: save(),
        ).pack(
            fill="x",
            pady=(10, 3),
        )

        ttk.Button(
            right,
            text="CLOSE",
            command=root.destroy,
        ).pack(
            fill="x",
            pady=3,
        )

        # =====================================================
        # FOOTER
        # =====================================================

        footer = ttk.Frame(
            root,
            padding=(20, 10),
        )

        footer.pack(fill="x")

        ttk.Separator(
            footer,
            orient="horizontal",
        ).pack(
            fill="x",
            pady=(0, 8),
        )

        ttk.Label(
            footer,
            textvariable=self.status_var,
        ).pack(side="left")

        # =====================================================
        # HELPERS
        # =====================================================

        def current_exchange() -> str:
            return (
                self.exchange_var.get()
                .strip()
                .upper()
            )

        def ensure_exchange() -> dict:
            exchange = current_exchange()

            if exchange not in self.selection:
                self.selection[exchange] = {
                    "symbols": set(),
                    "analysis": set(),
                }

            return self.selection[exchange]

        def refresh_count() -> None:
            total = sum(
                len(data["symbols"])
                for data in self.selection.values()
            )

            analysis_total = sum(
                len(data["analysis"] & data["symbols"])
                for data in self.selection.values()
            )

            self.count_var.set(
                f"{total} markets | {analysis_total} analysis"
            )

        def refresh_status_lists() -> None:

            db_list.delete(
                0,
                tk.END,
            )

            analysis_list.delete(
                0,
                tk.END,
            )

            database_count = 0
            analysis_count = 0

            for exchange, data in sorted(
                self.selection.items()
            ):

                symbols = sorted(
                    data["symbols"]
                )

                analysis = (
                    data["analysis"]
                    & data["symbols"]
                )

                for symbol in symbols:
                    db_list.insert(
                        tk.END,
                        f"{exchange:<10} | {symbol}",
                    )
                    database_count += 1

                for symbol in sorted(analysis):
                    analysis_list.insert(
                        tk.END,
                        f"{exchange:<10} | {symbol}",
                    )
                    analysis_count += 1

            if database_count == 0:
                db_list.insert(
                    tk.END,
                    "(none)",
                )

            if analysis_count == 0:
                analysis_list.insert(
                    tk.END,
                    "(none)",
                )

            refresh_count()

        def remove_database_item(event=None) -> None:
            selection = db_list.curselection()

            if not selection:
                return

            index = selection[0]
            text = db_list.get(index)

            if "|" not in text:
                return

            exchange, symbol = [
                x.strip()
                for x in text.split("|", 1)
            ]

            data = self.selection.get(exchange)

            if not data:
                return

            # Remove ONLY this market from DATABASE
            data["symbols"].discard(symbol)

            # It cannot remain in ANALYSIS if it is no longer in DATABASE
            data["analysis"].discard(symbol)

            refresh_status_lists()
            refresh_markets()

            self.status_var.set(
                f"Removed {exchange} | {symbol} from DATABASE."
            )


        def remove_analysis_item(event=None) -> None:
            selection = analysis_list.curselection()

            if not selection:
                return

            index = selection[0]
            text = analysis_list.get(index)

            if "|" not in text:
                return

            exchange, symbol = [
                x.strip()
                for x in text.split("|", 1)
            ]

            data = self.selection.get(exchange)

            if not data:
                return

            # Remove ONLY ANALYSIS status.
            # DATABASE remains untouched.
            data["analysis"].discard(symbol)

            refresh_status_lists()

            self.status_var.set(
                f"Removed {exchange} | {symbol} from ANALYSIS."
            )


        def refresh_markets() -> None:

            exchange = current_exchange()

            try:
                markets = self.load_markets(
                    exchange
                )

            except Exception as exc:
                messagebox.showerror(
                    "KIA BOT",
                    str(exc),
                )
                return

            query = (
                self.search_var.get()
                .strip()
                .upper()
            )

            market_list.delete(
                0,
                tk.END,
            )

            data = self.selection.get(
                exchange,
                {
                    "symbols": set(),
                    "analysis": set(),
                },
            )

            visible = []

            for market in markets:

                if query and query not in market:
                    continue

                visible.append(market)

                market_list.insert(
                    tk.END,
                    market,
                )

                index = market_list.size() - 1

                if market in data["symbols"]:
                    market_list.selection_set(
                        index
                    )

            self.status_var.set(
                f"{exchange}: "
                f"{len(markets)} markets | "
                f"{len(visible)} visible"
            )

            refresh_status_lists()

        def add_selected() -> None:

            data = ensure_exchange()

            selected = market_list.curselection()

            if not selected:
                messagebox.showinfo(
                    "KIA BOT",
                    "Select one or more markets first.",
                )
                return

            for index in selected:
                symbol = market_list.get(index)
                data["symbols"].add(symbol)

            refresh_status_lists()

            self.status_var.set(
                f"{current_exchange()}: "
                f"{len(data['symbols'])} database markets"
            )

        def mark_analysis() -> None:

            data = ensure_exchange()

            selected = market_list.curselection()

            if not selected:
                messagebox.showinfo(
                    "KIA BOT",
                    "Select markets to mark for analysis.",
                )
                return

            for index in selected:

                symbol = market_list.get(index)

                # ANALYSIS always requires DATABASE storage.
                data["symbols"].add(symbol)

                # Mark the same market for analysis.
                data["analysis"].add(symbol)

            # Refresh both DATABASE and ANALYSIS views.
            refresh_status_lists()

            self.status_var.set(
                "Selected markets marked for analysis."
            )

        def remove_selected() -> None:

            data = ensure_exchange()

            selected = market_list.curselection()

            if not selected:
                messagebox.showinfo(
                    "KIA BOT",
                    "Select markets to remove.",
                )
                return

            for index in reversed(selected):

                symbol = market_list.get(index)

                data["symbols"].discard(symbol)
                data["analysis"].discard(symbol)

            refresh_markets()

            self.status_var.set(
                "Selected markets removed."
            )

        def save() -> None:

            self.save_selection()

            refresh_status_lists()

            self.status_var.set(
                f"Saved to {STATE_FILE.name}"
            )

            messagebox.showinfo(
                "KIA BOT",
                "Market selection saved successfully.",
            )

        # =====================================================
        # EVENTS
        # =====================================================

        exchange_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: refresh_markets(),
        )

        search.bind(
            "<Return>",
            lambda event: refresh_markets(),
        )

        # =====================================================
        # SECTION-SPECIFIC REMOVE
        # =====================================================

        # Click a DATABASE item:
        # remove ONLY that database market.
        db_list.bind(
            "<ButtonRelease-1>",
            remove_database_item,
        )

        # Click an ANALYSIS item:
        # remove ONLY its analysis status.
        # The market remains in DATABASE.
        analysis_list.bind(
            "<ButtonRelease-1>",
            remove_analysis_item,
        )

        # =====================================================
        # INITIAL LOAD
        # =====================================================

        refresh_markets()

        root.mainloop()


if __name__ == "__main__":
    MarketSelector().show()
