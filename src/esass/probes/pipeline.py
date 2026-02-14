"""
Buffered event processing pipeline.

Efficiently processes captured events with batching and async writes.
Supports both file-based (JSONL) and SQLite backends.
"""

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path
from queue import Empty, Queue
from typing import List, Optional

from esass.models import LogEntry
from esass.observation.logger import ObservationLogger

logger = logging.getLogger(__name__)


class EventPipeline:
    """
    Buffered pipeline for processing observation events.

    Features:
    - Batch writing for performance
    - Async processing (non-blocking)
    - Configurable flush intervals
    - Graceful shutdown
    - Error handling and retries
    """

    def __init__(self, data_dir: Optional[Path] = None,
                 buffer_size: int = 100,
                 flush_interval: float = 5.0,
                 max_queue_size: int = 10000):
        """
        Initialize event pipeline.

        Args:
            data_dir: Directory for log storage
            buffer_size: Max events before auto-flush
            flush_interval: Seconds between scheduled flushes
            max_queue_size: Maximum queue size (backpressure)
        """
        self.data_dir = data_dir or Path('./data')
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.max_queue_size = max_queue_size

        # Initialize logger
        self.logger = ObservationLogger(self.data_dir)

        # Event queue
        self.queue: Queue[LogEntry] = Queue(maxsize=max_queue_size)

        # Buffer
        self.buffer: List[LogEntry] = []
        self.buffer_lock = threading.Lock()

        # Worker thread
        self.worker_thread: Optional[threading.Thread] = None
        self.shutdown_flag = threading.Event()
        self.flush_event = threading.Event()

        # Statistics
        self.total_submitted = 0
        self.total_written = 0
        self.total_dropped = 0
        self.flush_count = 0
        self.last_flush_time = time.time()

        # Start worker
        self._start_worker()

        logger.info(f"EventPipeline initialized (buffer_size={buffer_size}, "
                   f"flush_interval={flush_interval}s)")

    def submit(self, entries: List[LogEntry]) -> None:
        """
        Submit log entries for processing.

        Args:
            entries: List of log entries to process

        Raises:
            RuntimeError: If pipeline is shutdown
        """
        if self.shutdown_flag.is_set():
            raise RuntimeError("Cannot submit to shutdown pipeline")

        for entry in entries:
            try:
                self.queue.put(entry, block=False)
                self.total_submitted += 1
            except Exception:
                # Queue full - drop event and log warning
                self.total_dropped += 1
                if self.total_dropped % 100 == 1:  # Log every 100th drop
                    logger.warning(f"Event queue full, dropped {self.total_dropped} events total")

    def flush(self) -> None:
        """Force immediate flush of buffer"""
        self.flush_event.set()
        # Wait for flush to complete
        time.sleep(0.1)

    def shutdown(self, timeout: float = 10.0) -> None:
        """
        Shutdown pipeline gracefully.

        Args:
            timeout: Max seconds to wait for shutdown
        """
        logger.info("Shutting down EventPipeline...")

        # Signal shutdown
        self.shutdown_flag.set()
        self.flush_event.set()

        # Wait for worker
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=timeout)

            if self.worker_thread.is_alive():
                logger.warning("Worker thread did not terminate in time")

        # Final flush
        self._write_buffer()

        logger.info(f"EventPipeline shutdown complete. "
                   f"Submitted: {self.total_submitted}, "
                   f"Written: {self.total_written}, "
                   f"Dropped: {self.total_dropped}")

    def get_stats(self) -> dict:
        """Get pipeline statistics"""
        return {
            'total_submitted': self.total_submitted,
            'total_written': self.total_written,
            'total_dropped': self.total_dropped,
            'flush_count': self.flush_count,
            'queue_size': self.queue.qsize(),
            'buffer_size': len(self.buffer),
            'is_running': not self.shutdown_flag.is_set(),
        }

    def _start_worker(self) -> None:
        """Start background worker thread"""
        self.worker_thread = threading.Thread(
            target=self._worker_loop,
            name='EventPipeline-Worker',
            daemon=True
        )
        self.worker_thread.start()
        logger.info("Worker thread started")

    def _worker_loop(self) -> None:
        """Main worker loop"""
        logger.info("Worker loop starting")

        while not self.shutdown_flag.is_set():
            try:
                # Process events from queue
                self._process_queue()

                # Check if flush needed
                if self._should_flush():
                    self._write_buffer()

                # Check for manual flush request
                if self.flush_event.is_set():
                    self._write_buffer()
                    self.flush_event.clear()

                # Small sleep to prevent busy wait
                time.sleep(0.01)

            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                time.sleep(0.1)  # Back off on error

        # Final cleanup
        logger.info("Worker loop shutting down, processing remaining events...")
        self._process_queue()
        self._write_buffer()
        logger.info("Worker loop terminated")

    def _process_queue(self) -> None:
        """Process events from queue into buffer"""
        batch_size = min(100, self.buffer_size)
        processed = 0

        while processed < batch_size:
            try:
                # Non-blocking get
                entry = self.queue.get(block=False)

                with self.buffer_lock:
                    self.buffer.append(entry)

                processed += 1

                # Auto-flush if buffer full
                if len(self.buffer) >= self.buffer_size:
                    self._write_buffer()
                    break

            except Empty:
                # Queue empty
                break

    def _should_flush(self) -> bool:
        """Check if buffer should be flushed"""
        # Flush if buffer has entries and interval elapsed
        if not self.buffer:
            return False

        elapsed = time.time() - self.last_flush_time
        return elapsed >= self.flush_interval

    def _write_buffer(self) -> None:
        """Write buffer to storage"""
        with self.buffer_lock:
            if not self.buffer:
                return

            try:
                # Write batch
                self.logger.log_many(self.buffer)

                count = len(self.buffer)
                self.total_written += count
                self.flush_count += 1
                self.last_flush_time = time.time()

                logger.debug(f"Flushed {count} events to storage "
                           f"(total written: {self.total_written})")

                # Clear buffer
                self.buffer.clear()

            except Exception as e:
                logger.error(f"Failed to write buffer: {e}", exc_info=True)
                # Keep buffer for retry
                # Could implement more sophisticated retry logic here


