"""
간단한 Streamlit 테스트 앱
"""

import streamlit as st

st.title("🔷 Streamlit 테스트")
st.write("이 메시지가 보이면 Streamlit이 정상 작동합니다!")

if st.button("클릭해보세요"):
    st.success("버튼이 작동합니다! ✅")
    st.balloons()