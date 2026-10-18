from app.drivers.base import CollectedConfig
from app.drivers.registry import registry


def test_production_driver_keys_are_registered() -> None:
    keys = {item.key for item in registry.list_metadata()}
    assert "sangfor-nsf" in keys
    assert "mikrotik-routeros" in keys
    assert "ruijie-switch" in keys
    assert "ruijie-ap" in keys


def test_unknown_driver_is_not_registered() -> None:
    assert registry.has("does-not-exist") is False


def test_mikrotik_normalization_idempotent() -> None:
    driver = registry.create("mikrotik-routeros")
    sample = """# oct/04/2026 17:19:39 by RouterOS 6.49.20
# software id = 4K3K-Y62L
#
# model = CCR1016-12G
# serial number = E72E0DF3XXXX
/interface bridge
add admin-mac=00:00:00:00:00:00 auto-mac=no name=bridge1
"""
    c = CollectedConfig(text=sample, extension="rsc")
    norm = driver.normalize_config(c)
    assert "# oct/04/2026" not in norm
    assert "/interface bridge" in norm
    assert norm == driver.normalize_config(CollectedConfig(text=norm, extension="rsc"))
    driver.validate_config(c, norm)


def test_ruijie_ap_normalization_idempotent() -> None:
    driver = registry.create("ruijie-ap")
    sample = """Building configuration...
Current configuration: 6394 bytes

version AP_RGOS 11.9(6)W3B1, Release(11190308)
hostname MKK-HQ_AP-01
!
ip ssh port 22345
!
end
MKK-HQ_AP-01#
"""
    c = CollectedConfig(text=sample, extension="text", filename="config.text")
    norm = driver.normalize_config(c)
    assert "Building configuration" not in norm
    assert "Current configuration" not in norm
    assert "MKK-HQ_AP-01#" not in norm
    assert "hostname MKK-HQ_AP-01" in norm
    assert norm == driver.normalize_config(CollectedConfig(text=norm, extension="text"))
    driver.validate_config(c, norm)


def test_sangfor_nsf_normalization_idempotent() -> None:
    driver = registry.create("sangfor-nsf")
    sample = """config
ipgroup "Pirates URL" ipv4
type domains
importance ordinary
domains "yasir252.com"
domains "bagas-31.com"
end

config
ipgroup "DATA-Employees" ipv4
type ip
importance ordinary
ipentry 10.11.2.0-10.11.2.255
end
"""
    c = CollectedConfig(text=sample, extension="txt", filename="config.txt")
    norm = driver.normalize_config(c)
    assert 'ipgroup "Pirates URL" ipv4' in norm
    assert 'ipentry 10.11.2.0-10.11.2.255' in norm
    assert norm == driver.normalize_config(CollectedConfig(text=norm, extension="txt"))
    driver.validate_config(c, norm)


if __name__ == "__main__":
    test_production_driver_keys_are_registered()
    test_unknown_driver_is_not_registered()
    test_mikrotik_normalization_idempotent()
    test_ruijie_ap_normalization_idempotent()
    test_sangfor_nsf_normalization_idempotent()
    print("All driver registry tests passed!")