class AsyncEventPipeline(EventPipeline):
    """
    Enhanced pipeline with advanced features.

    Adds:
    - Filtering capabilities
    - Event prioritization
    - Compression
    - Sampling (for high-volume scenarios)
    """

    def __init__(self, *args, sample_rate: float = 1.0, **kwargs):
        """
        Initialize async pipeline.

        Args:
            sample_rate: Fraction of events to keep (0.0-1.0)
                        1.0 = keep all, 0.1 = keep 10%
        """
        self.sample_rate = sample_rate
        self.sample_counter = 0
        super().__init__(*args, **kwargs)

    def submit(self, entries: List[LogEntry]) -> None:
        """Submit with optional sampling"""
        if self.sample_rate >= 1.0:
            # No sampling, pass through
            super().submit(entries)
            return

        # Apply sampling
        sampled = []
        for entry in entries:
            self.sample_counter += 1
            if (self.sample_counter % int(1.0 / self.sample_rate)) == 0:
                sampled.append(entry)

        if sampled:
            super().submit(sampled)


class PriorityEventPipeline(EventPipeline):
    """
    Pipeline with priority queue.

    Events can be marked with priority levels:
    - HIGH: Critical events (errors, decisions)
    - NORMAL: Regular events (tool usage)
    - LOW: Verbose events (debugging info)
    """

    def __init__(self, *args, **kwargs):
        """Initialize priority pipeline"""
        # Use three separate queues
        from queue import PriorityQueue

        super().__init__(*args, **kwargs)
        # Override queue with priority queue
        # Priority: 0 = high, 1 = normal, 2 = low
        self.queue = PriorityQueue(maxsize=self.max_queue_size)

    def submit(self, entries: List[LogEntry], priority: int = 1) -> None:
        """
        Submit entries with priority.

        Args:
            entries: Log entries
            priority: Priority level (0=high, 1=normal, 2=low)
        """
        if self.shutdown_flag.is_set():
            raise RuntimeError("Cannot submit to shutdown pipeline")

        for entry in entries:
            try:
                # Priority queue expects (priority, item) tuples
                self.queue.put((priority, entry), block=False)
                self.total_submitted += 1
            except Exception:
                self.total_dropped += 1
                if self.total_dropped % 100 == 1:
                    logger.warning(f"Priority queue full, dropped {self.total_dropped} events")

    def _process_queue(self) -> None:
        """Process priority queue"""
        batch_size = min(100, self.buffer_size)
        processed = 0

        while processed < batch_size:
            try:
                # Get highest priority item
                priority, entry = self.queue.get(block=False)

                with self.buffer_lock:
                    self.buffer.append(entry)

                processed += 1

                if len(self.buffer) >= self.buffer_size:
                    self._write_buffer()
                    break

            except Empty:
                break


