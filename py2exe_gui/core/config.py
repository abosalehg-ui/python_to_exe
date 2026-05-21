"""Build configuration dataclass — decouples UI state from command construction."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class BuildConfig:
    """All parameters needed to construct a PyInstaller command."""

    source: str = ""
    output_name: str = ""
    output_dir: str = ""
    icon: str = ""

    onefile: bool = True
    windowed: bool = False
    noconsole: bool = False
    clean: bool = True
    noconfirm: bool = True
    strip: bool = False

    extra_files: List[str] = field(default_factory=list)
    hidden_imports: List[str] = field(default_factory=list)

    optimize: int = 0
    upx: bool = False
    upx_level: int = 0
    extra_args: str = ""

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "output_name": self.output_name,
            "output_dir": self.output_dir,
            "icon": self.icon,
            "onefile": self.onefile,
            "windowed": self.windowed,
            "noconsole": self.noconsole,
            "clean": self.clean,
            "noconfirm": self.noconfirm,
            "strip": self.strip,
            "extra_files": list(self.extra_files),
            "hidden_imports": list(self.hidden_imports),
            "optimize": self.optimize,
            "upx": self.upx,
            "upx_level": self.upx_level,
            "extra_args": self.extra_args,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BuildConfig":
        return cls(
            source=data.get("source", ""),
            output_name=data.get("output_name", ""),
            output_dir=data.get("output_dir", ""),
            icon=data.get("icon", ""),
            onefile=data.get("onefile", True),
            windowed=data.get("windowed", False),
            noconsole=data.get("noconsole", False),
            clean=data.get("clean", True),
            noconfirm=data.get("noconfirm", True),
            strip=data.get("strip", False),
            extra_files=list(data.get("extra_files", [])),
            hidden_imports=list(data.get("hidden_imports", [])),
            optimize=data.get("optimize", 0),
            upx=data.get("upx", False),
            upx_level=data.get("upx_level", 0),
            extra_args=data.get("extra_args", ""),
        )
