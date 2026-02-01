"""
JWT 시크릿 로테이션 Lambda
Secrets Manager 커스텀 로테이션: create_secret에서 새 랜덤 값 생성, finish_secret에서 AWSCURRENT로 전환.
set_secret/test_secret은 단순 문자열 시크릿에서 미사용이므로 no-op.
"""
import secrets
import boto3
from botocore.exceptions import ClientError


def lambda_handler(event, context):
    secret_id = event.get('SecretId')
    step = event.get('Step')
    token = event.get('Token') or event.get('ClientRequestToken')

    if not secret_id or not step:
        raise ValueError("Event must include SecretId and Step")
    if not token:
        raise ValueError("Event must include Token or ClientRequestToken")

    client = boto3.client('secretsmanager')

    # AWS 전달 값: create_secret, set_secret, test_secret, finish_secret (snake_case)
    if step == 'create_secret':
        # 이미 이 토큰(ClientRequestToken)으로 버전이 있으면 스킵 (재시도 시 idempotency)
        # VersionId만 사용: finish_secret 후 재시도 시 해당 버전은 AWSCURRENT이므로 VersionStage=AWSPENDING이면 실패함
        try:
            client.get_secret_value(SecretId=secret_id, VersionId=token)
            return
        except ClientError:
            pass
        # 새 JWT 시크릿 생성 (64자 hex)
        new_value = secrets.token_hex(32)
        client.put_secret_value(
            SecretId=secret_id,
            ClientRequestToken=token,
            SecretString=new_value,
            VersionStages=['AWSPENDING']
        )
    elif step == 'finish_secret':
        meta = client.describe_secret(SecretId=secret_id)
        current = meta.get('VersionIdsToStages') or {}
        old_version = None
        for vid, stages in current.items():
            if 'AWSCURRENT' in stages and vid != token:
                old_version = vid
                break
        if old_version:
            client.update_secret_version_stage(
                SecretId=secret_id,
                VersionStage='AWSCURRENT',
                RemoveFromVersionId=old_version,
                MoveToVersionId=token
            )
        else:
            # 최초 로테이션 등 AWSCURRENT가 없을 때: 토큰 버전만 AWSCURRENT로 설정
            client.update_secret_version_stage(
                SecretId=secret_id,
                VersionStage='AWSCURRENT',
                MoveToVersionId=token
            )
    # set_secret, test_secret: 단순 문자열 시크릿은 미사용, no-op
    return {}
