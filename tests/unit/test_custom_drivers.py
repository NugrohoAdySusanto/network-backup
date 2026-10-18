import pytest
import uuid
from app.drivers.base import CollectedConfig, DriverValidationError
from app.drivers.parametric import ParametricCLIDriver
from app.models.custom_driver import CustomDriver


def test_parametric_driver_normalization_and_stripping():
    definition = {
        "key": "huawei-vrp",
        "label": "Huawei VRP Switch",
        "vendor_hint": "Huawei",
        "model_hint": "S5700",
        "backup_command": "display current-configuration",
        "output_extension": "cfg",
        "strip_patterns": [
            r"^# Last configuration.*",
            r"^--More--.*",
        ],
        "validation_min_length": 30,
        "validation_required_keyword": "sysname",
    }
    driver = ParametricCLIDriver(definition)

    raw_output = """#
# Last configuration was saved on 2026-10-07 10:00:00
#
sysname SW-CORE-01
#
vlan batch 10 20 30
--More--
#
interface GigabitEthernet0/0/1
 port link-type trunk
#
return
"""
    collected = CollectedConfig(text=raw_output, extension="cfg")
    normalized = driver.normalize_config(collected)

    assert "Last configuration was saved" not in normalized
    assert "--More--" not in normalized
    assert "sysname SW-CORE-01" in normalized
    assert "vlan batch 10 20 30" in normalized

    # Validation succeeds
    driver.validate_config(collected, normalized)


def test_parametric_driver_validation_fails_on_missing_keyword():
    definition = {
        "key": "cisco-nxos",
        "label": "Cisco Nexus NX-OS",
        "backup_command": "show running-config",
        "output_extension": "txt",
        "validation_min_length": 20,
        "validation_required_keyword": "hostname",
    }
    driver = ParametricCLIDriver(definition)

    invalid_output = """! Command: show running-config
! Time: Wed Oct  7 14:00:00 2026
version 9.3(5)
feature ospf
end
"""
    collected = CollectedConfig(text=invalid_output, extension="txt")
    normalized = driver.normalize_config(collected)

    with pytest.raises(DriverValidationError, match="missing required keyword"):
        driver.validate_config(collected, normalized)


def test_parametric_driver_validation_fails_on_short_output():
    definition = {
        "key": "hp-procurve",
        "label": "HP ProCurve Switch",
        "backup_command": "show running-config",
        "output_extension": "cfg",
        "validation_min_length": 100,
    }
    driver = ParametricCLIDriver(definition)

    short_output = "hostname HP-SW1\nend\n"
    collected = CollectedConfig(text=short_output, extension="cfg")
    normalized = driver.normalize_config(collected)

    with pytest.raises(DriverValidationError, match="is too short"):
        driver.validate_config(collected, normalized)


def test_custom_driver_model_instantiation():
    driver_id = uuid.uuid4()
    model = CustomDriver(
        id=driver_id,
        key="arista-eos",
        label="Arista EOS Switch",
        vendor_hint="Arista",
        model_hint="7050SX",
        transport="ssh",
        default_port=22,
        connect_timeout=15,
        command_timeout=30,
        need_enable=True,
        enable_command="enable",
        enable_prompt_pattern=r"[>#]",
        backup_command="show running-config",
        output_extension="cfg",
        is_active=True,
    )
    assert str(model.id) == str(driver_id)
    assert model.key == "arista-eos"
    assert model.need_enable is True
