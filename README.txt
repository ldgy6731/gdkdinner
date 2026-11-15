우리 학교 석식 관리 사이트

구성
- app.py: Flask 서버 및 사이트 기능
- templates/: HTML 화면
- static/style.css: 디자인
- requirements.txt: 설치할 파이썬 패키지
- Procfile: Render 실행 명령

로컬 실행
1. Python 설치
2. 터미널에서 프로젝트 폴더로 이동
3. pip install -r requirements.txt
4. python app.py
5. 브라우저에서 http://127.0.0.1:5000 접속

관리자
- 최초 비밀번호: 1234
- 관리자 페이지에 로그인한 뒤 반드시 비밀번호를 변경하세요.
- 실제 배포 전 SECRET_KEY 환경변수를 반드시 설정하세요.

Render 배포 주의
- SQLite 파일은 기본적으로 임시 파일 시스템에 저장될 수 있습니다.
- Render에 영구 디스크를 연결하고 DATABASE_PATH=/var/data/dinner.db로 설정해야
  재배포나 재시작 뒤에도 데이터가 유지됩니다.
- 실제 학교에서 사용하기 전 학교 담당 교사의 허가와 개인정보 처리 기준을 확인하세요.

제보 주의
- 제보는 관리자에게만 표시됩니다.
- 신고 내용은 의심 또는 제보일 뿐 확정된 사실이 아닙니다.
- 사실에 근거한 내용만 작성하고, 관리자도 확인 절차를 거쳐야 합니다.
