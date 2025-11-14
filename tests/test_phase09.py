"""
test_phase09.py - PRISM Phase 0.9 통합 테스트
3단 계층 + LLM 리라이팅 + Sanity Check 검증

Usage:
    python tests/test_phase09.py

Author: 마창수산팀 (정수아 QA Lead)
Date: 2025-11-14
Version: Phase 0.9
"""

import sys
import logging
from pathlib import Path

# PRISM 모듈 import
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.law_parser import LawParser
from core.dual_qa_gate import extract_pdf_text_layer
from tests.llm_rewriter import LLMRewriter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_llm_rewriter_basic():
    """기본 리라이팅 테스트"""
    
    print("\n" + "="*60)
    print("🧪 Test 1: 기본 리라이팅")
    print("="*60)
    
    rewriter = LLMRewriter(
        provider="azure_openai",
        cache_enabled=True,
        sanity_check_enabled=True
    )
    
    # 테스트 조문
    article_number = "제1조"
    article_title = "목적"
    article_body = "이규정은한국농어촌공사직원에게적용할인사관리의기준을정하여합리적이고적정한인사관리를기하게하는것을목적으로한다."
    
    try:
        rewritten, validation = rewriter.rewrite_article(
            article_number=article_number,
            article_title=article_title,
            article_body=article_body,
            document_id="test_doc",
            parser_version="0.9.0"
        )
        
        print(f"✅ 리라이팅 성공")
        print(f"   - 원본 길이: {len(article_body)}자")
        print(f"   - 리라이팅 길이: {len(rewritten)}자")
        print(f"   - Sanity Check: {'✅ PASS' if validation.is_valid else '❌ FAIL'}")
        
        if validation.warnings:
            print(f"   - 경고: {validation.warnings}")
        
        print(f"\n원본:")
        print(f"  {article_body[:100]}...")
        
        print(f"\n리라이팅:")
        print(f"  {rewritten[:100]}...")
        
        return validation.is_valid
    
    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        return False


def test_llm_rewriter_cache():
    """캐시 동작 테스트"""
    
    print("\n" + "="*60)
    print("🧪 Test 2: 캐시 동작")
    print("="*60)
    
    rewriter = LLMRewriter(
        provider="azure_openai",
        cache_enabled=True,
        sanity_check_enabled=True
    )
    
    article_number = "제2조"
    article_title = "적용범위"
    article_body = "직원의인사관리는법령및정관에정한것을제외하고는이규정에따른다."
    
    try:
        # 첫 호출
        import time
        start = time.time()
        rewritten1, _ = rewriter.rewrite_article(
            article_number=article_number,
            article_title=article_title,
            article_body=article_body,
            document_id="test_cache",
            parser_version="0.9.0"
        )
        time1 = time.time() - start
        
        # 두 번째 호출 (캐시)
        start = time.time()
        rewritten2, _ = rewriter.rewrite_article(
            article_number=article_number,
            article_title=article_title,
            article_body=article_body,
            document_id="test_cache",
            parser_version="0.9.0"
        )
        time2 = time.time() - start
        
        print(f"✅ 캐시 테스트 성공")
        print(f"   - 첫 호출: {time1:.2f}초")
        print(f"   - 캐시 호출: {time2:.2f}초")
        print(f"   - 속도 향상: {time1/time2:.1f}배")
        
        # 결과 동일 확인
        assert rewritten1 == rewritten2, "캐시 결과 불일치!"
        print(f"   - 결과 일치: ✅")
        
        # 캐시 통계
        stats = rewriter.get_cache_stats()
        print(f"   - 캐시 항목: {stats['total_cached']}개")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        return False


