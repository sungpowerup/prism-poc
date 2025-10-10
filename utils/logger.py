"""
utils/logger.py
PRISM POC - Logger (수정: Windows 인코딩 처리)
"""

import sys
import logging
import io

# ============================================================
# Windows 콘솔 UTF-8 강제 설정
# ============================================================

if sys.platform == 'win32':
    # stdout/stderr을 UTF-8로 래핑
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, 
        encoding='utf-8', 
        errors='replace'  # 인코딩 불가능한 문자는 '?' 로 대체
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, 
        encoding='utf-8', 
        errors='replace'
    )

# ============================================================
# Logger 설정
# ============================================================

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Logger 초기화 (Windows UTF-8 안전)
    
    Args:
        name: Logger 이름
        level: 로그 레벨 (기본: INFO)
    
    Returns:
        logging.Logger
    """
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 중복 핸들러 방지
    if logger.handlers:
        return logger
    
    # StreamHandler 생성
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # 포맷터 설정 (이모지 제거, 안전한 문자만)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


# ============================================================
# 편의 함수
# ============================================================

def get_logger(name: str) -> logging.Logger:
    """Logger 가져오기"""
    return logging.getLogger(name)


def set_log_level(level: str):
    """
    전역 로그 레벨 설정
    
    Args:
        level: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    """
    
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    log_level = level_map.get(level.upper(), logging.INFO)
    logging.getLogger().setLevel(log_level)


# ============================================================
# 안전한 로그 출력 래퍼
# ============================================================

def safe_log_message(message: str) -> str:
    """
    이모지 및 특수문자 제거
    
    Args:
        message: 원본 메시지
    
    Returns:
        안전한 메시지 (ASCII + 한글만)
    """
    
    # 이모지 제거
    safe_chars = []
    for char in message:
        # ASCII 범위 (0-127) + 한글 범위 (0xAC00-0xD7A3) 유지
        code = ord(char)
        if (0 <= code <= 127) or (0xAC00 <= code <= 0xD7A3) or char in [' ', '\n', '\t']:
            safe_chars.append(char)
        else:
            safe_chars.append('[?]')  # 기타 문자는 [?]로 대체
    
    return ''.join(safe_chars)


class SafeLogger:
    """Windows 안전 Logger 래퍼"""
    
    def __init__(self, name: str):
        self.logger = setup_logger(name)
    
    def debug(self, message: str):
        self.logger.debug(safe_log_message(message))
    
    def info(self, message: str):
        self.logger.info(safe_log_message(message))
    
    def warning(self, message: str):
        self.logger.warning(safe_log_message(message))
    
    def error(self, message: str):
        self.logger.error(safe_log_message(message))
    
    def critical(self, message: str):
        self.logger.critical(safe_log_message(message))


# ============================================================
# 기본 export
# ============================================================

__all__ = [
    'setup_logger',
    'get_logger',
    'set_log_level',
    'safe_log_message',
    'SafeLogger'
]