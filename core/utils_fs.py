"""
core/utils_fs.py
PRISM Phase 0.3.4 P2.4 - 파일 시스템 유틸

✅ 기능:
1. 안전 임시 파일 생성 (UUID)
2. 안전 파일 삭제 (재시도 + GC)
"""

import os
import time
import uuid
import gc
import logging

logger = logging.getLogger(__name__)


def safe_temp_path(suffix=".pdf") -> str:
    """
    안전한 임시 파일 경로 생성
    
    Args:
        suffix: 파일 확장자
    
    Returns:
        UUID 기반 임시 파일 경로
    """
    return f"temp_{uuid.uuid4().hex}{suffix}"


def safe_remove(path: str, retries: int = 5, base_delay: float = 0.1) -> bool:
    """
    안전한 파일 삭제 (지수 백오프 재시도)
    
    Args:
        path: 삭제할 파일 경로
        retries: 최대 재시도 횟수
        base_delay: 기본 대기 시간 (초)
    
    Returns:
        성공 여부
    """
    for attempt in range(retries):
        try:
            os.remove(path)
            logger.debug(f"   ✅ 파일 삭제 성공: {path}")
            return True
        
        except FileNotFoundError:
            # 이미 삭제됨
            return True
        
        except PermissionError:
            if attempt < retries - 1:
                # 가비지 컬렉션 + 지수 백오프
                gc.collect()
                delay = base_delay * (2 ** attempt)
                logger.debug(f"   ⏳ 삭제 재시도 {attempt+1}/{retries} (대기 {delay:.2f}초)")
                time.sleep(delay)
            else:
                logger.warning(f"   ⚠️ 파일 삭제 실패 (최종): {path}")
                return False
        
        except Exception as e:
            logger.error(f"   ❌ 파일 삭제 오류: {e}")
            return False
    
    return False


# 사용 예시
if __name__ == "__main__":
    # 임시 파일 생성
    temp_path = safe_temp_path(".pdf")
    print(f"임시 파일: {temp_path}")
    
    # 파일 생성
    with open(temp_path, 'w') as f:
        f.write("test")
    
    # 안전 삭제
    success = safe_remove(temp_path)
    print(f"삭제 성공: {success}")
