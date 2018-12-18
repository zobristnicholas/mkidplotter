from setuptools import setup, find_packages

setup(name='mkidplotter',
      version='0.1',
      description='Plotting and GUI tools for analyzing MKID data',
      url='http://github.com/zobristnicholas/mkidplotter',
      author='Nicholas Zobrist',
      license='GNU GPLv3',
      packages=find_packages(),
      install_requires=["pymeasure",
                        "numpy",
                        "pyqtgraph",
                        "cycler",
                        "pytest"],
      zip_safe=False)
