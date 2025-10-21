"""
scripts/check_env.py
환경 변수 설정 확인 스크립트

실행: python scripts/check_env.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv

def check_environment():
    """환경 변수 확인"""
    
    print("\n" + "="*60)
    print("🔍 PRISM Phase 3.0 환경 설정 확인")
    print("="*60 + "\n")
    
    # .env 파일 존재 확인
    env_path = Path('.env')
    
    if not env_path.exists():
        print("❌ .env 파일이 존재하지 않습니다!")
        print(f"   경로: {env_path.absolute()}")
        print("\n💡 해결 방법:")
        print("   1. 프로젝트 루트에 .env 파일 생성")
        print("   2. 아래 내용 복사:")
        print("""
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://fressia-dev-east-us.openai.azure.com
AZURE_OPENAI_API_KEY=7f5f21cf2cf2440ea65a8d72394944d1
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
        """)
        return False
    
    print(f"✅ .env 파일 존재: {env_path.absolute()}\n")
    
    # 환경 변수 로드
    load_dotenv()
    
    # 필수 환경 변수 확인
    required_vars = {
        'AZURE_OPENAI_ENDPOINT': 'Azure OpenAI 엔드포인트',
        'AZURE_OPENAI_API_KEY': 'Azure OpenAI API 키',
        'AZURE_OPENAI_API_VERSION': 'Azure OpenAI API 버전',
        'AZURE_OPENAI_DEPLOYMENT': 'Azure OpenAI 배포명'
    }
    
    all_set = True
    
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        
        if value:
            # API 키는 마스킹
            if 'API_KEY' in var_name:
                display_value = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
            else:
                display_value = value
            
            print(f"✅ {var_name}")
            print(f"   {description}: {display_value}")
        else:
            print(f"❌ {var_name}")
            print(f"   {description}: 설정되지 않음")
            all_set = False
        
        print()
    
    # 선택적 환경 변수
    optional_vars = {
        'ANTHROPIC_API_KEY': 'Claude API 키 (옵션)',
        'OLLAMA_BASE_URL': 'Ollama 서버 URL (옵션)'
    }
    
    print("-" * 60)
    print("선택적 환경 변수:\n")
    
    for var_name, description in optional_vars.items():
        value = os.getenv(var_name)
        
        if value:
            if 'API_KEY' in var_name:
                display_value = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
            else:
                display_value = value
            
            print(f"✅ {var_name}")
            print(f"   {description}: {display_value}")
        else:
            print(f"⚪ {var_name}")
            print(f"   {description}: 설정 안됨 (정상)")
        
        print()
    
    # 최종 결과
    print("="*60)
    if all_set:
        print("✅ 모든 필수 환경 변수가 설정되었습니다!")
        print("\n다음 단계:")
        print("  streamlit run app_phase30.py")
    else:
        print("❌ 일부 환경 변수가 설정되지 않았습니다.")
        print("\n.env 파일을 확인하고 누락된 변수를 추가하세요.")
    print("="*60 + "\n")
    
    return all_set


if __name__ == '__main__':
    check_environment()