# ARM 호환성 분석기 - 배포 가이드

이 가이드는 ARM 호환성 분석기를 Terraform을 사용하여 AWS Lambda 함수로 배포하는 방법을 설명합니다. 배포된 Lambda 함수는 직접 호출하거나 포함된 `analyzer.py` 클라이언트 모듈을 통해 호출할 수 있으며, 자동화된 ARM64 마이그레이션 워크플로우를 위해 CostNorm MCP 서버와 통합됩니다.

## 아키텍처 개요

ARM 호환성 분석기는 다음으로 구성됩니다:

1. **Lambda 함수** (`src/`): AWS Lambda에 배포되는 핵심 분석 로직
2. **클라이언트 모듈** (`analyzer.py`): Lambda 함수를 호출하는 Python 클라이언트
3. **지원 도구**: Lambda 검색 및 아키텍처 변경 도구
4. **MCP 통합**: 자동화된 워크플로우를 위해 CostNorm MCP 서버에서 사용됨

## 사전 요구 사항

1. **AWS 계정 및 자격 증명**: Lambda 함수, IAM 역할 및 CloudWatch 로그 그룹을 생성할 수 있는 권한이 있는 AWS 자격 증명이 필요합니다.
    * AWS CLI 구성: `aws configure --profile costnorm`
    * 또는 AWS 환경 변수 설정: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`

2. **Terraform**: Terraform 다운로드 및 설치 (버전 >= 1.0.0)
    * 다운로드: <https://www.terraform.io/downloads>
    * 설치 확인: `terraform -v`

3. **Docker**: `terraform apply`를 실행하는 시스템에 Docker가 설치되어 있고 실행 중이어야 합니다. Python 의존성 레이어를 빌드하는 데 필요합니다.
    * 다운로드: <https://www.docker.com/get-started>
    * 설치 확인: `docker --version`

4. **Python 및 종속성 (로컬 개발용)**: Python 3.8+ 및 pip 설치.
    * 로컬에서 실행하거나 테스트하려면 `requirements.txt`에 나열된 종속성을 설치하십시오: `pip install -r requirements.txt`

## 로컬 개발

로컬 개발 및 테스트를 위해 `.env` 파일을 사용하여 환경 변수를 구성할 수 있습니다:

1. `src/` 디렉토리에 필요한 변수가 포함된 `.env` 파일을 생성합니다 (`src/.env.sample` 파일을 템플릿으로 사용):

    ```dotenv
    # GitHub API 액세스
    GITHUB_TOKEN=your_github_token_here

    # DockerHub 액세스 (Docker 이미지 검사용)
    DOCKERHUB_USERNAME=your_dockerhub_username
    DOCKERHUB_PASSWORD=your_dockerhub_password_or_token

    # 분석기 구성 (True/False로 설정)
    ENABLE_TERRAFORM_ANALYZER=True
    ENABLE_DOCKER_ANALYZER=True
    ENABLE_DEPENDENCY_ANALYZER=True
    ```

2. 분석기를 로컬에서 실행 (`src/` 디렉토리에서):

    ```bash
    cd src
    # 테스트에 필요한 경우 종속성을 로컬에 설치
    pip install -r ../requirements.txt
    python lambda_function.py
    ```

`src/config.py` 코드는 Lambda 환경에서 실행 중인지 로컬에서 실행 중인지 자동으로 감지하고, Lambda 환경이 아닌 경우 `.env` 파일을 로드합니다.

## 배포 단계

### 1. Terraform 변수 구성

1. Terraform 디렉토리로 이동:

    ```bash
    cd terraform
    ```

2. 예제 파일을 복사하여 변수 정의 파일 생성:

    ```bash
    cp terraform.auto.tfvars.example terraform.auto.tfvars
    ```

3. `terraform.auto.tfvars` 파일을 편집하여 값 입력:

    ```hcl
    # --- 필수 자격 증명 ---
    dockerhub_username = "YOUR_DOCKERHUB_USERNAME"
    dockerhub_password = "YOUR_DOCKERHUB_PASSWORD_OR_PAT"
    github_token       = "YOUR_GITHUB_TOKEN"

    # --- 분석기 구성 ---
    enable_terraform_analyzer  = "True"
    enable_docker_analyzer     = "True" 
    enable_dependency_analyzer = "True"

    # --- 선택적 재정의 ---
    aws_region = "ap-northeast-2"  # 기본 리전
    log_level  = "INFO"            # 또는 "DEBUG"
    
    # 필요한 경우 함수 이름 사용자 정의
    # lambda_function_name = "custom-arm-analyzer"
    # lambda_timeout = 300
    # lambda_memory_size = 1024
    ```

    **중요**: 민감한 자격 증명이 포함된 이 파일을 버전 관리 시스템에 커밋하지 마십시오.

### 2. Terraform으로 배포

`terraform/` 디렉토리 내에서 다음 명령어를 실행합니다:

```bash
# Terraform 초기화 (aws, archive 등 프로바이더 다운로드)
terraform init

