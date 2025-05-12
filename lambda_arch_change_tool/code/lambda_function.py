import boto3
from botocore.exceptions import ClientError
import json

def update_lambda_architecture(function_name: str, target_arch: str = "arm64") -> dict:
    """
    주어진 Lambda 함수의 아키텍처를 arm64로 변경합니다 (x86_64일 경우에만).

    Args:
        function_name (str): 대상 Lambda 함수 이름
        target_arch (str): 변경할 아키텍처 (기본값: arm64)

    Returns:
        dict: 결과 메시지 및 성공 여부
    """
    client = boto3.client('lambda')

    try:
        # 현재 설정 조회
        config = client.get_function_configuration(FunctionName=function_name)
        current_archs = config.get("Architectures", ["x86_64"])

        if target_arch in current_archs:
            return {
                "success": False,
                "message": f"{function_name} already uses {target_arch}"
            }

        # 아키텍처 변경
        response = client.update_function_configuration(
            FunctionName=function_name,
            Architectures=[target_arch]
        )

        return {
            "success": True,
            "message": f"{function_name} architecture updated to {target_arch}",
            "update_response": response
        }

    except ClientError as e:
        return {
            "success": False,
            "message": f"AWS error: {e.response['Error']['Message']}",
            "error_code": e.response['Error']['Code']
        }
    except Exception as ex:
        return {
            "success": False,
            "message": str(ex)
        }

def lambda_handler(event, context):
    """
    AWS Lambda 함수 핸들러
    
    Args:
        event (dict): Lambda 이벤트 데이터
        context (object): Lambda 컨텍스트 객체
        
    Returns:
        dict: API Gateway에 맞는 응답 형식
    """
    try:
        # Get parameters from event
        function_name = event.get('function_name')
        target_arch = event.get('target_arch', 'arm64')
        
        # Validate required parameters
        if not function_name:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'message': 'Missing required parameter: function_name'
                }),
                'headers': {
                    'Content-Type': 'application/json'
                }
            }
        
        # Call the update function
        result = update_lambda_architecture(
            function_name=function_name,
            target_arch=target_arch
        )
        
        # Return properly formatted response
        status_code = 200 if result.get('success', False) else 400
        return {
            'statusCode': status_code,
            'body': json.dumps(result),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'message': f'Unexpected error: {str(e)}'
            }),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
