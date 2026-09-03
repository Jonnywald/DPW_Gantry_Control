"""Non-blocking PySide6 QThread Serial Communication Engine for Marlin/BTT SKR Mini E3."""

from __future__ import annotations
import time
import queue
import re
from typing import List, Optional, Tuple, Dict
import serial
import serial.tools.list_ports
from PySide6.QtCore import QObject, Signal, Slot, QMutex, QMutexLocker, QCoreApplication


class SerialState:
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting"
    CONNECTED_IDLE = "Connected (Idle)"
    STREAMING = "Streaming Job"
    PAUSED = "Job Paused"
    ESTOP = "Emergency Stop Triggered"


class SerialWorker(QObject):
    """
    Worker running in dedicated QThread to manage serial communication,
    job streaming with 'ok' handshake, MDI queue, and virtual simulation.
    """

    # Connection signals
    connected = Signal(str, int)            # port, baud
    disconnected = Signal()
    connection_error = Signal(str)

    # I/O logging signals
    tx_line = Signal(str)                   # Sent command
    rx_line = Signal(str)                   # Received response

    # Job streaming signals
    job_started = Signal(int)               # total_lines
    job_progress = Signal(int, int, float, float, float)  # cur_line, total_lines, pct, x, y
    job_paused = Signal(bool)               # is_paused
    job_finished = Signal(bool)             # success

    # Coordinate & state signals
    position_updated = Signal(float, float) # x, y
    state_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self._serial: Optional[serial.Serial] = None
        self._port: str = ""
        self._baud: int = 250000
        self._is_virtual: bool = False
        
        self._running: bool = False
        self._is_streaming: bool = False
        self._is_paused: bool = False
        self._abort_requested: bool = False

        self._mdi_queue: queue.Queue = queue.Queue()
        self._job_lines: List[str] = []
        self._job_index: int = 0
        self._job_total: int = 0

        self._current_x: float = 0.0
        self._current_y: float = 0.0
        self._state: str = SerialState.DISCONNECTED

        self._mutex = QMutex()

    @staticmethod
    def get_available_ports() -> List[Tuple[str, str]]:
        """Returns list of (port_name, description)."""
        ports = serial.tools.list_ports.comports()
        return [(p.device, f"{p.device} ({p.description})") for p in ports]

    def set_state(self, new_state: str):
        self._state = new_state
        self.state_changed.emit(new_state)

    @Slot(str, int, bool)
    def connect_serial(self, port: str, baud: int = 250000, virtual: bool = False):
        """Attempts connection to physical port or initializes virtual mode."""
        self._is_virtual = virtual
        self._port = port
        self._baud = baud

        if self._is_virtual:
            self.set_state(SerialState.CONNECTED_IDLE)
            self.connected.emit("VIRTUAL", baud)
            self.rx_line.emit("[SYSTEM] Connected to Virtual Marlin Board (Simulation Mode)")
            self.rx_line.emit("echo: Marlin 2.0.9.x (BTT SKR Mini E3 Simulation)")
            self.rx_line.emit("echo: Ready.")
            return

        try:
            self.set_state(SerialState.CONNECTING)
            self._serial = serial.Serial(
                port=port,
                baudrate=baud,
                timeout=0.1,
                write_timeout=1.0
            )
            # Flush existing buffers
            time.sleep(0.5)
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            
            self.set_state(SerialState.CONNECTED_IDLE)
            self.connected.emit(port, baud)
            self.rx_line.emit(f"[SYSTEM] Successfully connected to {port} @ {baud} baud.")
            try:
                self._serial.write(b"M115\n")
                self._serial.flush()
            except Exception:
                pass
        except Exception as e:
            self.set_state(SerialState.DISCONNECTED)
            self.connection_error.emit(f"Connection failed: {str(e)}")

    @Slot()
    def disconnect_serial(self):
        """Disconnects serial port and cleans up state."""
        self._abort_requested = True
        self._is_streaming = False
        
        if self._serial and self._serial.is_open:
            try:
                # Turn off motor before disconnecting
                self._serial.write(b"M107\n")
                self._serial.close()
            except Exception:
                pass
        
        self._serial = None
        self.set_state(SerialState.DISCONNECTED)
        self.disconnected.emit()
        self.rx_line.emit("[SYSTEM] Disconnected.")

    @Slot(str)
    def send_mdi(self, command: str):
        """Pushes immediate manual command (jog, motor toggle, G-code) to MDI queue."""
        cmd = command.strip()
        if cmd:
            self._mdi_queue.put(cmd)

    @Slot(list)
    def start_job(self, gcode_lines: List[str]):
        """Starts streaming a full G-code program."""
        if not self.is_connected():
            self.connection_error.emit("Cannot start job: Not connected to board.")
            return

        with QMutexLocker(self._mutex):
            self._job_lines = [line.strip() for line in gcode_lines if line.strip() and not line.strip().startswith(";")]
            self._job_index = 0
            self._job_total = len(self._job_lines)
            self._is_streaming = True
            self._is_paused = False
            self._abort_requested = False

        self.set_state(SerialState.STREAMING)
        self.job_started.emit(self._job_total)

    @Slot()
    def pause_job(self):
        """Pauses the current job and turns off powder motor."""
        if self._is_streaming:
            self._is_paused = True
            self.set_state(SerialState.PAUSED)
            self.job_paused.emit(True)
            self._send_raw_line("M107 ; Pause: Turn off powder motor")

    @Slot()
    def resume_job(self):
        """Resumes a paused job."""
        if self._is_streaming and self._is_paused:
            self._is_paused = False
            self.set_state(SerialState.STREAMING)
            self.job_paused.emit(False)

    @Slot()
    def abort_job(self):
        """Aborts current job execution and shuts off powder motor."""
        self._abort_requested = True
        self._is_streaming = False
        self._is_paused = False
        self.set_state(SerialState.CONNECTED_IDLE)
        self._send_raw_line("M107 ; Abort: Turn off powder motor")
        self.job_finished.emit(False)
        self.rx_line.emit("[SYSTEM] Job aborted by user.")

    @Slot()
    def emergency_stop(self):
        """Triggers hardware Emergency Stop (M112) immediately."""
        self._abort_requested = True
        self._is_streaming = False
        self._is_paused = False
        
        # Clear MDI queue
        while not self._mdi_queue.empty():
            try:
                self._mdi_queue.get_nowait()
            except queue.Empty:
                break

        self.set_state(SerialState.ESTOP)
        self.tx_line.emit("M112 ; EMERGENCY STOP")
        
        if self._is_virtual:
            self.rx_line.emit("!! EMERGENCY STOP TRIGGERED !!")
            self.rx_line.emit("echo: M112 Emergency Stop Received")
        elif self._serial and self._serial.is_open:
            try:
                self._serial.reset_output_buffer()
                self._serial.write(b"M112\n")
                self._serial.flush()
            except Exception as e:
                self.connection_error.emit(f"E-Stop write error: {str(e)}")

    def is_connected(self) -> bool:
        return self._is_virtual or (self._serial is not None and self._serial.is_open)

    def process_loop(self):
        """Main processing loop executed in QThread."""
        self._running = True

        while self._running:
            # Process queued Qt events and signals on this thread
            QCoreApplication.processEvents()

            # 1. Handle MDI / Immediate commands
            while not self._mdi_queue.empty():
                try:
                    cmd = self._mdi_queue.get_nowait()
                    self._execute_line(cmd)
                except queue.Empty:
                    break

            # 2. Handle streaming job
            if self._is_streaming and not self._is_paused and not self._abort_requested:
                if self._job_index < self._job_total:
                    line = self._job_lines[self._job_index]
                    success = self._execute_line(line)
                    if success:
                        self._job_index += 1
                        pct = (self._job_index / self._job_total) * 100.0 if self._job_total > 0 else 100.0
                        self.job_progress.emit(
                            self._job_index,
                            self._job_total,
                            pct,
                            self._current_x,
                            self._current_y
                        )
                    else:
                        self.abort_job()
                        break
                else:
                    # Job completed
                    self._is_streaming = False
                    self.set_state(SerialState.CONNECTED_IDLE)
                    self.job_finished.emit(True)
                    self.rx_line.emit("[SYSTEM] Job completed successfully.")

            # 3. Read any background/unsolicited output from Marlin when idle
            if self._serial and self._serial.is_open and not self._is_streaming and self._mdi_queue.empty():
                try:
                    if self._serial.in_waiting > 0:
                        line_bytes = self._serial.readline()
                        rx = line_bytes.decode("utf-8", errors="replace").strip()
                        if rx:
                            self.rx_line.emit(rx)
                except Exception:
                    pass

            # Sleep briefly to avoid busy spinning
            time.sleep(0.005)

    def stop_loop(self):
        self._running = False

    def _execute_line(self, raw_cmd: str) -> bool:
        """Sends a single G-code line and waits for 'ok' response from Marlin."""
        # Strip trailing comments
        cmd = raw_cmd.split(";")[0].strip()
        if not cmd:
            return True

        self._track_coordinates(cmd)
        self.tx_line.emit(raw_cmd)

        if self._is_virtual:
            return self._virtual_execute(cmd)

        if not self._serial or not self._serial.is_open:
            self.connection_error.emit("Serial port is not open.")
            return False

        try:
            full_cmd = (cmd + "\n").encode("utf-8")
            self._serial.write(full_cmd)
            self._serial.flush()

            # Wait for 'ok' response
            start_time = time.time()
            timeout = 30.0  # Allow longer for long moves/dwells
            
            while time.time() - start_time < timeout:
                QCoreApplication.processEvents()
                if self._abort_requested:
                    return False

                if self._serial.in_waiting > 0:
                    line_bytes = self._serial.readline()
                    rx = line_bytes.decode("utf-8", errors="replace").strip()
                    if rx:
                        self.rx_line.emit(rx)
                        if rx.startswith("ok") or rx == "ok":
                            return True
                        elif rx.startswith("Error:") or rx.startswith("!!"):
                            self.connection_error.emit(f"Board Error: {rx}")
                            return False
                time.sleep(0.002)

            self.connection_error.emit(f"Timeout waiting for 'ok' on command: {cmd}")
            return False
        except Exception as e:
            self.connection_error.emit(f"Serial communication error: {str(e)}")
            return False

    def _virtual_execute(self, cmd: str) -> bool:
        """Simulates Marlin firmware execution."""
        # Simulate slight physical motion / processing delay
        delay = 0.005
        if cmd.startswith("G4"):
            # Dwell simulation
            match = re.search(r"P(\d+)", cmd)
            if match:
                delay = int(match.group(1)) / 1000.0
        elif cmd.startswith("G0") or cmd.startswith("G1"):
            delay = 0.01

        if delay > 0.5:
            # Chunk long delays for responsiveness
            chunks = int(delay / 0.1)
            for _ in range(chunks):
                if self._abort_requested:
                    return False
                time.sleep(0.1)
        else:
            time.sleep(delay)

        self.rx_line.emit("ok")
        return True

    def _send_raw_line(self, line: str):
        """Sends raw command without blocking for job queue."""
        self.tx_line.emit(line)
        cmd = line.split(";")[0].strip()
        if not cmd:
            return
        if self._is_virtual:
            self.rx_line.emit("ok")
        elif self._serial and self._serial.is_open:
            try:
                self._serial.write((cmd + "\n").encode("utf-8"))
            except Exception:
                pass

    def _track_coordinates(self, cmd: str):
        """Parses position from G0/G1/G28/G92 to maintain live coordinate tracking."""
        upper = cmd.upper()
        if upper.startswith("G28"):
            if "X" in upper or "Y" in upper or len(upper) == 3:
                self._current_x = 0.0
                self._current_y = 0.0
                self.position_updated.emit(self._current_x, self._current_y)
        elif upper.startswith("G92"):
            match_x = re.search(r"X([-+]?[0-9]*\.?[0-9]+)", upper)
            match_y = re.search(r"Y([-+]?[0-9]*\.?[0-9]+)", upper)
            if match_x:
                self._current_x = float(match_x.group(1))
            if match_y:
                self._current_y = float(match_y.group(1))
            self.position_updated.emit(self._current_x, self._current_y)
        elif upper.startswith("G0") or upper.startswith("G1"):
            match_x = re.search(r"X([-+]?[0-9]*\.?[0-9]+)", upper)
            match_y = re.search(r"Y([-+]?[0-9]*\.?[0-9]+)", upper)
            if match_x:
                self._current_x = float(match_x.group(1))
            if match_y:
                self._current_y = float(match_y.group(1))
            self.position_updated.emit(self._current_x, self._current_y)
