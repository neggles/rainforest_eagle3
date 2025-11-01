"""Eagle API client hub module."""

import logging

from aiohttp import BasicAuth, ClientSession
from xmltodict import parse as xml_parse, unparse as xml_unparse

from .meter import ElectricityMeter
from .model import DeviceDetailsResponse, DeviceQueryResponse, EagleApiCommand, EagleDevice
from .util import get_ensure_list

_LOGGER = logging.getLogger(__name__)


def device_command(device: EagleDevice, command_name: str, extra: dict | None = None) -> dict:
    """Build a device command dictionary."""
    command = {
        "Name": command_name,
        "DeviceDetails": {"HardwareAddress": device.HardwareAddress},
    }
    if extra:
        command.update(extra)
    return command


class EagleHub:
    """Eagle API client hub class."""

    manufacturer = "Rainforest Automation"
    model = "EAGLE-200"

    def __init__(
        self,
        session: ClientSession,
        cloud_id: str,
        install_code: str,
        hostname: str | None = None,
    ) -> None:
        """Initialize the EagleHub."""
        self.session = session
        self.cloud_id = cloud_id.lower()
        self.install_code = install_code
        self.hostname = hostname or f"eagle-{self.cloud_id}"

        self.headers = {"Content-Type": "text/xml"}
        self.auth = BasicAuth(cloud_id, install_code)

        self.devices: list[EagleDevice] = []
        self.meters: dict[str, ElectricityMeter] = {}
        self.online = False

    async def _post(self, content_xml: str) -> dict:
        """Send POST request to device."""
        url = f"http://{self.hostname}/cgi-bin/post_manager"
        async with self.session.post(url, auth=self.auth, headers=self.headers, data=content_xml) as response:
            try:
                response_text = await response.text()
                response.raise_for_status()
            except Exception as e:
                self.online = False
                raise e  # noqa: TRY201
            else:
                self.online = True
                return xml_parse(response_text)

    async def async_execute_command(self, command: dict | str) -> dict:
        """Execute command on device."""
        if isinstance(command, str):
            command = {"Command": {"Name": command}}
        if "Command" not in command:
            command = {"Command": command}
        command_xml = xml_unparse(command)
        _LOGGER.debug("Executing Eagle command", extra={"command": command, "command_xml": command_xml})
        return await self._post(command_xml)

    async def async_get_device_list(self) -> list[EagleDevice]:
        """Get device list from Eagle."""
        response = await self.async_execute_command(EagleApiCommand.DEVICE_LIST)
        devices = get_ensure_list(response, "DeviceList")
        return [EagleDevice.model_validate(device) for device in devices]

    async def async_refresh_devices(self) -> None:
        """Refresh the list of devices from the Eagle."""
        try:
            devices = await self.async_get_device_list()
            for device in devices:
                if device.ModelId == "electric_meter":
                    _LOGGER.debug("Found Eagle energy meter device", extra={"device": device})
                    meter = ElectricityMeter(hub=self, device=device)
                    await meter.refresh()
                    self.meters[meter.hardware_address] = meter
            self.devices = devices
            _LOGGER.debug("Eagle devices refreshed", extra={"devices": devices})
        except TimeoutError as e:
            msg = f"Timeout connecting to Eagle Hub at {self.hostname}"
            raise TimeoutError(msg) from e

    async def device_details(self, device: EagleDevice) -> DeviceDetailsResponse:
        """Get details for a specific device."""
        command = device_command(device, EagleApiCommand.DEVICE_DETAILS)
        response = await self.async_execute_command(command)
        details = response.get("Device", response)
        return DeviceDetailsResponse.model_validate(details)

    async def async_query_device(
        self,
        device: EagleDevice,
        variables: list[str] | None = None,
    ) -> DeviceQueryResponse:
        """Get data from a specific device."""
        if variables is None:
            component = {"All": "Y"}
        else:
            component = {
                "Component": {"Name": "Main", "Variables": [{"Variable": {"Name": x}} for x in variables]}
            }
        command = device_command(device, EagleApiCommand.DEVICE_QUERY, extra={"Components": component})
        response = await self.async_execute_command(command)
        details = response.get("Device", response)
        return DeviceQueryResponse.model_validate(details)

    async def async_query_all_devices(self) -> dict[str, DeviceQueryResponse]:
        """Get data from all devices."""
        data = {}
        for device in self.devices:
            try:
                data[device.HardwareAddress] = await self.async_query_device(device)
            except Exception:
                msg = f"Failed to query device {device.HardwareAddress}"
                _LOGGER.exception(msg)
                continue
        return data
