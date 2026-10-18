import os
import tempfile
from unittest.mock import patch, MagicMock
import pytest

from app.services.ssl_cert_service import (
    parse_endpoint,
    ensure_ca_bundle,
    auto_trust_endpoint_certificate,
    get_certs_dir,
    get_trusted_s3_ca_path,
)
from app.services.s3_service import S3Service


def test_parse_endpoint():
    scheme, host, port = parse_endpoint("https://10.11.40.41:9000")
    assert scheme == "https"
    assert host == "10.11.40.41"
    assert port == 9000

    scheme, host, port = parse_endpoint("https://s3.example.com")
    assert scheme == "https"
    assert host == "s3.example.com"
    assert port == 443

    scheme, host, port = parse_endpoint("http://minio.local:9000")
    assert scheme == "http"
    assert host == "minio.local"
    assert port == 9000


def test_ensure_ca_bundle_creates_valid_file():
    bundle_path = ensure_ca_bundle()
    assert os.path.exists(bundle_path)
    assert os.path.getsize(bundle_path) > 0
    with open(bundle_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "-----BEGIN CERTIFICATE-----" in content


def test_auto_trust_endpoint_skips_http():
    res = auto_trust_endpoint_certificate("http://10.11.40.41:9000")
    assert res["trusted"] is True
    assert res["action"] == "skipped"


def test_auto_trust_endpoint_pinning(tmp_path):
    dummy_pem = (
        "-----BEGIN CERTIFICATE-----\n"
        "MIIB/TCCAZSgAwIBAgIUdummyCertForTesting0001\n"
        "-----END CERTIFICATE-----\n"
    )
    mock_cert_info = {
        "host": "10.11.40.41",
        "port": 9000,
        "subject": "CN=test-minio",
        "issuer": "CN=test-minio",
        "fingerprint_sha256": "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99",
        "pem": dummy_pem,
    }

    test_trusted_file = str(tmp_path / "trusted_s3_ca.crt")
    test_bundle_file = str(tmp_path / "ca-bundle.crt")

    with patch("app.services.ssl_cert_service.get_trusted_s3_ca_path", return_value=test_trusted_file), \
         patch("app.services.ssl_cert_service.get_ca_bundle_path", return_value=test_bundle_file), \
         patch("app.services.ssl_cert_service.is_endpoint_trusted") as mock_is_trusted:
        # First check returns False (untrusted), second check returns True (trusted after pinning)
        mock_is_trusted.side_effect = [False, True]
        with patch("app.services.ssl_cert_service.fetch_remote_server_cert", return_value=mock_cert_info):
            res = auto_trust_endpoint_certificate(
                "https://10.11.40.41:9000",
                expected_fingerprint=mock_cert_info["fingerprint_sha256"],
            )
            assert res["trusted"] is True
            assert res["action"] == "pinned"
            assert res["fingerprint"] == mock_cert_info["fingerprint_sha256"]

            # Verify PEM was written to isolated test path
            with open(test_trusted_file, "r", encoding="utf-8") as f:
                saved = f.read()
            assert dummy_pem.strip() in saved


def test_auto_trust_endpoint_rejects_without_fingerprint():
    mock_cert_info = {
        "host": "10.11.40.41",
        "port": 9000,
        "subject": "CN=test-minio",
        "issuer": "CN=test-minio",
        "fingerprint_sha256": "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99",
        "pem": "-----BEGIN CERTIFICATE-----\ndummy\n-----END CERTIFICATE-----",
    }
    with patch("app.services.ssl_cert_service.is_endpoint_trusted", return_value=False), \
         patch("app.services.ssl_cert_service.fetch_remote_server_cert", return_value=mock_cert_info):
        res = auto_trust_endpoint_certificate("https://10.11.40.41:9000")
        assert res["trusted"] is False
        assert res["action"] == "unverified"
        assert res["fingerprint"] == mock_cert_info["fingerprint_sha256"]



def test_s3_service_initialization_with_ssl_bundle():
    with patch("boto3.client") as mock_boto:
        svc = S3Service(
            endpoint_url="https://10.11.40.41:9000",
            bucket_name="test-bucket",
            access_key="test-key",
            secret_key="test-secret",
            verify_ssl=True,
        )
        assert svc.verify_ssl is True
        mock_boto.assert_called_once()
        _, kwargs = mock_boto.call_args
        # kwargs['verify'] must be a non-empty string path pointing to the bundle, NOT False!
        assert isinstance(kwargs.get("verify"), str)
        assert os.path.exists(kwargs["verify"])
