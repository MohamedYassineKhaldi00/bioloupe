"""Device manager for GPU/CPU allocation."""

from __future__ import annotations

import logging
from typing import Literal

logger = logging.getLogger(__name__)


class DeviceManager:
    """Manages device allocation for ML models."""

    def __init__(self) -> None:
        self._cuda_available: bool | None = None
        self._cuda_device_count: int | None = None

    def is_cuda_available(self) -> bool:
        """Check if CUDA is available.

        Returns:
            True if CUDA is available
        """
        if self._cuda_available is None:
            try:
                import torch

                self._cuda_available = torch.cuda.is_available()
            except ImportError:
                self._cuda_available = False
                logger.warning("PyTorch not installed, CUDA unavailable")
        return self._cuda_available

    def get_cuda_device_count(self) -> int:
        """Get number of available CUDA devices.

        Returns:
            Number of CUDA devices
        """
        if not self.is_cuda_available():
            return 0

        if self._cuda_device_count is None:
            import torch

            self._cuda_device_count = torch.cuda.device_count()
        return self._cuda_device_count

    def select_device(self, device: str = "auto") -> str:
        """Select appropriate device for model execution.

        Args:
            device: Requested device (auto, cpu, cuda:0, etc.)

        Returns:
            Selected device string
        """
        if device == "auto":
            return "cuda:0" if self.is_cuda_available() else "cpu"

        if device.startswith("cuda"):
            if not self.is_cuda_available():
                logger.warning("CUDA requested but unavailable, using CPU")
                return "cpu"

            device_id = self._extract_device_id(device)
            if device_id >= self.get_cuda_device_count():
                logger.warning(
                    f"CUDA device {device_id} unavailable, using cuda:0"
                )
                return "cuda:0"

        return device

    def get_device_memory_info(self, device: str) -> dict[str, int]:
        """Get memory information for a device.

        Args:
            device: Device string (cuda:0, cpu)

        Returns:
            Dictionary with total and available memory in bytes
        """
        if device == "cpu":
            import psutil

            mem = psutil.virtual_memory()
            return {"total": mem.total, "available": mem.available}

        if device.startswith("cuda"):
            import torch

            device_id = self._extract_device_id(device)
            total = torch.cuda.get_device_properties(device_id).total_memory
            allocated = torch.cuda.memory_allocated(device_id)
            return {"total": total, "available": total - allocated}

        return {"total": 0, "available": 0}

    def check_memory_sufficient(
        self, device: str, required_bytes: int
    ) -> bool:
        """Check if device has sufficient memory.

        Args:
            device: Device string
            required_bytes: Required memory in bytes

        Returns:
            True if sufficient memory available
        """
        memory_info = self.get_device_memory_info(device)
        available = memory_info.get("available", 0)
        return available >= required_bytes

    def _extract_device_id(self, device: str) -> int:
        """Extract device ID from device string.

        Args:
            device: Device string (cuda:0, cuda:1, etc.)

        Returns:
            Device ID
        """
        if ":" in device:
            return int(device.split(":")[1])
        return 0


_device_manager: DeviceManager | None = None


def get_device_manager() -> DeviceManager:
    """Get singleton device manager instance.

    Returns:
        DeviceManager instance
    """
    global _device_manager
    if _device_manager is None:
        _device_manager = DeviceManager()
    return _device_manager
