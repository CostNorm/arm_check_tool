import boto3
import difflib
import json

def search_lambdas(query: str = None, only_x86: bool = True, cutoff: float = 0.3, max_results: int = 50):
    """
    검색어와 아키텍처 조건에 따라 Lambda 함수 목록을 필터링합니다.

    Args:
        query (str, optional): 검색어 (function name, description, runtime 등 포함 검색)
        only_x86 (bool): True면 x86_64만 필터링
        cutoff (float): fuzzy match 정확도 컷오프 (0.0 ~ 1.0)
        max_results (int): 최대 반환 함수 수

    Returns:
        list[dict]: Lambda 함수 정보 목록
    """
    client = boto3.client('lambda')
    all_functions = []
    next_marker = None

    while True:
        if next_marker:
            response = client.list_functions(Marker=next_marker)
        else:
            response = client.list_functions()

        for fn in response.get("Functions", []):
            arch = fn.get("Architectures", ["x86_64"])
            if only_x86 and "x86_64" not in arch:
                continue

            all_functions.append({
                "FunctionName": fn["FunctionName"],
                "Runtime": fn.get("Runtime"),
                "Architectures": arch,
                "LastModified": fn.get("LastModified"),
                "Description": fn.get("Description", "")
            })

        next_marker = response.get("NextMarker")
        if not next_marker:
            break

    if not query:
        return all_functions[:max_results]

    # Fuzzy search across multiple fields
    query = query.lower()
    scored = []
    for fn in all_functions:
        combined = " ".join([
            fn["FunctionName"],
            fn.get("Runtime") or "",
            fn.get("Description") or "",
            " ".join(fn.get("Architectures", []))
        ]).lower()

        score = difflib.SequenceMatcher(None, combined, query).ratio()
        if score >= cutoff:
            scored.append((score, fn))

    # Score 정렬 후 top N 추출
    scored.sort(reverse=True, key=lambda x: x[0])
    return [fn for _, fn in scored[:max_results]]

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
        query = event.get('query')
        only_x86 = event.get('only_x86', True)
        cutoff = event.get('cutoff', 0.3)
        max_results = event.get('max_results', 50)
        
        # Call the search function
        results = search_lambdas(
            query=query,
            only_x86=only_x86,
            cutoff=cutoff,
            max_results=max_results
        )
        
        # Return properly formatted response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'results': results,
                'count': len(results)
            }),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            }),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
