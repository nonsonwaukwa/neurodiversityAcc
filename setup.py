from setuptools import setup, find_packages

setup(
    name="neurodiversity-acc",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'flask>=3.1.0',
        'firebase-admin>=6.7.0',
        'firebase-functions>=0.1.0',
        'functions-framework>=3.8.2',
        'google-cloud-firestore>=2.20.1',
        'flask-cors>=5.0.1',
        'python-dotenv>=1.0.0',
        'requests>=2.31.0',
        'gunicorn>=21.2.0',
    ],
    python_requires='>=3.12',
) 