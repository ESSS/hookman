from hookman.hooks import HookSpecs


def friction_factor(v1: "int", v2: "double[2]") -> "int":
    """
    Docs for Friction Factor
        Input:
            Testing indentation
        Return:
                Integer
    """


specs = HookSpecs(
    project_name="ACME", version="1", pyd_name="_test_hook_man_generator", hooks=[friction_factor]
)
