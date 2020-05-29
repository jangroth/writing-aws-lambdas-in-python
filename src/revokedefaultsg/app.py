import logging
import os
from functools import wraps

import boto3

logging.basicConfig(format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("RevokeDefaultSgApplication")
logger.setLevel(os.environ.get("LOGGING", logging.DEBUG))


def notify_cloudwatch(function):
    @wraps(function)
    def wrapper(event, context):
        logger.info(f"'{context.function_name}' - entry.\nIncoming event: '{event}'")
        result = function(event, context)
        logger.info(f"'{context.function_name}' - exit.\nResult: '{result}'")
        return result

    return wrapper


class UnknownEventException(Exception):
    pass


class RevokeDefaultSg:
    def __init__(self, region="ap-southeast-2"):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(os.environ.get("LOGGING", logging.DEBUG))
        self.ec2_client = boto3.client("ec2", region_name=region)
        self.ec2_resource = boto3.resource("ec2", region_name=region)

    def _extract_sg_id(self, event):
        is_correct_event_source = (event.get("detail", {}).get("eventSource", None) == "ec2.amazonaws.com")
        is_correct_event_type = (event.get("detail", {}).get("eventType", None) == "AwsApiCall")
        event_sg_id = (event.get("detail", {}).get("requestParameters", {}).get("groupId", None))

        if not (is_correct_event_source and is_correct_event_type and event_sg_id):
            raise UnknownEventException(f"Cannot handle event: {event}")
        return event_sg_id

    def _is_default_sg(self, sg_id):
        sec_groups = self.ec2_client.describe_security_groups(GroupIds=[sg_id])[
            "SecurityGroups"
        ]
        return sec_groups[0]["GroupName"] == "default"

    def _revoke_and_tag(self, sg_id):
        security_group = self.ec2_resource.SecurityGroup(sg_id)
        should_tag = False
        if security_group.ip_permissions:
            security_group.revoke_ingress(IpPermissions=security_group.ip_permissions)
            should_tag = True
            self.logger.debug("Revoking ingress rules")
        if security_group.ip_permissions_egress:
            should_tag = True
            security_group.revoke_egress(
                IpPermissions=security_group.ip_permissions_egress
            )
            self.logger.debug("Revoking egress rules")
        if should_tag:
            security_group.create_tags(
                Tags=[
                    {
                        "Key": "auto:remediation-reason",
                        "Value": "AWS CIS Benchmark 4.4 - Default SG's rules are automatically revoked",
                    }
                ]
            )
            self.logger.debug("Adding tag.")
        else:
            self.logger.debug("No ingress/egress rules found to revoke")

    def process_event(self, event):
        sg_id = self._extract_sg_id(event)
        if self._is_default_sg(sg_id):
            self.logger.info(f"Revoking ingress/egress on default SG {sg_id}.")
            self._revoke_and_tag(sg_id)
        else:
            self.logger.info(f"SG {sg_id} is not a default SG, nothing to do.")
        return "SUCCESS"


@notify_cloudwatch
def handler(event, context):
    return RevokeDefaultSg().process_event(event)


if __name__ == "__main__":
    pass
