from __future__ import annotations

import json
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATABASE_ROOT = ROOT / "database"
SELECTION_FILE = ROOT / "market_selection.json"


class DatabaseManagerWindow:

    DATA_TYPES = {
        "candles": ("CANDLES", "candles"),
        "trades": ("TRADES", "trades"),
        "orderbook": ("ORDERBOOK", "orderbook"),
        "market_stats": ("MARKET STATS", "market_stats"),
    }

    def __init__(self, parent=None):

        self.parent = parent
        self.root = tk.Toplevel(parent) if parent else tk.Tk()

        self.root.title("KIA BOT - DATABASE MANAGER")
        self.root.geometry("1050x650")
        self.root.minsize(950, 580)

        self.markets = []
        self.current_market = None

        self._build_ui()
        self.refresh()

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close,
        )

    # ========================================================
    # UI
    # ========================================================

    def _build_ui(self):

        main = ttk.Frame(
            self.root,
            padding=15,
        )
        main.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            main,
            text="DATABASE MANAGER",
            font=("Segoe UI", 18, "bold"),
        ).pack(
            pady=(0, 5)
        )

        ttk.Label(
            main,
            text="SOURCE: MARKET SELECTION",
            font=("Segoe UI", 9),
        ).pack(
            pady=(0, 12)
        )

        top = ttk.Frame(main)
        top.pack(
            fill="x",
            pady=(0, 10),
        )

        ttk.Label(
            top,
            text="SELECTED MARKETS:",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        self.market_var = tk.StringVar()

        self.market_combo = ttk.Combobox(
            top,
            textvariable=self.market_var,
            state="readonly",
            width=42,
        )
        self.market_combo.pack(
            side="left",
            padx=10,
        )

        self.market_combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self._market_changed(),
        )

        ttk.Button(
            top,
            text="REFRESH",
            command=self.refresh,
        ).pack(side="right")

        columns = (
            "exchange",
            "symbol",
            "analysis",
            "type",
            "records",
            "size",
            "maximum",
            "database",
            "delete",
        )

        self.tree = ttk.Treeview(
            main,
            columns=columns,
            show="headings",
            height=17,
        )

        headings = {
            "exchange": "EXCHANGE",
            "symbol": "SYMBOL",
            "analysis": "ANALYSIS",
            "type": "DATA TYPE",
            "records": "CURRENT",
            "size": "SIZE",
            "maximum": "MAX RECORDS",
            "database": "DATABASE FILE",
            "delete": "ACTION",
        }

        widths = {
            "exchange": 90,
            "symbol": 105,
            "analysis": 80,
            "type": 110,
            "records": 85,
            "size": 90,
            "maximum": 105,
            "database": 230,
            "delete": 80,
        }

        for column in columns:

            self.tree.heading(
                column,
                text=headings[column],
            )

            self.tree.column(
                column,
                width=widths[column],
                anchor="center",
            )

        self.tree.pack(
            fill="both",
            expand=True,
        )

        self.tree.bind(
            "<Double-1>",
            self._tree_action,
        )

        settings = ttk.Frame(main)
        settings.pack(
            fill="x",
            pady=(12, 5),
        )

        ttk.Label(
            settings,
            text="MAX RECORDS:",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        self.maximum_var = tk.StringVar()

        ttk.Entry(
            settings,
            textvariable=self.maximum_var,
            width=15,
        ).pack(
            side="left",
            padx=8,
        )

        ttk.Label(
            settings,
            text="0 = UNLIMITED",
        ).pack(side="left")

        ttk.Button(
            settings,
            text="APPLY LIMIT",
            command=self.apply_limit,
        ).pack(
            side="left",
            padx=12,
        )

        self.total_var = tk.StringVar(
            value="TOTAL DATABASE SIZE: 0 B"
        )

        ttk.Label(
            main,
            textvariable=self.total_var,
            font=("Segoe UI", 11, "bold"),
        ).pack(
            anchor="w",
            pady=(8, 0),
        )

        ttk.Label(
            main,
            text="Double-click DELETE to permanently remove the selected data type.",
            font=("Segoe UI", 9),
        ).pack(
            anchor="w",
            pady=(5, 0),
        )

    # ========================================================
    # SELECTION SOURCE
    # ========================================================

    def _load_selection(self):

        if not SELECTION_FILE.exists():
            return []

        try:
            data = json.loads(
                SELECTION_FILE.read_text(
                    encoding="utf-8-sig"
                )
            )
        except Exception:
            return []

        result = []

        for item in data.get("selections", []):

            exchange = str(
                item.get("exchange", "")
            ).strip().upper()

            if not exchange:
                continue

            symbols = {
                str(symbol).strip().upper()
                for symbol in item.get("symbols", [])
                if str(symbol).strip()
            }

            analysis = {
                str(symbol).strip().upper()
                for symbol in item.get("analysis", [])
                if str(symbol).strip()
            }

            for symbol in sorted(symbols):

                result.append({
                    "exchange": exchange,
                    "symbol": symbol,
                    "analysis": symbol in analysis,
                })

        return result

    def refresh(self):

        self.markets = self._load_selection()

        values = [
            f"{item['exchange']} / {item['symbol']}"
            for item in self.markets
        ]

        self.market_combo["values"] = values

        current = self.market_var.get()

        if current not in values:

            if values:
                self.market_var.set(values[0])
            else:
                self.market_var.set("")

        self._refresh_table()

    def _market_changed(self):

        self._refresh_table()

    def _current_market(self):

        selected = self.market_var.get().strip()

        if not selected:
            return None

        for item in self.markets:

            key = (
                f"{item['exchange']} / "
                f"{item['symbol']}"
            )

            if key == selected:
                return item

        return None

    # ========================================================
    # DATABASE
    # ========================================================

    @staticmethod
    def _size_text(size):

        units = (
            "B",
            "KB",
            "MB",
            "GB",
            "TB",
        )

        value = float(size)

        for unit in units:

            if value < 1024 or unit == units[-1]:
                return f"{value:.2f} {unit}"

            value /= 1024

    @staticmethod
    def _count(db_path, table):

        if not db_path.exists():
            return 0

        try:

            with sqlite3.connect(db_path) as db:

                row = db.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()

                return int(row[0])

        except Exception:
            return 0

    def _retention(self):

        path = DATABASE_ROOT / "retention.json"

        if not path.exists():
            return {}

        try:

            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            return data if isinstance(data, dict) else {}

        except Exception:
            return {}

    def _refresh_table(self):

        for item in self.tree.get_children():
            self.tree.delete(item)

        total_size = 0

        selected = self._current_market()

        if selected is None:

            self.total_var.set(
                "TOTAL DATABASE SIZE: 0 B"
            )
            return

        exchange = selected["exchange"].lower()
        symbol = selected["symbol"]
        is_analysis = selected["analysis"]

        market_dir = (
            DATABASE_ROOT
            / exchange
            / symbol
        )

        retention = self._retention()

        for key, (label, table) in self.DATA_TYPES.items():

            db_path = (
                market_dir
                / f"{symbol}_{key}.db"
            )

            count = self._count(
                db_path,
                table,
            )

            size = (
                db_path.stat().st_size
                if db_path.exists()
                else 0
            )

            total_size += size

            retention_key = (
                f"{exchange}/"
                f"{symbol}/"
                f"{key}"
            )

            maximum = int(
                retention.get(
                    retention_key,
                    0,
                )
            )

            self.tree.insert(
                "",
                "end",
                values=(
                    exchange.upper(),
                    symbol,
                    "YES" if is_analysis else "NO",
                    label,
                    f"{count:,}",
                    self._size_text(size),
                    (
                        f"{maximum:,}"
                        if maximum > 0
                        else "UNLIMITED"
                    ),
                    db_path.name,
                    "DELETE",
                ),
            )

        self.total_var.set(
            "TOTAL DATABASE SIZE: "
            + self._size_text(total_size)
        )

    # ========================================================
    # RETENTION
    # ========================================================

    def apply_limit(self):

        selected = self.tree.selection()

        if not selected:
            messagebox.showwarning(
                "KIA BOT",
                "Select a data type first.",
                parent=self.root,
            )
            return

        values = self.tree.item(
            selected[0],
            "values",
        )

        data_type = str(
            values[3]
        ).strip().lower().replace(
            " ",
            "_",
        )

        try:

            maximum = int(
                self.maximum_var.get().strip()
            )

            if maximum < 0:
                raise ValueError

        except ValueError:

            messagebox.showerror(
                "KIA BOT",
                "Enter a valid integer. Use 0 for unlimited.",
                parent=self.root,
            )
            return

        market = self._current_market()

        if market is None:
            return

        exchange = market["exchange"].lower()
        symbol = market["symbol"]

        retention_file = (
            DATABASE_ROOT / "retention.json"
        )

        data = self._retention()

        retention_key = (
            f"{exchange}/"
            f"{symbol}/"
            f"{data_type}"
        )

        if maximum == 0:

            data.pop(
                retention_key,
                None,
            )

        else:

            data[retention_key] = maximum

        retention_file.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        self._trim(
            exchange,
            symbol,
            data_type,
            maximum,
        )

        self.maximum_var.set("")

        self._refresh_table()

        messagebox.showinfo(
            "KIA BOT",
            "Retention limit applied.",
            parent=self.root,
        )

    def _trim(
        self,
        exchange,
        symbol,
        data_type,
        maximum,
    ):

        if maximum <= 0:
            return

        market_dir = (
            DATABASE_ROOT
            / exchange
            / symbol
        )

        db_path = (
            market_dir
            / f"{symbol}_{data_type}.db"
        )

        if not db_path.exists():
            return

        with sqlite3.connect(db_path) as db:

            row = db.execute(
                f"SELECT COUNT(*) FROM {data_type}"
            ).fetchone()

            count = int(row[0])

            excess = count - maximum

            if excess <= 0:
                return

            db.execute(
                f"""
                DELETE FROM {data_type}
                WHERE id IN (
                    SELECT id
                    FROM {data_type}
                    ORDER BY timestamp ASC, id ASC
                    LIMIT ?
                )
                """,
                (excess,),
            )

            db.commit()

    # ========================================================
    # DELETE
    # ========================================================

    def _tree_action(self, event):

        item = self.tree.identify_row(event.y)

        if not item:
            return

        column = self.tree.identify_column(event.x)

        if column != "#9":
            return

        values = self.tree.item(
            item,
            "values",
        )

        data_type = str(
            values[3]
        ).strip().lower().replace(
            " ",
            "_",
        )

        self.delete_data(data_type)

    def delete_data(self, data_type):

        market = self._current_market()

        if market is None:
            return

        exchange = market["exchange"].lower()
        symbol = market["symbol"]

        market_dir = (
            DATABASE_ROOT
            / exchange
            / symbol
        )

        db_path = (
            market_dir
            / f"{symbol}_{data_type}.db"
        )

        if not db_path.exists():
            return

        answer = messagebox.askyesno(
            "KIA BOT",
            (
                f"Delete {data_type.upper()} database?\n\n"
                f"{exchange.upper()} / {symbol}\n"
                f"{db_path.name}"
            ),
            parent=self.root,
        )

        if not answer:
            return

        try:

            db_path.unlink()

            messagebox.showinfo(
                "KIA BOT",
                f"{data_type.upper()} database deleted.",
                parent=self.root,
            )

        except Exception as exc:

            messagebox.showerror(
                "KIA BOT",
                f"Delete failed:\n{exc}",
                parent=self.root,
            )

        self._refresh_table()

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        try:
            self.root.destroy()
        except Exception:
            pass


if __name__ == "__main__":

    app = DatabaseManagerWindow()
    app.root.mainloop()
