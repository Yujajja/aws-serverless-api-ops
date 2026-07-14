# AWS Serverless API 운영 실습 - 비용 최적화와 CI/CD 자동 배포

AWS 운영 실습 시리즈 3차 프로젝트입니다.  
EC2 기반 상시 실행 구조가 아닌 Serverless 구조로 장애 접수 API를 구성하고, 실패 요청 추적, CloudWatch Alarm 감지, GitHub Actions 자동 배포까지 실습했습니다.

---

## 프로젝트 개요

이번 실습에서는 API Gateway, Lambda, DynamoDB, SQS를 사용해 서버리스 기반 장애 접수 API를 구성했습니다.

운영 관점에서 단순히 API를 배포하는 것에 그치지 않고, 장애 데이터 저장, 실패 요청 분리, 로그 확인, 알람 감지, CI/CD 자동 배포까지 연결했습니다.

---

## 실습 목표

- EC2 없이 API Gateway와 Lambda로 API 구성
- Lambda에서 장애 접수 요청 처리
- DynamoDB에 장애 데이터 저장
- SQS에 실패 요청 적재
- CloudWatch Logs로 Lambda 실행 로그 확인
- CloudWatch Alarm으로 실패 큐 메시지 감지
- GitHub Actions와 OIDC를 활용한 Lambda 자동 배포
- Terraform으로 AWS 리소스 코드화
- 실습 후 리소스 삭제를 통한 비용 관리

---

## Serverless API 운영 및 자동 배포 흐름도

아래 흐름도는 이번 프로젝트의 요청 처리, 실패 이벤트 감지, 로그 확인, 자동 배포 흐름을 나타냅니다.

![Serverless API flow](docs/images/00-serverless-api-flow.png)

---

## 사용 기술

| 구분 | 사용 기술 |
|---|---|
| Cloud | AWS |
| API | API Gateway HTTP API |
| Compute | AWS Lambda |
| Database | DynamoDB |
| Queue | Amazon SQS |
| Monitoring | CloudWatch Logs, CloudWatch Alarm |
| Notification | Amazon SNS |
| IaC | Terraform |
| CI/CD | GitHub Actions |
| 인증 방식 | GitHub Actions OIDC |

---

## 주요 구현 내용

### 1. Serverless 장애 접수 API 구성

API Gateway HTTP API를 통해 외부 요청을 받고, Lambda에서 장애 접수 요청을 처리하도록 구성했습니다.

구현한 API는 다음과 같습니다.

```text
POST /incidents
GET /incidents/{incidentId}
POST /incidents/fail-test
```

`POST /incidents` 요청이 들어오면 Lambda가 `incidentId`를 자동 생성하고 DynamoDB에 장애 데이터를 저장합니다.

---

### 2. DynamoDB 장애 데이터 저장

DynamoDB 테이블의 기본키는 `incidentId`로 구성했습니다.

저장되는 데이터 예시는 다음과 같습니다.

```json
{
  "incidentId": "6f5c9418",
  "title": "API response delay",
  "severity": "HIGH",
  "service": "payment-api",
  "status": "OPEN",
  "description": "Payment API response time increased.",
  "createdAt": "2026-07-14T..."
}
```

---

### 3. 실패 요청 SQS 적재

실패 상황을 확인하기 위해 `POST /incidents/fail-test` API를 구성했습니다.

해당 API를 호출하면 Lambda가 실패 메시지를 SQS Failure Queue에 적재합니다.

```text
POST /incidents/fail-test
→ Lambda 실행
→ 실패 메시지 생성
→ SQS Failure Queue 적재
```

---

### 4. CloudWatch Logs / Alarm 구성

Lambda 실행 로그는 CloudWatch Logs에서 확인할 수 있도록 구성했습니다.

또한 SQS Failure Queue에 메시지가 1개 이상 쌓이면 CloudWatch Alarm이 `ALARM` 상태로 전환되도록 구성했습니다.

```text
ApproximateNumberOfMessagesVisible >= 1
→ CloudWatch Alarm 상태 전환
```

SNS Topic은 알림 연동 대상으로 구성했습니다.

---

### 5. GitHub Actions CI/CD 구성

