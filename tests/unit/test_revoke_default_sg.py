import json
from unittest import mock
from unittest.mock import MagicMock

import pytest

from revokedefaultsg.app import RevokeDefaultSg, UnknownEventException

GOOD_EVENT = '''
{
  "id": "3469fd4b-b00a-ede7-937b-b4da1faf5b81",
  "detail": {
    "eventVersion": "1.05",
    "eventTime": "2020-02-05T23:04:14Z",
    "eventSource": "ec2.amazonaws.com",
    "eventName": "AuthorizeSecurityGroupIngress",
    "eventID": "bc9e3252-6466-4720-955e-e342e782d405",
    "eventType": "AwsApiCall",
    "requestParameters": {
      "groupId": "sg-123"
      }
  }
}
'''

BAD_EVENT = '''
{
  "id": "3469fd4b-b00a-ede7-937b-b4da1faf5b81",
  "detail": {
    "eventVersion": "1.05",
    "eventTime": "2020-02-05T23:04:14Z",
    "eventSource": "barrista.arround.the.corner",
    "eventName": "AuthorizeSecurityGroupIngress",
    "eventID": "bc9e3252-6466-4720-955e-e342e782d405",
    "eventType": "DrinkMoreCoffee"
  }
}
'''

TEST_SG = 'sg-123'


@pytest.fixture
def bad_event():
    return json.loads(BAD_EVENT)


@pytest.fixture
def good_event():
    return json.loads(GOOD_EVENT)


@pytest.fixture()
def obj():
    obj = RevokeDefaultSg.__new__(RevokeDefaultSg)
    obj.logger = MagicMock()
    obj.ec2_client = MagicMock()
    obj.ec2_resource = MagicMock()
    return obj


def test_should_process_event_and_revoke_if_default_sg(obj, good_event):
    obj._is_default_sg = MagicMock(return_value=True)
    obj._revoke_and_tag = MagicMock()

    obj.process_event(good_event)

    obj._is_default_sg.assert_called_once_with(TEST_SG)
    obj._revoke_and_tag.assert_called_once_with(TEST_SG)


def test_should_process_event_and_do_nothing_if_non_default_sg(obj, good_event):
    obj._is_default_sg = MagicMock(return_value=False)
    obj._revoke_and_tag = MagicMock()

    obj.process_event(good_event)

    obj._is_default_sg.assert_called_once_with(TEST_SG)
    obj._revoke_and_tag.assert_not_called()


def test_should_extract_sg_id_from_good_event(obj, good_event):
    assert obj._extract_sg_id(good_event) == 'sg-123'


def test_should_raise_exception_if_unknown_event(obj):
    with pytest.raises(UnknownEventException):
        obj._extract_sg_id({'foo': 'bar'})


def test_should_raise_exception_if_wrong_event(obj, bad_event):
    with pytest.raises(UnknownEventException):
        obj._extract_sg_id(bad_event)


def test_should_find_default_sg(obj):
    obj.ec2_client.describe_security_groups.return_value = {"SecurityGroups": [{"GroupName": "default"}]}

    assert obj._is_default_sg(TEST_SG)


def test_should_find_non_default_sg(obj):
    obj.ec2_client.describe_security_groups.return_value = {"SecurityGroups": [{"GroupName": "not default"}]}

    assert not obj._is_default_sg(TEST_SG)


def test_should_tag_if_ingress_was_revoked(obj):
    mock_security_group = MagicMock()
    mock_security_group.ip_permissions = 'ingress'
    mock_security_group.ip_permissions_egress = None
    obj.ec2_resource.SecurityGroup.return_value = mock_security_group

    obj._revoke_and_tag(TEST_SG)

    mock_security_group.create_tags.assert_called_once_with(Tags=mock.ANY)


def test_should_tag_if_egress_was_revoked(obj):
    mock_security_group = MagicMock()
    mock_security_group.ip_permissions = None
    mock_security_group.ip_permissions_egress = 'egress'
    obj.ec2_resource.SecurityGroup.return_value = mock_security_group

    obj._revoke_and_tag(TEST_SG)

    mock_security_group.create_tags.assert_called_once_with(Tags=mock.ANY)


def test_should_not_tag_if_nothing_was_revoked(obj):
    mock_security_group = MagicMock()
    mock_security_group.ip_permissions = None
    mock_security_group.ip_permissions_egress = None
    obj.ec2_resource.SecurityGroup.return_value = mock_security_group

    obj._revoke_and_tag(TEST_SG)

    mock_security_group.create_tags.assert_not_called()