def test_sanity_check_validation():
    """Sanity Check 검증 테스트"""
    
    print("\n" + "="*60)
    print("🧪 Test 3: Sanity Check 검증")
    print("="*60)
    
    rewriter = LLMRewriter(
        provider="azure_openai",
        cache_enabled=False,
        sanity_check_enabled=True
    )
    
    # 테스트 케이스들
    test_cases = [
        {
            'name': '정상 케이스',
            'article_number': '제3조',
            'article_title': '정의',
            'article_body': '이규정에서사용하는용어의뜻은다음과같다.1.직위란직무와책임을말한다.2.임용이란신규채용을말한다.'
        },
        {
            'name': '숫자 포함 케이스',
            'article_number': '제4조',
            'article_title': '기간',
            'article_body': '수습기간은3개월로한다.다만특별한사유가있는경우5일이내에서연장할수있다.'
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        try:
            _, validation = rewriter.rewrite_article(
                article_number=test_case['article_number'],
                article_title=test_case['article_title'],
                article_body=test_case['article_body'],
                document_id="test_sanity",
                parser_version="0.9.0"
            )
            
            result = {
                'name': test_case['name'],
                'is_valid': validation.is_valid,
                'header_preserved': validation.header_preserved,
                'numbers_intact': validation.numbers_intact,
                'legal_terms_intact': validation.legal_terms_intact,
                'structure_preserved': validation.structure_preserved
            }
            
            results.append(result)
            
            status = "✅ PASS" if validation.is_valid else "❌ FAIL"
            print(f"{status} - {test_case['name']}")
            print(f"   - 헤더 보존: {'✅' if validation.header_preserved else '❌'}")
            print(f"   - 숫자 보존: {'✅' if validation.numbers_intact else '❌'}")
            print(f"   - 용어 보존: {'✅' if validation.legal_terms_intact else '❌'}")
            print(f"   - 구조 보존: {'✅' if validation.structure_preserved else '❌'}")
            
            if validation.warnings:
                print(f"   - 경고: {', '.join(validation.warnings)}")
        
        except Exception as e:
            logger.error(f"❌ {test_case['name']} 실패: {e}")
            results.append({'name': test_case['name'], 'is_valid': False})
    
    # 전체 통과율
    total = len(results)
    passed = sum(1 for r in results if r.get('is_valid', False))
    pass_rate = passed / total if total > 0 else 0.0
    
    print(f"\n📊 Sanity Check 통과율: {pass_rate:.0%} ({passed}/{total})")
    
    return pass_rate >= 0.95


def test_full_document_pipeline():
    """전체 문서 파이프라인 테스트"""
    
    print("\n" + "="*60)
    print("🧪 Test 4: 전체 문서 파이프라인")
    print("="*60)
    
    # 테스트 문서 경로
    pdf_path = "인사규정_일부개정전문-1-3_원본.pdf"
    
    if not Path(pdf_path).exists():
        print(f"⚠️ 테스트 문서 없음: {pdf_path}")
        return False
    
    try:
        # 1. PDF 파싱
        print("1️⃣ PDF 파싱...")
        pdf_text = extract_pdf_text_layer(pdf_path)
        parser = LawParser()
        parsed_result = parser.parse(
            pdf_text=pdf_text,
            document_title="인사규정",
            clean_artifacts=True,
            normalize_linebreaks=True
        )
        
        total_articles = parsed_result['total_articles']
        print(f"   ✅ {total_articles}개 조문 파싱 완료")
        
        # 2. LLM 리라이팅
        print("2️⃣ LLM 리라이팅...")
        rewriter = LLMRewriter(
            provider="azure_openai",
            cache_enabled=True,
            sanity_check_enabled=True
        )
        
        validation_results = []
        
        for article in parsed_result['articles'][:3]:  # 처음 3개만 테스트
            _, validation = rewriter.rewrite_article(
                article_number=article.number,
                article_title=article.title,
                article_body=article.body,
                document_id="인사규정",
                parser_version="0.9.0"
            )
            validation_results.append(validation.is_valid)
        
        passed = sum(validation_results)
        total = len(validation_results)
        pass_rate = passed / total if total > 0 else 0.0
        
        print(f"   ✅ {total}개 조문 리라이팅 완료")
        print(f"   📊 Sanity Check: {pass_rate:.0%} ({passed}/{total})")
        
        # 3. 캐시 통계
        stats = rewriter.get_cache_stats()
        print(f"   💾 캐시: {stats['total_cached']}개 항목")
        
        return pass_rate >= 0.95
    
    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        return False


def main():
    """통합 테스트 실행"""
    
    print("\n" + "="*60)
    print("🚀 PRISM Phase 0.9 통합 테스트")
    print("="*60)
    print()
    
    # 환경 확인
    import os
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        print("❌ AZURE_OPENAI_API_KEY 환경변수 미설정")
        print("   export AZURE_OPENAI_API_KEY=your-key-here")
        return False
    
    print("✅ 환경변수 확인 완료")
    
    # 테스트 실행
    tests = [
        ("기본 리라이팅", test_llm_rewriter_basic),
        ("캐시 동작", test_llm_rewriter_cache),
        ("Sanity Check", test_sanity_check_validation),
        ("전체 파이프라인", test_full_document_pipeline)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ {test_name} 실패: {e}")
            results.append((test_name, False))
    
    # 최종 결과
    print("\n" + "="*60)
    print("📊 테스트 결과")
    print("="*60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print()
    print(f"전체: {passed}/{total} 통과 ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 Phase 0.9 통합 테스트 완전 통과!")
        return True
    else:
        print("\n⚠️ 일부 테스트 실패")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
