from hookman.hooks import HooksSpecs


def friction_factor(v1: 'int', v2: 'int') -> 'int':
    """
    Docs for Friction Factor
    """


specs = HooksSpecs(
    project_name='ACME',
    version='1',
    pyd_name='_test_hooks',
    hooks=[
        friction_factor,
    ]
)
