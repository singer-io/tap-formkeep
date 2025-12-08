

from setuptools import setup, find_packages


setup(name="tap-formkeep",
      version="0.0.1",
      description="Singer.io tap for extracting data from formkeep API",
      author="Stitch",
      url="http://singer.io",
      classifiers=["Programming Language :: Python :: 3 :: Only"],
      py_modules=["tap_formkeep"],
      install_requires=[
        "singer-python==6.3.0",
        "requests==2.32.5",
        "backoff==2.2.1"
      ],
      extras_require={'dev': ['parameterized']},
      entry_points="""
          [console_scripts]
          tap-formkeep=tap_formkeep:main
      """,
      packages=find_packages(),
      package_data = {
          "tap_formkeep": ["schemas/*.json"],
      },
      include_package_data=True,
)