# Terraform이 적용할 변경 사항 미리보기
terraform plan

# AWS에 변경 사항 적용 및 배포
terraform apply
```

메시지가 표시되면 적용 작업을 확인합니다.

**`terraform apply`가 수행하는 작업:**

* `src/` 디렉토리에서 `.env`, `__pycache__/` 등의 개발 파일을 제외하고 zip 파일을 생성합니다
* Docker를 사용하여 ARM64 아키텍처용 Python 의존성을 Lambda 레이어로 빌드합니다
* AWS 계정에 IAM 역할, Lambda 레이어, Lambda 함수, CloudWatch 로그 그룹을 생성/업데이트합니다
* `terraform.auto.tfvars`의 변수들을 Lambda 함수 환경 변수로 주입합니다

성공적으로 완료되면 Terraform은 생성된 리소스에 대한 정보를 출력합니다.

### 3. 클라이언트 구성 업데이트 (analyzer.py 사용 시)

`analyzer.py` 클라이언트 모듈을 사용할 계획이라면 Lambda 함수 이름을 업데이트하세요:

1. `analyzer.py` 파일을 엽니다
2. Terraform 출력의 Lambda 함수 이름으로 `ARM_ANALYSIS_LAMBDA_FUNCTION_NAME` 변수를 업데이트합니다:

   ```python
   ARM_ANALYSIS_LAMBDA_FUNCTION_NAME = "arm-compatibility-analyzer"  # 이름을 사용자 정의한 경우 업데이트
   ```

3. 올바른 AWS 프로필이 구성되어 있는지 확인합니다:

   ```python
   boto3_session = boto3.Session(profile_name='costnorm', region_name='ap-northeast-2')
   ```

## 사용법

### 직접 Lambda 호출

Lambda 함수는 `github_url` 매개변수가 포함된 JSON 페이로드를 예상합니다:

```bash
# AWS CLI 사용
aws lambda invoke \
  --function-name arm-compatibility-analyzer \
  --payload '{"github_url":"https://github.com/username/repo-to-analyze"}' \
  response.json

# 결과 확인
cat response.json
```

### 클라이언트 모듈 사용

```python
from analyzer import _invoke_arm_analysis_lambda

# 리포지토리 분석
result = await _invoke_arm_analysis_lambda("https://github.com/username/repo")
print(result)
```

### MCP 서버 통합

Lambda 함수는 `analyze_repo_arm_compatibility` 도구를 통해 CostNorm MCP 서버와 자동으로 통합됩니다. MCP 서버는 다음을 수행할 수 있습니다:

1. 리포지토리 ARM 호환성 분석
2. 기존 Lambda 함수 검색
3. 호환 가능한 함수를 ARM64로 자동 마이그레이션

## 지원 도구

배포에는 ARM 마이그레이션 워크플로우를 위한 추가 Lambda 함수도 포함됩니다:

### Lambda 검색 도구

```bash
# 이름으로 Lambda 함수 검색
aws lambda invoke \
  --function-name lambda_search_tool \
  --payload '{"query":"my-function","only_x86":true}' \
  search_result.json
