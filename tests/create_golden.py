"""
create_golden.py - PRISM Phase 0.8 Golden File 생성 도구
PDF → Parser → Golden File 자동 생성

Usage:
    python create_golden.py <pdf_path> --type standard --verifier "법무팀 김민지"

Author: 마창수산팀
Date: 2025-11-14
Version: Phase 0.8
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# PRISM 모듈 import
try:
    from core.law_parser import LawParser
    from core.dual_qa_gate import extract_pdf_text_layer
    from golden_schema import (
        GoldenFile, GoldenMetadata,
        create_golden_from_parsed_result
    )
except ImportError as e:
    print(f"❌ 모듈 import 실패: {e}")
    print("   core/ 모듈이 PYTHONPATH에 있는지 확인하세요")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_golden_file(
    pdf_path: str,
    document_type: str = "standard",
    verifier: str = "자동생성",
    parser_version: str = "0.8.0",
    schema_version: str = "1.0",
    notes: str = None
) -> GoldenFile:
    """
    PDF로부터 Golden File 생성
    
    Args:
        pdf_path: PDF 파일 경로
        document_type: 문서 타입 (standard, edge_case)
        verifier: 검증자 정보
        parser_version: 파서 버전
        schema_version: 스키마 버전
        notes: 특이사항
    
    Returns:
        GoldenFile 객체
    """
    logger.info(f"📜 Golden File 생성 시작: {pdf_path}")
    
    # PDF 텍스트 추출
    logger.info("   1️⃣ PDF 텍스트 추출 중...")
    pdf_text = extract_pdf_text_layer(pdf_path)
    
    if not pdf_text:
        raise ValueError("PDF 텍스트 추출 실패")
    
    logger.info(f"      ✅ {len(pdf_text)}자 추출")
    
    # LawParser 파싱
    logger.info("   2️⃣ LawParser 파싱 중...")
    parser = LawParser()
    
    pdf_filename = Path(pdf_path).name
    document_title = Path(pdf_path).stem
    
    parsed_result = parser.parse(
        pdf_text=pdf_text,
        document_title=document_title,
        clean_artifacts=True,
        normalize_linebreaks=True
    )
    
    logger.info(f"      ✅ {parsed_result['total_chapters']}개 장, "
                f"{parsed_result['total_articles']}개 조문")
    
    # 페이지 수 계산
    from core.pdf_processor import PDFProcessor
    pdf_processor = PDFProcessor()
    pages = pdf_processor.process_pdf(pdf_path)
    page_count = len(pages)
    
    # Golden Metadata 생성
    logger.info("   3️⃣ Golden Metadata 생성 중...")
    metadata = GoldenMetadata(
        parser_version=parser_version,
        schema_version=schema_version,
        document_title=parsed_result['document_title'] or document_title,
        document_type=document_type,
        golden_verified_date=datetime.now().strftime("%Y-%m-%d"),
        golden_verified_by=verifier,
        source_file=pdf_filename,
        page_count=page_count,
        notes=notes
    )
    
    # Golden File 생성
    logger.info("   4️⃣ Golden File 생성 중...")
    golden = create_golden_from_parsed_result(parsed_result, metadata)
    
    logger.info("✅ Golden File 생성 완료!")
    logger.info(f"   - 타이틀: {golden.metadata.document_title}")
    logger.info(f"   - 타입: {golden.metadata.document_type}")
    logger.info(f"   - 검증자: {golden.metadata.golden_verified_by}")
    logger.info(f"   - 구조: {golden.structure.total_chapters}개 장, "
                f"{golden.structure.total_articles}개 조문")
    
    return golden


def main():
    """CLI 메인"""
    parser = argparse.ArgumentParser(
        description="PRISM Phase 0.8 Golden File 생성 도구"
    )
    
    parser.add_argument(
        'pdf_path',
        help='PDF 파일 경로'
    )
    
    parser.add_argument(
        '--type',
        choices=['standard', 'edge_case'],
        default='standard',
        help='문서 타입 (기본: standard)'
    )
    
    parser.add_argument(
        '--verifier',
        default='자동생성',
        help='검증자 정보 (기본: 자동생성)'
    )
    
    parser.add_argument(
        '--parser-version',
        default='0.8.0',
        help='파서 버전 (기본: 0.8.0)'
    )
    
    parser.add_argument(
        '--schema-version',
        default='1.0',
        help='스키마 버전 (기본: 1.0)'
    )
    
    parser.add_argument(
        '--notes',
        help='특이사항'
    )
    
    parser.add_argument(
        '--output',
        help='출력 파일 경로 (기본: <문서명>_golden.json)'
    )
    
    args = parser.parse_args()
    
    # Golden File 생성
    try:
        golden = create_golden_file(
            pdf_path=args.pdf_path,
            document_type=args.type,
            verifier=args.verifier,
            parser_version=args.parser_version,
            schema_version=args.schema_version,
            notes=args.notes
        )
        
        # 출력 경로 결정
        if args.output:
            output_path = args.output
        else:
            pdf_stem = Path(args.pdf_path).stem
            output_dir = Path('tests/golden') / args.type
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{pdf_stem}_golden.json"
        
        # 저장
        golden.to_json(output_path)
        logger.info(f"💾 Golden File 저장: {output_path}")
        
    except Exception as e:
        logger.error(f"❌ 생성 실패: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
