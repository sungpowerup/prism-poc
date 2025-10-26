"""
test_phase_530_simple.py
PRISM Phase 5.3.0 - Simple Integration Test (GPT 보완 반영)

목적: 핵심 모듈 동작 확인
"""

from core import QuickLayoutAnalyzer, PromptRules, KVSNormalizer
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_quick_layout_analyzer():
    """QuickLayoutAnalyzer 테스트"""
    logger.info("="*60)
    logger.info("TEST 1: QuickLayoutAnalyzer")
    logger.info("="*60)
    
    analyzer = QuickLayoutAnalyzer()
    
    # 가상 이미지 데이터 (실제로는 Base64)
    # 여기서는 None으로 테스트 (Fallback 동작 확인)
    logger.info("가상 이미지로 Fallback 테스트...")
    
    try:
        hints = analyzer.analyze("")  # 빈 데이터 → Fallback
        logger.info(f"✅ Fallback 힌트: {hints}")
        
        # 기대값 확인
        assert 'has_numbers' in hints
        assert 'diagram_count' in hints
        assert 'has_text' in hints
        logger.info("✅ 모든 필수 키 존재")
        
    except Exception as e:
        logger.error(f"❌ 실패: {e}")
        return False
    
    return True


def test_prompt_rules():
    """PromptRules DSL 테스트"""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: PromptRules DSL")
    logger.info("="*60)
    
    # MVP 힌트 (GPT 제안)
    hints = {
        'has_numbers': True,
        'diagram_count': 3,
        'has_text': True,
        'has_table': False,
        'has_map': True,
        'layout_complexity': 'complex'
    }
    
    logger.info(f"입력 힌트: {hints}")
    
    # 프롬프트 생성
    prompt = PromptRules.build_prompt(hints)
    
    logger.info(f"\n생성된 프롬프트 (첫 500자):")
    logger.info("-" * 60)
    logger.info(prompt[:500] + "...")
    logger.info("-" * 60)
    
    # 검증
    assert "## 숫자 정보" in prompt
    assert "## 지도 정보" in prompt
    assert "3개의 다이어그램" in prompt
    assert "복잡한 레이아웃" in prompt
    
    logger.info("✅ 모든 섹션 정상 생성")
    
    return True


def test_validation_rules():
    """Validation 규칙 테스트"""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Validation Rules")
    logger.info("="*60)
    
    hints = {
        'has_numbers': True,
        'diagram_count': 2,
        'has_map': True,
        'has_table': False
    }
    
    # 테스트 콘텐츠 1: 완전
    complete_content = """
## 운행 정보
- 배차간격: 27분
- 첫차: 05:30
- 막차: 22:40

## 지도 정보
동구 지역을 중심으로 주요 정류장 위치가 표시되어 있습니다.

## 다이어그램 1
꽃바위 → 화암 → 대왕암공원

## 다이어그램 2
꽃바위 → 일산해수욕장 → 꽃바위
"""
    
    validation = PromptRules.validate_extraction(complete_content, hints)
    logger.info(f"완전한 콘텐츠 검증: {validation}")
    
    assert validation['passed'] == True
    logger.info("✅ 완전한 콘텐츠 검증 통과")
    
    # 테스트 콘텐츠 2: 누락
    incomplete_content = """
## 텍스트 정보
일부 내용만 있음
"""
    
    validation = PromptRules.validate_extraction(incomplete_content, hints)
    logger.info(f"\n누락 콘텐츠 검증: {validation}")
    
    assert validation['passed'] == False
    assert 'numbers' in validation['missing']
    assert 'map' in validation['missing']
    logger.info("✅ 누락 콘텐츠 검증 실패 (정상)")
    
    return True


def test_retry_prompt():
    """Retry 프롬프트 테스트"""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Retry Prompt (GPT Enhancement)")
    logger.info("="*60)
    
    hints = {
        'has_numbers': True,
        'diagram_count': 2
    }
    
    missing = ['numbers', 'diagram']
    prev_content = "일부 텍스트만 추출됨..."
    
    retry_prompt = PromptRules.build_retry_prompt(hints, missing, prev_content)
    
    logger.info(f"\n재추출 프롬프트 (첫 500자):")
    logger.info("-" * 60)
    logger.info(retry_prompt[:500] + "...")
    logger.info("-" * 60)
    
    # 검증
    assert "[RETRY]" in retry_prompt
    assert "누락" in retry_prompt
    assert "## 숫자 정보" in retry_prompt
    
    logger.info("✅ 재추출 프롬프트 정상 생성")
    
    return True


def test_typo_correction():
    """오탈자 교정 테스트 (GPT 제안)"""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: Typo Correction")
    logger.info("="*60)
    
    text_with_typos = "임산해수욕장에서 출발하여 꽃비위로 돌아옵니다."
    
    corrected = PromptRules.correct_typos(text_with_typos)
    
    logger.info(f"원본: {text_with_typos}")
    logger.info(f"교정: {corrected}")
    
    assert "일산해수욕장" in corrected
    assert "꽃바위" in corrected
    
    logger.info("✅ 오탈자 교정 성공")
    
    return True


def test_kvs_normalization():
    """KVS 정규화 테스트 (GPT 제안 #4)"""
    logger.info("\n" + "="*60)
    logger.info("TEST 6: KVS Normalization (GPT Enhancement)")
    logger.info("="*60)
    
    # 테스트 KVS
    test_kvs = {
        '배차 간격': '27',
        '첫차시간': '5:30',
        '막 차': '22:40',
        '노선 번호': '111'
    }
    
    logger.info(f"원본 KVS: {test_kvs}")
    
    # 정규화
    normalized = KVSNormalizer.normalize_kvs(test_kvs)
    
    logger.info(f"정규화 KVS: {normalized}")
    
    # 검증
    assert normalized['배차간격'] == '27분', f"배차간격: {normalized.get('배차간격')}"
    assert normalized['첫차'] == '05:30', f"첫차: {normalized.get('첫차')}"
    assert normalized['막차'] == '22:40', f"막차: {normalized.get('막차')}"
    assert normalized['노선번호'] == '111', f"노선번호: {normalized.get('노선번호')}"
    
    logger.info("✅ KVS 정규화 성공")
    
    return True


def main():
    """전체 테스트 실행"""
    logger.info("\n")
    logger.info("🚀 PRISM Phase 5.3.0 통합 테스트 시작")
    logger.info("="*60)
    
    tests = [
        ("QuickLayoutAnalyzer", test_quick_layout_analyzer),
        ("PromptRules DSL", test_prompt_rules),
        ("Validation Rules", test_validation_rules),
        ("Retry Prompt", test_retry_prompt),
        ("Typo Correction", test_typo_correction),
        ("KVS Normalization", test_kvs_normalization)  # GPT 제안 #4
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            logger.error(f"❌ {name} 실패: {e}")
            results.append((name, False))
    
    # 결과 요약
    logger.info("\n" + "="*60)
    logger.info("📊 테스트 결과 요약")
    logger.info("="*60)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} - {name}")
    
    passed = sum(1 for _, s in results if s)
    total = len(results)
    
    logger.info(f"\n총 {total}개 중 {passed}개 통과 ({passed/total*100:.0f}%)")
    
    if passed == total:
        logger.info("\n🎉 Phase 5.3.0 핵심 모듈 모두 정상!")
    else:
        logger.warning(f"\n⚠️ {total - passed}개 테스트 실패")


if __name__ == "__main__":
    main()