```

### Lambda 아키텍처 변경 도구

```bash
# 함수 아키텍처를 ARM64로 변경
aws lambda invoke \
  --function-name lambda_architecture_change_tool \
  --payload '{"function_name":"my-function","target_arch":"arm64"}' \
  change_result.json
```

## 응답 형식

ARM 호환성 분석기는 구조화된 JSON 응답을 반환합니다:

```json
{
  "repository": "owner/repo",
  "github_url": "https://github.com/owner/repo",
  "default_branch": "main",
  "analysis_details": {
    "dependencies": {
      "results": [...],
      "recommendations": [...],
      "reasoning": [...]
    },
    "docker_analysis": {
      "results": [...], 
      "recommendations": [...],
      "reasoning": [...]
    },
    "instance_types": {
      "results": [...],
      "recommendations": [...], 
      "reasoning": [...]
    }
  },
  "overall_compatibility": "compatible|incompatible|unknown",
  "recommendations": [...],
  "context": {
    "analysis_summary": {...},
    "reasoning": [...],
    "enabled_analyzers": [...],
    "statistics": {...}
  }
}
```

## 정리

Terraform으로 생성된 모든 리소스를 제거하려면:

```bash
# terraform/ 디렉토리 내에서
terraform destroy
```

메시지가 표시되면 삭제 작업을 확인합니다.

## 문제 해결

* **Terraform 오류**: 출력을 주의 깊게 읽어보십시오. 일반적인 문제로는 자격 증명 누락, Docker 미실행, AWS 권한 오류 등이 있습니다. 새 프로바이더를 추가한 경우 `terraform init`을 실행하십시오.

* **Lambda 실행 오류**: 함수의 AWS CloudWatch 로그를 확인하십시오 (예: `/aws/lambda/arm-compatibility-analyzer`). 로그 그룹 이름은 Terraform 출력에서 확인할 수 있습니다.

* **구성**: AWS 콘솔을 통해 Lambda 함수 설정에서 환경 변수를 확인하십시오 (Terraform이 `terraform.auto.tfvars`에서 설정해야 함).

* **의존성**: `requirements.txt`가 올바른지 확인하십시오. `terraform apply` 중 `local-exec` 레이어 빌드 단계의 로그에서 Docker 오류를 확인하십시오.

* **권한**: IAM 역할에 필요한 권한이 있는지 확인하십시오 (`AWSLambdaBasicExecutionRole`이 기본적으로 연결됨).

* **클라이언트 연결**: `analyzer.py`를 사용하는 경우 AWS 프로필(`costnorm`)이 올바르게 구성되어 있고 Lambda 함수를 호출할 수 있는 권한이 있는지 확인하십시오.

## 보안 고려사항

* 민감한 자격 증명(GitHub 토큰, Docker Hub 자격 증명)을 안전하게 저장하십시오
* 프로덕션 배포에서는 환경 변수 대신 AWS Secrets Manager 사용을 고려하십시오
* Lambda 함수는 보안을 위해 최소한의 IAM 권한으로 실행됩니다
* 모든 네트워크 통신은 HTTPS를 사용합니다

## 기여하기

새로운 분석기를 추가하거나 기존 분석기를 수정할 때:

1. `src/analyzers/base_analyzer.py`의 `BaseAnalyzer` 인터페이스를 따르십시오
2. 새로운 분석기 구성을 `src/config.py`에 추가하십시오
3. 새로운 의존성이 필요한 경우 `requirements.txt`를 업데이트하십시오
4. 배포하기 전에 로컬에서 테스트하십시오
5. 새로운 구성 옵션이 있는 경우 이 README를 업데이트하십시오
