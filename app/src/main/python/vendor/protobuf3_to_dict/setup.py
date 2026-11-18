from setuptools import setup

setup(
    name="protobuf3-to-dict",
    version="0.1.5",
    description="Pure-Python compatibility package",
    py_modules=["protobuf3_to_dict"],
    install_requires=["protobuf>=3.19.4"],
    python_requires=">=3.10",
)
