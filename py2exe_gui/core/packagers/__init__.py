"""Package formats behind one ``Packager`` interface (2.0, milestone 4).

``get_packager(name)``, ``spec_from_project`` and ``run_packaging`` are the
entry points; the release pipeline, the command line and the GUI share them.
"""

import os
import subprocess
from typing import Callable, Dict, List, Optional, Sequence, Union

from py2exe_gui.core.diagnostics import build_name
from py2exe_gui.core.packagers.appimage import (
    AppImagePackager,
    appimagetool_url,
    download_appimagetool,
)
from py2exe_gui.core.packagers.base import (
    STAGING_DIR,
    Log,
    Packager,
    PackageResult,
    PackageSpec,
    Runner,
    errors_in,
    slug,
)
from py2exe_gui.core.packagers.deb import DebPackager
from py2exe_gui.core.packagers.dmg import DmgPackager
from py2exe_gui.core.platform_support import PACKAGE_FORMATS, is_supported, resolve

#: format name → packager, in the order the UI lists them.
_PACKAGERS: Dict[str, Packager] = {
    p.name: p for p in (AppImagePackager(), DebPackager(), DmgPackager())
}
assert tuple(_PACKAGERS) == PACKAGE_FORMATS

#: A consent callback: ``(url, target_path) -> True`` to download a file
#: whose SHA-256 matches the recorded one, or the string ``"unverified"`` to
#: also accept a file whose digest differs (a newer upstream build the user
#: chose to trust); anything else refuses.
Consent = Callable[[str, str], Union[bool, str]]
UNVERIFIED = "unverified"


class UnknownFormatError(KeyError):
    pass


def packager_names() -> List[str]:
    return list(_PACKAGERS)


def get_packager(name: str) -> Packager:
    try:
        return _PACKAGERS[name]
    except KeyError:
        raise UnknownFormatError(name) from None


def formats_for(platform: Optional[str] = None) -> List[str]:
    """The formats a build on ``platform`` (default: this one) can produce."""
    return [name for name in _PACKAGERS if is_supported(name, platform)]


def spec_from_project(project, built: str, version: str, out_dir: str,
                      sign_identity: str = "") -> PackageSpec:
    """A ``PackageSpec`` from the project file's sections.

    ``[packaging]`` wins; what it leaves empty falls back to Version Info and
    the installer tab, which already hold a publisher and a description.
    """
    build = project.build
    packaging = project.packaging
    repository = (project.release.repository or "").strip()
    identifier = packaging.identifier.strip()
    if not identifier and "/" in repository:
        owner, _name = repository.split("/", 1)
        identifier = f"io.github.{slug(owner)}.{slug(project.display_name() or 'app')}"
    return PackageSpec(
        name=project.display_name() or build_name(build) or "app",
        version=version,
        built=built,
        exe_name=os.path.basename(build_name(build)),
        icon=build.icon,
        description=packaging.description.strip() or project.version_info.file_description,
        maintainer=packaging.maintainer.strip() or project.version_info.company_name,
        homepage=packaging.homepage.strip() or project.installer.publisher_url,
        categories=packaging.categories or "Utility",
        identifier=identifier,
        license=project.release.winget.license,
        windowed=bool(build.windowed or build.noconsole),
        out_dir=out_dir,
        section=packaging.deb_section or "utils",
        depends=packaging.deb_depends,
        sign_identity=sign_identity,
    )


def preflight(spec: PackageSpec, formats: Sequence[str], platform: Optional[str] = None,
              env: Optional[dict] = None) -> Dict[str, list]:
    """Findings per format, before anything is staged."""
    return {name: get_packager(name).check(spec, platform, env) for name in formats}


def run_packaging(
    spec: PackageSpec,
    formats: Sequence[str],
    log: Log = lambda _m: None,
    runner: Runner = subprocess.run,
    platform: Optional[str] = None,
    env: Optional[dict] = None,
    download_consent: Optional[Consent] = None,
    downloader: Callable = download_appimagetool,
) -> List[PackageResult]:
    """Build every format in ``formats`` that this host can; one result each.

    ``appimagetool`` (and the runtime file it embeds) is fetched only when it
    is missing **and** ``download_consent(url, tools_dir)`` returns True (or
    ``"unverified"``, which also accepts a download whose SHA-256 differs
    from the recorded one); without a callback the AppImage is reported as
    blocked, never downloaded.
    """
    plat = resolve(platform)
    results = []
    for name in formats:
        packager = get_packager(name)
        findings = packager.check(spec, plat, env)
        blocking = errors_in(findings)
        if (blocking and isinstance(packager, AppImagePackager)
                and all(f.code == "appimagetool_missing" for f in blocking)):
            url = appimagetool_url(spec.machine())
            consent = download_consent(url, packager.tools_dir) if download_consent else False
            if consent is True or consent == UNVERIFIED:
                try:
                    path, digest, matches = downloader(packager.tools_dir, log, spec.machine(),
                                                       env=env,
                                                       allow_unverified=consent == UNVERIFIED)
                except (OSError, ValueError) as e:
                    results.append(PackageResult(name, False, error_code="appimagetool_download_failed",
                                                 error=str(e), findings=findings))
                    continue
                if matches is False:
                    log(f"appimagetool: sha256 {digest} differs from the one recorded when "
                        f"this version was written (a newer continuous build)")
                env = dict(os.environ if env is None else env)
                env["APPIMAGETOOL"] = path
                blocking = []
        if blocking:
            results.append(PackageResult(name, False, error_code=blocking[0].code,
                                         error=", ".join(f.code for f in blocking),
                                         findings=findings))
            continue
        result = packager.build(spec, log, runner, env)
        result.findings = [f for f in findings if f.severity != "error"] + result.findings
        results.append(result)
    return results


__all__ = [
    "STAGING_DIR",
    "AppImagePackager",
    "DebPackager",
    "DmgPackager",
    "Packager",
    "PackageResult",
    "PackageSpec",
    "UnknownFormatError",
    "formats_for",
    "get_packager",
    "packager_names",
    "preflight",
    "run_packaging",
    "spec_from_project",
]
