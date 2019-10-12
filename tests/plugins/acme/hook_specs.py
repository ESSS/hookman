from hookman.hooks import HookSpecs


def friction_factor(v1: "int", v2: "int") -> "int":
    """
    Docs for Friction Factor
    """


def friction_factor_2(v1: "int", v2: "int") -> "int":
    """
    Docs for Friction Factor

    Just to test a duplicated signature
    """


def env_temperature(v3: "float", v4: "float") -> "float":
    """
    Docs for Environment Temperature
    """


specs = HookSpecs(
    project_name="ACME",
    version="1",
    pyd_name="_simple",
    hooks=[friction_factor, friction_factor_2, env_temperature],
)
