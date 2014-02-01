#!/usr/bin/env python

from distutils.core import setup

setup(name='django-openid-celauth',
      version='1.6.0',
      install_requires=['Django>=1.6', 'python-openid>=2.2', 'South>=0.8'],
      description='Claimed Email Login Authentication with OpenID and Django',
      keywords='django, openid',
      author='Castedo Ellerman',
      author_email='castedo@castedo.com',
      url='http://www.castedo.com/',
      license='MIT',
      packages=['celauth',
                'celauth.dj',
                'celauth.dj.celauth',
                'celauth.dj.celauth.migrations',
               ],
      package_data={'celauth.dj.celauth': ['templates/celauth/*']},
      classifiers=['Development Status :: 2 - Pre-Alpha',
                   'Environment :: Web Environment',
                   'Intended Audience :: Developers',
                   'Framework :: Django',
                   'Programming Language :: Python',
                   'Programming Language :: Python :: 2.6',
                   'Programming Language :: Python :: 2.7',
                   'License :: OSI Approved :: MIT License',
                  ],
)

