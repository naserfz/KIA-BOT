from __future__ import annotations

import asyncio
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from core import KIACore


class KIAControlWindow:

    def __init__(self) -> None:

        self.root = tk.Tk()

        self.root.title("KIA BOT")
        self.root.geometry("470x380")
        self.root.resizable(False, False)

        self.core: KIACore | None = None

        self.loop: asyncio.AbstractEventLoop | None = None
        self.loop_thread: threading.Thread | None = None
        self.core_task = None

        self.running = False
        self.stopping = False

        self.exchange_var = tk.StringVar(
            value="NOBITEX"
        )

        self.market_var = tk.StringVar(
            value="MARKET: ---"
        )

        self.status_var = tk.StringVar(
            value="STATUS: STOPPED"
        )

        self._build_ui()

        try:

            self.core = KIACore()

            self.exchange_var.set(
                self.core.exchange_name
            )

            self.market_var.set(
                f"MARKET: {self.core.symbol}"
            )

        except Exception as exc:

            self.status_var.set(
                "STATUS: ERROR"
            )

            print(
                f"[GUI ERROR] {exc}"
            )

        self._start_event_loop()

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close,
        )

    # ========================================================
    # UI
    # ========================================================

    def _build_ui(self) -> None:

        frame = ttk.Frame(
            self.root,
            padding=25,
        )

        frame.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            frame,
            text="KIA BOT",
            font=("Segoe UI", 20, "bold"),
        ).pack(
            pady=(0, 18)
        )

        ttk.Label(
            frame,
            text="EXCHANGE",
            font=("Segoe UI", 10, "bold"),
        ).pack(
            pady=(0, 4)
        )

        exchange_frame = ttk.Frame(frame)

        exchange_frame.pack(
            fill="x",
            pady=(0, 12),
        )

        self.exchange_combo = ttk.Combobox(
            exchange_frame,
            textvariable=self.exchange_var,
            values=(
                "NOBITEX",
            ),
            state="readonly",
            width=20,
        )

        self.exchange_combo.pack(
            side="left",
            expand=True,
            fill="x",
        )

        self.exchange_button = ttk.Button(
            exchange_frame,
            text="SELECT",
            command=self.select_exchange,
            width=12,
        )

        self.exchange_button.pack(
            side="left",
            padx=(8, 0),
        )

        ttk.Label(
            frame,
            textvariable=self.market_var,
            font=("Segoe UI", 11),
        ).pack(
            pady=5
        )

        ttk.Label(
            frame,
            textvariable=self.status_var,
            font=("Segoe UI", 11),
        ).pack(
            pady=5
        )

        buttons = ttk.Frame(frame)

        buttons.pack(
            pady=25
        )

        self.start_button = ttk.Button(
            buttons,
            text="START",
            command=self.start,
            width=12,
        )

        self.start_button.grid(
            row=0,
            column=0,
            padx=5,
        )

        self.stop_button = ttk.Button(
            buttons,
            text="STOP",
            command=self.stop,
            width=12,
        )

        self.stop_button.grid(
            row=0,
            column=1,
            padx=5,
        )

        self.restart_button = ttk.Button(
            buttons,
            text="RESTART",
            command=self.restart,
            width=12,
        )

        self.restart_button.grid(
            row=0,
            column=2,
            padx=5,
        )

        self.exit_button = ttk.Button(
            buttons,
            text="EXIT",
            command=self.close,
            width=12,
        )

        self.exit_button.grid(
            row=1,
            column=0,
            columnspan=3,
            pady=(15, 0),
        )

    # ========================================================
    # EVENT LOOP
    # ========================================================

    def _start_event_loop(self) -> None:

        self.loop = asyncio.new_event_loop()

        self.loop_thread = threading.Thread(
            target=self._event_loop_worker,
            daemon=True,
        )

        self.loop_thread.start()

    def _event_loop_worker(self) -> None:

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
    # CORE START
    # ========================================================

    async def _start_core(self) -> None:

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
                lambda: self._set_stopped(
                    "STATUS: ERROR"
                ),
            )

        finally:

            self.running = False

    def start(self) -> None:

        if self.running or self.stopping:
            return

        if self.loop is None:
            return

        if self.core is None:
            return

        self.running = True

        self.status_var.set(
            "STATUS: RUNNING"
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

    async def _stop_core(self) -> None:

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
                    "STATUS: STOPPED"
                ),
            )

    def stop(self) -> None:

        if not self.running:
            self.status_var.set(
                "STATUS: STOPPED"
            )
            return

        if self.stopping:
            return

        if self.loop is None:
            return

        self.stopping = True

        self.status_var.set(
            "STATUS: STOPPING"
        )

        asyncio.run_coroutine_threadsafe(
            self._stop_core(),
            self.loop,
        )

    # ========================================================
    # RESTART
    # ========================================================

    async def _restart_core(self) -> None:

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

            self.root.after(
                0,
                lambda: self._set_stopped(
                    "STATUS: ERROR"
                ),
            )

        finally:

            self.running = False
            self.stopping = False

            self.root.after(
                0,
                lambda: self.status_var.set(
                    "STATUS: STOPPED"
                ),
            )

    def restart(self) -> None:

        if self.stopping:
            return

        if self.core is None:
            return

        if self.loop is None:
            return

        if not self.running:
            self.start()
            return

        self.stopping = True

        self.status_var.set(
            "STATUS: RESTARTING"
        )

        asyncio.run_coroutine_threadsafe(
            self._restart_core(),
            self.loop,
        )

    # ========================================================
    # EXCHANGE SELECT
    # ========================================================

    def select_exchange(self) -> None:

        selected = (
            self.exchange_var.get()
            .strip()
            .upper()
        )

        if not selected:
            return

        if self.core is None:
            return

        if selected == self.core.exchange_name:

            self.status_var.set(
                f"STATUS: "
                f"{selected} ACTIVE"
            )

            return

        if self.stopping:
            return

        if self.running:

            self.stopping = True

            self.status_var.set(
                "STATUS: SWITCHING EXCHANGE"
            )

            asyncio.run_coroutine_threadsafe(
                self._switch_exchange(
                    selected
                ),
                self.loop,
            )

        else:

            self._apply_exchange(
                selected
            )

    async def _switch_exchange(
        self,
        exchange: str,
    ) -> None:

        try:

            if self.core is not None:

                await self.core.switch_exchange(
                    exchange
                )

            self.root.after(
                0,
                lambda: self._exchange_changed(
                    exchange
                ),
            )

        except asyncio.CancelledError:
            raise

        except Exception as exc:

            print(
                f"[EXCHANGE SWITCH ERROR] "
                f"{exc}"
            )

            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "KIA BOT",
                    str(exc),
                ),
            )

            self.root.after(
                0,
                lambda: self._exchange_changed(
                    self.core.exchange_name
                    if self.core
                    else "NOBITEX"
                ),
            )

    def _exchange_changed(
        self,
        exchange: str,
    ) -> None:

        self.exchange_var.set(
            exchange
        )

        if self.core is not None:

            self.market_var.set(
                f"MARKET: "
                f"{self.core.symbol}"
            )

        self.stopping = False
        self.running = True

        self.status_var.set(
            f"STATUS: "
            f"RUNNING - {exchange}"
        )

    def _apply_exchange(
        self,
        exchange: str,
    ) -> None:

        try:

            if self.core is not None:

                self.core.exchange_name = (
                    exchange
                )

                self.core.bot = (
                    self.core._create_exchange(
                        exchange
                    )
                )

                self.core.database = (
                    self.core._create_database()
                )

                self.core.exchange_service.bot = (
                    self.core.bot
                )

                self.core.database_service.database = (
                    self.core.database
                )

            self.exchange_var.set(
                exchange
            )

            self.status_var.set(
                f"STATUS: "
                f"{exchange} SELECTED"
            )

        except Exception as exc:

            print(
                f"[EXCHANGE ERROR] {exc}"
            )

            messagebox.showerror(
                "KIA BOT",
                str(exc),
            )


    # ========================================================
    # DATABASE MANAGER
    # ========================================================

    def open_database(self) -> None:

        try:
            from database.manager import (
                open_database_manager
            )

            open_database_manager(
                self.root
            )

        except Exception as exc:

            print(
                f"[DATABASE GUI ERROR] {exc}"
            )

            messagebox.showerror(
                "KIA BOT",
                str(exc),
            )

    # ========================================================
    # STATUS
    # ========================================================

    def _set_stopped(
        self,
        status: str,
    ) -> None:

        self.running = False
        self.stopping = False

        self.status_var.set(
            status
        )

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self) -> None:

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
                    f"[CLOSE ERROR] "
                    f"{exc}"
                )

            try:

                self.loop.call_soon_threadsafe(
                    self.loop.stop
                )

            except Exception:
                pass

        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    KIAControlWindow().run()
