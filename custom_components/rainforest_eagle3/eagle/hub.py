"""Eagle API client hub module."""

from collections.abc import Callable
import logging

from aiohttp import BasicAuth, ClientSession
from xmltodict import parse as xml_parse, unparse as xml_unparse

from .meter import ElectricityMeter
from .model import DeviceQueryResponse, EagleApiCommand, EagleDevice
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
        cloud_id: str,
        install_code: str,
        session_callback: Callable[..., ClientSession] | None = None,
        hostname: str | None = None,
    ) -> None:
        """Initialize the EagleHub."""
        self.cloud_id = cloud_id.lower()
        self.install_code = install_code
        self.hostname = hostname or f"eagle-{self.cloud_id}"
        self.headers = {"Content-Type": "text/xml", "User-Agent": "RainforestEagle3Client/1.0"}
        self.auth = BasicAuth(cloud_id, install_code)
        if session_callback is None:
            session_callback = ClientSession
        self.session = session_callback(headers=self.headers, auth=self.auth)

        self.devices: dict[str, EagleDevice] = {}
        self.meters: dict[str, ElectricityMeter] = {}
        self.online = False

    @property
    def device_list(self) -> list[EagleDevice]:
        """Return the set of known devices."""
        return list(self.devices.values())

    async def close(self) -> None:
        """Close the client session."""
        self.online = False
        return await self.session.close()

    async def _post(self, content_xml: str) -> dict:
        """Send POST request to device."""
        url = f"http://{self.hostname}/cgi-bin/post_manager"
        async with self.session.post(url, data=content_xml) as response:
            try:
                response_text = await response.text()
                response.raise_for_status()
            except Exception as e:
                if self.online is True:
                    self.online = False
                    _LOGGER.exception("Eagle Hub at %s is offline", self.hostname)
                raise e  # noqa: TRY201
            else:
                if self.online is False:
                    self.online = True
                    _LOGGER.info("Eagle Hub at %s is online", self.hostname)
                return xml_parse(response_text)

    async def async_execute_command(self, command: dict | str) -> dict:
        """Execute command on device."""
        if isinstance(command, EagleApiCommand):
            command = command.value
        if isinstance(command, str):
            command = {"Command": {"Name": command}}
        if not isinstance(command, dict):
            msg = "Command must be a dict or str"
            raise TypeError(msg)
        if "Command" not in command:
            command = {"Command": command}
        command_xml = xml_unparse(command)
        return await self._post(command_xml)

    async def _async_get_device_list(self) -> list[EagleDevice]:
        """Get device list from Eagle."""
        response = await self.async_execute_command(EagleApiCommand.DEVICE_LIST)
        devices = get_ensure_list(response, "DeviceList")
        return [EagleDevice.model_validate(x) for x in devices]

    async def async_query_device(
        self, device: EagleDevice, variables: list[str] | None = None
    ) -> EagleDevice:
        """Get data from a specific device."""
        if variables is None:
            component = {"All": "Y"}
        else:
            component = {
                "Component": {"Name": "Main", "Variables": [{"Variable": {"Name": x}} for x in variables]}
            }
        command = device_command(device, EagleApiCommand.DEVICE_QUERY, extra={"Components": component})
        response = await self.async_execute_command(command)
        response = DeviceQueryResponse.model_validate(response.get("Device", response))
        return response.to_device()

    async def async_refresh_device(self, device: EagleDevice | str) -> None:
        """Update a specific device."""
        hw_address: str = device.HardwareAddress if isinstance(device, EagleDevice) else device
        if hw_address in self.devices:
            device = await self.async_query_device(self.devices[hw_address])
            self.devices[hw_address] = device

    async def async_refresh_devices(self, devices: list[EagleDevice] | None = None) -> None:
        """Refresh the list of devices from the Eagle."""
        try:
            if devices is None:
                devices = await self._async_get_device_list()
            for device in devices:
                self.devices[device.HardwareAddress] = await self.async_query_device(device)
                if device.ModelId == "electric_meter":
                    if device.HardwareAddress not in self.meters:
                        self.meters[device.HardwareAddress] = ElectricityMeter(
                            hub=self, address=device.HardwareAddress
                        )
                        _LOGGER.info(
                            "Discovered new energy meter name=%s addr=%s",
                            device.Name,
                            device.HardwareAddress,
                        )
                    else:
                        _LOGGER.debug(
                            "Refreshed energy meter '%s' at '%s'",
                            device.Name,
                            device.HardwareAddress,
                        )
                else:
                    _LOGGER.debug(
                        "Refreshed unknown device '%s' at '%s' (model=%s)",
                        device.Name,
                        device.HardwareAddress,
                        device.ModelId,
                    )

        except TimeoutError as e:
            msg = f"Timeout connecting to Eagle Hub at {self.hostname}"
            raise TimeoutError(msg) from e
        except Exception as e:
            msg = f"Error connecting to Eagle Hub at {self.hostname}"
            raise ConnectionError(msg) from e
