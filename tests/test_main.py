import pytest

from gui_mikroptim.__main__ import APP, build_argv


def test_build_argv_binds_localhost():
    argv = build_argv(["--server.port", "8502"])
    assert argv[:3] == ["streamlit", "run", str(APP)]
    i = argv.index("--server.address")
    assert argv[i + 1] == "127.0.0.1"
    assert argv[-2:] == ["--server.port", "8502"]
    assert APP.is_file()


@pytest.mark.parametrize("arg", ["--server.address=0.0.0.0", "--server.address"])
def test_build_argv_rejects_other_address(arg: str):
    with pytest.raises(SystemExit):
        build_argv([arg, "0.0.0.0"])
