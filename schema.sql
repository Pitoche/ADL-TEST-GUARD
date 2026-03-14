PRAGMA foreign_keys = ON;

-- =========================================
-- test_runs (main table)
-- =========================================

CREATE TABLE IF NOT EXISTS test_runs (
  test_id            TEXT PRIMARY KEY,
  test_area          TEXT NOT NULL,
  test_name          TEXT NOT NULL,

  test_parameters    TEXT NOT NULL,
  target_config      TEXT NOT NULL,

  execution_state    TEXT NOT NULL CHECK (
    execution_state IN ('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED')
  ),

  start_time         TEXT,
  end_time           TEXT,

  failure_reason     TEXT
);

CREATE INDEX IF NOT EXISTS idx_test_runs_start_time 
ON test_runs(start_time);

CREATE INDEX IF NOT EXISTS idx_test_runs_area_name  
ON test_runs(test_area, test_name);

CREATE INDEX IF NOT EXISTS idx_test_runs_state      
ON test_runs(execution_state);



-- =========================================
-- test_phases (baseline / full)
-- =========================================

CREATE TABLE IF NOT EXISTS test_phases (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  test_id           TEXT NOT NULL,

  phase_name        TEXT NOT NULL CHECK (
    phase_name IN ('BASELINE','FULL')
  ),

  planned_duration  INTEGER NOT NULL,
  schedule          TEXT,

  phase_start_time  TEXT,
  phase_end_time    TEXT,

  phase_status      TEXT NOT NULL CHECK (
    phase_status IN ('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED')
  ),

  FOREIGN KEY(test_id) REFERENCES test_runs(test_id)
);

CREATE INDEX IF NOT EXISTS idx_test_phases_test_id 
ON test_phases(test_id);

CREATE INDEX IF NOT EXISTS idx_test_phases_status 
ON test_phases(phase_status);

CREATE UNIQUE INDEX IF NOT EXISTS uq_test_phases_run_phase
ON test_phases(test_id, phase_name);



-- =========================================
-- run_artifacts (logs / outputs)
-- =========================================

CREATE TABLE IF NOT EXISTS run_artifacts (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  test_id       TEXT NOT NULL,

  artifact_type TEXT NOT NULL,
  file_path     TEXT NOT NULL,
  created_time  TEXT,
  meta          TEXT,

  FOREIGN KEY(test_id) REFERENCES test_runs(test_id)
);

CREATE INDEX IF NOT EXISTS idx_run_artifacts_test_id 
ON run_artifacts(test_id);

CREATE INDEX IF NOT EXISTS idx_run_artifacts_type 
ON run_artifacts(test_id, artifact_type);



-- =========================================
-- telemetry_samples (time-series metrics)
-- =========================================

CREATE TABLE IF NOT EXISTS telemetry_samples (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  test_id       TEXT NOT NULL,
  phase_id      INTEGER,

  ts            TEXT NOT NULL,

  cpu_pct       REAL,
  mem_pct       REAL,

  iops_read     REAL,
  iops_write    REAL,

  queue_len     INTEGER,

  p50_ms        REAL,
  p90_ms        REAL,
  p99_ms        REAL,
  error_rate    REAL,

  meta          TEXT,

  FOREIGN KEY(test_id) REFERENCES test_runs(test_id),
  FOREIGN KEY(phase_id) REFERENCES test_phases(id)
);

CREATE INDEX IF NOT EXISTS idx_tel_test_ts 
ON telemetry_samples(test_id, ts);

CREATE INDEX IF NOT EXISTS idx_tel_phase_ts 
ON telemetry_samples(phase_id, ts);