# Secrets Mount Guide (Gate-D)

- 디렉토리: secrets/ (로컬/컨테이너에 read-only 마운트 권장)
- 권한: 0400(리눅스) 또는 OS별 최소 권한, 저장소에 커밋 금지
- 예시 파일:
  - secrets/API_KEY — 게이트웨이 API Key
  - secrets/AES_KEY_B64 — 감사 로그 암호화 키(Fernet base64)
- Docker Compose 예시(참고):
  `yaml
  services:
    gateway:
      volumes:
        - ./secrets:/app/secrets:ro
      environment:
        - DOS_ADMIN_API_KEY_FILE=/app/secrets/API_KEY
        - DOS_AES_KEY_B64_FILE=/app/secrets/AES_KEY_B64
  `
- 앱에서 파일 로딩 패턴: *_FILE 환경변수 우선 → 없으면 일반 ENV → 최종 기본값.

