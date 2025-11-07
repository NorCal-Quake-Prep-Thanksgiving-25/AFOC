from setuptools import setup, find_packages

setup(
    name='afoc-ml-engine',
    version='1.0.0',
    description='AFOC ML Engine',
    packages=find_packages(),
    install_requires=[
        'flask>=3.0.0',
        'numpy>=1.26.2',
        'pandas>=2.1.4',
        'scikit-learn>=1.3.2',
    ],
    python_requires='>=3.11',
)
