"""
core/storage.py
PRISM Phase 5.0 - Storage

Author: 이서영 (Backend Lead)
Date: 2025-10-24
Version: 5.0
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class Storage:
    """
    데이터 저장소
    
    특징:
    - 메모리 기반 (POC용)
    - 향후 DB 연동 가능
    """
    
    def __init__(self):
        """Storage 초기화"""
        self.sessions = {}
        logger.info("✅ Storage 초기화 완료 (메모리 기반)")
    
    def save_session(self, result: Dict[str, Any]):
        """
        세션 결과 저장
        
        Args:
            result: 처리 결과 딕셔너리
        """
        session_id = result.get('session_id')
        if session_id:
            self.sessions[session_id] = result
            logger.info(f"💾 세션 저장 완료: {session_id}")
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        세션 결과 조회
        
        Args:
            session_id: 세션 ID
        
        Returns:
            처리 결과 딕셔너리
        """
        return self.sessions.get(session_id)
    
    def list_sessions(self) -> list:
        """모든 세션 ID 조회"""
        return list(self.sessions.keys())