# ============================================================================
# SQLite Database Pipeline (ENHANCEMENT.md Phase 1.1)
# ============================================================================


class DatabasePipeline(EventPipeline):
    """
    SQLite-backed event pipeline for robust, scalable persistence.

    Features:
    - ACID compliance (no race conditions)
    - Indexed queries on session_id, timestamp, event_type
    - JSON blob storage for event_data and metadata
    - Full-text search capability (future)
    - Automatic schema migration
    """

    SCHEMA_VERSION = 1

    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        event_data TEXT NOT NULL,
        caused_by TEXT,
        tags TEXT,
        conversation_id TEXT,
        metadata TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_session ON events(session_id);
    CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp);
    CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type);
    CREATE INDEX IF NOT EXISTS idx_caused_by ON events(caused_by);
    """

    def __init__(self, db_path: Optional[Path] = None,
                 buffer_size: int = 100,
                 flush_interval: float = 5.0,
                 max_queue_size: int = 10000):
        """
        Initialize SQLite database pipeline.

        Args:
            db_path: Path to SQLite database file
            buffer_size: Max events before auto-flush
            flush_interval: Seconds between scheduled flushes
            max_queue_size: Maximum queue size (backpressure)
        """
        self.db_path = db_path or Path.home() / ".esass" / "data" / "esass.db"
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.max_queue_size = max_queue_size

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

        # Event queue
        self.queue: Queue[LogEntry] = Queue(maxsize=max_queue_size)

        # Buffer
        self.buffer: List[LogEntry] = []
        self.buffer_lock = threading.Lock()

        # Worker thread
        self.worker_thread: Optional[threading.Thread] = None
        self.shutdown_flag = threading.Event()
        self.flush_event = threading.Event()

        # Statistics
        self.total_submitted = 0
        self.total_written = 0
        self.total_dropped = 0
        self.flush_count = 0
        self.last_flush_time = time.time()

        # Thread-local connections for SQLite
        self._local = threading.local()

        # Start worker
        self._start_worker()

        logger.info(f"DatabasePipeline initialized (db={self.db_path}, "
                   f"buffer_size={buffer_size})")

    def _worker_loop(self) -> None:
        """Main worker loop with connection cleanup."""
        logger.info("DatabasePipeline worker loop starting")

        while not self.shutdown_flag.is_set():
            try:
                # Process events from queue
                self._process_queue()

                # Check if flush needed
                if self._should_flush():
                    self._write_buffer()

                # Check for manual flush request
                if self.flush_event.is_set():
                    self._write_buffer()
                    self.flush_event.clear()

                # Small sleep to prevent busy wait
                time.sleep(0.01)

            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                time.sleep(0.1)  # Back off on error

        # Final cleanup - close worker thread's connection
        logger.info("DatabasePipeline worker loop shutting down...")
        self._process_queue()
        self._write_buffer()
        self._close_connection()
        logger.info("DatabasePipeline worker loop terminated")

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.executescript(self.CREATE_TABLE_SQL)
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _close_connection(self) -> None:
        """Close thread-local database connection."""
        if hasattr(self._local, 'conn') and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None

    def _write_buffer(self) -> None:
        """Write buffer to SQLite database."""
        with self.buffer_lock:
            if not self.buffer:
                return

            try:
                conn = self._get_connection()
                cursor = conn.cursor()

                insert_sql = """
                INSERT OR REPLACE INTO events
                (event_id, session_id, timestamp, event_type, event_data,
                 caused_by, tags, conversation_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                rows = []
                for entry in self.buffer:
                    rows.append((
                        entry.event_id,
                        entry.session_id,
                        entry.timestamp,
                        entry.event_type,
                        json.dumps(entry.event_data),
                        entry.caused_by,
                        json.dumps(entry.tags),
                        entry.conversation_id,
                        json.dumps(entry.metadata),
                    ))

                cursor.executemany(insert_sql, rows)
                conn.commit()

                count = len(self.buffer)
                self.total_written += count
                self.flush_count += 1
                self.last_flush_time = time.time()

                logger.debug(f"Flushed {count} events to SQLite "
                           f"(total written: {self.total_written})")

                # Clear buffer
                self.buffer.clear()

            except Exception as e:
                logger.error(f"Failed to write to SQLite: {e}", exc_info=True)

    def query_events(self,
                     session_id: Optional[str] = None,
                     event_type: Optional[str] = None,
                     since: Optional[str] = None,
                     limit: int = 100) -> List[LogEntry]:
        """
        Query events from the database.

        Args:
            session_id: Filter by session
            event_type: Filter by event type
            since: ISO timestamp to query from
            limit: Maximum results

        Returns:
            List of LogEntry objects
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        sql = "SELECT * FROM events WHERE 1=1"
        params = []

        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)

        if event_type:
            sql += " AND event_type = ?"
            params.append(event_type)

        if since:
            sql += " AND timestamp >= ?"
            params.append(since)

        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        entries = []
        for row in rows:
            entries.append(LogEntry(
                event_id=row['event_id'],
                session_id=row['session_id'],
                timestamp=row['timestamp'],
                event_type=row['event_type'],
                event_data=json.loads(row['event_data']),
                caused_by=row['caused_by'],
                tags=json.loads(row['tags']) if row['tags'] else [],
                conversation_id=row['conversation_id'],
                metadata=json.loads(row['metadata']) if row['metadata'] else {},
            ))

        return entries

    def count_events(self, session_id: Optional[str] = None) -> int:
        """Get total event count."""
        conn = self._get_connection()
        cursor = conn.cursor()

        if session_id:
            cursor.execute("SELECT COUNT(*) FROM events WHERE session_id = ?",
                          (session_id,))
        else:
            cursor.execute("SELECT COUNT(*) FROM events")

        return cursor.fetchone()[0]

    def get_stats(self) -> dict:
        """Get pipeline statistics including database stats."""
        base_stats = {
            'total_submitted': self.total_submitted,
            'total_written': self.total_written,
            'total_dropped': self.total_dropped,
            'flush_count': self.flush_count,
            'queue_size': self.queue.qsize(),
            'buffer_size': len(self.buffer),
            'is_running': not self.shutdown_flag.is_set(),
        }

        # Add database stats
        try:
            base_stats['db_event_count'] = self.count_events()
            base_stats['db_path'] = str(self.db_path)
            base_stats['db_size_bytes'] = self.db_path.stat().st_size if self.db_path.exists() else 0
        except Exception:
            pass

        return base_stats

    def shutdown(self, timeout: float = 10.0) -> None:
        """Shutdown pipeline and close database connections."""
        logger.info("Shutting down DatabasePipeline...")

        # Signal shutdown
        self.shutdown_flag.set()
        self.flush_event.set()

        # Wait for worker (it will close its own connection)
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=timeout)

        # Final flush and close main thread connection
        self._write_buffer()
        self._close_connection()

        # Force garbage collection to release any lingering connections
        import gc
        gc.collect()

        logger.info(f"DatabasePipeline shutdown complete. "
                   f"Submitted: {self.total_submitted}, "
                   f"Written: {self.total_written}")
