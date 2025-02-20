from setuptools import setup, find_packages

# Read the long description from README.md using a context manager.
with open('README.md', encoding='utf-8') as fh:
    long_description = fh.read()

setup(
    name='project_name',             # Replace with your library's name
    version='0.1.0',                 # Update the version as needed
    packages=find_packages(),        # Automatically find packages in the directory
    install_requires=[               # List your project dependencies here
        # 'requests>=2.25.1',        (uncomment and add dependencies as required)
    ],
    author='Your Name',
    author_email='your.email@example.com',
    description='A brief description of your library.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/xironix/libgfd',  # Change to your project's homepage
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',  # Change if needed
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',  # Change to the Python versions you support
) 