
from __future__ import annotations

import json
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path


ROOT = Path(__file__).parent
DATABASE_ROOT = ROOT


class DatabaseManagerWindow:

    DATA_TYPES = {
        "candles": "CANDLES",
        "trades": "TRADES",
        "orderbook": "ORDERBOOK",
        "market_stats": "MARKET STATS",
    }

    def __init__(self, parent=None):

        self.parent = parent

        self.root = tk.Toplevel(parent) if parent else tk.Tk()

        self.root.title("KIA BOT - DATABASE MANAGER")
        self.root.geometry("900x560")
        self.root.minsize(850, 500)

        self.rows = []

        self.exchange_var = tk.StringVar()
        self.symbol_var = tk.StringVar()

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
            pady=(0, 12)
        )

        top = ttk.Frame(main)
        top.pack(fill="x", pady=(0, 10))

        ttk.Label(
            top,
            text="EXCHANGE",
        ).pack(side="left")

        self.exchange_combo = ttk.Combobox(
            top,
            textvariable=self.exchange_var,
            state="readonly",
            width=18,
        )

        self.exchange_combo.pack(
            side="left",
            padx=(6, 20),
        )

        ttk.Label(
            top,
            text="SYMBOL",
        ).pack(side="left")

        self.symbol_combo = ttk.Combobox(
            top,
            textvariable=self.symbol_var,
            state="readonly",
            width=18,
        )

        self.symbol_combo.pack(
            side="left",
            padx=6,
        )

        self.exchange_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: self._exchange_changed(),
        )

        self.symbol_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: self.refresh(),
        )

        ttk.Button(
            top,
            text="REFRESH",
            command=self.refresh,
        ).pack(
            side="right"
        )

        columns = (
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
            height=13,
        )

        headings = {
            "type": "DATA TYPE",
            "records": "CURRENT",
            "size": "SIZE",
            "maximum": "MAX RECORDS",
            "database": "DATABASE FILE",
            "delete": "ACTION",
        }

        widths = {
            "type": 130,
            "records": 90,
            "size": 100,
            "maximum": 110,
            "database": 250,
            "delete": 100,
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
        ).pack(
            side="left"
        )

        self.maximum_var = tk.StringVar()

        self.maximum_entry = ttk.Entry(
            settings,
            textvariable=self.maximum_var,
            width=15,
        )

        self.maximum_entry.pack(
            side="left",
            padx=8,
        )

        ttk.Label(
            settings,
            text="0 = UNLIMITED",
        ).pack(
            side="left"
        )

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
    # DISCOVERY
    # ========================================================

    def _discover(self):

        exchanges = []

        if not DATABASE_ROOT.exists():
            return exchanges

        for exchange_dir in DATABASE_ROOT.iterdir():

            if not exchange_dir.is_dir():
                continue

            if exchange_dir.name.startswith("_"):
                continue

            symbols = []

            for symbol_dir in exchange_dir.iterdir():

                if symbol_dir.is_dir():
                    symbols.append(
                        symbol_dir.name.upper()
                    )

            if symbols:
                exchanges.append(
                    (
                        exchange_dir.name.upper(),
                        sorted(symbols),
                    )
                )

        return sorted(exchanges)

    def _exchange_changed(self):

        selected = (
            self.exchange_var.get()
            .strip()
            .lower()
        )

        data = self._discover()

        for exchange, symbols in data:

            if exchange.lower() == selected:

                self.symbol_combo["values"] = symbols

                if symbols:
                    self.symbol_var.set(
                        symbols[0]
                    )

                break

        self.refresh()

    def _market_dir(self):

        exchange = (
            self.exchange_var.get()
            .strip()
            .lower()
        )

        symbol = (
            self.symbol_var.get()
            .strip()
            .upper()
        )

        if not exchange or not symbol:
            return None

        return (
            DATABASE_ROOT
            / exchange
            / symbol
        )

    # ========================================================
    # DATABASE INFO
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

    def _count(self, db_path, table):

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

    def refresh(self):

        data = self._discover()

        exchanges = [
            item[0]
            for item in data
        ]

        self.exchange_combo["values"] = exchanges

        current_exchange = (
            self.exchange_var.get()
            .strip()
            .upper()
        )

        if current_exchange not in exchanges:

            if exchanges:
                self.exchange_var.set(
                    exchanges[0]
                )

            current_exchange = (
                self.exchange_var.get()
            )

        self._exchange_changed_without_loop(data)

        self._refresh_table()

    def _exchange_changed_without_loop(self, data):

        selected = (
            self.exchange_var.get()
            .strip()
            .upper()
        )

        for exchange, symbols in data:

            if exchange == selected:

                self.symbol_combo["values"] = symbols

                current = (
                    self.symbol_var.get()
                    .strip()
                    .upper()
                )

                if current not in symbols:

                    if symbols:
                        self.symbol_var.set(
                            symbols[0]
                        )
                    else:
                        self.symbol_var.set("")

                return

    def _refresh_table(self):

        for item in self.tree.get_children():
            self.tree.delete(item)

        market_dir = self._market_dir()

        total_size = 0

        if market_dir is None:
            self.total_var.set(
                "TOTAL DATABASE SIZE: 0 B"
            )
            return

        retention = self._retention()

        exchange = (
            self.exchange_var.get()
            .strip()
            .lower()
        )

        symbol = (
            self.symbol_var.get()
            .strip()
            .upper()
        )

        table_map = {
            "candles": "candles",
            "trades": "trades",
            "orderbook": "orderbook",
            "market_stats": "market_stats",
        }

        for key, label in self.DATA_TYPES.items():

            db_path = (
                market_dir
                / f"{symbol}_{key}.db"
            )

            table = table_map[key]

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
    # LIMIT
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
            values[0]
        ).strip().lower().replace(
            " ",
            "_",
        )

        if data_type == "market_stats":
            key = "market_stats"
        else:
            key = data_type

        try:
            maximum = int(
                self.maximum_var.get()
                .strip()
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

        market_dir = self._market_dir()

        if market_dir is None:
            return

        exchange = (
            self.exchange_var.get()
            .strip()
            .lower()
        )

        symbol = (
            self.symbol_var.get()
            .strip()
            .upper()
        )

        retention_file = (
            DATABASE_ROOT / "retention.json"
        )

        data = self._retention()

        retention_key = (
            f"{exchange}/"
            f"{symbol}/"
            f"{key}"
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

        self._trim_selected(
            key,
            maximum,
        )

        self.maximum_var.set("")

        self._refresh_table()

        messagebox.showinfo(
            "KIA BOT",
            "Retention limit applied.",
            parent=self.root,
        )

    def _trim_selected(
        self,
        data_type,
        maximum,
    ):

        if maximum <= 0:
            return

        market_dir = self._market_dir()

        if market_dir is None:
            return

        symbol = (
            self.symbol_var.get()
            .strip()
            .upper()
        )

        db_path = (
            market_dir
            / f"{symbol}_{data_type}.db"
        )

        table = data_type

        if not db_path.exists():
            return

        with sqlite3.connect(db_path) as db:

            db.execute(
                f"""
                DELETE FROM {table}
                WHERE id IN (
                    SELECT id
                    FROM {table}
                    ORDER BY timestamp ASC, id ASC
                    LIMIT (
                        SELECT MAX(COUNT(*) - ?, 0)
                        FROM {table}
                    )
                )
                """,
                (maximum,),
            )

            db.commit()

    # ========================================================
    # DELETE
    # ========================================================

    def _tree_action(self, event):

        item = self.tree.identify_row(
            event.y
        )

        if not item:
            return

        column = self.tree.identify_column(
            event.x
        )

        if column != "#6":
            return

        values = self.tree.item(
            item,
            "values",
        )

        label = values[0]

        data_type = (
            str(label)
            .strip()
            .lower()
            .replace(" ", "_")
        )

        if data_type == "market_stats":
            data_type = "market_stats"

        self.delete_data(data_type)

    def delete_data(self, data_type):

        market_dir = self._market_dir()

        if market_dir is None:
            return

        symbol = (
            self.symbol_var.get()
            .strip()
            .upper()
        )

        db_path = (
            market_dir
            / f"{symbol}_{data_type}.db"
        )

        table_map = {
            "candles": "candles",
            "trades": "trades",
            "orderbook": "orderbook",
            "market_stats": "market_stats",
        }

        table = table_map.get(data_type)

        if table is None:
            return

        if not db_path.exists():
            messagebox.showinfo(
                "KIA BOT",
                "No database file exists.",
                parent=self.root,
            )
            return

        answer = messagebox.askyesno(
            "CONFIRM DELETE",
            (
                f"Are you sure you want to permanently delete "
                f"ALL {data_type.upper()} data for {symbol}?\n\n"
                f"This action cannot be undone."
            ),
            parent=self.root,
            icon="warning",
        )

        if not answer:
            return

        try:

            with sqlite3.connect(db_path) as db:

                db.execute(
                    f"DELETE FROM {table}"
                )

                db.commit()

                db.execute(
                    "VACUUM"
                )

            messagebox.showinfo(
                "KIA BOT",
                f"ALL {data_type.upper()} DATA DELETED.",
                parent=self.root,
            )

            self._refresh_table()

        except Exception as exc:

            messagebox.showerror(
                "KIA BOT",
                f"DELETE ERROR:\n\n{exc}",
                parent=self.root,
            )

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        self.root.destroy()


def open_database_manager(parent=None):

    return DatabaseManagerWindow(parent)


if __name__ == "__main__":
    DatabaseManagerWindow().root.mainloop()
