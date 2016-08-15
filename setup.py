import setuptools

setuptools.setup(
    name='milight-controller',
    version='1.0',
    description='Controller for MiLight RGB lights',
    long_description='See GitHub for extra info: https://github.com/jdah/milight-controller',
    url='https://github.com/jdah/milight-controller',
    author='jdah',
    author_email='jh@jhenriksen.net',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Home Automation',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ],
    keywords='milight wifi led',
    packages=["milight_controller"],
    install_requires=[]
)