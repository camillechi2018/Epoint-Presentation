"""Select assembly independently from rendering and delivery acceptance."""
import platform

BACKENDS = ('auto', 'native', 'powerpoint')


def select_backend(requested='auto', *, legacy_native=False, system=None):
    if requested not in BACKENDS:
        raise ValueError('ASSEMBLY_BACKEND_UNKNOWN')
    if legacy_native:
        if requested == 'powerpoint':
            raise ValueError('ASSEMBLY_BACKEND_CONFLICT')
        return 'native'
    if requested != 'auto':
        return requested
    system = platform.system() if system is None else system
    if system == 'Windows':
        return 'powerpoint'
    if system in ('Darwin', 'Linux'):
        return 'native'
    raise ValueError('ASSEMBLY_PLATFORM_UNSUPPORTED')