GitHub Actions를 사용해 Lambda 코드 자동 배포를 구성했습니다.

GitHub에 코드를 push하면 workflow가 실행되고, OIDC 방식으로 AWS IAM Role을 Assume한 뒤 Lambda 코드를 업데이트합니다.

```text
GitHub Push
→ GitHub Actions 실행
→ OIDC 기반 AWS 인증
→ Lambda 코드 패키징
→ Lambda 함수 코드 업데이트
```

장기 Access Key를 GitHub Secrets에 저장하지 않고, OIDC 기반 임시 인증 방식을 사용했습니다.

---

## 실행 결과

### 1. API 장애 접수 및 조회 확인

`POST /incidents` 요청으로 장애 데이터를 생성하고, 응답으로 받은 `incidentId`를 사용해 조회까지 확인했습니다.

![API incident create and get](docs/images/01-api-incident-create-and-get.png)

---

### 2. DynamoDB 저장 확인

Lambda에서 생성한 장애 데이터가 DynamoDB 테이블에 저장된 것을 확인했습니다.

![DynamoDB incident item](docs/images/02-dynamodb-incident-item.png)

---

### 3. SQS 실패 큐 적재 확인

`POST /incidents/fail-test` 실행 후 SQS Failure Queue에 메시지가 적재된 것을 확인했습니다.

![SQS failure queue](docs/images/03-sqs-failure-queue.png)

---

### 4. CloudWatch Alarm 감지 확인

SQS Failure Queue의 메시지 수가 1 이상이 되자 CloudWatch Alarm이 `ALARM` 상태로 전환되는 것을 확인했습니다.

![CloudWatch alarm](docs/images/04-cloudwatch-alarm-sqs.png)

---

### 5. Lambda 로그 확인

CloudWatch Logs에서 실패 메시지 전송 로그와 fail-test 실행 로그를 확인했습니다.

![CloudWatch lambda logs](docs/images/05-cloudwatch-lambda-logs.png)

---

### 6. GitHub Actions 자동 배포 확인

GitHub Actions workflow가 성공적으로 실행되었고, Lambda 코드 변경 후 API 응답 메시지가 변경된 것을 확인했습니다.

![GitHub Actions deploy success](docs/images/06-github-actions-deploy-success.png)

---

## 트러블슈팅

### PowerShell 한글 인코딩 문제

초기 API 테스트에서 한글 요청 데이터가 깨져 보이는 문제가 있었습니다.

API Gateway, Lambda, DynamoDB 구조 문제는 아니었고, PowerShell에서 JSON 요청을 전송할 때 인코딩 차이로 발생한 문제였습니다.  
검증 화면은 영어 데이터로 다시 테스트하여 정상 동작을 확인했습니다.

---

### SNS 구독 메일 혼동

SNS 구독 확인 메일과 구독 해지 메일이 혼동되는 상황이 있었습니다.

이메일 수신 여부를 최종 검증 결과로 강조하기보다는, SQS 실패 큐 적재와 CloudWatch Alarm의 `ALARM` 상태 전환을 중심으로 실패 요청 감지 흐름을 검증했습니다.

---

## 비용 관리

이번 실습에서는 비용을 줄이기 위해 EC2, ALB, NAT Gateway를 사용하지 않고 Serverless 구조로 구성했습니다.

적용한 비용 관리 요소는 다음과 같습니다.

- EC2 상시 실행 제거
- API Gateway + Lambda 기반 요청 단위 실행
- DynamoDB On-Demand 사용
- CloudWatch Logs 보관 기간 1일 설정
- 실습 종료 후 Terraform Destroy로 리소스 삭제

---

## 정리

이번 프로젝트를 통해 EC2 없이 Serverless 구조로 API를 운영하는 흐름을 실습했습니다.

특히 단순 API 배포가 아니라 운영 관점에서 다음 흐름을 연결했습니다.

```text
API 요청 처리
→ 장애 데이터 저장
→ 실패 요청 분리
→ 로그 확인
→ 알람 감지
→ GitHub Actions 자동 배포
→ 리소스 삭제 및 비용 관리
```

이를 통해 Serverless 기반 운영 구조, 비용 최적화, 최소 권한 배포, CI/CD 자동화 흐름을 함께 경험했습니다.