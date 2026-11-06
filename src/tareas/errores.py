class TareasError(Exception):
    codigo_salida = 1


class ConfigError(TareasError):
    codigo_salida = 3


class AccionNoValida(ConfigError):
    pass


class AccionNoEncontrada(TareasError):
    codigo_salida = 2


class IAUnavailableError(TareasError):
    pass
