import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='librus_tricks',
    version='0.9.2',
    url='',
    license='MIT',
    author='Backdoorek, kosiacek',
    author_email='kosiacek@protonmail.com',
    description='A python wrapper of Librus API ',
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    install_requires=[
            'requests', 'beautifulsoup4', 'SQLAlchemy'
        ],
        extras_require={
            'tools': ['Flask', 'PrettyTable']
    },
)
