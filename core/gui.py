from __future__ import annotations

import asyncio
import json
import threading
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

from core import KIACore


ROOT = Path(__file__).resolve().parent.parent
SELECTION_FILE = ROOT / "market_selection.json"


class KIAControlWindow:

    def __init__(self) -> None:

        self.root = tk.Tk()

        self.root.title("KIA BOT")
        self.root.geometry("900x620")
        self.root.minsize(820, 560)

        self.core: KIACore | None = None

        self.loop: asyncio.AbstractEventLoop | None = None
        self.loop_thread: threading.Thread | None = None
        self.core_task = None

        self.running = False
        self.stopping = False

        self.selection_data = []

        self.exchange_var = tk.StringVar(
            value="NOBITEX"
        )

        self.status_var = tk.StringVar(
            value="STOPPED"
        )

        self.mode_var = tk.StringVar(
            value="PAPER"
        )

        self.database_var = tk.StringVar(
            value="0"
        )

        self.analysis_var = tk.StringVar(
            value="0"
        )

        self._load_selection()
        self._build_ui()
        self._start_event_loop()

        try:
            self.core = KIACore()
        except Exception as exc:
            print(f"[GUI CORE ERROR] {exc}")

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close,
        )

    # ========================================================
    # SELECTION
    # ========================================================

    def _load_selection(self) -> None:

        self.selection_data = []

        if not SELECTION_FILE.exists():
            return

        try:
            data = json.loads(
                SELECTION_FILE.read_text(
                    encoding="utf-8-sig"
                )
            )

            selections = data.get(
                "selections",
                [],
            )

            if isinstance(selections, list):
                for item in selections:

                    if not isinstance(item, dict):
                        continue

                    exchange = str(
                        item.get(
                            "exchange",
                            "",
                        )
                    ).strip().upper()

                    symbols = sorted(
                        {
                            str(x).strip().upper()
                            for x in item.get(
                                "symbols",
                                [],
                            )
                            if str(x).strip()
                        }
                    )

                    analysis = sorted(
                        {
                            str(x).strip().upper()
                            for x in item.get(
                                "analysis",
                                [],
                            )
                            if str(x).strip()
                        }
                        & set(symbols)
                    )

                    if exchange and symbols:
                        self.selection_data.append(
                            {
                                "exchange": exchange,
                                "symbols": symbols,
                                "analysis": analysis,
                            }
                        )

        except Exception as exc:
            print(
                f"[SELECTION ERROR] {exc}"
            )

    def _selection_summary(self):

        database_total = 0
        analysis_total = 0

        for item in self.selection_data:
            database_total += len(
                item["symbols"]
            )
            analysis_total += len(
                item["analysis"]
            )

        return database_total, analysis_total

    # ========================================================
    # UI
    # ========================================================

    def _build_ui(self) -> None:

        style = ttk.Style(self.root)

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 25, "bold"),
        )

        style.configure(
            "Subtitle.TLabel",
            font=("Segoe UI", 10),
        )

        style.configure(
            "CardTitle.TLabel",
            font=("Segoe UI", 10, "bold"),
        )

        style.configure(
            "Value.TLabel",
            font=("Segoe UI", 17, "bold"),
        )

        style.configure(
            "Action.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=9,
        )

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        header = ttk.Frame(
            self.root,
            padding=(25, 20, 25, 12),
        )

        header.pack(
            fill="x"
        )

        ttk.Label(
            header,
            text="KIA BOT",
            style="Title.TLabel",
        ).pack(
            side="left"
        )

        ttk.Label(
            header,
            text="  CONTROL CENTER",
            style="Subtitle.TLabel",
        ).pack(
            side="left",
            pady=(11, 0),
        )

        # ----------------------------------------------------
        # STATUS BAR
        # ----------------------------------------------------

        status_frame = ttk.LabelFrame(
            self.root,
            text=" SYSTEM STATUS ",
            padding=12,
        )

        status_frame.pack(
            fill="x",
            padx=25,
            pady=8,
        )

        status_grid = ttk.Frame(
            status_frame
        )

        status_grid.pack(
            fill="x"
        )

        self._status_card(
            status_grid,
            "BOT STATUS",
            self.status_var,
            0,
        )

        self._status_card(
            status_grid,
            "MODE",
            self.mode_var,
            1,
        )

        exchange_value = (
            self.selection_data[0]["exchange"]
            if self.selection_data
            else "---"
        )

        self.exchange_display = tk.StringVar(
            value=exchange_value
        )

        self._status_card(
            status_grid,
            "EXCHANGE",
            self.exchange_display,
            2,
        )

        self._status_card(
            status_grid,
            "DATABASE",
            self.database_var,
            3,
        )

        self._status_card(
            status_grid,
            "ANALYSIS",
            self.analysis_var,
            4,
        )

        # ----------------------------------------------------
        # SELECTION
        # ----------------------------------------------------

        selection_frame = ttk.LabelFrame(
            self.root,
            text=" MARKET SELECTION ",
            padding=12,
        )

        selection_frame.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=8,
        )

        body = ttk.Frame(
            selection_frame
        )

        body.pack(
            fill="both",
            expand=True,
        )

        # DATABASE

        db_frame = ttk.LabelFrame(
            body,
            text=" DATABASE MARKETS ",
            padding=8,
        )

        db_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 6),
        )

        self.database_list = tk.Listbox(
            db_frame,
            font=("Consolas", 11),
            activestyle="none",
        )

        self.database_list.pack(
            fill="both",
            expand=True,
        )

        # ANALYSIS

        analysis_frame = ttk.LabelFrame(
            body,
            text=" ANALYSIS MARKETS ",
            padding=8,
        )

        analysis_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=6,
        )

        self.analysis_list = tk.Listbox(
            analysis_frame,
            font=("Consolas", 11),
            activestyle="none",
        )

        self.analysis_list.pack(
            fill="both",
            expand=True,
        )

        # INFO

        info_frame = ttk.LabelFrame(
            body,
            text=" ACTIVE SELECTION ",
            padding=8,
        )

        info_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(6, 0),
        )

        self.info_text = tk.Text(
            info_frame,
            font=("Consolas", 10),
            height=10,
            width=28,
            state="disabled",
            wrap="none",
        )

        self.info_text.pack(
            fill="both",
            expand=True,
        )

        # ----------------------------------------------------
        # BUTTONS
        # ----------------------------------------------------

        buttons = ttk.Frame(
            self.root,
            padding=(25, 10, 25, 15),
        )

        buttons.pack(
            fill="x"
        )

        ttk.Button(
            buttons,
            text="MARKET SELECTOR",
            style="Action.TButton",
            command=self.open_market_selector,
        ).pack(
            side="left",
            padx=4,
        )

        ttk.Button(
            buttons,
            text="DATABASE MANAGER",
            style="Action.TButton",
            command=self.open_database_manager,
        ).pack(
            side="left",
            padx=4,
        )

        ttk.Button(
            buttons,
            text="REFRESH SELECTION",
            style="Action.TButton",
            command=self.refresh_selection,
        ).pack(
            side="left",
            padx=4,
        )

        ttk.Button(
            buttons,
            text="START",
            style="Action.TButton",
            command=self.start,
        ).pack(
            side="left",
            padx=4,
        )

        ttk.Button(
            buttons,
            text="STOP",
            style="Action.TButton",
            command=self.stop,
        ).pack(
            side="left",
            padx=4,
        )

        ttk.Button(
            buttons,
            text="RESTART",
            style="Action.TButton",
            command=self.restart,
        ).pack(
            side="left",
            padx=4,
        )

        ttk.Button(
            buttons,
            text="EXIT",
            command=self.close,
        ).pack(
            side="right",
            padx=4,
        )

        self._refresh_selection_view()

    def _status_card(
        self,
        parent,
        title,
        variable,
        column,
    ):

        card = ttk.Frame(
            parent,
            padding=(10, 3),
        )

        card.grid(
            row=0,
            column=column,
            sticky="ew",
        )

        parent.columnconfigure(
            column,
            weight=1,
        )

        ttk.Label(
            card,
            text=title,
            style="CardTitle.TLabel",
        ).pack()

        ttk.Label(
            card,
            textvariable=variable,
            style="Value.TLabel",
        ).pack(
            pady=(2, 0)
        )

    # ========================================================
    # SELECTION VIEW
    # ========================================================

    def _refresh_selection_view(self):

        self.database_list.delete(
            0,
            tk.END,
        )

        self.analysis_list.delete(
            0,
            tk.END,
        )

        self.info_text.config(
            state="normal"
        )

        self.info_text.delete(
            "1.0",
            tk.END,
        )

        database_total, analysis_total = (
            self._selection_summary()
        )

        self.database_var.set(
            str(database_total)
        )

        self.analysis_var.set(
            str(analysis_total)
        )

        for item in self.selection_data:

            exchange = item["exchange"]

            for symbol in item["symbols"]:
                self.database_list.insert(
                    tk.END,
                    f"{exchange:<10} | {symbol}",
                )

            for symbol in item["analysis"]:
                self.analysis_list.insert(
                    tk.END,
                    f"{exchange:<10} | {symbol}",
                )

            self.info_text.insert(
                tk.END,
                f"[{exchange}]\n"
            )

            self.info_text.insert(
                tk.END,
                f"Database : "
                f"{len(item['symbols'])}\n"
            )

            self.info_text.insert(
                tk.END,
                f"Analysis : "
                f"{len(item['analysis'])}\n\n"
            )

        if not self.selection_data:

            self.database_list.insert(
                tk.END,
                "(NO DATABASE MARKETS)",
            )

            self.analysis_list.insert(
                tk.END,
                "(NO ANALYSIS MARKETS)",
            )

            self.info_text.insert(
                tk.END,
                "No market selection found.\n\n"
                "Open Market Selector and\n"
                "configure the selection."
            )

        self.info_text.config(
            state="disabled"
        )

    def refresh_selection(self):

        self._load_selection()

        if self.selection_data:
            self.exchange_display.set(
                self.selection_data[0]["exchange"]
            )
        else:
            self.exchange_display.set(
                "---"
            )

        self._refresh_selection_view()

        self.status_var.set(
            "STOPPED"
            if not self.running
            else "RUNNING"
        )

    # ========================================================
    # EVENT LOOP
    # ========================================================

    def _start_event_loop(self):

        self.loop = (
            asyncio.new_event_loop()
        )

        self.loop_thread = threading.Thread(
            target=self._event_loop_worker,
            daemon=True,
        )

        self.loop_thread.start()

    def _event_loop_worker(self):

        if self.loop is None:
            return

        asyncio.set_event_loop(
            self.loop
        )

        self.loop.run_forever()

        pending = asyncio.all_tasks(
            self.loop
        )

        for task in pending:
            task.cancel()

        if pending:
            self.loop.run_until_complete(
                asyncio.gather(
                    *pending,
                    return_exceptions=True,
                )
            )

        self.loop.close()

    # ========================================================
    # EXTERNAL WINDOWS
    # ========================================================

    def open_market_selector(self):
        try:
            subprocess.Popen(
                [sys.executable, "-m", "market_selector"],
                cwd=str(ROOT),
            )
        except Exception as exc:
            messagebox.showerror(
                "KIA BOT",
                f"Could not open Market Selector.\n\n{exc}",
            )

    def open_database_manager(self):
        try:
            subprocess.Popen(
                [
                    sys.executable,
                    str(ROOT / "database" / "manager.py"),
                ],
                cwd=str(ROOT),
            )
        except Exception as exc:
            messagebox.showerror(
                "KIA BOT",
                f"Could not open Database Manager.\n\n{exc}",
            )

    # ========================================================
    # START
    # ========================================================

    async def _start_core(self):

        if self.core is None:
            return

        try:

            await self.core.start()

        except asyncio.CancelledError:
            raise

        except Exception as exc:

            print(
                f"[CORE ERROR] {exc}"
            )

            self.root.after(
                0,
                lambda: self._set_status(
                    "ERROR"
                ),
            )

        finally:

            self.running = False

            self.root.after(
                0,
                lambda: self.status_var.set(
                    "STOPPED"
                ),
            )

    def start(self):

        if self.running or self.stopping:
            return

        if self.loop is None:
            return

        if self.core is None:
            messagebox.showerror(
                "KIA BOT",
                "Core is not available.",
            )
            return

        if not self.selection_data:
            messagebox.showwarning(
                "KIA BOT",
                "No market selection found.",
            )
            return

        self.running = True

        self.status_var.set(
            "RUNNING"
        )

        self.core_task = (
            asyncio.run_coroutine_threadsafe(
                self._start_core(),
                self.loop,
            )
        )

    # ========================================================
    # STOP
    # ========================================================

    async def _stop_core(self):

        try:

            if self.core is not None:
                await self.core.stop()

        except Exception as exc:

            print(
                f"[STOP ERROR] {exc}"
            )

        finally:

            self.running = False
            self.stopping = False
            self.core_task = None

            self.root.after(
                0,
                lambda: self.status_var.set(
                    "STOPPED"
                ),
            )

    def stop(self):

        if not self.running:
            self.status_var.set(
                "STOPPED"
            )
            return

        if self.stopping:
            return

        if self.loop is None:
            return

        self.stopping = True

        self.status_var.set(
            "STOPPING"
        )

        asyncio.run_coroutine_threadsafe(
            self._stop_core(),
            self.loop,
        )

    # ========================================================
    # RESTART
    # ========================================================

    async def _restart_core(self):

        try:

            if self.core is not None:
                await self.core.stop()

            await asyncio.sleep(0.5)

            if self.core is not None:
                await self.core.start()

        except asyncio.CancelledError:
            raise

        except Exception as exc:

            print(
                f"[RESTART ERROR] {exc}"
            )

        finally:

            self.running = False
            self.stopping = False

            self.root.after(
                0,
                lambda: self.status_var.set(
                    "STOPPED"
                ),
            )

    def restart(self):

        if self.core is None:
            return

        if self.loop is None:
            return

        if self.stopping:
            return

        if not self.running:
            self.start()
            return

        self.stopping = True

        self.status_var.set(
            "RESTARTING"
        )

        asyncio.run_coroutine_threadsafe(
            self._restart_core(),
            self.loop,
        )

    # ========================================================
    # STATUS
    # ========================================================

    def _set_status(
        self,
        status: str,
    ):

        self.running = (
            status == "RUNNING"
        )

        self.status_var.set(
            status
        )

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        if self.loop is not None:

            try:

                future = (
                    asyncio.run_coroutine_threadsafe(
                        self._stop_core(),
                        self.loop,
                    )
                )

                future.result(
                    timeout=5
                )

            except Exception as exc:

                print(
                    f"[CLOSE ERROR] {exc}"
                )

            try:

                self.loop.call_soon_threadsafe(
                    self.loop.stop
                )

            except Exception:
                pass

        self.root.destroy()

    def run(self):

        self.root.mainloop()


if __name__ == "__main__":
    KIAControlWindow().run()
