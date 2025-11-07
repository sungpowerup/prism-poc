"""
utils/system_utils.py
PRISM Phase 0.3 - System Utilities (Logger & File Handling)

✅ Phase 0.3 개선사항:
1. 로거 중복 핸들러 방지
2. 임시파일 삭제 재시도 (지수 백오프)
3. Windows 파일 잠금 대응

Author: 황태민 (DevOps Lead) + GPT 피드백 반영
Date: 2025-11-06
Version: Phase 0.3
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    ✅ Phase 0.3: 중복 방지 로거 설정
    
    Args:
        name: 로거 이름
        level: 로그 레벨
        log_file: 로그 파일 경로 (선택)
    
    Returns:
        설정된 로거
    """
    logger = logging.getLogger(name)
    
    # ✅ Phase 0.3: 핸들러 중복 방지
    if logger.handlers:
        # 이미 핸들러가 있으면 재사용
        return logger
    
    logger.setLevel(level)
    
    # 포맷
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (선택)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def remove_temp_file_with_retry(
    file_path: str,
    max_retries: int = 3,
    base_delay: float = 0.3
) -> bool:
    """
    ✅ Phase 0.3: 임시파일 삭제 재시도 (지수 백오프)
    
    Args:
        file_path: 파일 경로
        max_retries: 최대 재시도 횟수
        base_delay: 기본 대기 시간 (초)
    
    Returns:
        True: 성공, False: 실패
    """
    path = Path(file_path)
    
    if not path.exists():
        logger.debug(f"   파일 없음 (이미 삭제?): {file_path}")
        return True
    
    for attempt in range(max_retries):
        try:
            os.remove(path)
            logger.info(f"   ✅ 임시 파일 삭제 성공: {file_path}")
            return True
        
        except PermissionError as e:
            if attempt < max_retries - 1:
                # 지수 백오프
                delay = base_delay * (attempt + 1)
                logger.debug(f"   ⏳ 파일 잠금 - {delay:.1f}초 후 재시도 ({attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                # 최종 실패
                logger.warning(f"   ⚠️ 임시 파일 삭제 실패 (파일 잠금): {file_path}")
                logger.warning(f"      → 시스템이 나중에 자동 정리할 예정")
                return False
        
        except Exception as e:
            logger.error(f"   ❌ 임시 파일 삭제 오류: {e}")
            return False
    
    return False


def cleanup_old_temp_files(
    directory: str = ".",
    pattern: str = "temp_*.pdf",
    max_age_hours: int = 24
) -> int:
    """
    ✅ Phase 0.3: 오래된 임시파일 정리
    
    Args:
        directory: 디렉토리
        pattern: 파일 패턴
        max_age_hours: 최대 보존 시간 (시간)
    
    Returns:
        삭제된 파일 수
    """
    dir_path = Path(directory)
    now = time.time()
    max_age_seconds = max_age_hours * 3600
    
    deleted = 0
    
    for file_path in dir_path.glob(pattern):
        try:
            file_age = now - file_path.stat().st_mtime
            
            if file_age > max_age_seconds:
                os.remove(file_path)
                deleted += 1
                logger.debug(f"   🗑️ 오래된 임시파일 삭제: {file_path.name}")
        
        except Exception as e:
            logger.debug(f"   ⚠️ 파일 삭제 실패: {file_path.name} ({e})")
    
    if deleted > 0:
        logger.info(f"   ✅ 오래된 임시파일 {deleted}개 정리 완료")
    
    return deleted


def get_safe_temp_filename(base_name: str) -> str:
    """
    ✅ Phase 0.3: 안전한 임시파일명 생성
    
    Args:
        base_name: 기본 파일명
    
    Returns:
        타임스탬프 포함 안전한 파일명
    """
    timestamp = int(time.time())
    safe_name = "".join(c for c in base_name if c.isalnum() or c in "._- ")
    return f"temp_{timestamp}_{safe_name}"


# ✅ Phase 0.3: 전역 로거 초기화 함수
def init_prism_logger(log_file: str = 'prism.log') -> None:
    """
    PRISM 전역 로거 초기화 (중복 방지)
    
    Args:
        log_file: 로그 파일명
    """
    root_logger = logging.getLogger()
    
    # ✅ 핸들러 중복 체크
    if root_logger.handlers:
        return
    
    root_logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 콘솔
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    root_logger.addHandler(console)
    
    # 파일
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    logger.info("✅ PRISM 로거 초기화 완료 (중복 방지)")
