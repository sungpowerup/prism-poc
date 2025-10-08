"""
core/storage.py
PRISM POC - SQLite 데이터베이스 저장소
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import json

class Storage:
    """SQLite 기반 데이터 저장소"""
    
    def __init__(self, db_path: str = "data/prism_poc.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Sessions 테이블
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_size INTEGER,
                page_count INTEGER,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)
        
        # Elements 테이블
        conn.execute("""
            CREATE TABLE IF NOT EXISTS elements (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                element_type TEXT NOT NULL,
                bbox TEXT,
                original_content TEXT,
                caption TEXT,
                confidence REAL,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                processing_time_ms INTEGER,
                created_at TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        
        # Metrics 테이블
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                session_id TEXT PRIMARY KEY,
                total_elements INTEGER DEFAULT 0,
                processed_elements INTEGER DEFAULT 0,
                failed_elements INTEGER DEFAULT 0,
                avg_confidence REAL,
                total_time_sec REAL,
                api_calls INTEGER DEFAULT 0,
                api_cost_usd REAL DEFAULT 0.0,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        
        # 인덱스
        conn.execute("CREATE INDEX IF NOT EXISTS idx_elements_session ON elements(session_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_elements_type ON elements(element_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_elements_status ON elements(status)")
        
        conn.commit()
        conn.close()
    
    def create_session(self, session_id: str, filename: str, file_size: int, page_count: int) -> bool:
        """새 세션 생성"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT INTO sessions (session_id, filename, file_size, page_count, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, filename, file_size, page_count, datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"세션 생성 오류: {e}")
            return False
    
    def save_element(self, element: Dict) -> bool:
        """Element 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT INTO elements 
                (id, session_id, page_number, element_type, bbox, original_content, 
                 caption, confidence, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                element['id'],
                element['session_id'],
                element['page_number'],
                element['element_type'],
                json.dumps(element.get('bbox')),
                element.get('original_content'),
                element.get('caption'),
                element.get('confidence'),
                element.get('status', 'pending'),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Element 저장 오류: {e}")
            return False
    
    def update_element(self, element_id: str, updates: Dict) -> bool:
        """Element 업데이트"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [element_id]
            
            conn.execute(
                f"UPDATE elements SET {set_clause} WHERE id = ?",
                values
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Element 업데이트 오류: {e}")
            return False
    
    def get_session_elements(self, session_id: str) -> List[Dict]:
        """세션의 모든 Element 조회"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute(
            "SELECT * FROM elements WHERE session_id = ? ORDER BY page_number, id",
            (session_id,)
        )
        
        elements = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return elements
    
    def update_session_status(self, session_id: str, status: str, error_message: str = None) -> bool:
        """세션 상태 업데이트"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            if status == 'completed':
                conn.execute(
                    "UPDATE sessions SET status = ?, completed_at = ? WHERE session_id = ?",
                    (status, datetime.now().isoformat(), session_id)
                )
            else:
                conn.execute(
                    "UPDATE sessions SET status = ?, error_message = ? WHERE session_id = ?",
                    (status, error_message, session_id)
                )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"세션 상태 업데이트 오류: {e}")
            return False
    
    def save_metrics(self, session_id: str, metrics: Dict) -> bool:
        """메트릭 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO metrics 
                (session_id, total_elements, processed_elements, failed_elements,
                 avg_confidence, total_time_sec, api_calls, api_cost_usd)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                metrics.get('total_elements', 0),
                metrics.get('processed_elements', 0),
                metrics.get('failed_elements', 0),
                metrics.get('avg_confidence', 0.0),
                metrics.get('total_time_sec', 0.0),
                metrics.get('api_calls', 0),
                metrics.get('api_cost_usd', 0.0)
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"메트릭 저장 오류: {e}")
            return False