"""Pinned Blender releases used by the matrix and the installer.

LTS is the maintained 4.x line (covers the 4.2+ contract). Current is the
latest stable 5.x. Bump both together when you refresh goldens.
"""

from __future__ import annotations

BLENDER_LTS = "4.5.13"
BLENDER_CURRENT = "5.2.1"

BLENDER_CHANNELS = {
    "lts": BLENDER_LTS,
    "current": BLENDER_CURRENT,
}

# Official linux-x64 tarball. This is the cache key and the only download URL.
RELEASE_URL = "https://download.blender.org/release/Blender{major}/blender-{version}-linux-x64.tar.xz"

# Software OpenGL + Vulkan on GitHub-hosted runners.
APT_PACKAGES = (
    "libegl1",
    "libgl1",
    "libgomp1",
    "libsm6",
    "libxfixes3",
    "libxi6",
    "libxkbcommon0",
    "libxrender1",
    "libxxf86vm1",
    "mesa-utils",
    "mesa-vulkan-drivers",
    "xvfb",
)

GPU_BACKENDS = ("opengl", "vulkan")


def release_url(version: str) -> str:
    major = ".".join(version.split(".")[:2])
    return RELEASE_URL.format(major=major, version=version)


def resolve_channel(name: str) -> str:
    key = name.strip().lower()
    if key in BLENDER_CHANNELS:
        return BLENDER_CHANNELS[key]
    return name.strip()
