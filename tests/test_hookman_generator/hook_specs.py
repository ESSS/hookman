from hookman.hooks import HookSpecs


def friction_factor(v1: "int", v2: "double[2]") -> "int":
    """
    Docs for Friction Factor
        Input:
            Testing indentation
        Return:
                Integer
    """


def friction_factor_2(v1: "int", v2: "double[2]") -> "int":
    """
    Docs for Friction Factor 2
        Input:
            Testing indentation
        Return:
                Integer

    Same signature as 'friction_factor' for testing.
    """


specs = HookSpecs(
    project_name="ACME",
    version="1",
    pyd_name="_test_hook_man_generator",
    hooks=[friction_factor, friction_factor_2],
    extra_includes=["custom_include1", "custom_include2"],
)
